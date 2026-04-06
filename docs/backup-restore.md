# ホームヘルパー管理システム - バックアップ・リストア手順書

## 目次
- [バックアップ戦略](#バックアップ戦略)
- [自動バックアップ設定](#自動バックアップ設定)
- [手動バックアップ](#手動バックアップ)
- [リストア手順](#リストア手順)
- [バックアップ検証](#バックアップ検証)

---

## バックアップ戦略

### バックアップ対象

| データ種別 | 頻度 | 保持期間 | 優先度 |
|-----------|------|---------|--------|
| PostgreSQLデータベース | 日次 | 30日 | 最高 |
| アップロードファイル | 日次 | 30日 | 高 |
| 環境設定ファイル | 変更時 | 永久 | 高 |
| Redisデータ | 日次 | 7日 | 中 |
| アプリケーションログ（運用系） | 日次 | 90日 | 中 |
| 監査ログ（DB: audit_logs） | 日次 | 6ヶ月 | 高 |
| データアクセスログ（DB: data_access_logs） | 日次 | 3年 | 最高 |
| コンプライアンスログ（DB: compliance_logs） | 日次 | 3年 | 最高 |

### バックアップ保存先

- **プライマリ**: サーバーローカル (`/backups`)
- **セカンダリ**: AWS S3 (推奨)
- **オフサイト**: 別リージョンのS3バケット (本番環境推奨)

### RPO/RTO目標

- **RPO (Recovery Point Objective)**: 24時間以内
- **RTO (Recovery Time Objective)**: 4時間以内

---

## 自動バックアップ設定

### Docker Compose設定確認

`docker-compose.prod.yml`にバックアップサービスが含まれていることを確認：

```bash
docker compose -f docker-compose.prod.yml ps backup
```

### Cronジョブ設定 (代替方法)

```bash
# Cronジョブ追加
crontab -e

# 毎日午前2時にDBバックアップ実行
0 2 * * * /opt/helper-system/scripts/backup.sh >> /var/log/helper-backup.log 2>&1

# 毎日午前2時30分にログバックアップ実行（日次: RPO 24h対応）
30 2 * * * /opt/helper-system/scripts/backup-logs.sh >> /var/log/helper-log-backup.log 2>&1

# 毎月1日午前4時にWarm→Coldアーカイブ移行
0 4 1 * * /opt/helper-system/scripts/archive-logs.sh >> /var/log/helper-archive.log 2>&1
```

> **変更履歴**: ログバックアップを週次から**日次**に変更。RPO 24時間目標との整合性を確保するため。

### バックアップスクリプトの確認

```bash
# 実行権限確認
ls -l /opt/helper-system/scripts/backup.sh

# 権限付与 (必要な場合)
chmod +x /opt/helper-system/scripts/backup.sh

# テスト実行
/opt/helper-system/scripts/backup.sh
```

---

## 手動バックアップ

### PostgreSQLデータベース

#### 完全バックアップ
```bash
cd /opt/helper-system

# Dockerコンテナ経由でバックアップ
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U prod_user helper_production | gzip > backups/manual_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# バックアップサイズ確認
ls -lh backups/manual_backup_*.sql.gz | tail -1
```

#### スキーマのみバックアップ
```bash
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U prod_user --schema-only helper_production | gzip > backups/schema_$(date +%Y%m%d).sql.gz
```

#### 特定テーブルのみバックアップ
```bash
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U prod_user -t users -t recipes helper_production | gzip > backups/users_recipes_$(date +%Y%m%d).sql.gz
```

### Redisデータ

```bash
# RDB snapshot
docker compose -f docker-compose.prod.yml exec redis redis-cli SAVE

# snapshotファイルをコピー
docker cp helper-redis-prod:/data/dump.rdb backups/redis_$(date +%Y%m%d).rdb
```

### アップロードファイル

```bash
# アップロードディレクトリをアーカイブ
docker run --rm -v helper_upload_data:/data -v $(pwd)/backups:/backups \
  alpine tar czf /backups/uploads_$(date +%Y%m%d).tar.gz /data

# サイズ確認
ls -lh backups/uploads_*.tar.gz | tail -1
```

### 環境設定ファイル

```bash
# 環境設定バックアップ
mkdir -p backups/config
cp backend/.env.production backups/config/.env.production.$(date +%Y%m%d)
cp frontend/.env.production backups/config/.env.frontend.production.$(date +%Y%m%d)
cp docker-compose.prod.yml backups/config/docker-compose.prod.yml.$(date +%Y%m%d)
```

---

## リストア手順

### 事前準備

#### 1. 現在のデータバックアップ
```bash
# リストア前に現在の状態を必ずバックアップ
./scripts/backup.sh
```

#### 2. メンテナンスモード有効化
```bash
# ユーザーアクセスを一時停止 (オプション)
docker compose -f docker-compose.prod.yml stop frontend
```

### PostgreSQLリストア

#### 自動リストア (推奨)
```bash
# リストアスクリプト使用
./scripts/restore.sh -f backups/backup_helper_production_20250110_020000.sql.gz

# 確認プロンプトをスキップ
./scripts/restore.sh -f backups/backup_helper_production_20250110_020000.sql.gz --yes

# 最新バックアップから自動リストア
./scripts/restore.sh -f latest --yes
```

#### 手動リストア
```bash
# Step 1: データベースへの接続を切断
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d postgres <<EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'helper_production' AND pid <> pg_backend_pid();
EOF

# Step 2: データベース削除と再作成
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d postgres <<EOF
DROP DATABASE IF EXISTS helper_production;
CREATE DATABASE helper_production WITH ENCODING 'UTF8' LC_COLLATE='ja_JP.UTF-8' LC_CTYPE='ja_JP.UTF-8';
EOF

# Step 3: バックアップからリストア
gunzip -c backups/backup_helper_production_20250110_020000.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U prod_user -d helper_production

# Step 4: マイグレーション実行 (必要な場合)
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Redisリストア

```bash
# Step 1: Redisサービス停止
docker compose -f docker-compose.prod.yml stop redis

# Step 2: バックアップファイルをコピー
docker cp backups/redis_20250110.rdb helper-redis-prod:/data/dump.rdb

# Step 3: Redisサービス起動
docker compose -f docker-compose.prod.yml start redis
```

### アップロードファイルリストア

```bash
# アップロードデータリストア
docker run --rm -v helper_upload_data:/data -v $(pwd)/backups:/backups \
  alpine sh -c "cd /data && tar xzf /backups/uploads_20250110.tar.gz --strip-components=1"
```

### 環境設定リストア

```bash
# 環境設定ファイルリストア
cp backups/config/.env.production.20250110 backend/.env.production
cp backups/config/.env.frontend.production.20250110 frontend/.env.production

# サービス再起動
docker compose -f docker-compose.prod.yml restart
```

---

## バックアップ検証

### 定期バックアップ検証 (月1回推奨)

```bash
# テスト環境でリストア検証
cd /opt/helper-system-test

# 最新バックアップをテスト環境にリストア
./scripts/restore.sh -f /opt/helper-system/backups/backup_helper_production_20250110_020000.sql.gz --yes

# データ整合性確認
docker compose exec postgres psql -U test_user -d helper_test <<EOF
-- テーブル数確認
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';

-- レコード数サンプル確認
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'recipes', COUNT(*) FROM recipes
UNION ALL
SELECT 'weekly_menus', COUNT(*) FROM weekly_menus;
EOF
```

### バックアップ完全性チェック

```bash
# バックアップファイルの整合性確認
for file in backups/backup_*.sql.gz; do
    echo "Checking: $file"
    gunzip -t "$file" && echo "  OK" || echo "  CORRUPTED"
done

# ファイルサイズ確認 (異常に小さいファイルを検出)
find backups -name "backup_*.sql.gz" -size -1M -ls
```

### S3バックアップ確認

```bash
# S3バックアップ一覧
aws s3 ls s3://helper-system-backups/backups/ --recursive

# S3から最新バックアップダウンロード
aws s3 cp s3://helper-system-backups/backups/backup_helper_production_20250110_020000.sql.gz backups/

# 整合性確認
gunzip -t backups/backup_helper_production_20250110_020000.sql.gz
```

---

## S3自動バックアップ設定

### AWS CLI設定

```bash
# AWS CLI インストール
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 認証情報設定
aws configure
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: ap-northeast-1
# Default output format: json
```

### S3バケット作成

```bash
# バックアップ用バケット作成
aws s3 mb s3://helper-system-backups --region ap-northeast-1

# ライフサイクルポリシー設定 (30日後に削除)
aws s3api put-bucket-lifecycle-configuration \
  --bucket helper-system-backups \
  --lifecycle-configuration file://s3-lifecycle.json
```

`s3-lifecycle.json`:
```json
{
  "Rules": [
    {
      "Id": "DeleteOldDBBackups",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "backups/db/"
      },
      "Expiration": {
        "Days": 30
      }
    },
    {
      "Id": "DeleteOldOperationalLogs",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "backups/logs/operational/"
      },
      "Expiration": {
        "Days": 90
      }
    },
    {
      "Id": "ArchiveAuditLogs",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "backups/logs/audit/"
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 180
      }
    },
    {
      "Id": "ArchiveComplianceLogs",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "backups/logs/compliance/"
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 1095
      }
    },
    {
      "Id": "ArchiveDataAccessLogs",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "backups/logs/data-access/"
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 1095
      }
    },
    {
      "Id": "DeleteOldRedisBackups",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "backups/redis/"
      },
      "Expiration": {
        "Days": 7
      }
    },
    {
      "Id": "DeleteOldUploadBackups",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "backups/uploads/"
      },
      "Expiration": {
        "Days": 30
      }
    }
  ]
}
```

> **S3保持期間の根拠**:
> - DB/アップロード: 30日（日次バックアップで十分な世代管理）
> - 運用ログ: 90日（障害調査目的）
> - 監査ログ: 6ヶ月（内部統制要件）
> - コンプライアンス/データアクセスログ: **3年（1095日）**（改正個人情報保護法 第25条 記録保管義務）
> - 90日経過後はS3 Glacierに移行しストレージ費用を削減

### バックアップスクリプトへのS3統合

```bash
# 環境変数設定
export AWS_S3_BUCKET=helper-system-backups

# バックアップスクリプト実行 (自動的にS3にアップロード)
./scripts/backup.sh
```

---

## ログバックアップスクリプト

### 日次ログバックアップ (`scripts/backup-logs.sh`)

```bash
#!/bin/bash
# backup-logs.sh - 日次ログバックアップ
set -euo pipefail

BACKUP_DIR="/backups/logs"
DATE=$(date +%Y%m%d)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="/var/log/helper-log-backup.log"
S3_BUCKET="${AWS_S3_BUCKET:-helper-system-backups}"

mkdir -p "$BACKUP_DIR"/{operational,audit,compliance,data-access}

echo "[$TIMESTAMP] ログバックアップ開始" >> "$LOG_FILE"

# 1. アプリケーション運用ログ（差分: 前回バックアップ以降）
LAST_BACKUP_MARKER="/backups/.last-log-backup"
FIND_OPTS=""
if [ -f "$LAST_BACKUP_MARKER" ]; then
    FIND_OPTS="-newer $LAST_BACKUP_MARKER"
fi

tar czf "$BACKUP_DIR/operational/app_logs_${DATE}.tar.gz" \
    $(find /opt/helper-system/backend/logs -name "*.log" $FIND_OPTS 2>/dev/null) \
    2>/dev/null || true

# 2. 監査ログ（DB: audit_logs テーブル）
cd /opt/helper-system
docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
    "COPY (SELECT * FROM audit_logs WHERE created_at >= CURRENT_DATE - INTERVAL '1 day') TO STDOUT WITH CSV HEADER" \
    | gzip > "$BACKUP_DIR/audit/audit_logs_${DATE}.csv.gz"

# 3. データアクセスログ（DB: data_access_logs テーブル）
docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
    "COPY (SELECT * FROM data_access_logs WHERE created_at >= CURRENT_DATE - INTERVAL '1 day') TO STDOUT WITH CSV HEADER" \
    | gzip > "$BACKUP_DIR/data-access/data_access_logs_${DATE}.csv.gz"

# 4. コンプライアンスログ（DB: compliance_logs テーブル）
docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
    "COPY (SELECT * FROM compliance_logs WHERE created_at >= CURRENT_DATE - INTERVAL '1 day') TO STDOUT WITH CSV HEADER" \
    | gzip > "$BACKUP_DIR/compliance/compliance_logs_${DATE}.csv.gz"

# タイムスタンプマーカー更新
touch "$LAST_BACKUP_MARKER"

# S3アップロード（設定されている場合）
if command -v aws &> /dev/null && [ -n "$S3_BUCKET" ]; then
    aws s3 sync "$BACKUP_DIR/" "s3://${S3_BUCKET}/backups/logs/" --quiet
fi

# バックアップサイズ集計
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "[$TIMESTAMP] ログバックアップ完了 - 合計サイズ: $TOTAL_SIZE" >> "$LOG_FILE"

# 成功通知送信
/opt/helper-system/scripts/backup-notify.sh success "ログバックアップ" "$TOTAL_SIZE"
```

### バックアップ通知スクリプト (`scripts/backup-notify.sh`)

```bash
#!/bin/bash
# backup-notify.sh - バックアップ成否通知
set -euo pipefail

STATUS="$1"        # success | failure
TARGET="$2"        # バックアップ対象名
DETAIL="${3:-}"     # 追加情報（サイズ、エラーメッセージ等）
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

SLACK_WEBHOOK="${SLACK_BACKUP_WEBHOOK_URL:-}"
NOTIFICATION_LOG="/var/log/helper-backup-notify.log"

# ログ記録
echo "[$TIMESTAMP] $STATUS: $TARGET - $DETAIL" >> "$NOTIFICATION_LOG"

# Slack通知
if [ -n "$SLACK_WEBHOOK" ]; then
    if [ "$STATUS" = "success" ]; then
        EMOJI="white_check_mark"
        COLOR="#36a64f"
        TEXT="バックアップ成功: $TARGET ($DETAIL)"
    else
        EMOJI="x"
        COLOR="#ff0000"
        TEXT="バックアップ失敗: $TARGET - $DETAIL"
    fi

    PAYLOAD=$(cat <<EOF
{
  "attachments": [{
    "color": "$COLOR",
    "title": ":${EMOJI}: ${TEXT}",
    "fields": [
      {"title": "対象", "value": "$TARGET", "short": true},
      {"title": "時刻", "value": "$TIMESTAMP", "short": true},
      {"title": "詳細", "value": "$DETAIL", "short": false}
    ]
  }]
}
EOF
)

    curl -s -X POST -H 'Content-type: application/json' \
        --data "$PAYLOAD" "$SLACK_WEBHOOK" > /dev/null 2>&1
fi

# メール通知（失敗時のみ）
if [ "$STATUS" = "failure" ] && command -v mail &> /dev/null; then
    echo "バックアップ失敗: $TARGET at $TIMESTAMP\n詳細: $DETAIL" | \
        mail -s "[ALERT] バックアップ失敗: $TARGET" "${BACKUP_ALERT_EMAIL:-admin@example.com}"
fi
```

**環境変数設定**:
```bash
# .env に追加
SLACK_BACKUP_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
BACKUP_ALERT_EMAIL=admin@your-domain.com
```

---

## トラブルシューティング

### バックアップ失敗

#### ディスク容量不足
```bash
# ディスク使用状況確認
df -h /backups

# 古いバックアップ削除
find /backups -name "backup_*.sql.gz" -mtime +30 -delete
```

#### 権限エラー
```bash
# バックアップディレクトリの権限確認
ls -ld /backups

# 権限修正
sudo chown -R $USER:$USER /backups
chmod 755 /backups
```

### リストア失敗

#### データベース接続エラー
```bash
# PostgreSQL接続確認
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d postgres -c "SELECT version();"

# ログ確認
docker compose -f docker-compose.prod.yml logs postgres
```

#### データ不整合
```bash
# マイグレーション状態確認
docker compose -f docker-compose.prod.yml exec backend alembic current

# マイグレーション実行
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## バックアップチェックリスト

### 日次
- [ ] 自動DBバックアップが正常に実行されたか確認
- [ ] 自動ログバックアップが正常に実行されたか確認
- [ ] バックアップファイルサイズが正常範囲か確認
- [ ] S3アップロードが成功したか確認
- [ ] Slack通知が正常に届いているか確認

### 週次
- [ ] バックアップファイルの整合性確認
- [ ] 古いバックアップの削除確認（ローカルディスク）
- [ ] S3ライフサイクル削除の正常動作確認

### 月次
- [ ] テスト環境でリストア検証
- [ ] バックアップ容量の見直し
- [ ] バックアップ手順の見直し

---

## 関連ドキュメント

- [デプロイ手順書](./deployment.md)
- [ロールバック手順書](./rollback.md)
- [トラブルシューティングガイド](./troubleshooting.md)
