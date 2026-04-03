# 環境変数設定ガイド

このドキュメントでは、ホームヘルパー管理システムの環境変数設定について説明します。

## 目次

1. [概要](#概要)
2. [環境別設定](#環境別設定)
3. [バックエンド環境変数](#バックエンド環境変数)
4. [フロントエンド環境変数](#フロントエンド環境変数)
5. [セットアップ手順](#セットアップ手順)
6. [環境変数の検証](#環境変数の検証)
7. [トラブルシューティング](#トラブルシューティング)
8. [セキュリティベストプラクティス](#セキュリティベストプラクティス)

---

## 概要

### 環境変数管理の原則

1. **環境分離**: 開発・ステージング・本番環境で異なる設定を使用
2. **シークレット管理**: 機密情報は環境変数管理ツールで管理
3. **デフォルト値**: 開発環境では合理的なデフォルト値を提供
4. **検証**: 起動時に必須変数の存在を確認
5. **ドキュメント化**: 全ての環境変数を文書化

### ファイル構成

```
backend/
├── .env.example           # 開発環境用テンプレート
├── .env.prod.example      # 本番環境用テンプレート
├── .env                   # 実際の環境変数（Gitignore対象）
└── app/core/config.py     # 設定クラス

frontend/
├── .env.example           # 開発環境用テンプレート
├── .env.prod.example      # 本番環境用テンプレート
├── .env.local             # ローカル開発用（Gitignore対象）
├── .env.production        # 本番ビルド用（Gitignore対象）
└── vite.config.ts         # ビルド設定
```

---

## 環境別設定

### 開発環境 (Development)

**目的**: ローカル開発とデバッグ

```bash
# バックエンド
cp backend/.env.example backend/.env

# フロントエンド
cp frontend/.env.example frontend/.env.local
```

**特徴**:
- デバッグログ有効
- ホットリロード有効
- 開発用データベース使用
- CORS制限緩和

### ステージング環境 (Staging)

**目的**: 本番環境に近い環境でのテスト

```bash
# 本番設定をベースに作成
cp backend/.env.prod.example backend/.env.staging
cp frontend/.env.prod.example frontend/.env.staging
```

**特徴**:
- 本番に近い設定
- テストデータ使用
- 詳細ログ有効
- 外部サービスはテスト環境使用

### 本番環境 (Production)

**目的**: 実際のサービス提供

```bash
# 本番設定を作成
cp backend/.env.prod.example backend/.env.production
cp frontend/.env.prod.example frontend/.env.production
```

**特徴**:
- 最小限のログ
- 厳格なセキュリティ設定
- 本番データベース使用
- パフォーマンス最適化

---

## バックエンド環境変数

### 必須環境変数

本番環境で必ず設定が必要な環境変数：

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `ENV` | 環境識別子 | `production` |
| `SECRET_KEY` | アプリケーションシークレットキー | `openssl rand -hex 32` |
| `JWT_SECRET_KEY` | JWT署名用シークレットキー | `openssl rand -hex 32` |
| `DATABASE_URL` | データベース接続URL | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis接続URL | `redis://:password@host:6379/0` |
| `BACKEND_CORS_ORIGINS` | CORS許可オリジン | `https://yourdomain.com` |

### データベース設定

```bash
# 基本設定
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/helper_db

# 接続プール設定（Task 11.1 最適化）
DB_POOL_SIZE=20              # 接続プールサイズ
DB_MAX_OVERFLOW=10           # 追加接続数
DB_POOL_TIMEOUT=30           # 接続タイムアウト（秒）
DB_POOL_RECYCLE=3600         # 接続リサイクル時間（秒）
DB_POOL_PRE_PING=true        # 接続前のpingチェック
```

**推奨値**:
- 開発環境: `POOL_SIZE=5`, `MAX_OVERFLOW=5`
- ステージング: `POOL_SIZE=10`, `MAX_OVERFLOW=10`
- 本番環境: `POOL_SIZE=20-30`, `MAX_OVERFLOW=10-20`

### Redis設定（Task 11.5 キャッシュ戦略）

```bash
# 基本設定
REDIS_URL=redis://:password@redis:6379/0
REDIS_MAX_CONNECTIONS=20

# キャッシュTTL設定
CACHE_TTL_RECIPE=3600          # レシピ詳細: 1時間
CACHE_TTL_SEARCH=900           # 検索結果: 15分
CACHE_TTL_STATISTICS=3600      # 統計情報: 1時間
CACHE_TTL_POPULAR=7200         # 人気レシピ: 2時間
```

**環境別推奨値**:

| データ種別 | 開発環境 | ステージング | 本番環境 |
|------------|----------|--------------|----------|
| レシピ詳細 | 300秒 | 1800秒 | 3600-7200秒 |
| 検索結果 | 60秒 | 300秒 | 900-1800秒 |
| 統計情報 | 300秒 | 1800秒 | 3600-7200秒 |

### セキュリティ設定

```bash
# シークレットキー生成方法
openssl rand -hex 32  # SECRET_KEY用
openssl rand -hex 32  # JWT_SECRET_KEY用

# JWT設定
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DELTA=3600              # アクセストークン有効期限（1時間）
JWT_REFRESH_EXPIRATION_DELTA=2592000   # リフレッシュトークン有効期限（30日）

# パスワードハッシュ
PASSWORD_BCRYPT_ROUNDS=12  # 本番環境推奨値

# セッション設定
SESSION_COOKIE_SECURE=true      # HTTPS必須
SESSION_COOKIE_HTTPONLY=true    # JavaScript無効化
SESSION_COOKIE_SAMESITE=strict  # CSRF対策
```

### レート制限設定

```bash
# 環境別推奨値
# 開発環境
RATE_LIMIT_PER_MINUTE=1000
AUTH_RATE_LIMIT_PER_MINUTE=10
MAX_FAILED_ATTEMPTS=10

# 本番環境
RATE_LIMIT_PER_MINUTE=60
AUTH_RATE_LIMIT_PER_MINUTE=5
MAX_FAILED_ATTEMPTS=3
ACCOUNT_LOCK_DURATION=1800  # 30分
```

### ロギング設定

```bash
# 環境別推奨値
# 開発環境
LOG_LEVEL=DEBUG
LOG_FILE=logs/app.log
LOG_STDOUT=true

# 本番環境
LOG_LEVEL=WARNING
LOG_FILE=/var/log/helper/app.log
LOG_ROTATION=daily
LOG_RETENTION_DAYS=90
LOG_FORMAT=json
```

---

## フロントエンド環境変数

### 重要な注意事項

⚠️ **フロントエンド環境変数の特性**:

1. **`VITE_` プレフィックス必須**: クライアントに公開される変数は `VITE_` で始める必要があります
2. **ビルド時埋め込み**: 環境変数はビルド時にバンドルに埋め込まれます
3. **実行時変更不可**: ビルド後は変更できません
4. **シークレット禁止**: 機密情報は絶対に含めないでください

### 必須環境変数

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `VITE_API_URL` | バックエンドAPIのURL | `https://api.yourdomain.com/api/v1` |
| `VITE_APP_URL` | アプリケーションのURL | `https://yourdomain.com` |
| `VITE_NODE_ENV` | 環境識別子 | `production` |

### API設定

```bash
# 開発環境
VITE_API_URL=/api/v1                    # プロキシ経由
VITE_API_TIMEOUT=30000                  # 30秒
VITE_API_RETRY_ATTEMPTS=3

# 本番環境
VITE_API_URL=https://api.yourdomain.com/api/v1
VITE_API_TIMEOUT=30000
VITE_API_RETRY_ATTEMPTS=2
```

### React Query設定（Task 11.3）

```bash
# 開発環境（短めのTTL）
VITE_CACHE_STALE_TIME_MASTER=300000      # 5分
VITE_CACHE_STALE_TIME_USER=60000         # 1分
VITE_CACHE_STALE_TIME_REALTIME=10000     # 10秒

# 本番環境（長めのTTL）
VITE_CACHE_STALE_TIME_MASTER=3600000     # 60分
VITE_CACHE_STALE_TIME_USER=600000        # 10分
VITE_CACHE_STALE_TIME_REALTIME=30000     # 30秒
VITE_CACHE_STALE_TIME_STATISTICS=1800000 # 30分
```

### パフォーマンス設定（Task 11.2, 11.4）

```bash
# コード分割
VITE_CODE_SPLITTING=true
VITE_LAZY_LOAD_ROUTES=true
VITE_CHUNK_SIZE_WARNING_LIMIT=500

# 画像最適化
VITE_IMAGE_LAZY_LOAD=true
VITE_IMAGE_WEBP_ENABLED=true
VITE_IMAGE_PLACEHOLDER=true
VITE_IMAGE_QUALITY=85
```

### アクセシビリティ設定（WCAG 2.1 AA）

```bash
VITE_DEFAULT_FONT_SIZE=large
VITE_MIN_CONTRAST_RATIO=4.5
VITE_SCREEN_READER_OPTIMIZED=true
VITE_KEYBOARD_NAVIGATION=true
VITE_WCAG_COMPLIANCE_LEVEL=AA
```

---

## セットアップ手順

### 1. 開発環境のセットアップ

```bash
# バックエンド
cd backend
cp .env.example .env
# 必要に応じて .env を編集

# フロントエンド
cd frontend
cp .env.example .env.local
# 必要に応じて .env.local を編集
```

### 2. 本番環境のセットアップ

#### バックエンド

```bash
cd backend

# 1. テンプレートをコピー
cp .env.prod.example .env

# 2. シークレットキーを生成
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env

# 3. データベース接続情報を設定
# .env ファイルを編集

# 4. パーミッションを設定
chmod 600 .env

# 5. 設定を検証
python -c "from app.core.config import settings; print('OK')"
```

#### フロントエンド

```bash
cd frontend

# 1. テンプレートをコピー
cp .env.prod.example .env.production

# 2. API URLを設定
# .env.production ファイルを編集

# 3. ビルドして確認
npm run build
```

### 3. Docker環境でのセットアップ

```bash
# docker-compose.yml で環境変数ファイルを指定
services:
  backend:
    env_file:
      - ./backend/.env
    # または環境変数を直接指定
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
```

### 4. AWS環境でのセットアップ（推奨）

```bash
# AWS Secrets Manager を使用
aws secretsmanager create-secret \
  --name helper-system/backend/secret-key \
  --secret-string "$(openssl rand -hex 32)"

# アプリケーションから取得
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='helper-system/backend/secret-key')
```

---

## 環境変数の検証

### バックエンド検証スクリプト

`backend/scripts/validate_env.py`:

```python
"""環境変数検証スクリプト"""
import sys
from app.core.config import settings

def validate_environment():
    """環境変数を検証"""
    errors = []
    
    # 必須変数チェック
    required_vars = [
        'SECRET_KEY',
        'JWT_SECRET_KEY',
        'DATABASE_URL',
        'REDIS_URL',
    ]
    
    for var in required_vars:
        if not getattr(settings, var.lower(), None):
            errors.append(f"必須変数 {var} が設定されていません")
    
    # 本番環境チェック
    if settings.env == 'production':
        if settings.debug:
            errors.append("本番環境でDEBUGが有効です")
        
        if 'localhost' in settings.backend_cors_origins:
            errors.append("本番環境でlocalhostがCORSに含まれています")
        
        if settings.secret_key == 'your-secret-key-here':
            errors.append("SECRET_KEYがデフォルト値です")
    
    # 結果出力
    if errors:
        print("❌ 環境変数の検証に失敗しました:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✅ 環境変数の検証に成功しました")
        sys.exit(0)

if __name__ == '__main__':
    validate_environment()
```

実行方法:

```bash
cd backend
python scripts/validate_env.py
```

### フロントエンド検証

`frontend/scripts/validate-env.js`:

```javascript
/**
 * フロントエンド環境変数検証スクリプト
 */

const requiredVars = [
  'VITE_API_URL',
  'VITE_APP_URL',
];

const errors = [];

// 必須変数チェック
for (const varName of requiredVars) {
  if (!process.env[varName]) {
    errors.push(`必須変数 ${varName} が設定されていません`);
  }
}

// 本番環境チェック
if (process.env.VITE_NODE_ENV === 'production') {
  if (process.env.VITE_DEBUG === 'true') {
    errors.push('本番環境でDEBUGが有効です');
  }
  
  if (process.env.VITE_API_URL?.includes('localhost')) {
    errors.push('本番環境でlocalhostがAPI URLに含まれています');
  }
}

// 結果出力
if (errors.length > 0) {
  console.error('❌ 環境変数の検証に失敗しました:');
  errors.forEach(error => console.error(`  - ${error}`));
  process.exit(1);
} else {
  console.log('✅ 環境変数の検証に成功しました');
  process.exit(0);
}
```

実行方法:

```bash
cd frontend
node scripts/validate-env.js
```

---

## トラブルシューティング

### よくある問題

#### 1. 環境変数が読み込まれない

**症状**: アプリケーション起動時に環境変数が見つからない

**原因と対処**:
```bash
# 1. ファイル名を確認
ls -la backend/.env
ls -la frontend/.env.local

# 2. パーミッションを確認
chmod 600 backend/.env

# 3. フロントエンドはVITE_プレフィックスを確認
# ❌ API_URL=http://localhost:8000
# ✅ VITE_API_URL=http://localhost:8000

# 4. バックエンドは読み込みを確認
python -c "from app.core.config import settings; print(settings.database_url)"
```

#### 2. データベース接続エラー

**症状**: `sqlalchemy.exc.OperationalError: could not connect to server`

**原因と対処**:
```bash
# 1. DATABASE_URLの形式を確認
# ❌ postgresql://user:pass@host/db
# ✅ postgresql+asyncpg://user:pass@host:5432/db

# 2. 接続テスト
docker-compose exec backend python -c "
from app.database import engine
import asyncio
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT 1')
        print('接続成功:', result.scalar())
asyncio.run(test())
"

# 3. PostgreSQL起動確認
docker-compose ps postgres
docker-compose logs postgres
```

#### 3. Redis接続エラー

**症状**: `redis.exceptions.ConnectionError`

**原因と対処**:
```bash
# 1. REDIS_URLの形式を確認
# ✅ redis://redis:6379
# ✅ redis://:password@redis:6379/0

# 2. 接続テスト
docker-compose exec backend python -c "
from app.core.redis import redis_client
import asyncio
async def test():
    await redis_client.set('test', 'ok')
    value = await redis_client.get('test')
    print('接続成功:', value)
asyncio.run(test())
"

# 3. Redis起動確認
docker-compose ps redis
docker-compose logs redis
```

#### 4. CORS エラー

**症状**: `Access to XMLHttpRequest has been blocked by CORS policy`

**原因と対処**:
```bash
# 1. BACKEND_CORS_ORIGINSを確認
# バックエンド .env
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# 2. カンマ区切りで複数指定可能
BACKEND_CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 3. 設定反映を確認
docker-compose restart backend
```

#### 5. ビルドエラー（フロントエンド）

**症状**: `ReferenceError: process is not defined`

**原因と対処**:
```bash
# フロントエンドはVITE_プレフィックス必須
# ❌ API_URL
# ✅ VITE_API_URL

# ビルド時に環境変数を確認
npm run build -- --mode production
```

---

## セキュリティベストプラクティス

### 1. シークレット管理

#### 開発環境

```bash
# .env ファイルを使用（Gitignore済み）
backend/.env
frontend/.env.local
```

#### 本番環境

**推奨**: AWS Secrets Manager / HashiCorp Vault

```bash
# AWS Secrets Managerの使用例
aws secretsmanager create-secret \
  --name helper-system/database-url \
  --secret-string "postgresql+asyncpg://..."

# アプリケーションから取得
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='ap-northeast-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# 環境変数にフォールバック
DATABASE_URL = get_secret('helper-system/database-url') or os.getenv('DATABASE_URL')
```

### 2. シークレットローテーション

```bash
# 定期的にシークレットをローテーション（3ヶ月ごと推奨）

# 1. 新しいシークレット生成
NEW_SECRET=$(openssl rand -hex 32)

# 2. データベース更新（古いシークレットと新しいシークレット両方有効に）
# アプリケーション設定で新旧両方を許可

# 3. 全インスタンスに新シークレットをデプロイ

# 4. 全インスタンス更新後、古いシークレットを無効化
```

### 3. アクセス制御

```bash
# ファイルパーミッション
chmod 600 backend/.env
chown app:app backend/.env

# Docker Secretsの使用
docker secret create db_password -
# パスワードを入力

# docker-compose.yml
services:
  backend:
    secrets:
      - db_password
secrets:
  db_password:
    external: true
```

### 4. 監査とロギング

```python
# backend/app/core/config.py
import logging

class Settings(BaseSettings):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 本番環境でのシークレット警告
        if self.env == 'production':
            if 'localhost' in self.backend_cors_origins:
                logging.warning("本番環境でlocalhostがCORS許可されています")
            
            if len(self.secret_key) < 32:
                logging.error("SECRET_KEYが短すぎます（32文字以上推奨）")
```

### 5. 環境分離

```bash
# 環境ごとに完全に分離された設定を使用
backend/
├── .env.development    # 開発環境
├── .env.staging        # ステージング環境
└── .env.production     # 本番環境

# 環境指定でアプリケーション起動
ENV=production uvicorn app.main:app
```

---

## まとめ

### デプロイ前チェックリスト

#### バックエンド
- [ ] `SECRET_KEY` を強力なランダム値に変更
- [ ] `JWT_SECRET_KEY` を強力なランダム値に変更
- [ ] `DATABASE_URL` のパスワードを変更
- [ ] `REDIS_URL` のパスワードを設定
- [ ] `BACKEND_CORS_ORIGINS` を本番ドメインに変更
- [ ] `DEBUG=false` に設定
- [ ] `LOG_LEVEL=WARNING` に設定
- [ ] SMTP設定を本番環境に変更
- [ ] ファイルパーミッションを `600` に設定
- [ ] 環境変数検証スクリプトを実行

#### フロントエンド
- [ ] `VITE_API_URL` を本番APIのURLに変更
- [ ] `VITE_APP_URL` を本番ドメインに変更
- [ ] `VITE_DEBUG=false` に設定
- [ ] `VITE_LOG_LEVEL=error` に設定
- [ ] 外部サービスAPIキーを設定
- [ ] 環境変数検証スクリプトを実行
- [ ] ビルドテストを実行

### 参考資料

- [Vite環境変数とモード](https://ja.vitejs.dev/guide/env-and-mode.html)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [AWS Secrets Manager](https://aws.amazon.com/jp/secrets-manager/)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
- [Twelve-Factor App](https://12factor.net/ja/)
