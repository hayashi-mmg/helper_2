#!/usr/bin/env bash
# =============================================================================
# verify-backup-tables.sh - バックアップ対象テーブル網羅性チェック
# =============================================================================
# 概要: 直近の pg_dump 結果に必須テーブルが含まれているか検証する。
#       新機能で追加されたテーブル (themes, user_preferences 等) や
#       法令対応上必須のテーブル (data_access_logs 等) の組込みを担保する。
#
# Cronジョブ (月次):
#   0 3 1 * * /opt/helper-system/scripts/verify-backup-tables.sh \
#       >> /var/log/helper-backup-verify.log 2>&1
#
# 終了コード:
#   0  全必須テーブルが含まれる
#   1  不足テーブルあり / 検証エラー
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
DB_BACKUP_DIR="${BACKUP_DIR}/db"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 必須テーブル一覧
# - 新機能テーブル: themes, user_preferences (2026年Q1追加)
# - 法令対応 (改正個人情報保護法): audit_logs, data_access_logs, compliance_logs
# - コア業務テーブル: users, recipes, weekly_menus, tasks, messages,
#                     shopping_requests, pantry_items, qr_tokens, notifications
REQUIRED_TABLES=(
    users
    recipes
    weekly_menus
    tasks
    messages
    shopping_requests
    pantry_items
    qr_tokens
    notifications
    audit_logs
    data_access_logs
    compliance_logs
    themes
    user_preferences
)

# --- カラー出力 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[$TIMESTAMP][INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[$TIMESTAMP][OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[$TIMESTAMP][WARN]${NC} $1"; }
err()   { echo -e "${RED}[$TIMESTAMP][ERROR]${NC} $1"; }

# 失敗通知ヘルパ
notify_failure() {
    local detail="$1"
    if [ -x "$SCRIPT_DIR/backup-notify.sh" ]; then
        "$SCRIPT_DIR/backup-notify.sh" failure "バックアップ網羅性検証" "$detail"
    fi
}

main() {
    info "=== バックアップ対象テーブル網羅性チェック ==="

    # 最新のDBダンプを特定
    local latest_dump
    latest_dump=$(ls -t "$DB_BACKUP_DIR"/backup_*.sql.gz 2>/dev/null | head -1 || true)

    if [ -z "$latest_dump" ]; then
        err "DBバックアップファイルが見つかりません: $DB_BACKUP_DIR"
        notify_failure "DBバックアップファイル未検出"
        exit 1
    fi

    info "検証対象: $(basename "$latest_dump")"

    # gzip整合性
    if ! gzip -t "$latest_dump" 2>/dev/null; then
        err "gzipファイルが破損しています: $latest_dump"
        notify_failure "gzip破損: $(basename "$latest_dump")"
        exit 1
    fi

    # 含まれるテーブル一覧を抽出 (CREATE TABLE 行)
    local found_tables
    found_tables=$(gunzip -c "$latest_dump" \
        | grep -oE '^CREATE TABLE (public\.)?[a-zA-Z_][a-zA-Z0-9_]*' \
        | sed -E 's/^CREATE TABLE (public\.)?//' \
        | sort -u)

    local missing=()
    for table in "${REQUIRED_TABLES[@]}"; do
        if ! echo "$found_tables" | grep -qx "$table"; then
            missing+=("$table")
        fi
    done

    if [ ${#missing[@]} -eq 0 ]; then
        ok "全 ${#REQUIRED_TABLES[@]} 必須テーブルが含まれています"
        info "検出テーブル数: $(echo "$found_tables" | wc -l)"
    else
        err "不足テーブル: ${missing[*]}"
        err "REQUIRED_TABLES の更新、または backup.sh の pg_dump 設定確認が必要"
        notify_failure "不足テーブル: ${missing[*]}"
        exit 1
    fi

    ok "=== 検証完了 ==="
}

main "$@"
