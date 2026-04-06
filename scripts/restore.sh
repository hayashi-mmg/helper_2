#!/usr/bin/env bash
# =============================================================================
# restore.sh - データベースリストア
# =============================================================================
# 概要: PostgreSQLバックアップからのリストアを実行する。
#       リストア前に現在の状態を自動バックアップし、安全にリストアする。
#
# 使い方:
#   ./scripts/restore.sh -f backups/db/backup_helper_production_20260401_020000.sql.gz
#   ./scripts/restore.sh -f backups/db/backup_helper_production_20260401_020000.sql.gz --yes
#   ./scripts/restore.sh -f latest --yes
#
# 依存: docker compose, gzip
# =============================================================================
set -euo pipefail

# --- 定数 ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
BACKUP_DIR="/backups"
LOG_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
AUTO_CONFIRM=0
BACKUP_FILE=""

# DB設定読み込み
if [ -f "$PROJECT_DIR/.env" ]; then
    POSTGRES_USER=$(grep '^POSTGRES_USER=' "$PROJECT_DIR/.env" | cut -d= -f2)
    POSTGRES_DB=$(grep '^POSTGRES_DB=' "$PROJECT_DIR/.env" | cut -d= -f2)
else
    echo "[$LOG_TIMESTAMP] ERROR: .env ファイルが見つかりません: $PROJECT_DIR/.env"
    exit 1
fi

# --- カラー出力 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[$LOG_TIMESTAMP][INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[$LOG_TIMESTAMP][OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[$LOG_TIMESTAMP][WARN]${NC} $1"; }
err()   { echo -e "${RED}[$LOG_TIMESTAMP][ERROR]${NC} $1"; }

# --- 使い方 ---
show_usage() {
    echo "データベースリストアスクリプト"
    echo ""
    echo "使い方: $0 -f <バックアップファイル> [--yes]"
    echo ""
    echo "オプション:"
    echo "  -f <file>    リストアするバックアップファイル（.sql.gz）"
    echo "               'latest' を指定すると最新のバックアップを使用"
    echo "  --yes        確認プロンプトをスキップ"
    echo ""
    echo "例:"
    echo "  $0 -f backups/db/backup_helper_production_20260401_020000.sql.gz"
    echo "  $0 -f latest --yes"
}

# --- 引数パース ---
while [ $# -gt 0 ]; do
    case "$1" in
        -f)
            BACKUP_FILE="$2"
            shift 2
            ;;
        --yes)
            AUTO_CONFIRM=1
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            err "不明なオプション: $1"
            show_usage
            exit 1
            ;;
    esac
done

if [ -z "$BACKUP_FILE" ]; then
    err "バックアップファイルを指定してください (-f オプション)"
    show_usage
    exit 1
fi

# --- 'latest' 解決 ---
if [ "$BACKUP_FILE" = "latest" ]; then
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/db/backup_*.sql.gz 2>/dev/null | head -1 || true)
    if [ -z "$BACKUP_FILE" ]; then
        err "バックアップファイルが見つかりません: $BACKUP_DIR/db/"
        exit 1
    fi
    info "最新バックアップを使用: $BACKUP_FILE"
fi

# --- バックアップファイル検証 ---
if [ ! -f "$BACKUP_FILE" ]; then
    err "ファイルが見つかりません: $BACKUP_FILE"
    exit 1
fi

# gzip 整合性チェック
info "バックアップファイルの整合性を確認中..."
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
    err "バックアップファイルが破損しています: $BACKUP_FILE"
    exit 1
fi
ok "バックアップファイルの整合性: OK"

# ファイル情報表示
local_size=$(du -h "$BACKUP_FILE" | cut -f1)
local_date=$(stat -c%y "$BACKUP_FILE" 2>/dev/null | cut -d. -f1)
info "ファイル: $BACKUP_FILE"
info "サイズ: $local_size"
info "作成日: $local_date"

# --- 確認プロンプト ---
if [ $AUTO_CONFIRM -eq 0 ]; then
    echo ""
    warn "=========================================="
    warn "  データベース '$POSTGRES_DB' をリストアします"
    warn "  現在のデータは上書きされます"
    warn "=========================================="
    echo ""
    read -r -p "続行しますか? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        info "リストアをキャンセルしました"
        exit 0
    fi
fi

# --- リストア前バックアップ ---
info "リストア前に現在の状態をバックアップ中..."
pre_restore_file="$BACKUP_DIR/db/pre_restore_${POSTGRES_DB}_$(date +%Y%m%d_%H%M%S).sql.gz"
mkdir -p "$BACKUP_DIR/db"

docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=plain \
    | gzip > "$pre_restore_file" 2>/dev/null || {
    warn "リストア前バックアップの作成に失敗（新規DBの可能性）"
}

if [ -f "$pre_restore_file" ]; then
    local pre_size
    pre_size=$(du -h "$pre_restore_file" | cut -f1)
    ok "リストア前バックアップ: $pre_restore_file ($pre_size)"
fi

# --- 既存接続の切断 ---
info "既存のDB接続を切断中..."
docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U "$POSTGRES_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();" \
    > /dev/null 2>&1 || true

# --- データベース再作成 ---
info "データベースを再作成中..."
docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U "$POSTGRES_USER" -d postgres -c \
    "DROP DATABASE IF EXISTS $POSTGRES_DB;" > /dev/null 2>&1

docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U "$POSTGRES_USER" -d postgres -c \
    "CREATE DATABASE $POSTGRES_DB WITH ENCODING 'UTF8' LC_COLLATE='ja_JP.UTF-8' LC_CTYPE='ja_JP.UTF-8';" \
    > /dev/null 2>&1 || {
    # ja_JP.UTF-8 が無い場合のフォールバック
    docker compose -f "$COMPOSE_FILE" exec -T db \
        psql -U "$POSTGRES_USER" -d postgres -c \
        "CREATE DATABASE $POSTGRES_DB WITH ENCODING 'UTF8';" > /dev/null 2>&1
}

ok "データベース再作成完了"

# --- リストア実行 ---
info "バックアップからリストア中..."
gunzip -c "$BACKUP_FILE" | \
    docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1

ok "リストア完了"

# --- マイグレーション実行 ---
info "Alembicマイグレーションを確認中..."
docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head 2>/dev/null || {
    warn "Alembicマイグレーションをスキップ（backendサービス未起動の可能性）"
}

# --- リストア後の検証 ---
info "リストア後の検証中..."

# テーブル数確認
table_count=$(docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")

# 主要テーブルのレコード数
info "テーブル数: $table_count"

docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
    "SELECT 'users' AS table_name, COUNT(*) AS count FROM users
     UNION ALL SELECT 'recipes', COUNT(*) FROM recipes
     UNION ALL SELECT 'weekly_menus', COUNT(*) FROM weekly_menus;" 2>/dev/null || {
    warn "レコード数の確認に失敗（テーブルが存在しない可能性）"
}

# --- 完了 ---
echo ""
ok "=========================================="
ok "  リストア完了"
ok "  データベース: $POSTGRES_DB"
ok "  ソース: $(basename "$BACKUP_FILE")"
ok "  テーブル数: $table_count"
ok "=========================================="
echo ""
info "リストア前バックアップ: $pre_restore_file"
info "問題がある場合は以下でロールバック可能:"
info "  $0 -f $pre_restore_file --yes"
