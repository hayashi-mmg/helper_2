#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
TRAEFIK_COMPOSE_FILE="traefik/docker-compose.yml"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# --- カラー出力 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

# --- 前提条件チェック ---
check_prerequisites() {
    local missing=0
    for cmd in docker git openssl curl; do
        if ! command -v "$cmd" &>/dev/null; then
            err "$cmd が見つかりません。インストールしてください。"
            missing=1
        fi
    done
    if ! docker compose version &>/dev/null; then
        err "Docker Compose V2 が見つかりません。"
        missing=1
    fi
    if [ "$missing" -eq 1 ]; then
        exit 1
    fi
    ok "前提条件チェック完了"
}

# --- Traefikネットワーク・起動 ---
ensure_traefik() {
    # proxy ネットワーク作成（存在しない場合）
    if ! docker network inspect proxy &>/dev/null; then
        info "proxy ネットワークを作成中..."
        docker network create proxy
        ok "proxy ネットワーク作成完了"
    fi

    # Traefik起動確認
    if ! docker ps --format '{{.Names}}' | grep -q '^traefik$'; then
        info "Traefikを起動中..."
        docker compose -f "$TRAEFIK_COMPOSE_FILE" up -d
        ok "Traefik起動完了"
    else
        ok "Traefikは既に稼働中です"
    fi
}

# --- 初回セットアップ ---
do_init() {
    info "=== 初回デプロイセットアップ ==="
    check_prerequisites

    # .env 生成
    if [ ! -f .env ]; then
        info ".env ファイルを生成中..."
        cp .env.production.example .env

        POSTGRES_PASSWORD=$(openssl rand -hex 16)
        REDIS_PASSWORD=$(openssl rand -hex 16)
        JWT_SECRET_KEY=$(openssl rand -hex 32)

        sed -i "s/CHANGE_ME_openssl_rand_hex_16/${POSTGRES_PASSWORD}/" .env
        # Redis用パスワード (2番目の出現)
        sed -i "0,/CHANGE_ME_openssl_rand_hex_16/s/CHANGE_ME_openssl_rand_hex_16/$(openssl rand -hex 16)/" .env
        sed -i "s/CHANGE_ME_openssl_rand_hex_32/${JWT_SECRET_KEY}/" .env

        chmod 600 .env
        ok ".env ファイルを生成しました"
        warn "必ず .env のドメイン設定 (DOMAIN, CORS_ORIGINS) を編集してください"
        warn "  nano .env"
    else
        ok ".env ファイルは既に存在します"
    fi

    # Traefik起動
    ensure_traefik

    # イメージビルド
    info "Dockerイメージをビルド中..."
    docker compose -f "$COMPOSE_FILE" build
    ok "ビルド完了"

    # DB & Redis 起動
    info "データベースとRedisを起動中..."
    docker compose -f "$COMPOSE_FILE" up -d db redis

    info "データベースの起動を待機中..."
    local retries=0
    while [ $retries -lt 30 ]; do
        if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "$(grep POSTGRES_USER .env | cut -d= -f2)" &>/dev/null; then
            break
        fi
        retries=$((retries + 1))
        sleep 2
    done

    if [ $retries -ge 30 ]; then
        err "データベースの起動がタイムアウトしました"
        exit 1
    fi
    ok "データベース起動完了"

    # マイグレーション
    info "データベースマイグレーションを実行中..."
    docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head
    ok "マイグレーション完了"

    # 全サービス起動
    info "全サービスを起動中..."
    docker compose -f "$COMPOSE_FILE" up -d
    ok "全サービス起動完了"

    sleep 5
    do_status

    echo ""
    ok "=== 初回デプロイ完了 ==="
}

# --- アップデートデプロイ ---
do_update() {
    info "=== アップデートデプロイ ==="
    check_prerequisites

    if [ ! -f .env ]; then
        err ".env ファイルが見つかりません。先に ./deploy.sh init を実行してください。"
        exit 1
    fi

    # Traefik確認
    ensure_traefik

    # 最新コード取得
    info "最新コードを取得中..."
    git pull origin "$(git branch --show-current)"
    ok "コード取得完了"

    # イメージ再ビルド
    info "Dockerイメージを再ビルド中..."
    docker compose -f "$COMPOSE_FILE" build
    ok "ビルド完了"

    # マイグレーション
    info "データベースマイグレーションを確認中..."
    docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head
    ok "マイグレーション完了"

    # ローリング再起動
    info "サービスを再起動中..."
    docker compose -f "$COMPOSE_FILE" up -d --no-deps --build backend
    docker compose -f "$COMPOSE_FILE" up -d --no-deps --build frontend
    ok "再起動完了"

    sleep 5
    do_status

    echo ""
    ok "=== アップデートデプロイ完了 ==="
}

# --- ステータス確認 ---
do_status() {
    info "=== Traefik状態 ==="
    docker ps --filter "name=traefik" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true
    echo ""

    info "=== サービス状態 ==="
    docker compose -f "$COMPOSE_FILE" ps
    echo ""

    info "=== ヘルスチェック ==="
    if curl -sf http://localhost/api/v1/health 2>/dev/null; then
        echo ""
        ok "Backend API: 正常"
    else
        if curl -sfk https://localhost/api/v1/health 2>/dev/null; then
            echo ""
            ok "Backend API: 正常 (HTTPS)"
        else
            warn "Backend API: ヘルスチェック失敗 (起動中の可能性があります)"
        fi
    fi
    echo ""

    info "=== リソース使用量 ==="
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null || true
}

# --- ログ確認 ---
do_logs() {
    local service="${1:-}"
    if [ "$service" = "traefik" ]; then
        docker logs -f --tail=100 traefik
    elif [ -n "$service" ]; then
        docker compose -f "$COMPOSE_FILE" logs -f --tail=100 "$service"
    else
        docker compose -f "$COMPOSE_FILE" logs -f --tail=100
    fi
}

# --- バックアップ ---
do_backup() {
    info "=== データベースバックアップ ==="
    local backup_dir="backups"
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$backup_dir"

    local db_name
    db_name=$(grep POSTGRES_DB .env | cut -d= -f2)
    local db_user
    db_user=$(grep POSTGRES_USER .env | cut -d= -f2)

    info "バックアップを作成中..."
    docker compose -f "$COMPOSE_FILE" exec -T db \
        pg_dump -U "$db_user" -d "$db_name" --format=custom \
        > "${backup_dir}/db_${timestamp}.dump"

    ok "バックアップ完了: ${backup_dir}/db_${timestamp}.dump"
    info "バックアップサイズ: $(du -h "${backup_dir}/db_${timestamp}.dump" | cut -f1)"
}

# --- 停止 ---
do_stop() {
    info "アプリサービスを停止中..."
    docker compose -f "$COMPOSE_FILE" down
    ok "アプリサービス停止完了"
    warn "Traefikは停止していません。停止する場合: docker compose -f $TRAEFIK_COMPOSE_FILE down"
}

# --- ヘルプ ---
show_usage() {
    echo "ホームヘルパー管理システム - デプロイスクリプト"
    echo ""
    echo "使い方: ./deploy.sh <コマンド> [オプション]"
    echo ""
    echo "コマンド:"
    echo "  init              初回セットアップ (環境変数生成、Traefik起動、ビルド、マイグレーション、起動)"
    echo "  update            アップデートデプロイ (pull、ビルド、マイグレーション、再起動)"
    echo "  status            サービス状態・ヘルスチェック確認"
    echo "  logs [service]    ログ確認 (service省略で全サービス、traefik指定でTraefikログ)"
    echo "  backup            データベースバックアップ"
    echo "  stop              アプリサービス停止 (Traefikは維持)"
    echo ""
    echo "例:"
    echo "  ./deploy.sh init            # 初回セットアップ"
    echo "  ./deploy.sh update          # コード更新後のデプロイ"
    echo "  ./deploy.sh logs backend    # バックエンドログ確認"
    echo "  ./deploy.sh logs traefik    # Traefikログ確認"
    echo "  ./deploy.sh backup          # DBバックアップ"
}

# --- メイン ---
case "${1:-}" in
    init)   do_init ;;
    update) do_update ;;
    status) do_status ;;
    logs)   do_logs "${2:-}" ;;
    backup) do_backup ;;
    stop)   do_stop ;;
    *)      show_usage ;;
esac
