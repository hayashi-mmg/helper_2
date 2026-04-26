# 運用クイックリファレンス (デプロイ + バックアップ)

本番VPS `h.kokoro-shift.jp` (`/opt/helper-system/`) での日常運用コマンド集。
詳細仕様や設計意図は末尾「関連ドキュメント」参照。

---

## 0. 前提

- 作業ディレクトリ: `/opt/helper-system`
- 環境ファイル: `.env.production` (R2 / Slack / メール通知設定済み)
- すべて `ssh user@h.kokoro-shift.jp` 後に実行する想定

---

## 1. デイリー運用

| やりたいこと | コマンド |
|------------|---------|
| サービス全体の稼働確認 | `./deploy.sh status` |
| バックエンドのログ追従 | `./deploy.sh logs backend` |
| 全サービスのログ追従 | `./deploy.sh logs` |
| Traefik のログ追従 | `./deploy.sh logs traefik` |
| 直近20件のデプロイ履歴 | `./deploy.sh history` |
| 手動バックアップ (R2 含む) | `./scripts/backup.sh` |
| バックアップ完全性テスト | `./scripts/backup.sh test` |

**自動実行 (cron)**:
- `02:00` 日次DBバックアップ (`backup.sh`)
- `02:30` 日次ログバックアップ (`backup-logs.sh`)
- 月初 `03:00` バックアップ網羅性検証 (`verify-backup-tables.sh`)
- 月初 `04:00` ログのアーカイブ移行 (`archive-logs.sh`)

---

## 2. 通常デプロイ (機能追加・修正)

```bash
# 1. リモートに最新コードがあることを確認
git fetch origin

# 2. 通常デプロイ実行
#    内部処理: safety check → pre-deploy backup (R2) → git pull
#                → docker build → alembic upgrade → ローリング再起動 → Slack通知
./deploy.sh update

# 3. デプロイ後の確認
./deploy.sh status
curl -s https://h.kokoro-shift.jp/api/v1/health | jq .
```

**特殊オプション**:
```bash
./deploy.sh update --force                # uncommitted変更を無視 (緊急時のみ)
./deploy.sh update --force --skip-backup  # バックアップ不要なホットフィックス時
```

> ⚠️ デプロイ前 SHA は `.deploy-history` に自動記録される (rollback 用)

---

## 3. ロールバック

### 3-1. コードのみロールバック (DB変更を伴わない場合)

```bash
# 直前のデプロイへ戻す
./deploy.sh rollback

# 任意SHA指定
./deploy.sh rollback abc1234

# 確認
./deploy.sh status
./deploy.sh history 5
```

### 3-2. DB変更を伴うロールバック

`alembic` migration が新規追加されていた場合は **手動 downgrade** が必要:

```bash
# 1. 直前のリビジョン確認 (デプロイ前に控えておく)
./deploy.sh logs backend | grep -i alembic

# 2. ターゲットリビジョンへ downgrade
docker compose --env-file .env.production -f docker-compose.prod.yml \
  run --rm backend alembic downgrade <target_revision>

# 3. その後コードロールバック
./deploy.sh rollback
```

### 3-3. データも含めて戻す (最終手段)

`/scripts/restore.sh` で R2 上の最新DBダンプから復旧。**全データ巻き戻りに注意**。
詳細手順: [docs/backup-restore.md](../backup-restore.md) の「リストア手順」章

---

## 4. 手動バックアップとリストア

### 4-1. 緊急バックアップ取得

```bash
# 全部 (DB + Redis + uploads + config) を /backups と R2 へ
./scripts/backup.sh

# 結果の確認
ls -lh /backups/db/ | tail -3
aws s3 ls s3://helper-backups-prod/backups/db/ \
  --profile r2 --endpoint-url=https://<account_id>.r2.cloudflarestorage.com | tail -3
```

### 4-2. R2 から最新DBダンプ取得

```bash
LATEST=$(aws s3 ls s3://helper-backups-prod/backups/db/ \
  --profile r2 --endpoint-url=https://<account_id>.r2.cloudflarestorage.com \
  | sort | tail -1 | awk '{print $4}')

aws s3 cp "s3://helper-backups-prod/backups/db/$LATEST" ./ \
  --profile r2 --endpoint-url=https://<account_id>.r2.cloudflarestorage.com
```

### 4-3. リストア演習 (四半期)

[docs/operations/backup-restore-drill.md](./backup-restore-drill.md) のチェックリストに従う

---

## 5. トラブル対応

### 5-1. デプロイが失敗した

```bash
# 1. エラーログ確認
./deploy.sh logs backend | tail -50

# 2. 履歴確認
./deploy.sh history 5

# 3. 直前の正常状態へ戻す
./deploy.sh rollback

# 4. Slack に届いた失敗通知の詳細を確認
```

### 5-2. バックアップが失敗した

```bash
# 1. 直近の cron 実行ログ
sudo tail -100 /var/log/helper-backup.log

# 2. 完全性テスト
./scripts/backup.sh test

# 3. 手動再実行
sudo /opt/helper-system/scripts/backup.sh

# 4. 必須テーブル網羅性チェック
sudo /opt/helper-system/scripts/verify-backup-tables.sh
```

### 5-3. R2 アップロードが失敗する

```bash
# 認証確認
aws s3 ls s3://helper-backups-prod/ \
  --profile r2 --endpoint-url=https://<account_id>.r2.cloudflarestorage.com

# 失敗する場合は ~/.aws/credentials の [r2] プロファイルを再設定
aws configure --profile r2
```

### 5-4. アプリが応答しない

```bash
# ヘルスチェック
curl -v https://h.kokoro-shift.jp/api/v1/health

# 全コンテナ状態
./deploy.sh status

# DB / Redis 単体確認
docker compose --env-file .env.production -f docker-compose.prod.yml \
  exec db pg_isready
docker compose --env-file .env.production -f docker-compose.prod.yml \
  exec redis redis-cli -a "$REDIS_PASSWORD" ping
```

詳細インシデント手順: [docs/operations/incident-response-guide.md](./incident-response-guide.md)

---

## 6. 通知連携の設定状況確認

| 項目 | 確認コマンド | 期待値 |
|-----|-------------|-------|
| Slack Webhook | `grep SLACK_BACKUP_WEBHOOK_URL .env.production` | 値あり |
| メール通知先 | `grep BACKUP_ALERT_EMAIL .env.production` | 値あり |
| Slackテスト送信 | `./scripts/backup-notify.sh success "テスト" "通知テスト"` | Slack に届く |

---

## 7. cron 設定 (本番VPS既定)

```cron
# /var/spool/cron/crontabs/root
0  2 * * * /opt/helper-system/scripts/backup.sh                >> /var/log/helper-backup.log 2>&1
30 2 * * * /opt/helper-system/scripts/backup-logs.sh           >> /var/log/helper-log-backup.log 2>&1
0  4 1 * * /opt/helper-system/scripts/archive-logs.sh          >> /var/log/helper-archive.log 2>&1
0  3 1 * * /opt/helper-system/scripts/verify-backup-tables.sh  >> /var/log/helper-backup-verify.log 2>&1
```

確認: `sudo crontab -l`

---

## 関連ドキュメント (詳細仕様)

| 目的 | ドキュメント |
|-----|-------------|
| 本番VPS固有のセットアップ手順 | [vps-deployment-h.kokoro-shift.jp.md](./vps-deployment-h.kokoro-shift.jp.md) |
| Docker / 本番デプロイの詳細 | [../DOCKER_DEPLOYMENT.md](../DOCKER_DEPLOYMENT.md) / [production-deployment-guide.md](./production-deployment-guide.md) |
| バックアップ戦略・R2セットアップ・リストア手順 | [../backup-restore.md](../backup-restore.md) |
| 四半期リストア演習ランブック | [backup-restore-drill.md](./backup-restore-drill.md) |
| インシデント対応 | [incident-response-guide.md](./incident-response-guide.md) |
| 監視・アラート | [monitoring-guide.md](./monitoring-guide.md) |
| 環境変数リファレンス | [../ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md) |
