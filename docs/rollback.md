# ホームヘルパー管理システム - ロールバック手順書

## 目次
- [概要](#概要)
- [ロールバック戦略](#ロールバック戦略)
- [緊急ロールバック手順](#緊急ロールバック手順)
- [部分ロールバック](#部分ロールバック)
- [ロールバック検証](#ロールバック検証)

---

## 概要

本番環境でデプロイ後に問題が発生した場合の緊急対応手順を記載します。
ロールバックは以下の優先順位で実施します：

1. **サービスレベルロールバック** (最速、影響小)
2. **コードロールバック** (中速、影響中)
3. **データベースロールバック** (低速、影響大)

---

## ロールバック戦略

### ロールバック判断基準

以下の状況でロールバックを検討してください：

#### 即座にロールバック (Critical)
- [ ] 認証システムが完全に停止
- [ ] データベース接続が完全に失敗
- [ ] 500エラー率が50%超
- [ ] 個人情報漏洩の可能性
- [ ] セキュリティ脆弱性の発見

#### 調査後にロールバック (High)
- [ ] 500エラー率が10-50%
- [ ] レスポンスタイムが通常の3倍以上
- [ ] 特定機能が完全に動作しない
- [ ] データ整合性の問題

#### 修正対応可能 (Medium)
- [ ] 500エラー率が10%未満
- [ ] UI表示の軽微な問題
- [ ] 特定ブラウザでの問題
- [ ] ログに大量のWarning

---

## 緊急ロールバック手順

### Phase 1: 状況確認 (1-2分)

```bash
# サービス状態確認
cd /opt/helper-system
docker compose -f docker-compose.prod.yml ps

# エラーログ確認
docker compose -f docker-compose.prod.yml logs --tail=100 backend | grep ERROR
docker compose -f docker-compose.prod.yml logs --tail=100 frontend | grep ERROR

# ヘルスチェック
curl -f https://your-domain.com/health
curl -f https://your-domain.com/api/v1/health
```

### Phase 2: 即座対応 - サービス再起動 (1分)

```bash
# 問題のあるサービスのみ再起動
docker compose -f docker-compose.prod.yml restart backend

# または全サービス再起動
docker compose -f docker-compose.prod.yml restart
```

### Phase 3: コードロールバック (5-10分)

#### Step 1: 前バージョン確認
```bash
# デプロイ履歴確認
git log --oneline -n 10

# タグ確認
git tag -l | tail -5
```

#### Step 2: コードロールバック実行
```bash
# 方法1: 直前のコミットに戻す
git reset --hard HEAD~1

# 方法2: 特定のコミットに戻す
git reset --hard <commit-hash>

# 方法3: 特定のバージョンタグに戻す
git checkout tags/v1.0.0 -b rollback-v1.0.0
```

#### Step 3: イメージ再ビルド
```bash
# キャッシュを使用して高速ビルド
docker compose -f docker-compose.prod.yml build backend frontend

# サービス再起動
docker compose -f docker-compose.prod.yml up -d --no-deps backend frontend
```

#### Step 4: 動作確認
```bash
# ヘルスチェック
curl -f https://your-domain.com/health
curl -f https://your-domain.com/api/v1/health

# ログ確認
docker compose -f docker-compose.prod.yml logs --tail=50 backend frontend
```

### Phase 4: データベースロールバック (10-30分)

**警告**: データベースロールバックは最終手段です。データ損失の可能性があります。

#### Step 1: 現在のデータバックアップ
```bash
# 緊急バックアップ作成
docker compose -f docker-compose.prod.yml exec postgres \
  bash -c "pg_dump -U prod_user helper_production | gzip > /backups/emergency_$(date +%Y%m%d_%H%M%S).sql.gz"
```

#### Step 2: ロールバック用バックアップ選択
```bash
# 利用可能なバックアップ一覧
ls -lh /opt/helper-system/backups/

# 最新のデプロイ前バックアップを確認
ls -lht /opt/helper-system/backups/ | grep pre_deploy | head -1
```

#### Step 3: データベースリストア
```bash
# リストア実行 (確認プロンプトあり)
./scripts/restore.sh -f /backups/pre_deploy_20250110_120000.sql.gz

# または確認なしで実行
./scripts/restore.sh -f /backups/pre_deploy_20250110_120000.sql.gz --yes
```

#### Step 4: マイグレーション調整
```bash
# マイグレーション状態確認
docker compose -f docker-compose.prod.yml exec backend alembic current

# 必要に応じてダウングレード
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1

# または特定のリビジョンに
docker compose -f docker-compose.prod.yml exec backend alembic downgrade <revision>
```

---

## 部分ロールバック

### フロントエンドのみロールバック

```bash
# フロントエンドコードをロールバック
cd /opt/helper-system/frontend
git checkout <commit-hash> -- .

# フロントエンド再ビルド
cd ..
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d --no-deps frontend

# 確認
curl -f https://your-domain.com/
```

### バックエンドのみロールバック

```bash
# バックエンドコードをロールバック
cd /opt/helper-system/backend
git checkout <commit-hash> -- .

# バックエンド再ビルド
cd ..
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d --no-deps backend

# 確認
curl -f https://your-domain.com/api/v1/health
```

### 環境変数のみロールバック

```bash
# バックアップから環境変数をリストア
cp backend/.env.production.backup backend/.env.production

# サービス再起動
docker compose -f docker-compose.prod.yml restart backend
```

---

## ロールバック検証

### チェックリスト

#### 1. サービス起動確認
```bash
# 全サービスが起動しているか
docker compose -f docker-compose.prod.yml ps

# 期待される出力: すべてのサービスが "Up" 状態
```

#### 2. ヘルスチェック
```bash
# フロントエンド
curl -f https://your-domain.com/health
# 期待される出力: "healthy"

# バックエンドAPI
curl -f https://your-domain.com/api/v1/health
# 期待される出力: {"status": "healthy"}
```

#### 3. データベース接続確認
```bash
docker compose -f docker-compose.prod.yml exec backend python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connection: OK')
"
```

#### 4. 主要機能テスト
```bash
# ログイン機能
curl -X POST https://your-domain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test1234"}'

# レシピ一覧取得
curl -H "Authorization: Bearer <token>" \
  https://your-domain.com/api/v1/recipes
```

#### 5. ログ確認
```bash
# エラーログがないことを確認
docker compose -f docker-compose.prod.yml logs --tail=100 backend | grep -i error
docker compose -f docker-compose.prod.yml logs --tail=100 frontend | grep -i error

# 期待される出力: エラーなし or 既知の無害なエラーのみ
```

#### 6. パフォーマンス確認
```bash
# レスポンスタイム測定
time curl -s https://your-domain.com/ > /dev/null
time curl -s https://your-domain.com/api/v1/health > /dev/null

# リソース使用状況
docker stats --no-stream
```

---

## ロールバック後の対応

### 1. ステークホルダーへの通知

```
件名: [緊急] 本番環境ロールバック実施のお知らせ

本番環境にて問題が発生したため、ロールバックを実施しました。

■ ロールバック時刻: 2025-01-10 14:30 JST
■ 対象バージョン: v1.1.0 → v1.0.0
■ 影響範囲: [影響を受けた機能]
■ ダウンタイム: [時間]
■ 現在の状態: 正常稼働中

詳細は別途報告いたします。
```

### 2. インシデントレポート作成

以下の情報を記録：
- 発生時刻
- 検知方法
- 影響範囲
- 対応内容
- ロールバック理由
- 根本原因
- 再発防止策

### 3. 根本原因分析 (RCA)

```bash
# ログ保存
mkdir -p /opt/helper-system/incidents/$(date +%Y%m%d_%H%M%S)
docker compose -f docker-compose.prod.yml logs > incidents/$(date +%Y%m%d_%H%M%S)/all_logs.txt

# データベース状態保存
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U prod_user -d helper_production -c "\dt" > incidents/$(date +%Y%m%d_%H%M%S)/db_schema.txt
```

### 4. 修正版の準備

```bash
# 修正用ブランチ作成
git checkout -b hotfix/issue-description

# 修正実施後、ステージング環境でテスト
# 問題なければ再デプロイ
```

---

## ロールバック失敗時の対応

### ロールバックが失敗した場合

#### 1. メンテナンスモード有効化
```bash
# Nginxメンテナンスページ表示
cat > nginx/maintenance.conf <<EOF
server {
    listen 80 default_server;
    listen 443 ssl default_server;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location / {
        return 503;
    }
    
    error_page 503 @maintenance;
    location @maintenance {
        root /usr/share/nginx/html;
        rewrite ^(.*)$ /maintenance.html break;
    }
}
EOF

docker compose -f docker-compose.prod.yml restart nginx
```

#### 2. バックアップサーバーへ切り替え

```bash
# DNSをバックアップサーバーに変更
# または
# ロードバランサーでトラフィックを振り分け
```

#### 3. 専門家への連絡

緊急連絡先リスト：
- システム管理者: admin@your-domain.com
- 技術サポート: support@your-domain.com
- インフラチーム: infra@your-domain.com

---

## ロールバック訓練

### 定期訓練の実施 (月1回推奨)

```bash
# ステージング環境でロールバック訓練
cd /opt/helper-system-staging

# 1. 現在の状態を記録
docker compose ps
git log --oneline -n 1

# 2. 意図的に問題を発生させる
# (例: 環境変数を誤設定)

# 3. ロールバック手順を実行
# 4. 動作確認
# 5. 所要時間を記録
```

### 訓練チェックリスト
- [ ] ロールバック手順書に従って実施できるか
- [ ] 想定時間内に完了するか
- [ ] 手順に不明点はないか
- [ ] 必要な権限・アクセスがあるか
- [ ] バックアップが正常に機能するか

---

## 関連ドキュメント

- [デプロイ手順書](./deployment.md)
- [バックアップ・リストア手順](./backup-restore.md)
- [トラブルシューティングガイド](./troubleshooting.md)
