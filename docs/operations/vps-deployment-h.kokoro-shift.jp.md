# VPS本番デプロイ手順 — h.kokoro-shift.jp

## 前提条件

| 項目 | 要件 |
|------|------|
| OS | Ubuntu 22.04 LTS |
| CPU | 2コア以上（推奨4コア） |
| RAM | 4GB以上（推奨8GB） |
| ストレージ | 20GB以上（推奨50GB SSD） |
| ドメイン | h.kokoro-shift.jp（Aレコード → VPS IPアドレス） |

---

## 1. DNS設定

VPSのIPアドレスを取得し、ドメインレジストラで以下を設定:

```
h.kokoro-shift.jp.  A  <VPSのIPアドレス>
```

設定反映の確認:

```bash
dig h.kokoro-shift.jp +short
# → VPSのIPアドレスが表示されること
```

---

## 2. VPSサーバー初期設定

```bash
# システム更新
sudo apt update && sudo apt upgrade -y

# 必要パッケージ
sudo apt install -y curl git openssl ufw

# ファイアウォール設定
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable
sudo ufw status
```

---

## 3. Docker インストール

```bash
# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
rm get-docker.sh

# 再ログインしてdockerグループ反映
exit
# → 再度SSH接続

# 確認
docker --version
docker compose version
```

---

## 4. プロジェクト配置

```bash
# ディレクトリ作成
sudo mkdir -p /opt/helper-system
sudo chown $USER:$USER /opt/helper-system
cd /opt/helper-system

# Gitクローン
git clone <リポジトリURL> .
git checkout main
```

---

## 5. SSL証明書取得 (Let's Encrypt)

```bash
# certbot インストール
sudo apt install -y certbot

# ポート80が空いていることを確認（Dockerが起動していないこと）
sudo certbot certonly --standalone -d h.kokoro-shift.jp

# 証明書をプロジェクトにコピー
sudo cp /etc/letsencrypt/live/h.kokoro-shift.jp/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/h.kokoro-shift.jp/privkey.pem nginx/ssl/
sudo chown $USER:$USER nginx/ssl/*.pem
chmod 600 nginx/ssl/*.pem
```

### 証明書の自動更新設定

```bash
# 更新スクリプト作成
sudo tee /etc/cron.d/certbot-renew << 'CRON'
0 3 1 */2 * root certbot renew --pre-hook "cd /opt/helper-system && docker compose -f docker-compose.prod.yml stop nginx" --post-hook "cp /etc/letsencrypt/live/h.kokoro-shift.jp/fullchain.pem /opt/helper-system/nginx/ssl/ && cp /etc/letsencrypt/live/h.kokoro-shift.jp/privkey.pem /opt/helper-system/nginx/ssl/ && cd /opt/helper-system && docker compose -f docker-compose.prod.yml start nginx" >> /var/log/certbot-renew.log 2>&1
CRON
```

---

## 6. 初回デプロイ

```bash
cd /opt/helper-system

# deploy.sh で初回セットアップ
./deploy.sh init
```

このコマンドで以下が自動実行されます:

1. `.env` ファイル生成（シークレット自動生成）
2. Dockerイメージビルド
3. DB & Redis起動
4. Alembicマイグレーション
5. 全サービス起動

### .env 確認・編集

`deploy.sh init` 実行後、`.env` を確認してドメインが正しいことを確認:

```bash
cat .env
# CORS_ORIGINS=https://h.kokoro-shift.jp
# DOMAIN=h.kokoro-shift.jp
```

---

## 7. 動作確認

```bash
# サービス状態確認
./deploy.sh status

# ブラウザでアクセス
# https://h.kokoro-shift.jp

# API ヘルスチェック
curl -sf https://h.kokoro-shift.jp/api/v1/health

# SSL確認
curl -vI https://h.kokoro-shift.jp 2>&1 | grep -E "SSL|subject|expire"
```

---

## 8. 運用コマンド

```bash
# ステータス確認
./deploy.sh status

# ログ確認
./deploy.sh logs              # 全サービス
./deploy.sh logs backend      # バックエンドのみ
./deploy.sh logs nginx        # Nginxのみ

# DBバックアップ
./deploy.sh backup

# コード更新・再デプロイ
./deploy.sh update

# 全サービス停止
./deploy.sh stop
```

---

## 9. アップデートデプロイ

```bash
cd /opt/helper-system
./deploy.sh update
```

自動で `git pull` → ビルド → マイグレーション → ローリング再起動が行われます。

---

## 10. トラブルシューティング

### サービスが起動しない

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs db
```

### SSL証明書エラー

```bash
# 証明書の存在確認
ls -la nginx/ssl/
# fullchain.pem と privkey.pem が存在すること

# 証明書の有効期限確認
openssl x509 -in nginx/ssl/fullchain.pem -noout -enddate

# 手動更新
sudo certbot renew
sudo cp /etc/letsencrypt/live/h.kokoro-shift.jp/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/h.kokoro-shift.jp/privkey.pem nginx/ssl/
docker compose -f docker-compose.prod.yml restart nginx
```

### ディスク容量不足

```bash
df -h
docker system df
docker system prune -a    # 未使用イメージ等を削除
```

---

## セキュリティチェックリスト

- [ ] DNS Aレコードが VPS IP に向いている
- [ ] ファイアウォール (UFW) が有効: 22, 80, 443 のみ開放
- [ ] SSL証明書が取得・配置済み
- [ ] `.env` のシークレットがランダム値に変更済み
- [ ] `.env` のパーミッションが `600`
- [ ] SSH 鍵認証を使用（パスワード認証無効化推奨）
- [ ] 自動セキュリティアップデート有効化
- [ ] 証明書自動更新 cron 設定済み
- [ ] DBバックアップの定期実行設定
