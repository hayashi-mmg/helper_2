# ホームヘルパー管理システム - デプロイ手順書

## 目次
- [前提条件](#前提条件)
- [初回デプロイ](#初回デプロイ)
- [更新デプロイ](#更新デプロイ)
- [ロールバック](#ロールバック)
- [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

### サーバー要件
- **OS**: Ubuntu 22.04 LTS以降
- **CPU**: 4コア以上推奨
- **メモリ**: 8GB以上推奨
- **ストレージ**: 100GB以上（SSD推奨）
- **ネットワーク**: 固定IPアドレス、ドメイン設定済み

### 必要なソフトウェア
```bash
# システム更新
sudo apt update && sudo apt upgrade -y

# Docker & Docker Composeインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose V2インストール
sudo apt install docker-compose-plugin -y

# Git、その他ツール
sudo apt install -y git curl wget htop
```

### ドメイン設定
- DNS Aレコード: `your-domain.com` → サーバーIPアドレス
- DNS Aレコード: `www.your-domain.com` → サーバーIPアドレス

---

## 初回デプロイ

### 1. リポジトリクローン
```bash
cd /opt
sudo git clone https://github.com/your-org/helper-system.git
sudo chown -R $USER:$USER helper-system
cd helper-system
```

### 2. 環境変数設定

#### バックエンド環境変数
```bash
cd backend
cp .env.production.template .env.production

# 以下の値を必ず変更してください
nano .env.production
```

**必須変更項目:**
- `SECRET_KEY`: `openssl rand -hex 32` で生成
- `JWT_SECRET_KEY`: `openssl rand -hex 32` で生成
- `ENCRYPTION_KEY`: Python Fernet鍵を生成
- `POSTGRES_PASSWORD`: 強力なパスワード
- `REDIS_PASSWORD`: 強力なパスワード
- `BACKEND_CORS_ORIGINS`: 本番ドメインに設定
- `SMTP_*`: メールサーバー設定

#### フロントエンド環境変数
```bash
cd ../frontend
cp .env.production.template .env.production
nano .env.production
```

**必須変更項目:**
- `VITE_API_BASE_URL`: `https://api.your-domain.com`
- `VITE_WS_URL`: `wss://api.your-domain.com`

#### Docker Compose環境変数
```bash
cd ..
cat > .env <<EOF
POSTGRES_USER=prod_user
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=helper_production
REDIS_PASSWORD=$(openssl rand -base64 32)
VITE_API_BASE_URL=https://api.your-domain.com
VITE_WS_URL=wss://api.your-domain.com
BACKUP_RETENTION_DAYS=30
EOF
```

### 3. SSL証明書取得 (Let's Encrypt)

#### 初回セットアップ
```bash
# Certbot用の一時Nginx設定
mkdir -p nginx/ssl
cat > nginx/nginx-init.conf <<EOF
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 200 'OK';
    }
}
EOF

# 初回Nginx起動
docker run -d --name nginx-init \
  -p 80:80 \
  -v $(pwd)/nginx/nginx-init.conf:/etc/nginx/conf.d/default.conf \
  -v $(pwd)/certbot_www:/var/www/certbot \
  nginx:alpine

# SSL証明書取得
docker run -it --rm \
  -v $(pwd)/certbot_data:/etc/letsencrypt \
  -v $(pwd)/certbot_www:/var/www/certbot \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d kokoro-shift.jp \
  -d www.kokoro-shift.jp \
  -d h.kokoro-shift.jp \
  --email hayaei.com@gmail.com \
  --agree-tos \
  --no-eff-email

# 初回Nginx停止
docker stop nginx-init && docker rm nginx-init
```

### 4. Nginx HTTPS設定更新
```bash
# nginx-https.confのドメイン名を置換
sed -i 's/kokoro-shift.jp/actual-domain.com/g' nginx/nginx-https.conf
```

### 5. 本番環境ビルド＆起動
```bash
# イメージビルド
docker compose -f docker-compose.prod.yml build

# サービス起動
docker-compose -f docker-compose.prod.yml up -d

# ログ確認
docker-compose -f docker-compose.prod.yml logs -f
```

### 6. データベース初期化
```bash
# マイグレーション確認
docker compose -f docker-compose.prod.yml exec backend alembic current

# 初期データ投入 (必要に応じて)
docker compose -f docker-compose.prod.yml exec backend python -m app.scripts.init_data
```

### 7. 動作確認
```bash
# ヘルスチェック
curl -f https://your-domain.com/health
curl -f https://your-domain.com/api/v1/health

# サービス状態確認
docker compose -f docker-compose.prod.yml ps
```

---

## 更新デプロイ

### 1. 現在の状態バックアップ
```bash
# コードのバックアップ
git stash

# データベースバックアップ
docker compose -f docker-compose.prod.yml exec postgres \
  bash -c "pg_dump -U prod_user helper_production | gzip > /backups/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz"
```

### 2. 最新コード取得
```bash
cd /opt/helper-system
git pull origin main
```

### 3. 依存関係更新
```bash
# バックエンド
cd backend
pip install -r requirements.txt

# フロントエンド
cd ../frontend
npm ci
```

### 4. データベースマイグレーション
```bash
cd ..
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 5. イメージ再ビルド
```bash
# 変更があったサービスのみ再ビルド
docker compose -f docker-compose.prod.yml build backend frontend

# サービス再起動 (ダウンタイム最小化)
docker compose -f docker-compose.prod.yml up -d --no-deps --build backend
docker compose -f docker-compose.prod.yml up -d --no-deps --build frontend
```

### 6. 動作確認
```bash
# ヘルスチェック
curl -f https://your-domain.com/health
curl -f https://your-domain.com/api/v1/health

# ログ確認
docker compose -f docker-compose.prod.yml logs --tail=100 backend frontend
```

---

## ロールバック

### 緊急ロールバック手順

#### 1. 前バージョンのコードに戻す
```bash
cd /opt/helper-system

# 直前のコミットに戻す
git log --oneline -n 5  # コミット履歴確認
git reset --hard <commit-hash>

# または特定のタグに戻す
git checkout v1.0.0
```

#### 2. Docker イメージロールバック
```bash
# 前バージョンのイメージを使用
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

#### 3. データベースロールバック (必要な場合)
```bash
# バックアップからリストア
./scripts/restore.sh -f /backups/pre_deploy_20250110_120000.sql.gz --yes

# またはマイグレーションダウングレード
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1
```

#### 4. 動作確認
```bash
curl -f https://your-domain.com/health
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100
```

---

## トラブルシューティング

### サービスが起動しない

#### 1. ログ確認
```bash
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs frontend
docker compose -f docker-compose.prod.yml logs postgres
```

#### 2. 環境変数確認
```bash
docker compose -f docker-compose.prod.yml exec backend env | grep -E "(DATABASE|REDIS|SECRET)"
```

#### 3. データベース接続確認
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d helper_production -c "SELECT version();"
```

### SSL証明書エラー

#### 証明書更新
```bash
docker compose -f docker-compose.prod.yml run --rm certbot renew
docker compose -f docker-compose.prod.yml restart nginx
```

#### 証明書確認
```bash
openssl s_client -connect your-domain.com:443 -servername your-domain.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

### パフォーマンス問題

#### リソース使用状況確認
```bash
docker stats
```

#### スケールアップ (ワーカー数増加)
```bash
docker compose -f docker-compose.prod.yml up -d --scale backend=3
```

### データベースパフォーマンス

#### 接続数確認
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d helper_production -c "SELECT count(*) FROM pg_stat_activity;"
```

#### スロークエリ確認
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d helper_production -c "SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

---

## 定期メンテナンス

### 日次
- [ ] バックアップ確認
- [ ] ログ確認
- [ ] ディスク使用量確認

### 週次
- [ ] セキュリティアップデート適用
- [ ] パフォーマンスメトリクス確認
- [ ] エラーログレビュー

### 月次
- [ ] SSL証明書有効期限確認
- [ ] バックアップリストアテスト
- [ ] 脆弱性スキャン実行

---

## 緊急連絡先

- **システム管理者**: admin@your-domain.com
- **技術サポート**: support@your-domain.com
- **緊急ホットライン**: XXX-XXXX-XXXX

---

## 関連ドキュメント

- [バックアップ・リストア手順](./backup-restore.md)
- [トラブルシューティングガイド](./troubleshooting.md)
- [セキュリティガイドライン](./security.md)
