# ホームヘルパー管理システム 本番環境デプロイ・運用ガイド

## 目次
1. [システム概要](#システム概要)
2. [事前準備](#事前準備)
3. [初回デプロイ手順](#初回デプロイ手順)
4. [継続的運用](#継続的運用)
5. [監視・アラート](#監視アラート)
6. [障害対応](#障害対応)
7. [バックアップ・復旧](#バックアップ復旧)
8. [セキュリティ管理](#セキュリティ管理)

---

## システム概要

### アーキテクチャ
```
Internet → [Nginx(SSL)] → [FastAPI Backend] → [PostgreSQL + Redis]
                      ↓
                 [React Frontend]
                      ↓
            [Prometheus + Grafana 監視]
```

### 技術スタック
- **OS**: Ubuntu Server 22.04 LTS
- **コンテナ**: Docker Swarm
- **フロントエンド**: React 19 + Vite + TypeScript
- **バックエンド**: FastAPI + Python 3.11
- **データベース**: PostgreSQL 15 (Master-Slave構成)
- **キャッシュ**: Redis 7 (Cluster構成)
- **Webサーバー**: Nginx (リバースプロキシ + SSL終端)
- **監視**: Prometheus + Grafana + Alertmanager

---

## 事前準備

### 1. サーバー要件

#### 最小構成 (小規模運用: ~500ユーザー)
- **CPU**: 4 vCPU
- **メモリ**: 8GB RAM
- **ストレージ**: 100GB SSD
- **ネットワーク**: 1Gbps

#### 推奨構成 (中規模運用: ~2000ユーザー)
- **CPU**: 8 vCPU
- **メモリ**: 16GB RAM
- **ストレージ**: 200GB SSD
- **ネットワーク**: 1Gbps

#### 本格運用構成 (大規模運用: 5000+ユーザー)
- **マネージャーノード**: 3台 (8 vCPU, 16GB RAM, 200GB SSD)
- **ワーカーノード**: 5台以上 (4 vCPU, 8GB RAM, 100GB SSD)
- **ロードバランサー**: 外部ALB推奨

### 2. ドメイン・DNS設定

```bash
# 必要なDNSレコード
helper-system.example.com.     A      203.0.113.10
www.helper-system.example.com. CNAME  helper-system.example.com.
```

### 3. 必要なアカウント・サービス

- **VPSプロバイダー**: さくらのVPS / ConoHa / DigitalOcean等
- **ドメイン管理**: お名前.com / Route53等
- **SSL証明書**: Let's Encrypt (自動取得)
- **監視通知**: Slack Workspace + Webhook URL
- **バックアップストレージ**: AWS S3 (推奨)

---

## 初回デプロイ手順

### Phase 1: サーバー基盤セットアップ

#### 1.1 サーバー初期設定

```bash
# サーバーにSSH接続
ssh root@your-server-ip

# システム更新
apt update && apt upgrade -y

# 必要パッケージのインストール
apt install -y curl wget git ufw fail2ban

# ユーザー作成 (rootログインを無効化)
useradd -m -s /bin/bash helper-admin
usermod -aG sudo helper-admin
mkdir -p /home/helper-admin/.ssh
cp ~/.ssh/authorized_keys /home/helper-admin/.ssh/
chown -R helper-admin:helper-admin /home/helper-admin/.ssh
chmod 700 /home/helper-admin/.ssh
chmod 600 /home/helper-admin/.ssh/authorized_keys

# SSH設定の強化
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# ファイアウォール設定
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 2377/tcp
ufw allow 7946/tcp
ufw allow 7946/udp
ufw allow 4789/udp
ufw --force enable
```

#### 1.2 Docker環境セットアップ

```bash
# 一般ユーザーに切り替え
su - helper-admin

# Dockerのインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 再ログイン必要
exit
ssh helper-admin@your-server-ip

# Docker Composeインストール
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 動作確認
docker --version
docker-compose --version
```

### Phase 2: アプリケーションデプロイ

#### 2.1 プロジェクトファイル配置

```bash
# プロジェクトディレクトリ作成
sudo mkdir -p /opt/helper-system
sudo chown helper-admin:helper-admin /opt/helper-system
cd /opt/helper-system

# GitHubからクローン
git clone https://github.com/your-org/helper-system.git .

# ブランチ確認・切り替え
git checkout main

# 設定ファイルコピー
cp infrastructure/production.env.example infrastructure/production.env

# 設定ファイル編集
nano infrastructure/production.env
```

#### 2.2 設定ファイル編集 (重要)

```bash
# infrastructure/production.env を編集
# 以下の値を必ず変更してください:

DOMAIN_NAME=your-actual-domain.com
EMAIL_FOR_SSL=your-email@example.com

# 強力なパスワードを生成
DB_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 64)
SECRET_KEY=$(openssl rand -base64 64)
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 32)

# 生成されたパスワードを記録 (安全な場所に保管)
echo "DB_PASSWORD=$DB_PASSWORD" >> /opt/helper-system/credentials.txt
echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> /opt/helper-system/credentials.txt
echo "JWT_SECRET_KEY=$JWT_SECRET_KEY" >> /opt/helper-system/credentials.txt
echo "GRAFANA_ADMIN_PASSWORD=$GRAFANA_ADMIN_PASSWORD" >> /opt/helper-system/credentials.txt

chmod 600 /opt/helper-system/credentials.txt
```

#### 2.3 インフラストラクチャセットアップ

```bash
# Docker Swarmの初期化
cd /opt/helper-system
chmod +x infrastructure/*.sh

# セットアップ実行
./infrastructure/docker-swarm-setup.sh

# SSL証明書取得
./infrastructure/ssl-setup.sh

# 実行結果確認
docker node ls
docker network ls
docker secret ls
```

#### 2.4 アプリケーションデプロイ

```bash
# イメージビルド (初回のみ)
docker-compose -f infrastructure/docker-compose.production.yml build

# サービス起動
docker stack deploy -c infrastructure/docker-compose.production.yml helper-system

# 起動確認
docker service ls
docker service ps helper-system_backend
docker service ps helper-system_frontend
docker service ps helper-system_nginx

# ログ確認
docker service logs helper-system_backend
docker service logs helper-system_nginx
```

### Phase 3: 動作確認

#### 3.1 ヘルスチェック

```bash
# Webサイトアクセス確認
curl -I https://your-domain.com/health

# APIヘルスチェック
curl -I https://your-domain.com/api/v1/health

# SSL証明書確認
openssl s_client -connect your-domain.com:443 -servername your-domain.com < /dev/null | openssl x509 -text

# サービス状況確認
docker service ls
docker service ps helper-system_backend --no-trunc
```

#### 3.2 監視ダッシュボード確認

```bash
# Grafanaアクセス
echo "Grafana URL: https://your-domain.com/grafana/"
echo "Username: admin"
echo "Password: $(grep GRAFANA_ADMIN_PASSWORD /opt/helper-system/credentials.txt | cut -d'=' -f2)"

# Prometheusアクセス確認 (内部確認用)
docker exec -it $(docker ps -q -f name=helper-system_prometheus) wget -qO- http://localhost:9090/targets
```

---

## 継続的運用

### 日次運用タスク

#### 1. システム状況確認 (9:00 AM)
```bash
# サービス状況確認
docker service ls

# リソース使用状況確認
docker stats --no-stream

# ディスク使用量確認
df -h

# ログエラー確認
docker service logs helper-system_backend --tail 100 | grep ERROR
docker service logs helper-system_nginx --tail 100 | grep error
```

#### 2. Grafanaダッシュボード確認
- システムリソース状況
- アプリケーションパフォーマンス
- エラー率・レスポンス時間
- ユーザーアクティビティ

#### 3. バックアップ状況確認
```bash
# バックアップログ確認
docker service logs helper-system_backup-service --tail 50

# バックアップファイル確認
ls -la /opt/helper-system/backup/postgres/
ls -la /opt/helper-system/backup/redis/
```

### 週次運用タスク

#### 1. セキュリティ更新 (日曜日 14:00)
```bash
# システム更新
sudo apt update && sudo apt upgrade -y

# Docker更新確認
docker version
docker-compose version

# 脆弱性スキャン実行
docker run --rm -v /opt/helper-system:/app aquasec/trivy fs /app
```

#### 2. パフォーマンス分析
- 週次レポート生成
- トレンド分析
- 容量プランニング

#### 3. バックアップテスト
```bash
# テスト復旧実行 (ステージング環境)
./infrastructure/backup/restore-test.sh
```

### 月次運用タスク

#### 1. 容量監視・拡張計画
```bash
# ディスク使用量トレンド確認
df -h | grep -E "(backup|postgres|redis)"

# ログローテーション確認
ls -la /var/log/helper-system/
```

#### 2. SSL証明書更新確認
```bash
# 証明書有効期限確認
sudo certbot certificates

# 自動更新ログ確認
grep renewal /var/log/letsencrypt/letsencrypt.log
```

#### 3. セキュリティ監査
- アクセスログ分析
- 不審なアクティビティ確認
- 権限レビュー

---

## 監視・アラート

### Grafanaダッシュボード

#### 1. システム概要ダッシュボード
- サービス稼働状況
- システムリソース (CPU, Memory, Disk)
- ネットワーク使用量
- コンテナ状態

#### 2. アプリケーションダッシュボード
- リクエスト数・レスポンス時間
- エラー率
- データベース接続数・クエリ時間
- Redis接続数・メモリ使用量

#### 3. ビジネスメトリクス
- アクティブユーザー数
- 献立作成数
- ヘルパー作業完了率
- システム利用状況

### アラート設定

#### クリティカルアラート (即座対応)
- サービス停止
- データベース接続エラー
- 高エラー率 (15%以上)
- SSL証明書期限切れ
- セキュリティ異常

#### 警告アラート (監視強化)
- 高CPU使用率 (80%以上)
- 高メモリ使用率 (85%以上)
- 高ディスク使用率 (85%以上)
- 応答時間増加 (2秒以上)

#### 情報アラート (記録)
- コンテナ再起動
- バックアップ完了
- SSL証明書更新

### Slackアラート設定

```bash
# Slack Webhook URL設定
echo "SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK" >> infrastructure/production.env

# アラート確認
docker service update --env-add SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK" helper-system_alertmanager
```

---

## 障害対応

### 障害レベル分類

#### Level 1: サービス停止 (即座対応)
- Webサイト全体アクセス不可
- データベース完全停止
- セキュリティ侵害

#### Level 2: 機能障害 (1時間以内)
- 特定機能の停止
- 高エラー率
- 性能大幅劣化

#### Level 3: 性能劣化 (4時間以内)
- 応答時間増加
- 部分的な機能停止

### 障害対応フロー

#### 1. 初期対応 (発見から5分以内)
```bash
# 1. サービス状況確認
docker service ls
docker service ps helper-system_backend --no-trunc

# 2. ログ確認
docker service logs helper-system_backend --tail 100
docker service logs helper-system_nginx --tail 100

# 3. リソース確認
docker stats --no-stream
df -h
```

#### 2. 原因調査 (5-15分)
```bash
# システムログ確認
sudo journalctl -u docker -f

# アプリケーションログ詳細確認
docker exec -it $(docker ps -q -f name=helper-system_backend) tail -f /app/logs/app.log

# データベース状況確認
docker exec -it $(docker ps -q -f name=helper-system_postgres-master) psql -U helper_user -d helper_db -c "SELECT version();"
```

#### 3. 応急対応
```bash
# サービス再起動
docker service update --force helper-system_backend

# スケール調整
docker service scale helper-system_backend=2

# トラフィック制御
# 必要に応じてnginxでメンテナンスページ表示
```

#### 4. 恒久対応
- 根本原因修正
- 再発防止策実装
- 監視強化

### よくある障害と対処法

#### 1. 高負荷によるレスポンス遅延
```bash
# バックエンドサービスのスケールアップ
docker service scale helper-system_backend=4

# データベース接続数確認
docker exec -it $(docker ps -q -f name=postgres-master) psql -U helper_user -d helper_db -c "SELECT count(*) FROM pg_stat_activity;"

# Redisメモリ使用量確認
docker exec -it $(docker ps -q -f name=redis-cluster) redis-cli info memory
```

#### 2. データベース接続エラー
```bash
# PostgreSQL状況確認
docker service ps helper-system_postgres-master
docker service logs helper-system_postgres-master

# 接続テスト
docker exec -it $(docker ps -q -f name=postgres-master) pg_isready -U helper_user

# 必要に応じて再起動
docker service update --force helper-system_postgres-master
```

#### 3. SSL証明書エラー
```bash
# 証明書状況確認
sudo certbot certificates

# 手動更新
sudo certbot renew --force-renewal

# Docker Secretsの更新
docker secret rm ssl_cert ssl_key
docker secret create ssl_cert /etc/letsencrypt/live/your-domain.com/fullchain.pem
docker secret create ssl_key /etc/letsencrypt/live/your-domain.com/privkey.pem

# Nginxサービス更新
docker service update --force helper-system_nginx
```

---

## バックアップ・復旧

### バックアップ戦略

#### 自動バックアップ
- **頻度**: 日次 (毎日 2:00 AM)
- **対象**: PostgreSQL、Redis、アプリケーションログ
- **保持期間**: 30日間
- **リモートバックアップ**: AWS S3 (推奨)

#### 手動バックアップ
```bash
# 完全バックアップ実行
docker exec -it $(docker ps -q -f name=backup-service) python /scripts/backup-service.py --type full

# データベースのみバックアップ
docker exec -it $(docker ps -q -f name=backup-service) python /scripts/backup-service.py --type database

# バックアップファイル確認
ls -la /opt/helper-system/backup/postgres/
ls -la /opt/helper-system/backup/redis/
```

### 復旧手順

#### 1. データベース復旧
```bash
# PostgreSQL復旧
# 1. サービス停止
docker service scale helper-system_backend=0
docker service scale helper-system_postgres-master=0

# 2. データ復旧
BACKUP_FILE="/backup/postgres/helper_db_20240315_020000.sql.gz"
zcat $BACKUP_FILE | docker exec -i $(docker ps -q -f name=postgres-master) psql -U helper_user -d helper_db

# 3. サービス再開
docker service scale helper-system_postgres-master=1
sleep 30
docker service scale helper-system_backend=2
```

#### 2. Redis復旧
```bash
# Redis復旧
# 1. Redisサービス停止
docker service scale helper-system_redis-cluster=0

# 2. RDBファイル復旧
BACKUP_FILE="/backup/redis/redis_20240315_020000.rdb.gz"
zcat $BACKUP_FILE > /tmp/dump.rdb
docker cp /tmp/dump.rdb $(docker ps -q -f name=redis-cluster):/data/dump.rdb

# 3. サービス再開
docker service scale helper-system_redis-cluster=3
```

#### 3. 完全システム復旧
```bash
# 災害復旧時の完全復旧手順
# 1. 新しいサーバー環境構築
# 2. Docker環境セットアップ
# 3. バックアップファイル復旧
# 4. DNS切り替え
# 5. SSL証明書再発行
```

### バックアップ監視

```bash
# バックアップ状況確認
docker service logs helper-system_backup-service --tail 50

# バックアップサイズ確認
du -h /opt/helper-system/backup/

# S3バックアップ確認 (AWS CLIが必要)
aws s3 ls s3://your-backup-bucket/backups/ --recursive --human-readable
```

---

## セキュリティ管理

### セキュリティ監視

#### 1. 日次チェック項目
```bash
# 失敗ログイン試行確認
docker service logs helper-system_backend | grep "login_failed"

# システムログ確認
sudo journalctl --since "yesterday" | grep -i "authentication failure"

# ファイアウォール状況確認
sudo ufw status verbose
```

#### 2. セキュリティ更新

```bash
# セキュリティ更新確認
sudo apt list --upgradable | grep -i security

# 自動セキュリティ更新設定
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

#### 3. 脆弱性スキャン

```bash
# 週次脆弱性スキャン
docker run --rm -v /opt/helper-system:/app aquasec/trivy fs /app

# 定期的なイメージスキャン
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image helper-system/backend:latest
```

### アクセス制御

#### 1. SSH アクセス管理
```bash
# SSHキーローテーション (月次)
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_new
# 新しいキーを authorized_keys に追加
# 古いキーを削除
```

#### 2. アプリケーションアクセス制御
- 管理者権限の定期レビュー
- パスワードポリシーの確認
- セッションタイムアウト設定

#### 3. ファイアウォール管理
```bash
# ファイアウォールルール確認
sudo ufw status numbered

# 不要なポート閉鎖
sudo ufw delete [rule_number]

# ログ確認
sudo tail -f /var/log/ufw.log
```

### インシデント対応

#### セキュリティインシデント発生時
1. **即座の対応** (15分以内)
   - 影響範囲の特定
   - 攻撃源の遮断
   - 証拠保全

2. **調査・分析** (1時間以内)
   - ログ分析
   - 被害状況確認
   - 原因究明

3. **復旧・対策** (4時間以内)
   - システム復旧
   - セキュリティ強化
   - 再発防止策

4. **報告・改善** (24時間以内)
   - インシデント報告書作成
   - セキュリティポリシー見直し
   - 監視強化

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. Docker Swarmノード離脱
```bash
# ノード状況確認
docker node ls

# ノード復帰
docker node update --availability active [NODE_ID]

# 新しいワーカーノード追加
WORKER_TOKEN=$(docker swarm join-token worker -q)
# 新しいノードで実行:
# docker swarm join --token $WORKER_TOKEN manager-node-ip:2377
```

#### 2. ディスク容量不足
```bash
# 容量確認
df -h

# Dockerシステム清理
docker system prune -a

# ログローテーション
sudo logrotate -f /etc/logrotate.conf

# 古いバックアップ削除
find /opt/helper-system/backup -type f -mtime +30 -delete
```

#### 3. メモリ不足
```bash
# メモリ使用量確認
free -h

# プロセス別メモリ使用量
docker stats --no-stream

# サービススケール調整
docker service scale helper-system_backend=1
```

### ログ収集・分析

#### 重要ログファイル
```bash
# アプリケーションログ
/var/log/helper-system/app.log
/var/log/helper-system/error.log

# Nginxログ
/var/log/nginx/access.log
/var/log/nginx/error.log

# Dockerログ
sudo journalctl -u docker

# システムログ
/var/log/syslog
/var/log/auth.log
```

#### ログ分析コマンド
```bash
# エラー集計
grep ERROR /var/log/helper-system/app.log | wc -l

# アクセス数集計
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -nr | head -10

# レスポンス時間分析
awk '$9 ~ /^2/ {print $NF}' /var/log/nginx/access.log | sort -n | tail -10
```

---

## パフォーマンス最適化

### 定期的な最適化作業

#### 1. データベース最適化 (月次)
```bash
# PostgreSQL統計更新
docker exec -it $(docker ps -q -f name=postgres-master) psql -U helper_user -d helper_db -c "ANALYZE;"

# インデックス再構築
docker exec -it $(docker ps -q -f name=postgres-master) psql -U helper_user -d helper_db -c "REINDEX DATABASE helper_db;"

# 不要データクリーンアップ
docker exec -it $(docker ps -q -f name=postgres-master) psql -U helper_user -d helper_db -c "VACUUM FULL;"
```

#### 2. Redis最適化
```bash
# Redis情報確認
docker exec -it $(docker ps -q -f name=redis-cluster) redis-cli info memory

# メモリ最適化
docker exec -it $(docker ps -q -f name=redis-cluster) redis-cli memory purge
```

#### 3. Nginx最適化
```bash
# アクセスログ分析
docker exec -it $(docker ps -q -f name=nginx) nginx -t

# 設定リロード
docker service update --force helper-system_nginx
```

### 容量プランニング

#### リソース使用量監視
```bash
# CPU使用率トレンド
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# ディスク使用量トレンド
df -h | grep -E "(postgres|redis|backup)"

# ネットワーク使用量
docker exec -it $(docker ps -q -f name=nginx) cat /proc/net/dev
```

---

## 連絡先・エスカレーション

### 緊急連絡先

#### Level 1 (クリティカル障害)
- **技術責任者**: [氏名] - [電話番号] - [メールアドレス]
- **システム管理者**: [氏名] - [電話番号] - [メールアドレス]
- **事業責任者**: [氏名] - [電話番号] - [メールアドレス]

#### Level 2 (通常障害)
- **開発チーム**: [メールアドレス] - [Slackチャンネル]
- **運用チーム**: [メールアドレス] - [Slackチャンネル]

#### 外部サポート
- **VPSプロバイダー**: [サポート番号] - [サポートURL]
- **ドメイン管理**: [サポート番号] - [サポートURL]

### 定期会議

#### 週次運用会議 (毎週月曜日 10:00)
- システム状況レビュー
- 週次課題確認
- 改善提案

#### 月次レビュー会議 (毎月第1金曜日 14:00)
- パフォーマンスレビュー
- セキュリティレビュー
- 容量プランニング

---

## 付録

### A. 設定ファイルテンプレート

#### production.env
[設定ファイルの完全版は `infrastructure/production.env.example` を参照]

#### nginx.conf
[Nginx設定の完全版は `infrastructure/nginx/nginx.conf` を参照]

### B. 監視メトリクス一覧

#### システムメトリクス
- CPU使用率
- メモリ使用率
- ディスク使用率
- ネットワーク使用量

#### アプリケーションメトリクス
- レスポンス時間
- スループット
- エラー率
- アクティブユーザー数

### C. チェックリスト

#### 日次チェックリスト
- [ ] サービス稼働状況確認
- [ ] リソース使用状況確認
- [ ] エラーログ確認
- [ ] バックアップ状況確認
- [ ] Grafanaダッシュボード確認

#### 週次チェックリスト
- [ ] セキュリティ更新適用
- [ ] パフォーマンス分析
- [ ] 容量使用量確認
- [ ] バックアップテスト実行
- [ ] 脆弱性スキャン実行

#### 月次チェックリスト
- [ ] SSL証明書期限確認
- [ ] アクセスログ分析
- [ ] データベース最適化
- [ ] セキュリティ監査
- [ ] 容量プランニング見直し

---

**この運用ガイドは定期的に更新し、最新の状況を反映してください。**

**文書バージョン**: 1.0  
**最終更新日**: 2025年7月15日  
**作成者**: DevOpsチーム  
**承認者**: 技術責任者