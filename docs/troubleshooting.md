# ホームヘルパー管理システム - トラブルシューティングガイド

## 目次
- [一般的な問題](#一般的な問題)
- [サービス起動問題](#サービス起動問題)
- [パフォーマンス問題](#パフォーマンス問題)
- [データベース問題](#データベース問題)
- [ネットワーク問題](#ネットワーク問題)
- [セキュリティ問題](#セキュリティ問題)

---

## 一般的な問題

### サービスが起動しない

#### 症状
```bash
$ docker compose -f docker-compose.prod.yml ps
NAME                      STATUS
helper-backend-prod       Exited (1)
```

#### 診断手順
```bash
# 1. ログ確認
docker compose -f docker-compose.prod.yml logs backend --tail=100

# 2. 環境変数確認
docker compose -f docker-compose.prod.yml exec backend env | grep -E "(DATABASE|REDIS|SECRET)"

# 3. ヘルスチェック
docker compose -f docker-compose.prod.yml exec backend curl -f http://localhost:8000/health
```

#### 一般的な原因と解決策

**原因1: データベース接続失敗**
```bash
# エラー: could not connect to server: Connection refused

# 解決策: PostgreSQL起動確認
docker compose -f docker-compose.prod.yml ps postgres

# PostgreSQLログ確認
docker compose -f docker-compose.prod.yml logs postgres

# 再起動
docker compose -f docker-compose.prod.yml restart postgres
docker compose -f docker-compose.prod.yml restart backend
```

**原因2: 環境変数未設定**
```bash
# エラー: SECRET_KEY is required

# 解決策: 環境変数ファイル確認
cat backend/.env.production | grep SECRET_KEY

# 環境変数設定
echo "SECRET_KEY=$(openssl rand -hex 32)" >> backend/.env.production
docker compose -f docker-compose.prod.yml restart backend
```

**原因3: マイグレーション未実行**
```bash
# エラー: relation "users" does not exist

# 解決策: マイグレーション実行
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## サービス起動問題

### Docker Composeエラー

#### Error: network not found
```bash
# エラーメッセージ
ERROR: Network helper-network declared as external, but could not be found

# 解決策
docker network create helper-network
docker compose -f docker-compose.prod.yml up -d
```

#### Error: port is already allocated
```bash
# エラーメッセージ
ERROR: Bind for 0.0.0.0:80 failed: port is already allocated

# 診断: ポート使用状況確認
sudo lsof -i :80
sudo netstat -tlnp | grep :80

# 解決策1: 既存プロセス停止
sudo systemctl stop nginx  # システムのNginxを停止

# 解決策2: ポート変更
# docker-compose.prod.ymlのポート設定変更
ports:
  - "8080:80"
```

### Permission denied エラー

```bash
# エラー: permission denied while trying to connect to the Docker daemon socket

# 解決策: Dockerグループに追加
sudo usermod -aG docker $USER
newgrp docker

# または一時的にsudo使用
sudo docker compose -f docker-compose.prod.yml up -d
```

---

## パフォーマンス問題

### レスポンスが遅い

#### 診断手順

**1. システムリソース確認**
```bash
# CPU、メモリ使用状況
docker stats --no-stream

# ディスクI/O確認
iostat -x 1 10

# ネットワーク確認
iftop
```

**2. アプリケーションレベル診断**
```bash
# APIレスポンスタイム測定
time curl -s https://your-domain.com/api/v1/recipes > /dev/null

# バックエンドログ確認 (スロークエリ)
docker compose -f docker-compose.prod.yml logs backend | grep "Slow query"
```

**3. データベースパフォーマンス**
```bash
# 接続数確認
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d helper_production <<EOF
SELECT count(*) as connections, state
FROM pg_stat_activity
GROUP BY state;
EOF

# スロークエリ確認
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d helper_production <<EOF
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
EOF
```

#### 解決策

**CPU使用率が高い場合**
```bash
# ワーカー数調整
# docker-compose.prod.ymlでbackendをスケールアップ
docker compose -f docker-compose.prod.yml up -d --scale backend=3
```

**メモリ不足の場合**
```bash
# Redisメモリ制限調整
docker compose -f docker-compose.prod.yml exec redis redis-cli CONFIG SET maxmemory 1gb

# PostgreSQL接続プール調整
# backend/.env.productionで設定
DB_POOL_SIZE=10  # 減らす
DB_MAX_OVERFLOW=5
```

**データベースが遅い場合**
```bash
# インデックス追加
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d helper_production <<EOF
CREATE INDEX CONCURRENTLY idx_recipes_category ON recipes(category);
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
EOF

# VACUUM実行
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d helper_production -c "VACUUM ANALYZE;"
```

---

## データベース問題

### 接続数上限エラー

#### 症状
```
FATAL: sorry, too many clients already
```

#### 解決策
```bash
# 現在の接続数確認
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d postgres <<EOF
SELECT count(*) FROM pg_stat_activity;
SELECT max_connections FROM pg_settings WHERE name = 'max_connections';
EOF

# アイドル接続を切断
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d postgres <<EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND state_change < current_timestamp - INTERVAL '10 minutes';
EOF

# max_connections増加 (要PostgreSQL再起動)
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U prod_user -d postgres -c "ALTER SYSTEM SET max_connections = 200;"
docker compose -f docker-compose.prod.yml restart postgres
```

### データ不整合

#### 外部キー制約違反
```bash
# エラー: insert or update on table violates foreign key constraint

# 診断: 孤立レコード確認
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d helper_production <<EOF
SELECT * FROM weekly_menus
WHERE user_id NOT IN (SELECT id FROM users);
EOF

# 修正: 孤立レコード削除 (要注意!)
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d helper_production <<EOF
DELETE FROM weekly_menus
WHERE user_id NOT IN (SELECT id FROM users);
EOF
```

### ロック問題

```bash
# ロック待ちクエリ確認
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d helper_production <<EOF
SELECT
  pid,
  now() - pg_stat_activity.query_start AS duration,
  query,
  state
FROM pg_stat_activity
WHERE state != 'idle' AND query NOT ILIKE '%pg_stat_activity%'
ORDER BY duration DESC;
EOF

# ロック解除 (慎重に!)
docker compose -f docker-compose.prod.yml exec postgres psql -U prod_user -d helper_production <<EOF
SELECT pg_terminate_backend(<pid>);
EOF
```

---

## ネットワーク問題

### SSL証明書エラー

#### 症状
```
curl: (60) SSL certificate problem: certificate has expired
```

#### 診断
```bash
# 証明書有効期限確認
echo | openssl s_client -servername your-domain.com -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates

# Certbot証明書確認
docker compose -f docker-compose.prod.yml exec certbot certbot certificates
```

#### 解決策
```bash
# 証明書更新
docker compose -f docker-compose.prod.yml exec certbot certbot renew

# 強制更新
docker compose -f docker-compose.prod.yml exec certbot certbot renew --force-renewal

# Nginx再起動
docker compose -f docker-compose.prod.yml restart nginx
```

### CORS エラー

#### 症状
```
Access to XMLHttpRequest has been blocked by CORS policy
```

#### 診断
```bash
# CORS設定確認
docker compose -f docker-compose.prod.yml exec backend env | grep CORS

# Nginxヘッダー確認
curl -I -X OPTIONS https://your-domain.com/api/v1/recipes \
  -H "Origin: https://your-domain.com" \
  -H "Access-Control-Request-Method: GET"
```

#### 解決策
```bash
# backend/.env.productionで設定
BACKEND_CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# バックエンド再起動
docker compose -f docker-compose.prod.yml restart backend
```

### WebSocket接続失敗

#### 診断
```bash
# WebSocketエンドポイント確認
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: $(openssl rand -base64 16)" \
  https://your-domain.com/ws

# Nginxログ確認
docker compose -f docker-compose.prod.yml logs nginx | grep websocket
```

#### 解決策
```bash
# Nginx設定確認 (nginx-https.conf)
# WebSocket用のproxy設定が正しいか確認
location /ws {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    ...
}

# Nginx再起動
docker compose -f docker-compose.prod.yml restart nginx
```

---

## セキュリティ問題

### 不正アクセス検知

#### ログ監視
```bash
# 認証失敗ログ確認
docker compose -f docker-compose.prod.yml logs backend | grep "Authentication failed"

# IPアドレス別失敗回数
docker compose -f docker-compose.prod.yml logs backend | \
  grep "Authentication failed" | \
  awk '{print $NF}' | sort | uniq -c | sort -rn | head -10
```

#### 対策
```bash
# 特定IPをブロック (Nginxレベル)
docker compose -f docker-compose.prod.yml exec nginx sh -c "
echo 'deny 192.168.1.100;' >> /etc/nginx/conf.d/blocked_ips.conf
nginx -s reload
"

# レート制限強化
# nginx-https.confで設定
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=3r/m;
```

### シークレットキー漏洩疑い

#### 緊急対応
```bash
# 1. 即座にキーをローテーション
cd backend
mv .env.production .env.production.old
cp .env.production.template .env.production

# 新しいシークレットキー生成
NEW_SECRET=$(openssl rand -hex 32)
NEW_JWT=$(openssl rand -hex 32)
sed -i "s/CHANGE_THIS_TO_STRONG_RANDOM_SECRET_KEY.*/$NEW_SECRET/" .env.production
sed -i "s/CHANGE_THIS_TO_STRONG_RANDOM_JWT_SECRET_KEY.*/$NEW_JWT/" .env.production

# 2. 全サービス再起動
cd ..
docker compose -f docker-compose.prod.yml restart

# 3. 全ユーザーのセッション無効化 (Redisフラッシュ)
docker compose -f docker-compose.prod.yml exec redis redis-cli FLUSHDB

# 4. ユーザーに再ログイン依頼
```

---

## モニタリング・アラート

### リソース監視

```bash
# 継続的なリソース監視
watch -n 5 docker stats --no-stream

# ディスク使用量アラート
df -h | awk '$5+0 > 80 {print "WARNING: "$0}'

# メモリ使用量アラート
free -m | awk 'NR==2{printf "Memory Usage: %.2f%%\n", $3*100/$2 }'
```

### ログ監視

```bash
# エラーログリアルタイム監視
docker compose -f docker-compose.prod.yml logs -f backend frontend | grep -i error

# 1時間ごとのエラーカウント
docker compose -f docker-compose.prod.yml logs backend --since 1h | \
  grep ERROR | wc -l
```

---

## 緊急連絡先

### エスカレーションフロー

1. **Level 1**: システム管理者
   - Email: admin@your-domain.com
   - 対応時間: 平日9:00-18:00

2. **Level 2**: 技術サポート
   - Email: support@your-domain.com
   - 対応時間: 24時間365日

3. **Level 3**: インフラチーム
   - Email: infra@your-domain.com
   - 電話: XXX-XXXX-XXXX (緊急時のみ)

### インシデント報告テンプレート

```
件名: [緊急度] システム障害報告 - [簡潔な説明]

■ 発生日時: YYYY-MM-DD HH:MM JST
■ 検知方法: [監視/ユーザー報告/その他]
■ 影響範囲: [全体/特定機能/ユーザー数]
■ 現在の状況: [詳細な状況説明]
■ 実施した対応: [対応内容]
■ 次のアクション: [今後の対応予定]

報告者: [氏名]
連絡先: [メール/電話]
```

---

## 関連ドキュメント

- [デプロイ手順書](./deployment.md)
- [ロールバック手順書](./rollback.md)
- [バックアップ・リストア手順](./backup-restore.md)
