#!/usr/bin/env bash
# =============================================================================
# backup-notify.sh - バックアップ成否通知
# =============================================================================
# 概要: バックアップの成功/失敗をSlackとメールで通知する。
#       他のバックアップスクリプトから呼び出される共通通知ユーティリティ。
#
# 使い方:
#   ./backup-notify.sh success "日次ログバックアップ" "サイズ: 150MB"
#   ./backup-notify.sh failure "DBバックアップ" "ディスク容量不足"
#
# 環境変数:
#   SLACK_BACKUP_WEBHOOK_URL  - Slack Webhook URL（任意）
#   BACKUP_ALERT_EMAIL        - アラート送信先メール（任意、失敗時のみ）
# =============================================================================
set -euo pipefail

# --- 引数パース ---
STATUS="${1:-}"
TARGET="${2:-不明}"
DETAIL="${3:-}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
HOSTNAME=$(hostname -f 2>/dev/null || hostname)

if [ -z "$STATUS" ]; then
    echo "使い方: $0 <success|failure> <対象名> [詳細]"
    exit 1
fi

if [ "$STATUS" != "success" ] && [ "$STATUS" != "failure" ]; then
    echo "ERROR: STATUS は 'success' または 'failure' を指定してください"
    exit 1
fi

# --- 環境変数 ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# .env から通知設定を読み込む（存在する場合）
if [ -f "$PROJECT_DIR/.env" ]; then
    SLACK_BACKUP_WEBHOOK_URL="${SLACK_BACKUP_WEBHOOK_URL:-$(grep '^SLACK_BACKUP_WEBHOOK_URL=' "$PROJECT_DIR/.env" 2>/dev/null | cut -d= -f2- || true)}"
    BACKUP_ALERT_EMAIL="${BACKUP_ALERT_EMAIL:-$(grep '^BACKUP_ALERT_EMAIL=' "$PROJECT_DIR/.env" 2>/dev/null | cut -d= -f2- || true)}"
fi

SLACK_WEBHOOK="${SLACK_BACKUP_WEBHOOK_URL:-}"
ALERT_EMAIL="${BACKUP_ALERT_EMAIL:-}"
NOTIFICATION_LOG="/var/log/helper-backup-notify.log"

# --- ログ記録 ---
log_entry="[$TIMESTAMP] $STATUS: $TARGET - $DETAIL"
if [ -w "$(dirname "$NOTIFICATION_LOG")" ] || [ -w "$NOTIFICATION_LOG" ]; then
    echo "$log_entry" >> "$NOTIFICATION_LOG"
else
    echo "$log_entry"
fi

# --- Slack通知 ---
send_slack() {
    if [ -z "$SLACK_WEBHOOK" ]; then
        return 0
    fi

    local emoji color text

    if [ "$STATUS" = "success" ]; then
        emoji="white_check_mark"
        color="#36a64f"
        text="バックアップ成功: $TARGET"
    else
        emoji="x"
        color="#ff0000"
        text="バックアップ失敗: $TARGET"
    fi

    local payload
    payload=$(cat <<EOF
{
  "attachments": [{
    "color": "$color",
    "title": ":${emoji}: ${text}",
    "fields": [
      {"title": "対象", "value": "$TARGET", "short": true},
      {"title": "サーバー", "value": "$HOSTNAME", "short": true},
      {"title": "時刻", "value": "$TIMESTAMP", "short": true},
      {"title": "ステータス", "value": "$STATUS", "short": true},
      {"title": "詳細", "value": "${DETAIL:-なし}", "short": false}
    ],
    "footer": "Home Helper Backup System",
    "ts": $(date +%s)
  }]
}
EOF
)

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST -H 'Content-type: application/json' \
        --data "$payload" "$SLACK_WEBHOOK" \
        --connect-timeout 10 --max-time 30 2>/dev/null || echo "000")

    if [ "$http_code" = "200" ]; then
        echo "[$TIMESTAMP] Slack通知送信成功"
    else
        echo "[$TIMESTAMP] WARNING: Slack通知送信失敗 (HTTP $http_code)"
    fi
}

# --- メール通知（失敗時のみ） ---
send_email() {
    if [ "$STATUS" != "failure" ]; then
        return 0
    fi

    if [ -z "$ALERT_EMAIL" ]; then
        return 0
    fi

    if ! command -v mail &> /dev/null; then
        echo "[$TIMESTAMP] WARNING: mail コマンドが見つかりません。メール通知をスキップ"
        return 0
    fi

    local subject="[ALERT] バックアップ失敗: $TARGET - $HOSTNAME"
    local body
    body=$(cat <<EOF
バックアップ失敗アラート
========================

対象:     $TARGET
サーバー: $HOSTNAME
時刻:     $TIMESTAMP
詳細:     ${DETAIL:-なし}

対処手順:
1. サーバーにSSH接続し、ログを確認してください
   tail -50 /var/log/helper-log-backup.log
   tail -50 /var/log/helper-backup.log

2. ディスク容量を確認してください
   df -h /backups

3. Docker サービスの状態を確認してください
   docker compose -f docker-compose.prod.yml ps

---
Home Helper Management System
Automated Backup Notification
EOF
)

    echo "$body" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null && \
        echo "[$TIMESTAMP] メール通知送信成功: $ALERT_EMAIL" || \
        echo "[$TIMESTAMP] WARNING: メール通知送信失敗"
}

# --- 標準出力サマリー ---
print_summary() {
    if [ "$STATUS" = "success" ]; then
        echo "[$TIMESTAMP] OK: $TARGET 完了 - $DETAIL"
    else
        echo "[$TIMESTAMP] FAILED: $TARGET - $DETAIL"
    fi
}

# --- メイン ---
print_summary
send_slack
send_email
