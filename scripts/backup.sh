#!/usr/bin/env bash
# =============================================================================
# backup.sh - 日次データベース・ファイルバックアップ
# =============================================================================
# 概要: PostgreSQL、Redis、アップロードファイル、環境設定を一括バックアップし、
#       S3にアップロードする。RPO 24時間・RTO 4時間の目標に対応。
#
# Cronジョブ:
#   0 2 * * * /opt/helper-system/scripts/backup.sh >> /var/log/helper-backup.log 2>&1
#
# 使い方:
#   ./scripts/backup.sh          # 全バックアップ実行
#   ./scripts/backup.sh test     # バックアップ完全性テスト
#
# 依存: docker compose, gzip, (任意) aws cli
# =============================================================================
set -euo pipefail

# --- 定数 ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y%m%d)
LOG_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
S3_BUCKET="${AWS_S3_BUCKET:-}"

# DB設定読み込み
if [ -f "$PROJECT_DIR/.env" ]; then
    POSTGRES_USER=$(grep '^POSTGRES_USER=' "$PROJECT_DIR/.env" | cut -d= -f2)
    POSTGRES_DB=$(grep '^POSTGRES_DB=' "$PROJECT_DIR/.env" | cut -d= -f2)
    REDIS_PASSWORD=$(grep '^REDIS_PASSWORD=' "$PROJECT_DIR/.env" | cut -d= -f2 || true)
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

# --- エラーハンドリング ---
BACKUP_FAILED=0
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ] || [ $BACKUP_FAILED -ne 0 ]; then
        err "バックアップが失敗しました (exit code: $exit_code)"
        if [ -x "$SCRIPT_DIR/backup-notify.sh" ]; then
            "$SCRIPT_DIR/backup-notify.sh" failure "日次DBバックアップ" "exit code: $exit_code"
        fi
    fi
}
trap cleanup EXIT

# --- ディスク空き容量チェック ---
check_disk_space() {
    local required_mb="${1:-500}"
    local available_mb
    available_mb=$(df -m "$BACKUP_DIR" | awk 'NR==2 {print $4}')

    if [ "${available_mb:-0}" -lt "$required_mb" ]; then
        err "ディスク空き容量不足: ${available_mb}MB (必要: ${required_mb}MB)"
        return 1
    fi
    info "ディスク空き容量: ${available_mb}MB"
}

# --- PostgreSQL バックアップ ---
backup_postgres() {
    info "PostgreSQLバックアップを作成中..."
    local db_backup_dir="$BACKUP_DIR/db"
    mkdir -p "$db_backup_dir"

    local dump_file="$db_backup_dir/backup_${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

    docker compose -f "$COMPOSE_FILE" exec -T db \
        pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=plain \
        | gzip > "$dump_file"

    # バックアップの妥当性チェック（最小サイズ）
    local size_bytes
    size_bytes=$(stat -c%s "$dump_file" 2>/dev/null || echo "0")
    if [ "$size_bytes" -lt 1024 ]; then
        err "PostgreSQLバックアップが異常に小さい: ${size_bytes} bytes"
        BACKUP_FAILED=1
        return 1
    fi

    local size
    size=$(du -h "$dump_file" | cut -f1)
    ok "PostgreSQL: $dump_file ($size)"
}

# --- Redis バックアップ ---
backup_redis() {
    info "Redisバックアップを作成中..."
    local redis_backup_dir="$BACKUP_DIR/redis"
    mkdir -p "$redis_backup_dir"

    # RDB snapshot 作成
    local redis_auth=""
    if [ -n "${REDIS_PASSWORD:-}" ]; then
        redis_auth="-a $REDIS_PASSWORD"
    fi

    docker compose -f "$COMPOSE_FILE" exec -T redis \
        redis-cli $redis_auth BGSAVE 2>/dev/null || true

    # BGSAVE完了待ち（最大30秒）
    local retries=0
    while [ $retries -lt 15 ]; do
        local bgsave_status
        bgsave_status=$(docker compose -f "$COMPOSE_FILE" exec -T redis \
            redis-cli $redis_auth LASTSAVE 2>/dev/null || echo "")
        sleep 2
        local new_status
        new_status=$(docker compose -f "$COMPOSE_FILE" exec -T redis \
            redis-cli $redis_auth LASTSAVE 2>/dev/null || echo "")
        if [ "$bgsave_status" != "$new_status" ] || [ $retries -gt 0 ]; then
            break
        fi
        retries=$((retries + 1))
    done

    # dump.rdb をコピー
    local container_name
    container_name=$(docker compose -f "$COMPOSE_FILE" ps -q redis 2>/dev/null || true)
    if [ -n "$container_name" ]; then
        docker cp "${container_name}:/data/dump.rdb" \
            "$redis_backup_dir/redis_${DATE}.rdb" 2>/dev/null || {
            warn "Redis dump.rdb のコピーに失敗（appendonly モードの可能性）"
            return 0
        }
        local size
        size=$(du -h "$redis_backup_dir/redis_${DATE}.rdb" | cut -f1)
        ok "Redis: $redis_backup_dir/redis_${DATE}.rdb ($size)"
    else
        warn "Redisコンテナが見つかりません（スキップ）"
    fi
}

# --- アップロードファイル バックアップ ---
backup_uploads() {
    info "アップロードファイルをバックアップ中..."
    local upload_backup_dir="$BACKUP_DIR/uploads"
    mkdir -p "$upload_backup_dir"

    # Docker volumeからアーカイブ
    local volume_name
    volume_name=$(docker volume ls --format '{{.Name}}' | grep -E "upload" | head -1 || true)

    if [ -n "$volume_name" ]; then
        docker run --rm \
            -v "${volume_name}:/data:ro" \
            -v "$upload_backup_dir:/backups" \
            alpine tar czf "/backups/uploads_${DATE}.tar.gz" -C /data . 2>/dev/null

        local size
        size=$(du -h "$upload_backup_dir/uploads_${DATE}.tar.gz" | cut -f1)
        ok "アップロードファイル: $upload_backup_dir/uploads_${DATE}.tar.gz ($size)"
    else
        info "アップロードボリュームが見つかりません（スキップ）"
    fi
}

# --- 環境設定 バックアップ ---
backup_config() {
    info "環境設定ファイルをバックアップ中..."
    local config_backup_dir="$BACKUP_DIR/config"
    mkdir -p "$config_backup_dir"

    local count=0

    for env_file in \
        "$PROJECT_DIR/.env" \
        "$PROJECT_DIR/backend/.env.production" \
        "$PROJECT_DIR/backend/.env" \
        "$PROJECT_DIR/frontend/.env.production" \
        "$PROJECT_DIR/docker-compose.prod.yml" \
        "$PROJECT_DIR/nginx/nginx.conf"; do

        if [ -f "$env_file" ]; then
            local basename
            basename=$(basename "$env_file")
            cp "$env_file" "$config_backup_dir/${basename}.${DATE}"
            count=$((count + 1))
        fi
    done

    ok "環境設定: ${count} ファイルをバックアップ"
}

# --- 古いバックアップの削除 ---
cleanup_old_backups() {
    info "古いバックアップを削除中..."

    # DB: 30日超過
    local db_deleted
    db_deleted=$(find "$BACKUP_DIR/db" -name "backup_*.sql.gz" -mtime +30 -delete -print 2>/dev/null | wc -l)

    # Redis: 7日超過
    local redis_deleted
    redis_deleted=$(find "$BACKUP_DIR/redis" -name "redis_*.rdb" -mtime +7 -delete -print 2>/dev/null | wc -l)

    # アップロード: 30日超過
    local upload_deleted
    upload_deleted=$(find "$BACKUP_DIR/uploads" -name "uploads_*.tar.gz" -mtime +30 -delete -print 2>/dev/null | wc -l)

    # 設定: 30日超過
    local config_deleted
    config_deleted=$(find "$BACKUP_DIR/config" -type f -mtime +30 -delete -print 2>/dev/null | wc -l)

    local total=$((db_deleted + redis_deleted + upload_deleted + config_deleted))
    if [ "$total" -gt 0 ]; then
        info "削除: DB=${db_deleted}, Redis=${redis_deleted}, Upload=${upload_deleted}, Config=${config_deleted}"
    else
        info "削除対象なし"
    fi
}

# --- S3アップロード ---
upload_to_s3() {
    if ! command -v aws &> /dev/null || [ -z "$S3_BUCKET" ]; then
        info "AWS CLI未設定またはS3バケット未指定（S3アップロードをスキップ）"
        return 0
    fi

    info "S3にアップロード中..."

    aws s3 sync "$BACKUP_DIR/db/" "s3://${S3_BUCKET}/backups/db/" --quiet
    aws s3 sync "$BACKUP_DIR/redis/" "s3://${S3_BUCKET}/backups/redis/" --quiet
    aws s3 sync "$BACKUP_DIR/uploads/" "s3://${S3_BUCKET}/backups/uploads/" --quiet

    ok "S3アップロード完了"
}

# --- バックアップ完全性テスト ---
test_backups() {
    info "=== バックアップ完全性テスト ==="

    local errors=0

    # gzip 整合性チェック
    info "gzipファイルの整合性を確認中..."
    for file in "$BACKUP_DIR"/db/backup_*.sql.gz; do
        [ -f "$file" ] || continue
        if gzip -t "$file" 2>/dev/null; then
            ok "$(basename "$file"): OK"
        else
            err "$(basename "$file"): 破損"
            errors=$((errors + 1))
        fi
    done

    # 異常に小さいファイルの検出
    info "異常に小さいバックアップファイルを検出中..."
    while IFS= read -r file; do
        warn "異常に小さいファイル: $file"
        errors=$((errors + 1))
    done < <(find "$BACKUP_DIR/db" -name "backup_*.sql.gz" -size -1k 2>/dev/null)

    # 最新バックアップの日付チェック
    local latest_db
    latest_db=$(ls -t "$BACKUP_DIR"/db/backup_*.sql.gz 2>/dev/null | head -1 || true)
    if [ -n "$latest_db" ]; then
        local age_hours
        age_hours=$(( ($(date +%s) - $(stat -c%Y "$latest_db")) / 3600 ))
        if [ "$age_hours" -gt 48 ]; then
            warn "最新DBバックアップが ${age_hours} 時間前（RPO 24h超過）"
            errors=$((errors + 1))
        else
            ok "最新DBバックアップ: ${age_hours} 時間前"
        fi
    else
        err "DBバックアップが見つかりません"
        errors=$((errors + 1))
    fi

    # サマリー
    local total_size
    total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    info "バックアップ総サイズ: ${total_size}"

    if [ "$errors" -eq 0 ]; then
        ok "=== 完全性テスト: すべてパス ==="
    else
        err "=== 完全性テスト: ${errors} 件の問題あり ==="
        return 1
    fi
}

# --- メイン ---
main() {
    local mode="${1:-backup}"

    if [ "$mode" = "test" ]; then
        test_backups
        return $?
    fi

    info "=========================================="
    info "  日次バックアップ開始"
    info "=========================================="

    mkdir -p "$BACKUP_DIR"/{db,redis,uploads,config}

    # ディスク空き容量チェック
    check_disk_space 500

    # 各バックアップ実行
    backup_postgres
    backup_redis
    backup_uploads
    backup_config

    # 古いバックアップ削除
    cleanup_old_backups

    # S3アップロード
    upload_to_s3

    # サイズ集計
    local total_size
    total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    local today_db_size
    today_db_size=$(du -h "$BACKUP_DIR/db/backup_${POSTGRES_DB}_${TIMESTAMP}.sql.gz" 2>/dev/null | cut -f1 || echo "N/A")

    ok "=========================================="
    ok "  日次バックアップ完了"
    ok "  DB: ${today_db_size}"
    ok "  合計: ${total_size}"
    ok "=========================================="

    # 成功通知
    if [ -x "$SCRIPT_DIR/backup-notify.sh" ]; then
        "$SCRIPT_DIR/backup-notify.sh" success "日次DBバックアップ" "DB: ${today_db_size}, 合計: ${total_size}"
    fi
}

main "$@"
