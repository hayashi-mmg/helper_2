#!/usr/bin/env bash
# =============================================================================
# archive-logs.sh - 月次ログアーカイブ（Warm→Cold ティア移行）
# =============================================================================
# 概要: ログライフサイクル管理の自動化。
#   - Warm ティア（31-90日）: DB監査系ログをCSV+gzip圧縮でアーカイブ
#   - Cold ティア（90日超）: Warmアーカイブを暗号化してS3 Glacierへ
#   - 保持期間超過データのDBからの削除
#
# Cronジョブ:
#   0 4 1 * * /opt/helper-system/scripts/archive-logs.sh >> /var/log/helper-archive.log 2>&1
#
# 依存: docker compose, gzip, openssl, (任意) aws cli
# =============================================================================
set -euo pipefail

# --- 定数 ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
ARCHIVE_DIR="/opt/home-helper-system/log-archives"
ARCHIVE_KEY="/opt/home-helper-system/.archive-key"
S3_BUCKET="${AWS_S3_BUCKET:-}"
DATE=$(date +%Y%m%d)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ティア境界日付
WARM_BOUNDARY=$(date -d "31 days ago" +%Y-%m-%d)
COLD_BOUNDARY=$(date -d "90 days ago" +%Y-%m-%d)
WARM_MONTH=$(date -d "31 days ago" +%Y-%m)
COLD_MONTH=$(date -d "90 days ago" +%Y-%m)

# DB設定
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
        err "ログアーカイブが失敗しました (exit code: $exit_code)"
        if [ -x "$SCRIPT_DIR/backup-notify.sh" ]; then
            "$SCRIPT_DIR/backup-notify.sh" failure "月次ログアーカイブ" "exit code: $exit_code"
        fi
    fi
}
trap cleanup EXIT

# --- テーブル存在チェック ---
table_exists() {
    local table_name="$1"
    docker compose -f "$COMPOSE_FILE" exec -T db \
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '$table_name')" \
        2>/dev/null | grep -q "t"
}

# --- DBテーブルをCSV+gzipでエクスポート ---
export_table() {
    local table_name="$1"
    local condition="$2"
    local output_file="$3"

    docker compose -f "$COMPOSE_FILE" exec -T db \
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
        "COPY (SELECT * FROM $table_name WHERE $condition) TO STDOUT WITH CSV HEADER" \
        | gzip > "$output_file"

    local size
    size=$(du -h "$output_file" | cut -f1)
    ok "$table_name → $output_file ($size)"
}

# --- Warmティアアーカイブ ---
archive_warm() {
    info "--- Warm ティアアーカイブ（31日超過 → 圧縮保管） ---"

    local warm_dir="$ARCHIVE_DIR/warm"
    mkdir -p "$warm_dir"

    local tables=("data_access_logs" "compliance_logs" "audit_logs")
    local warm_count=0

    for table in "${tables[@]}"; do
        if table_exists "$table"; then
            local condition="created_at < '$WARM_BOUNDARY' AND created_at >= '$COLD_BOUNDARY'"
            local output="$warm_dir/${table}_${WARM_MONTH}.csv.gz"

            # 既にアーカイブ済みの場合はスキップ
            if [ -f "$output" ]; then
                info "$table ($WARM_MONTH): 既にアーカイブ済み（スキップ）"
                continue
            fi

            # レコード数確認
            local count
            count=$(docker compose -f "$COMPOSE_FILE" exec -T db \
                psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
                "SELECT COUNT(*) FROM $table WHERE $condition" 2>/dev/null || echo "0")

            if [ "${count:-0}" -gt 0 ]; then
                export_table "$table" "$condition" "$output"
                warm_count=$((warm_count + 1))
            else
                info "$table ($WARM_MONTH): 対象レコードなし（スキップ）"
            fi
        else
            warn "$table テーブルが存在しません（スキップ）"
        fi
    done

    ok "Warm ティアアーカイブ完了: ${warm_count} テーブル処理"
    echo "$warm_count"
}

# --- Coldティアアーカイブ（暗号化） ---
archive_cold() {
    info "--- Cold ティアアーカイブ（90日超過 → 暗号化保管） ---"

    local cold_dir="$ARCHIVE_DIR/cold"
    mkdir -p "$cold_dir"

    # 暗号化鍵の存在チェック
    if [ ! -f "$ARCHIVE_KEY" ]; then
        warn "暗号化鍵が見つかりません: $ARCHIVE_KEY"
        warn "以下のコマンドで鍵を生成してください:"
        warn "  openssl rand -base64 32 > $ARCHIVE_KEY && chmod 600 $ARCHIVE_KEY"
        return 0
    fi

    local cold_count=0

    # Warmアーカイブの中で90日超過分を暗号化
    for warmfile in "$ARCHIVE_DIR"/warm/*_"${COLD_MONTH}".csv.gz; do
        [ -f "$warmfile" ] || continue

        local basename
        basename=$(basename "$warmfile")
        local encrypted_file="$cold_dir/${basename}.enc"

        # 既に暗号化済みの場合はスキップ
        if [ -f "$encrypted_file" ]; then
            info "$basename: 既に暗号化済み（スキップ）"
            continue
        fi

        openssl enc -aes-256-cbc -salt -pbkdf2 \
            -in "$warmfile" \
            -out "$encrypted_file" \
            -pass file:"$ARCHIVE_KEY"

        local size
        size=$(du -h "$encrypted_file" | cut -f1)
        ok "Cold暗号化完了: $basename → ${basename}.enc ($size)"
        cold_count=$((cold_count + 1))
    done

    ok "Cold ティアアーカイブ完了: ${cold_count} ファイル暗号化"
    echo "$cold_count"
}

# --- S3アップロード ---
upload_to_s3() {
    if ! command -v aws &> /dev/null || [ -z "$S3_BUCKET" ]; then
        info "AWS CLI未設定またはS3バケット未指定（S3アップロードをスキップ）"
        return 0
    fi

    info "--- S3アップロード ---"

    # Warmアーカイブ → S3 Standard
    if [ -d "$ARCHIVE_DIR/warm" ] && [ "$(ls -A "$ARCHIVE_DIR/warm" 2>/dev/null)" ]; then
        aws s3 sync "$ARCHIVE_DIR/warm/" "s3://${S3_BUCKET}/backups/logs/audit/" \
            --storage-class STANDARD --quiet
        ok "Warm → S3 Standard アップロード完了"
    fi

    # Coldアーカイブ → S3 Glacier
    if [ -d "$ARCHIVE_DIR/cold" ] && [ "$(ls -A "$ARCHIVE_DIR/cold" 2>/dev/null)" ]; then
        aws s3 sync "$ARCHIVE_DIR/cold/" "s3://${S3_BUCKET}/backups/logs/compliance/" \
            --storage-class GLACIER --quiet
        ok "Cold → S3 Glacier アップロード完了"
    fi
}

# --- 保持期間超過データの削除（DBクリーンアップ） ---
cleanup_expired() {
    info "--- 保持期間超過データの削除 ---"

    # audit_logs: 6ヶ月超過分を削除
    if table_exists "audit_logs"; then
        local audit_boundary
        audit_boundary=$(date -d "6 months ago" +%Y-%m-%d)
        local audit_deleted
        audit_deleted=$(docker compose -f "$COMPOSE_FILE" exec -T db \
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
            "DELETE FROM audit_logs WHERE created_at < '$audit_boundary' RETURNING id" \
            2>/dev/null | wc -l || echo "0")
        info "audit_logs: ${audit_deleted} 件削除（6ヶ月超過）"
    fi

    # frontend_error_logs: 90日超過分を削除
    if table_exists "frontend_error_logs"; then
        local fe_boundary
        fe_boundary=$(date -d "90 days ago" +%Y-%m-%d)
        local fe_deleted
        fe_deleted=$(docker compose -f "$COMPOSE_FILE" exec -T db \
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
            "DELETE FROM frontend_error_logs WHERE created_at < '$fe_boundary' RETURNING id" \
            2>/dev/null | wc -l || echo "0")
        info "frontend_error_logs: ${fe_deleted} 件削除（90日超過）"
    fi

    # data_access_logs / compliance_logs は3年保持のため、ここでは削除しない
    # 3年超過分の削除は別途 data_retention.py バッチで実行される
    info "data_access_logs / compliance_logs: 3年保持（自動削除対象外）"

    ok "保持期間超過データ削除完了"
}

# --- ローカルアーカイブの古いファイル削除 ---
cleanup_local_archives() {
    info "--- ローカルアーカイブの古いファイル削除 ---"

    # S3にアップロード済みのColdアーカイブで1年超過のものをローカルから削除
    local deleted_count
    deleted_count=$(find "$ARCHIVE_DIR/cold" -name "*.enc" -mtime +365 -delete -print 2>/dev/null | wc -l)
    if [ "$deleted_count" -gt 0 ]; then
        info "Cold ローカルアーカイブ: ${deleted_count} 件削除（1年超過、S3保管済み前提）"
    fi

    # Warmアーカイブで6ヶ月超過のものを削除（Coldに移行済み前提）
    deleted_count=$(find "$ARCHIVE_DIR/warm" -name "*.csv.gz" -mtime +180 -delete -print 2>/dev/null | wc -l)
    if [ "$deleted_count" -gt 0 ]; then
        info "Warm ローカルアーカイブ: ${deleted_count} 件削除（6ヶ月超過、Cold移行済み前提）"
    fi

    ok "ローカルアーカイブ削除完了"
}

# --- メイン ---
main() {
    info "=========================================="
    info "  月次ログアーカイブ開始"
    info "  Warm境界: $WARM_BOUNDARY (31日前)"
    info "  Cold境界: $COLD_BOUNDARY (90日前)"
    info "=========================================="

    mkdir -p "$ARCHIVE_DIR"/{warm,cold}

    # Warmティアアーカイブ
    local warm_result
    warm_result=$(archive_warm)

    # Coldティアアーカイブ
    local cold_result
    cold_result=$(archive_cold)

    # S3アップロード
    upload_to_s3

    # 保持期間超過データの削除
    cleanup_expired

    # ローカルアーカイブの古いファイル削除
    cleanup_local_archives

    # サイズ集計
    local total_size
    total_size=$(du -sh "$ARCHIVE_DIR" 2>/dev/null | cut -f1)
    local warm_count
    warm_count=$(ls -1 "$ARCHIVE_DIR/warm/"*.csv.gz 2>/dev/null | wc -l)
    local cold_count
    cold_count=$(ls -1 "$ARCHIVE_DIR/cold/"*.enc 2>/dev/null | wc -l)

    ok "=========================================="
    ok "  月次ログアーカイブ完了"
    ok "  Warm: ${warm_count} ファイル"
    ok "  Cold: ${cold_count} ファイル"
    ok "  合計サイズ: ${total_size}"
    ok "=========================================="

    # 成功通知
    if [ -x "$SCRIPT_DIR/backup-notify.sh" ]; then
        "$SCRIPT_DIR/backup-notify.sh" success \
            "月次ログアーカイブ" \
            "Warm: ${warm_count}件, Cold: ${cold_count}件, サイズ: ${total_size}"
    fi
}

main "$@"
