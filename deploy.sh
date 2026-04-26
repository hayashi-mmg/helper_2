#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
TRAEFIK_COMPOSE_FILE="traefik/docker-compose.yml"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
DC="docker compose --env-file $ENV_FILE -f $COMPOSE_FILE"

DEPLOY_HISTORY="$PROJECT_DIR/.deploy-history"
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup.sh"
NOTIFY_SCRIPT="$PROJECT_DIR/scripts/backup-notify.sh"

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

# --- デプロイ通知 ---
# backup-notify.sh を流用し Slack/メールに送信。
# notify_deploy success|failure "<title>" "<detail>"
notify_deploy() {
    local status="$1"
    local title="$2"
    local detail="$3"
    if [ -x "$NOTIFY_SCRIPT" ]; then
        "$NOTIFY_SCRIPT" "$status" "$title" "$detail" || true
    fi
}

# --- デプロイ履歴 ---
# .deploy-history への追記。rollback対象の特定に使用。
# format: "<unix_ts> <iso_ts> <event> <git_sha> <branch> <message>"
record_deploy_event() {
    local event="$1"   # update_start | update_success | update_failure | rollback
    local message="$2"
    local sha
    sha=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    local branch
    branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    local ts_unix
    ts_unix=$(date +%s)
    local ts_iso
    ts_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$ts_unix" "$ts_iso" "$event" "$sha" "$branch" "$message" \
        >> "$DEPLOY_HISTORY"
}

# --- pre-deploy セーフティチェック ---
# uncommitted変更検出、リモートとの差分、ブランチ名を返す。
# update実行前の必須チェック。--force で警告のみに格下げ可能。
pre_deploy_safety_check() {
    local force="${1:-}"
    local issues=0

    if ! git rev-parse --git-dir &>/dev/null; then
        err "git リポジトリではありません"
        return 1
    fi

    # uncommitted 変更
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        if [ "$force" = "--force" ]; then
            warn "uncommitted な変更があります (--force で続行)"
        else
            err "uncommitted な変更があります。コミットまたは stash してください。"
            err "  git status"
            err "  強行する場合: ./deploy.sh update --force"
            issues=$((issues + 1))
        fi
    fi

    # 現在のブランチ
    local branch
    branch=$(git branch --show-current 2>/dev/null || echo "")
    if [ -z "$branch" ]; then
        warn "detached HEAD 状態です"
    else
        info "現在のブランチ: $branch"
    fi

    # 現在のSHA
    local sha
    sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    info "現在のコミット: $sha"

    if [ "$issues" -gt 0 ]; then
        return 1
    fi
    ok "セーフティチェック完了"
}

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
    if [ ! -f "$ENV_FILE" ]; then
        info "$ENV_FILE ファイルを生成中..."
        cp .env.production.example "$ENV_FILE"

        POSTGRES_PASSWORD=$(openssl rand -hex 16)
        REDIS_PASSWORD=$(openssl rand -hex 16)
        JWT_SECRET_KEY=$(openssl rand -hex 32)

        sed -i "s/CHANGE_ME_openssl_rand_hex_16/${POSTGRES_PASSWORD}/" "$ENV_FILE"
        # Redis用パスワード (2番目の出現)
        sed -i "0,/CHANGE_ME_openssl_rand_hex_16/s/CHANGE_ME_openssl_rand_hex_16/$(openssl rand -hex 16)/" "$ENV_FILE"
        sed -i "s/CHANGE_ME_openssl_rand_hex_32/${JWT_SECRET_KEY}/" "$ENV_FILE"

        chmod 600 "$ENV_FILE"
        ok "$ENV_FILE ファイルを生成しました"
        warn "必ず $ENV_FILE のドメイン設定 (DOMAIN, CORS_ORIGINS) を編集してください"
        warn "  nano $ENV_FILE"
    else
        ok "$ENV_FILE ファイルは既に存在します"
    fi

    # Traefik起動
    ensure_traefik

    # イメージビルド
    info "Dockerイメージをビルド中..."
    $DC build
    ok "ビルド完了"

    # DB & Redis 起動
    info "データベースとRedisを起動中..."
    $DC up -d db redis

    info "データベースの起動を待機中..."
    local retries=0
    while [ $retries -lt 30 ]; do
        if $DC exec -T db pg_isready -U "$(grep POSTGRES_USER "$ENV_FILE" | cut -d= -f2)" &>/dev/null; then
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
    $DC run --rm backend alembic upgrade head
    ok "マイグレーション完了"

    # 全サービス起動
    info "全サービスを起動中..."
    $DC up -d
    ok "全サービス起動完了"

    sleep 5
    do_status

    echo ""
    ok "=== 初回デプロイ完了 ==="
}

# --- アップデートデプロイ ---
# 流れ: safety check → pre-deploy backup → git pull → build → migrate → restart
# 失敗時は cleanup trap で Slack/メール通知 + 履歴記録。
do_update() {
    local force_flag="${1:-}"
    local skip_backup="${2:-}"

    info "=== アップデートデプロイ ==="
    check_prerequisites

    if [ ! -f "$ENV_FILE" ]; then
        err "$ENV_FILE ファイルが見つかりません。先に ./deploy.sh init を実行してください。"
        exit 1
    fi

    # セーフティチェック
    if ! pre_deploy_safety_check "$force_flag"; then
        notify_deploy failure "デプロイ中止" "セーフティチェック失敗"
        exit 1
    fi

    # 失敗時の通知 trap
    local pre_sha
    pre_sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    record_deploy_event update_start "デプロイ開始 (pre_sha=$pre_sha)"

    update_failure_trap() {
        local exit_code=$?
        if [ $exit_code -ne 0 ]; then
            err "デプロイが失敗しました (exit code: $exit_code)"
            record_deploy_event update_failure "exit=$exit_code, pre_sha=$pre_sha"
            notify_deploy failure "アップデートデプロイ" \
                "exit=$exit_code, pre_sha=$pre_sha, 必要なら ./deploy.sh rollback で復旧"
        fi
    }
    trap update_failure_trap EXIT

    # Traefik確認
    ensure_traefik

    # pre-deploy バックアップ (R2へオフサイト含む)
    if [ "$skip_backup" != "--skip-backup" ] && [ -x "$BACKUP_SCRIPT" ]; then
        info "pre-deploy バックアップを実行中..."
        if "$BACKUP_SCRIPT"; then
            ok "pre-deploy バックアップ完了"
        else
            err "pre-deploy バックアップ失敗。デプロイを中止します。"
            err "  バックアップ無しで強行する場合: ./deploy.sh update --force --skip-backup"
            exit 1
        fi
    elif [ "$skip_backup" = "--skip-backup" ]; then
        warn "--skip-backup 指定: pre-deploy バックアップをスキップ"
    else
        warn "scripts/backup.sh が見つからない or 実行不可。バックアップなしで続行"
    fi

    # 最新コード取得
    info "最新コードを取得中..."
    git pull origin "$(git branch --show-current)"
    ok "コード取得完了"

    local post_sha
    post_sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    info "更新後のコミット: $post_sha (pre: $pre_sha)"

    # イメージ再ビルド
    info "Dockerイメージを再ビルド中..."
    $DC build
    ok "ビルド完了"

    # マイグレーション
    info "データベースマイグレーションを確認中..."
    $DC run --rm backend alembic upgrade head
    ok "マイグレーション完了"

    # ローリング再起動
    info "サービスを再起動中..."
    $DC up -d --no-deps --build backend
    $DC up -d --no-deps --build frontend
    ok "再起動完了"

    sleep 5
    do_status

    # trap解除し成功イベント記録
    trap - EXIT
    record_deploy_event update_success "pre=$pre_sha, post=$post_sha"
    notify_deploy success "アップデートデプロイ" "pre=$pre_sha → post=$post_sha"

    echo ""
    ok "=== アップデートデプロイ完了 ==="
}

# --- ロールバック ---
# .deploy-history から直近の update_start エントリの pre_sha を取得し、
# git checkout → リビルド → 再起動。マイグレーションは互換性確認が必要なため
# 自動 downgrade はせず、警告のみ出して手動対応を促す。
do_rollback() {
    local target_sha="${1:-}"

    info "=== ロールバック ==="
    check_prerequisites

    if [ ! -f "$ENV_FILE" ]; then
        err "$ENV_FILE が見つかりません"
        exit 1
    fi

    # ターゲットSHA決定: 引数指定 or 履歴から直近のpre_sha
    if [ -z "$target_sha" ]; then
        if [ ! -f "$DEPLOY_HISTORY" ]; then
            err "デプロイ履歴 ($DEPLOY_HISTORY) が見つかりません。SHA を引数で指定してください。"
            err "  例: ./deploy.sh rollback abc1234"
            exit 1
        fi
        # 直近の update_start エントリから pre_sha を抽出
        local last_entry
        last_entry=$(grep -E $'\tupdate_start\t' "$DEPLOY_HISTORY" | tail -1 || true)
        if [ -z "$last_entry" ]; then
            err "update_start イベントが履歴にありません。SHA を引数で指定してください。"
            exit 1
        fi
        target_sha=$(echo "$last_entry" | awk -F'\t' '{print $4}')
        if [ -z "$target_sha" ] || [ "$target_sha" = "unknown" ]; then
            err "履歴から有効な SHA を抽出できませんでした"
            exit 1
        fi
    fi

    local current_sha
    current_sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

    info "ロールバック対象: $target_sha (現在: $current_sha)"
    warn "DBマイグレーションは自動 downgrade されません。"
    warn "新規マイグレーション (alembic) が含まれていた場合は手動で downgrade が必要です:"
    warn "  $DC run --rm backend alembic downgrade <revision>"
    warn ""
    warn "5秒後にロールバックを開始します。中止する場合は Ctrl+C..."
    sleep 5

    # uncommitted変更があれば中止
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        err "uncommitted な変更があります。先にコミット/stashしてください。"
        exit 1
    fi

    info "git checkout $target_sha ..."
    git checkout "$target_sha"

    info "Dockerイメージを再ビルド中..."
    $DC build

    info "サービスを再起動中..."
    $DC up -d --no-deps --build backend
    $DC up -d --no-deps --build frontend

    sleep 5
    do_status

    record_deploy_event rollback "from=$current_sha, to=$target_sha"
    notify_deploy success "ロールバック" "from=$current_sha → to=$target_sha (DB downgradeは手動対応)"

    echo ""
    ok "=== ロールバック完了 ==="
    warn "DB スキーマと コード のバージョン整合性を必ず確認してください"
}

# --- デプロイ履歴表示 ---
do_history() {
    local limit="${1:-20}"
    if [ ! -f "$DEPLOY_HISTORY" ]; then
        info "デプロイ履歴はまだありません ($DEPLOY_HISTORY)"
        return 0
    fi
    info "=== 直近 $limit 件のデプロイ履歴 ==="
    printf "%-21s %-16s %-10s %-15s %s\n" "TIMESTAMP" "EVENT" "SHA" "BRANCH" "MESSAGE"
    tail -n "$limit" "$DEPLOY_HISTORY" \
        | awk -F'\t' '{ printf "%-21s %-16s %-10s %-15s %s\n", $2, $3, $4, $5, $6 }'
}

# --- ステータス確認 ---
do_status() {
    info "=== Traefik状態 ==="
    docker ps --filter "name=traefik" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true
    echo ""

    info "=== サービス状態 ==="
    $DC ps
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
        $DC logs -f --tail=100 "$service"
    else
        $DC logs -f --tail=100
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
    db_name=$(grep POSTGRES_DB "$ENV_FILE" | cut -d= -f2)
    local db_user
    db_user=$(grep POSTGRES_USER "$ENV_FILE" | cut -d= -f2)

    info "バックアップを作成中..."
    $DC exec -T db \
        pg_dump -U "$db_user" -d "$db_name" --format=custom \
        > "${backup_dir}/db_${timestamp}.dump"

    ok "バックアップ完了: ${backup_dir}/db_${timestamp}.dump"
    info "バックアップサイズ: $(du -h "${backup_dir}/db_${timestamp}.dump" | cut -f1)"
}

# --- 停止 ---
do_stop() {
    info "アプリサービスを停止中..."
    $DC down
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
    echo "  init                                初回セットアップ"
    echo "                                      (環境変数生成、Traefik起動、ビルド、マイグレーション、起動)"
    echo "  update [--force] [--skip-backup]    アップデートデプロイ"
    echo "                                      (safety check → pre-deploy backup → pull → build → migrate → restart)"
    echo "  rollback [<sha>]                    直前デプロイ前のSHAへ戻す (引数で任意SHA指定可、DB downgradeは手動)"
    echo "  history [<件数>]                    .deploy-history を表示 (デフォルト20件)"
    echo "  status                              サービス状態・ヘルスチェック確認"
    echo "  logs [service]                      ログ確認 (省略で全サービス、traefik 指定でTraefikログ)"
    echo "  backup                              簡易DBバックアップ (scripts/backup.sh の方が推奨)"
    echo "  stop                                アプリサービス停止 (Traefikは維持)"
    echo ""
    echo "例:"
    echo "  ./deploy.sh init                       # 初回セットアップ"
    echo "  ./deploy.sh update                     # 通常デプロイ (バックアップ + Slack通知)"
    echo "  ./deploy.sh update --force             # uncommitted無視で強行"
    echo "  ./deploy.sh update --force --skip-backup  # ホットフィックス時"
    echo "  ./deploy.sh rollback                   # 直前のデプロイへロールバック"
    echo "  ./deploy.sh rollback abc1234           # 特定SHAへロールバック"
    echo "  ./deploy.sh history 10                 # 直近10件のデプロイ履歴"
    echo "  ./deploy.sh logs backend               # バックエンドログ確認"
    echo ""
    echo "通知連携: SLACK_BACKUP_WEBHOOK_URL / BACKUP_ALERT_EMAIL を $ENV_FILE に設定済みなら自動送信"
}

# --- メイン ---
case "${1:-}" in
    init)     do_init ;;
    update)   do_update "${2:-}" "${3:-}" ;;
    rollback) do_rollback "${2:-}" ;;
    history)  do_history "${2:-20}" ;;
    status)   do_status ;;
    logs)     do_logs "${2:-}" ;;
    backup)   do_backup ;;
    stop)     do_stop ;;
    *)        show_usage ;;
esac
