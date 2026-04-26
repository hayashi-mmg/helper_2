#!/usr/bin/env bash
# =============================================================================
# check-loki-wal.sh - Loki WAL ディレクトリサイズ監視
# =============================================================================
# 概要: LokiのWAL（Write-Ahead Log）がディスクを圧迫していないか定期チェックし、
#       閾値超過時にアラートを送信する。
#
# Cronジョブ:
#   0 * * * * /opt/helper-system/scripts/check-loki-wal.sh >> /var/log/helper-loki-wal.log 2>&1
#
# 依存: du, (任意) backup-notify.sh
# =============================================================================
set -euo pipefail

# --- 定数 ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
THRESHOLD_MB="${LOKI_WAL_THRESHOLD_MB:-2048}"  # デフォルト2GB

# Loki データパス候補
LOKI_PATHS=(
    "/var/lib/docker/volumes/*loki*/_data/wal"
    "/var/lib/docker/volumes/*loki*/_data"
)

# --- WALサイズ取得 ---
get_wal_size_mb() {
    for pattern in "${LOKI_PATHS[@]}"; do
        local size_mb
        size_mb=$(du -sm $pattern 2>/dev/null | awk '{sum+=$1} END {print sum+0}')
        if [ "${size_mb:-0}" -gt 0 ]; then
            echo "$size_mb"
            return 0
        fi
    done
    echo "0"
}

# --- メイン ---
main() {
    local wal_size_mb
    wal_size_mb=$(get_wal_size_mb)

    if [ "$wal_size_mb" -eq 0 ]; then
        echo "[$TIMESTAMP] INFO: Lokiデータディレクトリが見つかりません（Loki未起動の可能性）"
        return 0
    fi

    echo "[$TIMESTAMP] Loki WAL/データサイズ: ${wal_size_mb}MB (閾値: ${THRESHOLD_MB}MB)"

    if [ "$wal_size_mb" -gt "$THRESHOLD_MB" ]; then
        echo "[$TIMESTAMP] WARNING: Loki WAL容量が閾値を超過 (${wal_size_mb}MB > ${THRESHOLD_MB}MB)"

        if [ -x "$SCRIPT_DIR/backup-notify.sh" ]; then
            "$SCRIPT_DIR/backup-notify.sh" failure \
                "Loki WAL容量警告" \
                "${wal_size_mb}MB (閾値: ${THRESHOLD_MB}MB) - コンパクション確認またはディスク拡張が必要"
        fi
        return 1
    fi
}

main "$@"
