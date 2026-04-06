#!/usr/bin/env bash
# =============================================================================
# backup-logs.sh - 日次ログバックアップ
# =============================================================================
# 概要: アプリケーション運用ログ + DB監査系ログを日次でバックアップし、
#       S3にアップロードする。RPO 24時間目標に対応。
#
# Cronジョブ:
#   30 2 * * * /opt/helper-system/scripts/backup-logs.sh >> /var/log/helper-log-backup.log 2>&1
#
# 依存: docker compose, gzip, (任意) aws cli
# =============================================================================
set -euo pipefail

# --- 定数 ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
BACKUP_DIR="/backups/logs"
LAST_BACKUP_MARKER="/backups/.last-log-backup"
DATE=$(date +%Y%m%d)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
S3_BUCKET="${AWS_S3_BUCKET:-}"

# .env から DB接続情報を読み込む
if [ -f "$PROJECT_DIR/.env" ]; then
    POSTGRES_USER=$(grep '^POSTGRES_USER=' "$PROJECT_DIR/.env" | cut -d= -f2)
    POSTGRES_DB=$(grep '^POSTGRES_DB=' "$PROJECT_DIR/.env" | cut -d= -f2)
else
    echo "[$TIMESTAMP] ERROR: .env ファイルが見つかりません: $PROJECT_DIR/.env"
    exit 1
fi

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

# --- エラーハンドリング ---
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        err "ログバックアップが失敗しました (exit code: $exit_code)"
        if [ -x "$SCRIPT_DIR/backup-notify.sh" ]; then
            "$SCRIPT_DIR/backup-notify.sh" failure "日次ログバックアップ" "exit code: $exit_code"
        fi
    fi
}
trap cleanup EXIT

# --- メイン処理 ---
main() {
    info "=== 日次ログバックアップ開始 ==="

    mkdir -p "$BACKUP_DIR"/{operational,audit,compliance,data-access}

    # 1. アプリケーション運用ログ（差分: 前回バックアップ以降の新規ファイル）
    info "アプリケーションログをバックアップ中..."
    local find_opts=""
    if [ -f "$LAST_BACKUP_MARKER" ]; then
        find_opts="-newer $LAST_BACKUP_MARKER"
    fi

    local app_log_dir="$PROJECT_DIR/backend/logs"
    if [ -d "$app_log_dir" ]; then
        local log_files
        log_files=$(find "$app_log_dir" -name "*.log" $find_opts 2>/dev/null || true)
        if [ -n "$log_files" ]; then
            tar czf "$BACKUP_DIR/operational/app_logs_${DATE}.tar.gz" $log_files
            ok "アプリケーションログ: $BACKUP_DIR/operational/app_logs_${DATE}.tar.gz"
        else
            info "新規アプリケーションログなし（スキップ）"
        fi
    else
        warn "アプリケーションログディレクトリが見つかりません: $app_log_dir"
    fi

    # 2. 監査ログ（DB: audit_logs テーブル）
    info "監査ログ(audit_logs)をバックアップ中..."
    if docker compose -f "$COMPOSE_FILE" exec -T db \
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_logs'" \
        | grep -q "1"; then

        docker compose -f "$COMPOSE_FILE" exec -T db \
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
            "COPY (SELECT * FROM audit_logs WHERE created_at >= CURRENT_DATE - INTERVAL '1 day') TO STDOUT WITH CSV HEADER" \
            | gzip > "$BACKUP_DIR/audit/audit_logs_${DATE}.csv.gz"
        ok "監査ログ: $BACKUP_DIR/audit/audit_logs_${DATE}.csv.gz"
    else
        warn "audit_logs テーブルが存在しません（スキップ）"
    fi

    # 3. データアクセスログ（DB: data_access_logs テーブル）
    info "データアクセスログ(data_access_logs)をバックアップ中..."
    if docker compose -f "$COMPOSE_FILE" exec -T db \
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'data_access_logs'" \
        | grep -q "1"; then

        docker compose -f "$COMPOSE_FILE" exec -T db \
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
            "COPY (SELECT * FROM data_access_logs WHERE created_at >= CURRENT_DATE - INTERVAL '1 day') TO STDOUT WITH CSV HEADER" \
            | gzip > "$BACKUP_DIR/data-access/data_access_logs_${DATE}.csv.gz"
        ok "データアクセスログ: $BACKUP_DIR/data-access/data_access_logs_${DATE}.csv.gz"
    else
        warn "data_access_logs テーブルが存在しません（スキップ）"
    fi

    # 4. コンプライアンスログ（DB: compliance_logs テーブル）
    info "コンプライアンスログ(compliance_logs)をバックアップ中..."
    if docker compose -f "$COMPOSE_FILE" exec -T db \
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'compliance_logs'" \
        | grep -q "1"; then

        docker compose -f "$COMPOSE_FILE" exec -T db \
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
            "COPY (SELECT * FROM compliance_logs WHERE created_at >= CURRENT_DATE - INTERVAL '1 day') TO STDOUT WITH CSV HEADER" \
            | gzip > "$BACKUP_DIR/compliance/compliance_logs_${DATE}.csv.gz"
        ok "コンプライアンスログ: $BACKUP_DIR/compliance/compliance_logs_${DATE}.csv.gz"
    else
        warn "compliance_logs テーブルが存在しません（スキップ）"
    fi

    # タイムスタンプマーカー更新
    touch "$LAST_BACKUP_MARKER"

    # S3アップロード
    if command -v aws &> /dev/null && [ -n "$S3_BUCKET" ]; then
        info "S3にアップロード中..."
        aws s3 sync "$BACKUP_DIR/operational/" "s3://${S3_BUCKET}/backups/logs/operational/" --quiet
        aws s3 sync "$BACKUP_DIR/audit/" "s3://${S3_BUCKET}/backups/logs/audit/" --quiet
        aws s3 sync "$BACKUP_DIR/data-access/" "s3://${S3_BUCKET}/backups/logs/data-access/" --quiet
        aws s3 sync "$BACKUP_DIR/compliance/" "s3://${S3_BUCKET}/backups/logs/compliance/" --quiet
        ok "S3アップロード完了"
    else
        info "AWS CLI未設定またはS3バケット未指定（S3アップロードをスキップ）"
    fi

    # ローカルの古いバックアップ削除（90日超過の運用ログ）
    local deleted_count
    deleted_count=$(find "$BACKUP_DIR/operational" -name "*.tar.gz" -mtime +90 -delete -print 2>/dev/null | wc -l)
    if [ "$deleted_count" -gt 0 ]; then
        info "古い運用ログバックアップを ${deleted_count} 件削除"
    fi

    # サイズ集計
    local total_size
    total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    local today_size
    today_size=$(find "$BACKUP_DIR" -name "*${DATE}*" -exec du -ch {} + 2>/dev/null | tail -1 | cut -f1)

    ok "=== 日次ログバックアップ完了 ==="
    info "本日のバックアップサイズ: ${today_size:-0}"
    info "バックアップ総サイズ: ${total_size:-0}"

    # 成功通知
    if [ -x "$SCRIPT_DIR/backup-notify.sh" ]; then
        "$SCRIPT_DIR/backup-notify.sh" success "日次ログバックアップ" "サイズ: ${today_size:-0}"
    fi
}

main "$@"
