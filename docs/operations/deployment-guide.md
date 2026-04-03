# デプロイメントガイド - ホームヘルパー管理システム

## 概要

本文書は、ホームヘルパー管理システムの本番環境へのデプロイメント手順を説明します。アクセシビリティ対応とセキュリティを最優先とした運用を前提としています。

## 前提条件

### システム要件
- **OS**: Ubuntu Server 22.04 LTS
- **メモリ**: 最低8GB、推奨16GB
- **ストレージ**: 最低100GB SSD
- **CPU**: 最低4コア、推奨8コア
- **ネットワーク**: 固定IPアドレス、HTTPS対応

### 必要なソフトウェア
- Docker Engine (24.0+)
- Docker Compose (2.20+)
- Git
- curl
- openssl

## 初回デプロイメント

### 1. サーバー準備

```bash
# システム更新
sudo apt update && sudo apt upgrade -y

# 必要なパッケージインストール
sudo apt install -y git curl wget gnupg lsb-release

# Dockerインストール
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Dockerサービス開始
sudo systemctl enable docker
sudo systemctl start docker

# 非rootユーザーをdockerグループに追加
sudo usermod -aG docker $USER
```

### 2. アプリケーションディレクトリ作成

```bash
# アプリケーション用ディレクトリ作成
sudo mkdir -p /opt/home-helper-system
sudo chown $USER:$USER /opt/home-helper-system
cd /opt/home-helper-system

# Gitリポジトリクローン
git clone https://github.com/your-org/home-helper-system.git .
```

### 3. 環境変数設定

```bash
# 本番環境用設定ファイル作成
cp .env.example .env.production

# 環境変数編集（セキュアな値に変更）
nano .env.production
```

#### 設定すべき環境変数

```bash
# データベース設定
POSTGRES_DB=helper_db
POSTGRES_USER=helper_user
POSTGRES_PASSWORD=<secure_password>

# Redis設定
REDIS_PASSWORD=<secure_password>

# アプリケーション設定
SECRET_KEY=<generate_secure_key>
JWT_SECRET_KEY=<generate_secure_key>
ENVIRONMENT=production

# SSL設定
SSL_DOMAIN=your-domain.com
SSL_EMAIL=admin@your-domain.com

# CORS設定
CORS_ORIGINS=["https://your-domain.com"]
VITE_API_URL=https://your-domain.com/api

# 通知設定
SLACK_WEBHOOK_URL=<optional>
NOTIFICATION_EMAIL=admin@your-domain.com

# 監視設定
GRAFANA_PASSWORD=<secure_password>
```

### 4. SSL証明書設定

```bash
# SSL証明書ディレクトリ作成
mkdir -p nginx/ssl

# Let's Encrypt証明書取得（本番環境）
chmod +x nginx/scripts/renew-ssl.sh
./nginx/scripts/renew-ssl.sh generate
```

### 5. データベース初期化

```bash
# PostgreSQLコンテナ起動
docker-compose -f docker-compose.prod.yml up -d postgres redis

# データベース初期化待機
sleep 30

# マイグレーション実行
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 初期データ投入（必要に応じて）
docker-compose -f docker-compose.prod.yml exec backend python scripts/init_data.py
```

### 6. 本番環境起動

```bash
# 全サービス起動
docker-compose -f docker-compose.prod.yml up -d

# サービス状態確認
docker-compose -f docker-compose.prod.yml ps

# ヘルスチェック実行
chmod +x scripts/health-check.sh
./scripts/health-check.sh
```

### 7. 監視システム設定

```bash
# Prometheus・Grafanaアクセス確認
curl -f http://localhost:9090  # Prometheus
curl -f http://localhost:3001  # Grafana

# Grafana初期設定
# ブラウザで http://your-domain:3001 にアクセス
# admin / ${GRAFANA_PASSWORD} でログイン
# ダッシュボードインポート: monitoring/grafana/dashboards/
```

## 更新デプロイメント

### 1. 事前確認

```bash
# 現在のシステム状態確認
./scripts/health-check.sh

# バックアップ実行
./scripts/backup.sh

# 最新コード取得
git fetch origin
git checkout main
git pull origin main
```

### 2. ローリングアップデート

```bash
# 新しいイメージをプル
docker-compose -f docker-compose.prod.yml pull

# サービス停止前の確認
docker-compose -f docker-compose.prod.yml ps

# ローリングアップデート実行
docker-compose -f docker-compose.prod.yml up -d --no-deps --build

# データベースマイグレーション（必要時）
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 3. デプロイ後確認

```bash
# サービス状態確認
docker-compose -f docker-compose.prod.yml ps

# ヘルスチェック実行
./scripts/health-check.sh

# ログ確認
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
docker-compose -f docker-compose.prod.yml logs --tail=100 frontend
docker-compose -f docker-compose.prod.yml logs --tail=100 nginx

# アクセシビリティ確認
curl -f https://your-domain.com/health
curl -f https://your-domain.com/api/health
```

## ロールバック手順

### 1. 緊急ロールバック

```bash
# 前のバージョンのコンテナタグを確認
docker images | grep home-helper-system

# 前のバージョンに戻す
git log --oneline -10
git checkout <previous_commit>

# 前のイメージで再起動
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# ヘルスチェック実行
./scripts/health-check.sh
```

### 2. データベースロールバック

```bash
# データベースバックアップから復元
docker-compose -f docker-compose.prod.yml exec postgres pg_restore -h localhost -U $POSTGRES_USER -d $POSTGRES_DB /backups/helper_system_database_YYYYMMDD_HHMMSS.sql

# マイグレーション状態確認
docker-compose -f docker-compose.prod.yml exec backend alembic current
```

## 監視・アラート設定

### 1. Prometheusアラート設定

```bash
# アラートルール確認
curl -f http://localhost:9090/api/v1/rules

# アラート状態確認
curl -f http://localhost:9090/api/v1/alerts
```

### 2. ログ監視設定

```bash
# ログローテーション設定
sudo nano /etc/logrotate.d/home-helper-system

# 内容:
/opt/home-helper-system/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        docker-compose -f /opt/home-helper-system/docker-compose.prod.yml restart nginx
    endscript
}
```

### 3. 自動バックアップ設定

```bash
# cronジョブ設定
sudo crontab -e

# 内容追加:
# 毎日3:00にバックアップ実行
0 3 * * * /opt/home-helper-system/scripts/backup.sh

# 毎時間ヘルスチェック実行
0 * * * * /opt/home-helper-system/scripts/health-check.sh endpoints
```

## セキュリティ設定

### 1. ファイアウォール設定

```bash
# UFW有効化
sudo ufw enable

# 必要なポートのみ開放
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS

# 管理者用ポート（制限付き）
sudo ufw allow from <admin_ip> to any port 3001  # Grafana
sudo ufw allow from <admin_ip> to any port 9090  # Prometheus
```

### 2. SSL証明書自動更新

```bash
# SSL証明書更新cronジョブ
sudo crontab -e

# 内容追加:
# 毎日2:00にSSL証明書チェック・更新
0 2 * * * /opt/home-helper-system/nginx/scripts/renew-ssl.sh
```

### 3. セキュリティ更新

```bash
# システム自動更新設定
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Dockerイメージ定期更新
# cronで週1回最新イメージチェック
0 1 * * 0 cd /opt/home-helper-system && docker-compose -f docker-compose.prod.yml pull && docker-compose -f docker-compose.prod.yml up -d
```

## トラブルシューティング

### 1. サービス起動失敗

```bash
# ログ確認
docker-compose -f docker-compose.prod.yml logs <service_name>

# コンテナ状態確認
docker ps -a

# 設定ファイル確認
docker-compose -f docker-compose.prod.yml config
```

### 2. データベース接続エラー

```bash
# PostgreSQL接続テスト
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U $POSTGRES_USER

# 接続情報確認
docker-compose -f docker-compose.prod.yml exec backend env | grep DATABASE
```

### 3. SSL証明書問題

```bash
# 証明書状態確認
openssl x509 -in nginx/ssl/server.crt -text -noout

# 証明書更新
./nginx/scripts/renew-ssl.sh renew
```

## パフォーマンス最適化

### 1. データベース最適化

```bash
# データベース統計更新
docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "ANALYZE;"

# インデックス確認
docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\di"
```

### 2. Nginx最適化

```bash
# アクセスログ確認
tail -f nginx/logs/access.log

# エラーログ確認
tail -f nginx/logs/error.log

# キャッシュ状態確認
curl -I https://your-domain.com/static/
```

## アクセシビリティ確認

### 1. 自動アクセシビリティテスト

```bash
# axe-coreによるチェック
npx @axe-core/cli https://your-domain.com --tags wcag2a,wcag2aa

# Lighthouseによるアクセシビリティスコア
npx lighthouse https://your-domain.com --only-categories=accessibility --output=json
```

### 2. 手動アクセシビリティ確認

- スクリーンリーダー（NVDA、JAWS）での動作確認
- キーボードのみでの操作確認
- 高コントラストモードでの表示確認
- フォントサイズ拡大時の表示確認

## 連絡先・エスカレーション

### 緊急時連絡先
- **システム管理者**: admin@your-domain.com
- **開発チーム**: dev-team@your-domain.com
- **緊急対応**: +81-XX-XXXX-XXXX

### エスカレーション手順
1. **Level 1**: 自動アラート→運用チーム
2. **Level 2**: 15分以内に解決しない→システム管理者
3. **Level 3**: 30分以内に解決しない→開発チーム
4. **Level 4**: 1時間以内に解決しない→CTO

---

**注意**: 本番環境での作業は必ず事前にバックアップを取得し、メンテナンス時間内で実施してください。