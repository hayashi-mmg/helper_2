# Docker本番デプロイガイド

Task 12.2: Docker本番イメージビルドとデプロイ手順

## 目次

1. [概要](#概要)
2. [前提条件](#前提条件)
3. [本番環境準備](#本番環境準備)
4. [イメージビルド](#イメージビルド)
5. [デプロイ手順](#デプロイ手順)
6. [サービス管理](#サービス管理)
7. [ヘルスチェック](#ヘルスチェック)
8. [ログ管理](#ログ管理)
9. [トラブルシューティング](#トラブルシューティング)
10. [セキュリティ](#セキュリティ)

---

## 概要

このドキュメントでは、ホームヘルパー管理システムのDocker本番環境へのデプロイ方法を説明します。

### アーキテクチャ

```
        ┌──────────────────────────────────────────┐
        │     Traefik (Reverse Proxy + Auto SSL)   │
        │       Port 80/443 (Let's Encrypt)        │
        │     [traefik/docker-compose.yml]          │
        └─────────┬────────────────────────────────┘
                  │  proxy ネットワーク (外部)
             ┌────┴────┐
             │         │
        ┌────▼────┐ ┌─▼──────────┐
        │Frontend │ │  Backend   │
        │ (Nginx) │ │ (FastAPI)  │
        │Port 3000│ │ Port 8000  │
        └────┬────┘ └──┬─────────┘
             │         │  app_network (内部)
             │  ┌──────┴───────┐
             │  │              │
        ┌────▼──▼─────┐  ┌────▼────┐
        │ PostgreSQL  │  │  Redis  │
        │ Port 5432   │  │Port 6379│
        └─────────────┘  └─────────┘
```

Traefikは別docker-composeファイルで管理され、複数プロジェクトで共有可能。
アプリケーションサービスはDockerラベルでルーティングを定義。

### マルチステージビルドの利点

- **イメージサイズ削減**: ビルド依存関係を除外
- **セキュリティ向上**: 最小限のランタイム依存関係
- **ビルド速度向上**: レイヤーキャッシング最適化
- **本番環境最適化**: 不要なファイルを除外

---

## 前提条件

### 必須ソフトウェア

| ソフトウェア | バージョン | 確認コマンド |
|------------|------------|-------------|
| Docker | 20.10+ | `docker --version` |
| Docker Compose | 2.0+ | `docker-compose --version` |
| Git | 2.0+ | `git --version` |

### サーバー要件

#### 最小構成
- **CPU**: 2コア
- **RAM**: 6GB（ログ基盤Loki+Promtail込み）
- **ストレージ**: 40GB
- **OS**: Ubuntu 22.04 LTS / CentOS 8+

#### 推奨構成
- **CPU**: 4コア以上
- **RAM**: 8GB以上（ログ基盤込みで推奨10GB）
- **ストレージ**: 80GB以上（SSD推奨、ログ保持領域含む）
- **OS**: Ubuntu 22.04 LTS

### ネットワーク要件

- **ポート80**: HTTP（HTTPSへのリダイレクト）
- **ポート443**: HTTPS
- **ポート22**: SSH管理用
- **ファイアウォール**: 外部からは80, 443のみ開放

---

## 本番環境準備

### 1. サーバーセットアップ

```bash
# システム更新
sudo apt update && sudo apt upgrade -y

# Docker インストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose インストール
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# インストール確認
docker --version
docker-compose --version
```

### 2. プロジェクトクローン

```bash
# プロジェクトディレクトリ作成
sudo mkdir -p /opt/helper-system
sudo chown $USER:$USER /opt/helper-system
cd /opt/helper-system

# Gitクローン
git clone https://github.com/your-org/helper-system.git .
git checkout main  # または production ブランチ
```

### 3. 環境変数設定

```bash
# 本番環境変数ファイル作成
cp backend/.env.prod.example backend/.env
cp frontend/.env.prod.example frontend/.env.production

# シークレットキー生成
export SECRET_KEY=$(openssl rand -hex 32)
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export POSTGRES_PASSWORD=$(openssl rand -hex 16)
export REDIS_PASSWORD=$(openssl rand -hex 16)

# バックエンド環境変数編集
nano backend/.env
# 以下を設定:
# - SECRET_KEY
# - JWT_SECRET_KEY
# - DATABASE_URL (PostgreSQLパスワード)
# - REDIS_URL (Redisパスワード)
# - BACKEND_CORS_ORIGINS (本番ドメイン)
# - SMTP設定

# フロントエンド環境変数編集
nano frontend/.env.production
# 以下を設定:
# - VITE_API_URL (本番APIのURL)
# - VITE_APP_URL (本番ドメイン)
# - 外部サービスAPIキー

# Docker Compose用環境変数
cat > .env << EOF
# PostgreSQL
POSTGRES_DB=helper_prod_db
POSTGRES_USER=helper_user
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# Redis
REDIS_PASSWORD=${REDIS_PASSWORD}

# Application
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Frontend
VITE_API_URL=https://api.yourdomain.com/api/v1

# Monitoring
GRAFANA_PASSWORD=$(openssl rand -hex 16)
EOF

# パーミッション設定
chmod 600 backend/.env
chmod 600 frontend/.env.production
chmod 600 .env
```

### 4. Traefikセットアップ（リバースプロキシ + 自動SSL）

TraefikはLet's Encrypt証明書を自動取得・更新します。手動でのSSL設定は不要です。

```bash
# proxyネットワーク作成
docker network create proxy

# Traefik起動
cd traefik
docker compose up -d
cd ..

# ACME証明書取得の確認
docker logs traefik
```

Traefikの設定ファイル:
- `traefik/docker-compose.yml` — Traefikコンテナ定義
- `traefik/traefik.yml` — 静的設定（エントリポイント、ACME、プロバイダ）
- `traefik/dynamic/middlewares.yml` — ミドルウェア（レート制限、セキュリティヘッダー、圧縮）

---

## イメージビルド

### 1. ビルド前チェック

```bash
# 環境変数検証
cd backend && python scripts/validate_env.py
cd ../frontend && node scripts/validate-env.js
cd ..

# Dockerfileの存在確認
ls -la backend/Dockerfile.prod
ls -la frontend/Dockerfile.prod

# .dockerignoreの存在確認
ls -la backend/.dockerignore
ls -la frontend/.dockerignore
```

### 2. イメージビルド

```bash
# すべてのイメージをビルド
docker-compose -f docker-compose.prod.yml build

# または個別にビルド
docker-compose -f docker-compose.prod.yml build backend
docker-compose -f docker-compose.prod.yml build frontend

# ビルドログ確認
docker-compose -f docker-compose.prod.yml build --progress=plain
```

### 3. イメージサイズ確認

```bash
# ビルドされたイメージ一覧
docker images | grep helper

# 期待されるサイズ:
# backend: ~300-400MB (Python + 依存関係)
# frontend: ~50-100MB (Nginx + 静的ファイル)
```

### 4. イメージのレジストリプッシュ（オプション）

```bash
# Docker Hubにログイン
docker login

# タグ付け
docker tag helper4-backend:latest your-dockerhub-username/helper-backend:v1.0.0
docker tag helper4-frontend:latest your-dockerhub-username/helper-frontend:v1.0.0

# プッシュ
docker push your-dockerhub-username/helper-backend:v1.0.0
docker push your-dockerhub-username/helper-frontend:v1.0.0
```

---

## デプロイ手順

### 初回デプロイ

```bash
# 1. データベースとRedisのみ起動（初期化のため）
docker-compose -f docker-compose.prod.yml up -d postgres redis

# 2. データベース起動待ち（30秒）
sleep 30

# 3. データベースマイグレーション実行
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 4. 初期データ投入（必要な場合）
# docker-compose -f docker-compose.prod.yml run --rm backend python scripts/seed_data.py

# 5. すべてのサービスを起動
docker-compose -f docker-compose.prod.yml up -d

# 6. 起動確認
docker-compose -f docker-compose.prod.yml ps
```

### アップデートデプロイ

```bash
# 1. 最新コードを取得
git pull origin main

# 2. 環境変数の変更確認
git diff HEAD~1 backend/.env.example
git diff HEAD~1 frontend/.env.example

# 3. イメージ再ビルド
docker compose -f docker-compose.prod.yml build

# 4. データベースマイグレーション（必要な場合）
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 5. ローリングアップデート
docker compose -f docker-compose.prod.yml up -d --no-deps --build backend
docker compose -f docker-compose.prod.yml up -d --no-deps --build frontend

# 6. ヘルスチェック
docker compose -f docker-compose.prod.yml ps
curl -f https://localhost/api/v1/health -k || echo "Health check failed"
```

---

## サービス管理

### 基本コマンド

```bash
# すべてのサービス起動
docker-compose -f docker-compose.prod.yml up -d

# すべてのサービス停止
docker-compose -f docker-compose.prod.yml down

# 特定サービスの再起動
docker-compose -f docker-compose.prod.yml restart backend

# サービス状態確認
docker-compose -f docker-compose.prod.yml ps

# リソース使用状況
docker stats

# ログ確認
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs --tail=100 frontend
```

### スケーリング

```bash
# バックエンドを3インスタンスに拡大
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# フロントエンドを2インスタンスに縮小
docker-compose -f docker-compose.prod.yml up -d --scale frontend=2

# 現在のスケール確認
docker-compose -f docker-compose.prod.yml ps
```

---

## ヘルスチェック

### 自動ヘルスチェック

Docker Composeで設定されたヘルスチェック:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### 手動ヘルスチェック

```bash
# バックエンドヘルスチェック
curl -f http://localhost:8000/health
# 期待: {"status": "healthy", "database": "connected", "redis": "connected"}

# フロントエンドヘルスチェック
curl -f http://localhost:3000/health
# 期待: HTTP 200 OK

# Nginx経由でのヘルスチェック
curl -f https://yourdomain.com/api/health
curl -f https://yourdomain.com/health

# データベース接続確認
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U helper_user -d helper_prod_db

# Redis接続確認
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a ${REDIS_PASSWORD} ping
```

### モニタリング

```bash
# Prometheus
open http://localhost:9090

# Grafana
open http://localhost:3001
# Username: admin
# Password: ${GRAFANA_PASSWORD}

# コンテナメトリクス
docker stats --no-stream
```

---

## ログ管理

### ログ確認

```bash
# リアルタイムログ
docker-compose -f docker-compose.prod.yml logs -f

# 特定サービスのログ
docker-compose -f docker-compose.prod.yml logs -f backend

# 最新100行のログ
docker-compose -f docker-compose.prod.yml logs --tail=100 backend

# タイムスタンプ付きログ
docker-compose -f docker-compose.prod.yml logs -f -t backend

# 特定期間のログ
docker-compose -f docker-compose.prod.yml logs --since="2025-07-13T10:00:00" backend
```

### ログローテーション

Docker Composeでログローテーション設定済み:

```yaml
# Backend（高トラフィックサービス）
logging:
  driver: "json-file"
  options:
    max-size: "50m"      # 最大50MB
    max-file: "5"        # 最大5ファイル保持（合計250MB/サービス）

# PostgreSQL
logging:
  driver: "json-file"
  options:
    max-size: "20m"      # 最大20MB
    max-file: "5"        # 最大5ファイル保持（合計100MB）

# Frontend / Redis / Loki / Promtail（低トラフィックサービス）
logging:
  driver: "json-file"
  options:
    max-size: "20m"      # 最大20MB
    max-file: "3"        # 最大3ファイル保持（合計60MB/サービス）
```

> **容量設計の根拠**: Promtailがログを収集する前にDockerがファイルをローテーションしてログが消失するリスクを防ぐため、高トラフィックサービス（Backend）は50MB×5ファイル（250MB）に拡大。Traefikは別docker-composeで管理（同設定）。VPS全体のログストレージ上限は約750MBを想定。

手動でのログクリア:

```bash
# 全コンテナのログクリア
docker-compose -f docker-compose.prod.yml down
sudo truncate -s 0 /var/lib/docker/containers/*/*-json.log
docker-compose -f docker-compose.prod.yml up -d
```

---

## トラブルシューティング

### コンテナが起動しない

```bash
# エラーログ確認
docker-compose -f docker-compose.prod.yml logs backend

# コンテナ詳細情報
docker inspect helper4-backend

# ヘルスチェック状態
docker-compose -f docker-compose.prod.yml ps

# コンテナ内でコマンド実行
docker-compose -f docker-compose.prod.yml exec backend bash
```

### データベース接続エラー

```bash
# PostgreSQL接続確認
docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.database import engine
import asyncio
async def test():
    async with engine.connect() as conn:
        result = await conn.execute('SELECT 1')
        print('接続成功:', result.scalar())
asyncio.run(test())
"

# データベースログ確認
docker-compose -f docker-compose.prod.yml logs postgres

# データベースに直接接続
docker-compose -f docker-compose.prod.yml exec postgres psql -U helper_user -d helper_prod_db
```

### Redis接続エラー

```bash
# Redis接続テスト
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a ${REDIS_PASSWORD} ping

# Redisログ確認
docker-compose -f docker-compose.prod.yml logs redis

# Python経由でRedis接続確認
docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.core.redis import redis_client
import asyncio
async def test():
    await redis_client.set('test', 'ok')
    value = await redis_client.get('test')
    print('接続成功:', value)
asyncio.run(test())
"
```

### パフォーマンス問題

```bash
# リソース使用状況
docker stats

# コンテナCPU/メモリ制限確認
docker inspect helper4-backend | grep -A 10 Resources

# スロークエリログ確認
docker-compose -f docker-compose.prod.yml logs backend | grep "slow query"

# ネットワーク遅延確認
docker-compose -f docker-compose.prod.yml exec backend ping postgres
```

### ディスク容量不足

```bash
# ディスク使用量確認
df -h
docker system df

# 未使用リソース削除
docker system prune -a
docker volume prune

# 特定イメージ削除
docker rmi $(docker images -f "dangling=true" -q)

# ログファイルサイズ確認
sudo du -sh /var/lib/docker/containers/*/
```

---

## セキュリティ

### セキュリティチェックリスト

- [ ] 全環境変数を`.env`ファイルで管理（Gitにコミットしない）
- [ ] SSL/TLS証明書を設定（Let's Encrypt推奨）
- [ ] Dockerコンテナを非rootユーザーで実行
- [ ] ファイアウォール設定（UFW/iptables）
- [ ] データベース・Redisにパスワード設定
- [ ] 定期的なセキュリティアップデート
- [ ] バックアップの定期実行と確認
- [ ] ログ監視とアラート設定
- [ ] 不要なポート公開を削除
- [ ] Docker Socketへのアクセス制限

### セキュリティ強化

```bash
# ファイアウォール設定
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable
sudo ufw status

# Docker Socketのパーミッション
sudo chmod 660 /var/run/docker.sock
sudo chown root:docker /var/run/docker.sock

# 自動セキュリティアップデート
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 脆弱性スキャン

```bash
# Trivyインストール
sudo apt install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt update && sudo apt install trivy

# イメージスキャン
trivy image helper4-backend:latest
trivy image helper4-frontend:latest

# 高/重大な脆弱性のみ表示
trivy image --severity HIGH,CRITICAL helper4-backend:latest
```

---

## まとめ

### デプロイ前チェックリスト

#### 環境準備
- [ ] Docker・Docker Composeインストール済み
- [ ] サーバー要件を満たしている（CPU: 4コア, RAM: 8GB以上（ログ基盤込みで推奨10GB）, ストレージ: 80GB）
- [ ] プロジェクトをクローン済み
- [ ] 本番ドメイン取得済み
- [ ] SSL証明書取得済み

#### 設定
- [ ] `backend/.env`に本番環境変数を設定
- [ ] `frontend/.env.production`に本番環境変数を設定
- [ ] `.env`（Docker Compose用）に環境変数を設定
- [ ] 環境変数検証スクリプトで確認済み
- [ ] 全シークレットを強力なランダム値に変更

#### イメージビルド
- [ ] Dockerfileが正しく設定されている
- [ ] .dockerignoreが設定されている
- [ ] イメージビルド成功
- [ ] イメージサイズが適切（backend: <400MB, frontend: <100MB）

#### デプロイ
- [ ] データベースマイグレーション実行済み
- [ ] 全サービス起動成功
- [ ] ヘルスチェック通過
- [ ] 本番ドメインでアクセス可能

#### セキュリティ
- [ ] ファイアウォール設定済み
- [ ] SSL/TLS有効化
- [ ] 非rootユーザーで実行
- [ ] パスワード保護設定済み

#### 監視・バックアップ
- [ ] ログローテーション設定済み
- [ ] モニタリングツール稼働中（Prometheus/Grafana）
- [ ] 自動バックアップ設定済み
- [ ] バックアップリストア手順確認済み

#### ログ監査基盤（[ログ監査・収集強化仕様書](./logging_audit_specification.md)参照）
- [ ] Loki サービス起動・ヘルスチェック通過
- [ ] Promtail サービス起動・ログ収集確認
- [ ] Grafana に Loki データソース追加済み
- [ ] ログ検索ダッシュボード表示確認
- [ ] セキュリティアラートルール設定済み
- [ ] ログ完全性検証バッチ（日次）設定済み
- [ ] データ保持期間自動削除バッチ設定済み

### ログ収集基盤サービス（Loki + Promtail）

※ 詳細設定は[ログ監査・収集強化仕様書](./logging_audit_specification.md) セクション2を参照

```yaml
# docker-compose.prod.yml への追加サービス

  loki:
    image: grafana/loki:2.9
    container_name: helper-loki
    command: -config.file=/etc/loki/loki-config.yml
    volumes:
      - loki_data:/loki
      - ./loki/loki-config.yml:/etc/loki/loki-config.yml:ro
    ports:
      - "127.0.0.1:3100:3100"
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3100/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "3"
    networks:
      - app-network

  promtail:
    image: grafana/promtail:2.9
    container_name: helper-promtail
    command: -config.file=/etc/promtail/promtail-config.yml
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/log:/var/log:ro
      - app_logs:/app/logs:ro
      - ./promtail/promtail-config.yml:/etc/promtail/promtail-config.yml:ro
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.25'
    depends_on:
      loki:
        condition: service_healthy
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "3"
    networks:
      - app-network
```

**追加リソース要件**:
- Loki: メモリ512MB、CPU 0.5コア
- Promtail: メモリ128MB、CPU 0.25コア
- ストレージ: Lokiデータ用に10-20GB追加（31日ホット保持 + 圧縮）

**起動確認**:
```bash
# Lokiヘルスチェック
curl -f http://localhost:3100/ready

# Promtailターゲット確認
curl -f http://localhost:9080/targets
```

### 参考資料

- [Docker公式ドキュメント](https://docs.docker.com/)
- [Docker Compose公式ドキュメント](https://docs.docker.com/compose/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Vite Production Build](https://vitejs.dev/guide/build.html)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Let's Encrypt](https://letsencrypt.org/)
