#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
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

    # SSL証明書チェック
    if [ ! -f nginx/ssl/fullchain.pem ] || [ ! -f nginx/ssl/privkey.pem ]; then
        warn "SSL証明書が見つかりません。以下のコマンドで取得してください:"
        echo ""
        echo "  sudo certbot certonly --standalone -d h.kokoro-shift.jp"
        echo "  sudo cp /etc/letsencrypt/live/h.kokoro-shift.jp/fullchain.pem nginx/ssl/"
        echo "  sudo cp /etc/letsencrypt/live/h.kokoro-shift.jp/privkey.pem nginx/ssl/"
        echo "  chmod 600 nginx/ssl/*.pem"
        echo ""
        warn "SSL証明書を配置後、再度 ./deploy.sh init を実行してください"
        return 1
    fi
    ok "SSL証明書を確認しました"

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
    docker compose -f "$COMPOSE_FILE" up -d --no-deps --build nginx
    ok "再起動完了"

    sleep 5
    do_status

    echo ""
    ok "=== アップデートデプロイ完了 ==="
}

# --- ステータス確認 ---
do_status() {
    info "=== サービス状態 ==="
    docker compose -f "$COMPOSE_FILE" ps
    echo ""

    info "=== ヘルスチェック ==="
    if curl -sf http://localhost/api/v1/health 2>/dev/null; then
        echo ""
        ok "Backend API: 正常"
    else
        # SSL経由を試行
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
    if [ -n "$service" ]; then
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
    info "全サービスを停止中..."
    docker compose -f "$COMPOSE_FILE" down
    ok "全サービス停止完了"
}

# --- ヘルプ ---
show_usage() {
    echo "ホームヘルパー管理システム - デプロイスクリプト"
    echo ""
    echo "使い方: ./deploy.sh <コマンド> [オプション]"
    echo ""
    echo "コマンド:"
    echo "  init              初回セットアップ (環境変数生成、ビルド、マイグレーション、起動)"
    echo "  update            アップデートデプロイ (pull、ビルド、マイグレーション、再起動)"
    echo "  status            サービス状態・ヘルスチェック確認"
    echo "  logs [service]    ログ確認 (service省略で全サービス)"
    echo "  backup            データベースバックアップ"
    echo "  stop              全サービス停止"
    echo ""
    echo "例:"
    echo "  ./deploy.sh init            # 初回セットアップ"
    echo "  ./deploy.sh update          # コード更新後のデプロイ"
    echo "  ./deploy.sh logs backend    # バックエンドログ確認"
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
