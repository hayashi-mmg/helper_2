#!/usr/bin/env bash
# =============================================================================
# backup-metrics.sh - Prometheus textfile collector 向けメトリクス出力
# =============================================================================
# 概要: backup.sh / backup-logs.sh の成功・失敗状況を Prometheus が収集できる
#       textfile 形式で書き出す。node_exporter の --collector.textfile.directory
#       で指定したディレクトリへ書き込む。
#
# 使い方:
#   backup-metrics.sh <job> <status> <exit_code>
#     job:       db | logs (任意のラベル文字列)
#     status:    success | failure
#     exit_code: 数値 (成功時は 0)
#
# 出力先 (環境変数で上書き可):
#   BACKUP_METRICS_DIR (デフォルト: /var/lib/node_exporter/textfile_collector)
#
# 出力メトリクス:
#   backup_last_run_timestamp_seconds{job="<job>"}            実行時刻 (Unix秒)
#   backup_last_success_timestamp_seconds{job="<job>"}        最終成功時刻
#   backup_last_status{job="<job>"}                           1=success, 0=failure
#   backup_last_exit_code{job="<job>"}                        最終終了コード
# =============================================================================
set -euo pipefail

JOB="${1:-unknown}"
STATUS="${2:-failure}"
EXIT_CODE="${3:-1}"

METRICS_DIR="${BACKUP_METRICS_DIR:-/var/lib/node_exporter/textfile_collector}"
METRICS_FILE="${METRICS_DIR}/backup_${JOB}.prom"
TMP_FILE="${METRICS_FILE}.$$"

NOW=$(date +%s)

# 出力先ディレクトリが無い場合は何もせず終了 (node_exporter未導入環境を想定)
if [ ! -d "$METRICS_DIR" ]; then
    exit 0
fi

# 直前の最終成功時刻を引き継ぐ (失敗時は last_success を更新しない)
last_success="$NOW"
if [ "$STATUS" != "success" ] && [ -f "$METRICS_FILE" ]; then
    prev=$(grep -E "^backup_last_success_timestamp_seconds\{job=" "$METRICS_FILE" 2>/dev/null \
           | awk '{print $2}' | head -1 || true)
    if [ -n "$prev" ]; then
        last_success="$prev"
    else
        last_success=0
    fi
fi

status_value=0
if [ "$STATUS" = "success" ]; then
    status_value=1
fi

cat > "$TMP_FILE" <<EOF
# HELP backup_last_run_timestamp_seconds バックアップが最後に実行された Unix タイムスタンプ
# TYPE backup_last_run_timestamp_seconds gauge
backup_last_run_timestamp_seconds{job="${JOB}"} ${NOW}
# HELP backup_last_success_timestamp_seconds バックアップが最後に成功した Unix タイムスタンプ
# TYPE backup_last_success_timestamp_seconds gauge
backup_last_success_timestamp_seconds{job="${JOB}"} ${last_success}
# HELP backup_last_status 直近実行の結果 (1=success, 0=failure)
# TYPE backup_last_status gauge
backup_last_status{job="${JOB}"} ${status_value}
# HELP backup_last_exit_code 直近実行の終了コード
# TYPE backup_last_exit_code gauge
backup_last_exit_code{job="${JOB}"} ${EXIT_CODE}
EOF

# atomic rename
mv "$TMP_FILE" "$METRICS_FILE"
