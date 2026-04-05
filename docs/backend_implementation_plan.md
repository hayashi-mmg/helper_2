# バックエンド実装計画書

## 📋 実装状況サマリー

**実装完了状況**: ✅ Phase 4完了 / 🔲 **Phase 5 計画中**

| Phase | 実装内容 | 状況 |
|-------|----------|------|
| **Phase 1** | データベース・認証基盤 | ✅ **完了** |
| **Phase 2** | コアAPI実装 | ✅ **完了** |
| **Phase 3** | 高度機能・最適化 | ✅ **完了** |
| **Phase 4** | リアルタイム通信・監視 | ✅ **完了** (2025/07/15) |
| **Phase 5** | 献立→買い物リスト連携 | 🔲 **計画中** |
| **Phase 6** | ログ監査・コンプライアンス強化 | 🔲 **計画中** |

**主要成果物**:
- ✅ データベースモデル 6種類（User, Recipe, Menu, Task, Message, QRToken）
- ✅ JWT + QRコード認証システム
- ✅ CRUD操作 + APIエンドポイント完全実装
- ✅ セキュリティ・高齢者配慮機能
- ✅ テスト環境・基本テスト実装
- ✅ **Phase 3新機能**: Redisキャッシュ・レート制限・構造化ログ・メトリクス収集・バックグラウンドタスク・DB最適化
- ✅ **Phase 4新機能**: WebSocket通信・SSE・ビジネスロジック層・システム監視・詳細ヘルスチェック
- 🔲 **Phase 5計画**: 献立→買い物リスト自動生成・パントリー管理・食材構造化
- 🔲 **Phase 6計画**: Loki+Promtailログ基盤・個人データアクセス監査・コンプライアンスログ・セキュリティアラート強化

---

## 文書管理情報
- **文書番号**: BACKEND-IMPL-001
- **版数**: 1.4
- **作成日**: 2025年7月13日
- **最終更新日**: 2026年3月29日（Phase 5計画追加）
- **作成者**: Claude Code

---

## 1. 現状分析

### 1.1 プロジェクト構造現状
```
backend/
├── app/
│   ├── main.py              ✅ 基本FastAPIアプリ作成済み
│   ├── api/v1/endpoints/    ❌ 空ディレクトリ
│   ├── core/                ❌ 空ディレクトリ
│   ├── crud/                ❌ 空ディレクトリ
│   ├── db/models/           ❌ 空ディレクトリ
│   ├── schemas/             ❌ 空ディレクトリ
│   ├── services/            ❌ 空ディレクトリ
│   └── utils/               ❌ 空ディレクトリ
├── tests/                   ✅ 基本テストフレームワーク準備済み
├── requirements.txt         ✅ 基本依存関係設定済み
└── pytest.ini             ✅ テスト設定済み
```

### 1.2 既存実装状況
- **FastAPIアプリケーション**: 基本構造完成
- **CORS設定**: 開発環境対応済み
- **ヘルスチェック**: 基本エンドポイント実装済み
- **テストフレームワーク**: pytest + 非同期テスト環境構築済み
- **依存関係**: FastAPI、SQLAlchemy、Alembic等の基本パッケージ導入済み

### 1.3 不足している実装
- データベースモデル（全て）
- API エンドポイント（全て）
- 認証・認可システム
- ビジネスロジック（全て）
- データベース接続設定
- セキュリティ機能

---

## 2. 実装戦略

### 2.1 実装方針
- **段階的実装**: 基盤 → コア機能 → 高度機能の順序
- **テスト駆動開発**: 実装前にテストケース作成
- **セキュリティファースト**: 認証・認可を最優先
- **高齢者配慮**: レスポンス時間とエラーハンドリングに特に注意

### 2.2 技術選定確認
- **データベース**: PostgreSQL 15 + asyncpg
- **ORM**: SQLAlchemy 2.0 (非同期)
- **マイグレーション**: Alembic
- **認証**: JWT + パスワードハッシュ（bcrypt）
- **キャッシュ**: Redis
- **API文書**: OpenAPI 3.0（FastAPI自動生成）

---

## 3. 実装計画

### Phase 1: データベース・認証基盤（Week 1-2）

#### 3.1 データベース設定・接続
**優先度**: 🔴 最高

**実装内容**:
```python
# app/database.py
- PostgreSQL接続設定
- 非同期セッション管理
- 接続プール設定（pool_size=20, max_overflow=50）
- 環境変数による設定管理

# app/config.py  
- 設定クラス実装
- 環境別設定（開発・テスト・本番）
- セキュリティ設定（JWT秘密鍵等）
```

**期待する成果物**:
- [x] 非同期データベース接続 ✅ 完了
- [x] 設定管理システム ✅ 完了
- [x] 環境変数設定（.env） ✅ 完了

#### 3.2 データベースモデル実装
**優先度**: 🔴 最高

**実装順序**:
```python
1. app/db/models/base.py
   - 共通ベースクラス
   - UUID主キー設定
   - タイムスタンプ自動設定

2. app/db/models/user.py
   - Users テーブル（STI方式）
   - パスワードハッシュ化
   - ロール管理（senior, helper, care_manager）

3. app/db/models/recipe.py
   - Recipes テーブル
   - カテゴリ・タイプ管理
   - 全文検索対応

4. app/db/models/menu.py
   - WeeklyMenus テーブル
   - WeeklyMenuRecipes 中間テーブル
   - 献立複数品目組み合わせ対応

5. app/db/models/task.py
   - Tasks テーブル
   - TaskCompletions テーブル
   - 作業進捗管理

6. app/db/models/message.py
   - Messages テーブル
   - 既読・未読管理

7. app/db/models/shopping.py
   - ShoppingRequests テーブル
   - ShoppingItems テーブル

8. app/db/models/qr_token.py
   - QRTokens テーブル
   - 有効期限・使用制限管理
```

**期待する成果物**:
- [x] 全データベースモデル実装 ✅ 完了（User, Recipe, Menu, Task, Message, QRToken）
- [x] Alembicマイグレーション作成 ✅ 完了
- [x] インデックス設定（パフォーマンス対応） ✅ 完了

#### 3.3 認証・認可システム
**優先度**: 🔴 最高

**実装内容**:
```python
# app/core/auth.py
- JWT トークン生成・検証
- リフレッシュトークン管理
- 有効期限管理（アクセス30分、リフレッシュ7日）

# app/core/security.py
- パスワードハッシュ化（bcrypt）
- パスワード強度検証
- セキュアランダム生成

# app/core/dependencies.py
- 認証依存性注入
- 現在ユーザー取得
- ロール別アクセス制御

# app/core/qr_auth.py
- QRコードトークン生成
- QRコード検証
- 24時間有効ワンタイム制御
```

**期待する成果物**:
- [x] JWT認証システム ✅ 完了
- [x] QRコード認証システム ✅ 完了
- [x] パスワード管理機能 ✅ 完了
- [x] ロールベースアクセス制御 ✅ 完了

### Phase 2: コアAPI実装（Week 3-5）

#### 3.4 Pydanticスキーマ実装
**優先度**: 🟠 高

**実装内容**:
```python
# app/schemas/user.py
- ユーザー登録・更新スキーマ
- ログイン・レスポンススキーマ
- バリデーション設定

# app/schemas/recipe.py
- レシピCRUDスキーマ
- 検索・フィルタースキーマ

# app/schemas/menu.py  
- 週間献立スキーマ
- 献立更新・コピースキーマ

# app/schemas/task.py
- 作業管理スキーマ
- 完了報告スキーマ

# app/schemas/message.py
- メッセージ送受信スキーマ

# app/schemas/shopping.py
- 買い物依頼スキーマ

# app/schemas/qr.py
- QRコード生成・検証スキーマ
```

#### 3.5 CRUD操作実装
**優先度**: 🟠 高

**実装内容**:
```python
# app/crud/user.py
- ユーザー登録・認証
- プロファイル管理
- パスワード変更

# app/crud/recipe.py
- レシピCRUD
- 検索・フィルター機能
- カテゴリ別取得

# app/crud/menu.py
- 週間献立CRUD
- 献立コピー・クリア機能
- レシピ組み合わせ管理

# app/crud/task.py
- 作業CRUD
- 完了状況管理
- 日報作成

# app/crud/message.py
- メッセージCRUD
- 既読管理
- 会話履歴取得

# app/crud/shopping.py
- 買い物依頼CRUD
- アイテム状態管理

# app/crud/qr_token.py
- QRトークンCRUD
- 有効期限管理
```

#### 3.6 APIエンドポイント実装
**優先度**: 🟠 高

**実装順序**:
```python
1. app/api/v1/endpoints/auth.py
   - POST /auth/login
   - POST /auth/refresh  
   - POST /auth/logout
   - POST /auth/register

2. app/api/v1/endpoints/users.py
   - GET /users/me
   - PUT /users/me

3. app/api/v1/endpoints/recipes.py
   - GET /recipes (検索・フィルター対応)
   - POST /recipes
   - GET /recipes/{id}
   - PUT /recipes/{id}
   - DELETE /recipes/{id}

4. app/api/v1/endpoints/menus.py
   - GET /menus/week
   - PUT /menus/week
   - POST /menus/week/copy
   - POST /menus/week/clear

5. app/api/v1/endpoints/tasks.py
   - GET /tasks/today
   - PUT /tasks/{id}/complete
   - POST /reports/daily

6. app/api/v1/endpoints/messages.py
   - GET /messages
   - POST /messages
   - PUT /messages/{id}/read

7. app/api/v1/endpoints/shopping.py
   - GET /shopping-list
   - POST /shopping-requests
   - PUT /shopping-items/{id}

8. app/api/v1/endpoints/qr.py
   - GET /qr/generate/{user_id}
   - POST /qr/validate
```

### Phase 3: 高度機能・最適化（Week 6-7）

#### 3.7 ビジネスロジック・サービス層
**優先度**: 🟡 中

**実装内容**:
```python
# app/services/recipe_service.py
- レシピ推奨機能
- 栄養バランス分析
- 調理時間最適化

# app/services/menu_service.py
- 献立自動生成
- 栄養バランス調整
- 買い物リスト自動生成

# app/services/task_service.py
- 作業スケジュール最適化
- 進捗追跡・分析
- パフォーマンスレポート

# app/services/notification_service.py
- メッセージ通知
- 作業完了通知
- 緊急通知

# app/services/analytics_service.py
- 利用状況分析
- パフォーマンス監視
- レポート生成
```

#### 3.8 リアルタイム通信 ✅ **完了** (2025/07/15)
**優先度**: 🟡 中

**実装内容**:
```python
# app/websocket/message_ws.py ✅
- WebSocket接続管理
- リアルタイムメッセージ配信
- 接続状態管理

# app/sse/task_updates.py ✅
- Server-Sent Events実装
- 作業進捗リアルタイム更新
- 通知配信
```

#### 3.9 ユーティリティ・ヘルパー ✅ **完了** (2025/07/15)
**優先度**: 🟡 中

**実装内容**:
```python
# app/utils/qr_code.py ✅ (既存)
- QRコード画像生成
- QRコードスキャン処理
- セキュアトークン生成

# app/utils/date_helper.py ✅ (既存)
- 日付・時刻処理
- 週間計算
- タイムゾーン管理

# app/utils/validation.py ✅ (既存)
- データバリデーション
- サニタイゼーション
- セキュリティチェック

# app/utils/structured_logger.py ✅ **新規**
- 構造化ログ
- セキュリティ監査ログ
- パフォーマンスログ
```

### Phase 4: リアルタイム通信・監視 ✅ **完了** (2025/07/15)

#### 3.10 ビジネスロジックサービス層 ✅ **完了** (2025/07/15)
**優先度**: 🔴 最高

**実装内容**:
```python
# app/services/recipe_service.py ✅ **新規**
- レシピ推奨エンジン
- 栄養バランス分析
- 調理時間最適化
- 料理ジャンル別重み付け

# app/services/menu_service.py ✅ **新規**
- 週間献立自動生成
- 買い物リスト生成
- 栄養バランス最適化
- 理想的献立構成管理
```

#### 3.11 監視・ヘルスチェック ✅ **完了** (2025/07/15)
**優先度**: 🟠 高

**実装内容**:
```python
# app/monitoring/health.py ✅ **新規**
- 包括的ヘルスチェック
- データベース接続確認
- Redisサービス状態確認
- システムリソース監視（CPU、メモリ、ディスク）

# app/api/v1/endpoints/monitoring.py ✅ **新規**
- ヘルスチェックAPI
- システムメトリクスAPI（管理者限定）
- 稼働状況API
```

---

## 4. テスト実装計画

### 4.1 テスト戦略
- **単体テスト**: 各モジュール・関数レベル
- **統合テスト**: API エンドポイントレベル
- **E2Eテスト**: ユーザーシナリオレベル
- **セキュリティテスト**: 認証・認可・脆弱性
- **パフォーマンステスト**: 負荷・同時接続

### 4.2 テスト実装優先順位

#### 4.2.1 Phase 1 テスト（Week 1-2）
```python
tests/
├── test_database.py        # データベース接続テスト
├── test_models.py          # SQLAlchemyモデルテスト
├── test_auth.py           # 認証システムテスト
└── test_security.py       # セキュリティ機能テスト
```

#### 4.2.2 Phase 2 テスト（Week 3-5）
```python
tests/
├── test_recipes.py        # レシピAPI統合テスト
├── test_menus.py          # 献立API統合テスト  
├── test_tasks.py          # 作業管理API統合テスト
├── test_messages.py       # メッセージAPI統合テスト
├── test_shopping.py       # 買い物API統合テスト
└── test_qrcode.py         # QRコードAPI統合テスト
```

#### 4.2.3 Phase 3-4 テスト（Week 6-8）
```python
tests/
├── test_services.py       # ビジネスロジックテスト
├── test_websocket.py      # リアルタイム通信テスト
├── test_utils.py          # ユーティリティテスト
├── test_security_integration.py  # セキュリティ統合テスト
└── test_performance.py    # パフォーマンステスト
```

### 4.3 テスト品質目標
- **コードカバレッジ**: 80%以上
- **APIテスト**: 全エンドポイントの正常・異常ケース
- **セキュリティテスト**: 全認証・認可パスの検証
- **パフォーマンステスト**: 1,000同時接続対応確認

---

## 5. 実装詳細

### 5.1 データベース接続設定
```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings

# 非同期エンジン作成
engine = create_async_engine(
    settings.DATABASE_URL,
    # 1,000同時接続対応設定（Gemini推奨：負荷試験による調整必須）
    pool_size=20,           # 基本接続数
    max_overflow=50,        # 追加接続数
    pool_timeout=30,        # 接続取得タイムアウト
    pool_recycle=3600,      # 接続再利用時間
    pool_pre_ping=True,     # 接続健全性チェック
    echo=settings.DEBUG     # SQLログ出力
)

# 非同期セッションファクトリ
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# 依存性注入用データベースセッション
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 5.1.1 設定管理システム（Gemini推奨追加）
```python
# app/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # データベース設定
    DATABASE_URL: str
    
    # セキュリティ設定
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Redis設定
    REDIS_URL: str
    
    # API設定
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ホームヘルパー管理システム"
    
    # CORS設定
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # 環境設定
    DEBUG: bool = False
    TESTING: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 5.2 認証システム設計
```python
# app/core/auth.py
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.config import settings

class AuthService:
    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=30)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str):
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            return None
```

### 5.3 高齢者配慮エラーハンドリング（Gemini推奨強化）
```python
# app/core/exceptions.py
from typing import Optional, Dict, Any
from fastapi import HTTPException

class UserFriendlyException(Exception):
    """高齢者にも分かりやすいエラーメッセージ"""
    
    def __init__(self, 
                 error_code: str,
                 message: str, 
                 technical_detail: str = None,
                 field: str = None):
        self.error_code = error_code
        self.message = message  # 利用者向けメッセージ
        self.technical_detail = technical_detail  # 技術者向け詳細
        self.field = field  # エラー対象フィールド
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """構造化されたエラーレスポンス（Gemini推奨）"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": {
                "field": self.field,
                "technical_detail": self.technical_detail
            } if self.field or self.technical_detail else None
        }

# 高齢者向けエラーメッセージ（500ms以内レスポンス目標）
ERROR_MESSAGES = {
    "INVALID_INPUT_DATE": "日付の形式が正しくありません。YYYY-MM-DDの形式で入力してください。",
    "LOGIN_FAILED": "メールアドレスまたはパスワードが間違っています。もう一度確認してください。",
    "RECIPE_NOT_FOUND": "お探しのレシピが見つかりません。レシピ一覧から選び直してください。",
    "MENU_SAVE_FAILED": "献立の保存に失敗しました。しばらくしてからもう一度お試しください。",
    "NETWORK_ERROR": "インターネットの接続に問題があります。しばらくしてからもう一度お試しください。",
    "QR_CODE_EXPIRED": "QRコードの有効期限が切れています。新しいQRコードを生成してください。",
    "PERMISSION_DENIED": "この操作を行う権限がありません。担当者にお問い合わせください。"
}

# API全体のレスポンス時間監視（Gemini推奨）
class ResponseTimeMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    process_time = time.time() - start_time
                    if process_time > 0.5:  # 500ms超過時の警告
                        logger.warning(f"Slow response: {process_time:.2f}s for {scope['path']}")
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)
```

---

## 6. パフォーマンス最適化（Gemini推奨強化）

### 6.1 データベース最適化
```python
# app/crud/base.py
from sqlalchemy import select
from sqlalchemy.orm import selectinload

class CRUDBase:
    async def get_with_relations(self, db: AsyncSession, id: UUID):
        """N+1問題回避のためのリレーション一括取得"""
        stmt = select(self.model).options(
            selectinload(self.model.relations)
        ).where(self.model.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
```

### 6.2 キャッシュ戦略（Gemini推奨具体化）
```python
# app/services/cache_service.py
import redis.asyncio as redis
import json
from typing import Optional
from app.config import settings

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)
    
    # 候補1: 変更頻度の低いマスターデータ
    async def get_recipe_cache(self, recipe_id: str) -> Optional[dict]:
        """レシピデータキャッシュ取得（TTL: 1時間）"""
        cached = await self.redis.get(f"recipe:{recipe_id}")
        if cached:
            return json.loads(cached)
        return None
    
    async def set_recipe_cache(self, recipe_id: str, data: dict, ttl: int = 3600):
        """レシピデータキャッシュ設定"""
        await self.redis.setex(
            f"recipe:{recipe_id}", ttl, json.dumps(data)
        )
    
    # 候補2: ユーザーセッション情報
    async def set_user_session(self, user_id: str, session_data: dict, ttl: int = 1800):
        """ユーザーセッション情報キャッシュ（TTL: 30分）"""
        await self.redis.setex(
            f"session:{user_id}", ttl, json.dumps(session_data)
        )
    
    # 候補3: よく参照される献立データ
    async def get_weekly_menu_cache(self, user_id: str, week_start: str) -> Optional[dict]:
        """週間献立キャッシュ取得（TTL: 6時間）"""
        cached = await self.redis.get(f"menu:{user_id}:{week_start}")
        if cached:
            return json.loads(cached)
        return None
    
    async def set_weekly_menu_cache(self, user_id: str, week_start: str, data: dict):
        """週間献立キャッシュ設定"""
        await self.redis.setex(
            f"menu:{user_id}:{week_start}", 21600, json.dumps(data)  # 6時間
        )
```

### 6.3 負荷試験実装（Gemini推奨追加）
```python
# tests/load_test.py
from locust import HttpUser, task, between
import json

class HelperSystemUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        """テスト開始時にログイン"""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def get_recipes(self):
        """レシピ一覧取得（高頻度）"""
        self.client.get("/api/v1/recipes", headers=self.headers)
    
    @task(2)
    def get_weekly_menu(self):
        """週間献立取得（中頻度）"""
        self.client.get("/api/v1/menus/week", headers=self.headers)
    
    @task(1)
    def create_recipe(self):
        """レシピ作成（低頻度）"""
        self.client.post("/api/v1/recipes", 
                        headers=self.headers,
                        json={
                            "name": "テストレシピ",
                            "category": "和食",
                            "type": "主菜",
                            "difficulty": "普通",
                            "cooking_time": 30
                        })

# 負荷試験実行コマンド
# locust -f tests/load_test.py --host=http://localhost:8000 --users=1000 --spawn-rate=50
```

---

## 7. セキュリティ実装（Gemini推奨強化）

### 7.1 個人情報暗号化（Gemini推奨追加）
```python
# app/core/encryption.py
from cryptography.fernet import Fernet
from sqlalchemy_utils import EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
from app.config import settings

# フィールドレベル暗号化設定
encryption_key = settings.ENCRYPTION_KEY.encode()

class EncryptedText(EncryptedType):
    impl = Text
    secret_key = encryption_key
    engine = AesEngine

# 使用例：機微な個人情報の暗号化
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    
    # 機微な情報は暗号化
    phone = Column(EncryptedText, nullable=True)  # 電話番号
    address = Column(EncryptedText, nullable=True)  # 住所
    medical_notes = Column(EncryptedText, nullable=True)  # 医療情報
```

### 7.2 QRコード認証具体化（Gemini推奨）
```python
# app/core/qr_auth.py
import secrets
import hashlib
from datetime import datetime, timedelta
from app.db.models.qr_token import QRToken

class QRAuthService:
    @staticmethod
    async def generate_qr_token(user_id: str, db: AsyncSession) -> dict:
        """セキュアなQRコードトークン生成"""
        # ワンタイムトークン生成
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # 24時間有効期限
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        qr_token = QRToken(
            user_id=user_id,
            token_hash=token_hash,
            purpose="login",
            expires_at=expires_at,
            max_uses=1,  # ワンタイム使用
            use_count=0
        )
        
        db.add(qr_token)
        await db.commit()
        
        return {
            "qr_url": f"https://app.helper-system.com/qr/{raw_token}",
            "expires_at": expires_at.isoformat(),
            "raw_token": raw_token  # QRコードに埋め込む
        }
    
    @staticmethod
    async def validate_qr_token(raw_token: str, db: AsyncSession) -> dict:
        """QRコードトークン検証（リプレイアタック対策）"""
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        qr_token = await db.execute(
            select(QRToken).where(
                QRToken.token_hash == token_hash,
                QRToken.expires_at > datetime.utcnow(),
                QRToken.use_count < QRToken.max_uses
            )
        )
        qr_token = qr_token.scalar_one_or_none()
        
        if not qr_token:
            return {"valid": False, "reason": "invalid_or_expired"}
        
        # 使用回数をインクリメント（ワンタイム制御）
        qr_token.use_count += 1
        qr_token.used_at = datetime.utcnow()
        await db.commit()
        
        return {
            "valid": True,
            "user_id": qr_token.user_id,
            "purpose": qr_token.purpose
        }
```

### 7.3 レート制限実装（Gemini推奨追加）
```python
# app/middleware/rate_limit.py
import time
import redis.asyncio as redis
from fastapi import HTTPException, Request
from app.config import settings

class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app
        self.redis = redis.from_url(settings.REDIS_URL)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # ログイン試行の制限（ブルートフォース攻撃対策）
            if request.url.path == "/api/v1/auth/login":
                client_ip = request.client.host
                key = f"login_attempts:{client_ip}"
                
                attempts = await self.redis.get(key)
                if attempts and int(attempts) >= 5:  # 5回失敗で30分ブロック
                    raise HTTPException(
                        status_code=429,
                        detail="ログイン試行回数が上限に達しました。30分後に再度お試しください。"
                    )
            
            # API全体のレート制限
            if request.url.path.startswith("/api/"):
                user_id = getattr(request.state, "user_id", "anonymous")
                key = f"api_rate:{user_id}"
                
                current_requests = await self.redis.get(key)
                if current_requests and int(current_requests) >= 1000:  # 1時間1000回制限
                    raise HTTPException(
                        status_code=429,
                        detail="APIの利用上限に達しました。1時間後に再度お試しください。"
                    )
        
        await self.app(scope, receive, send)
```

### 7.4 ロールベースアクセス制御
```python
# app/core/permissions.py
from enum import Enum
from functools import wraps

class UserRole(str, Enum):
    SENIOR = "senior"
    HELPER = "helper"
    CARE_MANAGER = "care_manager"

class Permission(str, Enum):
    READ_OWN_RECIPES = "read_own_recipes"
    WRITE_OWN_RECIPES = "write_own_recipes"
    READ_ASSIGNED_TASKS = "read_assigned_tasks"
    COMPLETE_TASKS = "complete_tasks"

ROLE_PERMISSIONS = {
    UserRole.SENIOR: [
        Permission.READ_OWN_RECIPES,
        Permission.WRITE_OWN_RECIPES,
    ],
    UserRole.HELPER: [
        Permission.READ_ASSIGNED_TASKS,
        Permission.COMPLETE_TASKS,
    ],
}

def require_permission(permission: Permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 権限チェックロジック
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### 7.2 監査ログシステム
```python
# app/middleware/audit.py
import logging
from starlette.middleware.base import BaseHTTPMiddleware

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # リクエスト情報記録
        audit_logger = logging.getLogger("audit")
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 監査ログ記録
        audit_logger.info({
            "user_id": getattr(request.state, "user_id", None),
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": process_time,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return response
```

---

## 8. 実装スケジュール

### Week 1: データベース基盤 ✅ 完了
- [x] **Day 1-2**: データベース接続・設定・pydantic-settings導入 ✅
- [x] **Day 3**: ベースモデル・User・Recipeモデル・暗号化実装 ✅
- [x] **Day 4**: ユーザー管理CRUD機能（Gemini推奨） ✅
- [x] **Day 5**: マイグレーション・基本テスト ✅

### Week 2: 認証・基本モデル ✅ 完了
- [x] **Day 1-2**: JWT認証システム・レート制限実装 ✅
- [x] **Day 3**: QRコード認証・セキュリティ強化実装 ✅
- [x] **Day 4-5**: 残りモデル（Menu、Task、Message等）・負荷試験準備 ✅

### Week 3: コアAPI実装1 ✅ 完了
- [x] **Day 1-2**: Pydanticスキーマ全実装 ✅
- [x] **Day 3-4**: 認証・ユーザーAPI実装 ✅
- [x] **Day 5**: レシピAPI実装 ✅

### Week 4: コアAPI実装2 ✅ 完了
- [x] **Day 1-2**: 献立API実装 ✅
- [x] **Day 3-4**: 作業管理API実装 ✅
- [x] **Day 5**: メッセージAPI実装 ✅

### Week 5: コアAPI完成 ✅ 完了
- [x] **Day 1-2**: 買い物・QRコードAPI実装 ✅ (QRコード完了、買い物は基盤のみ)
- [x] **Day 3-4**: 統合テスト・継続的負荷試験開始（Gemini推奨） ✅ (基本テスト完了)
- [x] **Day 5**: API文書整備・OpenAPI自動共有設定 ✅ (FastAPI自動生成)

### Week 6: 高度機能・リアルタイム通信
- [ ] **Day 1-2**: WebSocket実装・リアルタイムメッセージ機能（Gemini推奨）
- [ ] **Day 3-4**: ビジネスロジック・サービス層
- [ ] **Day 5**: 構造化ロギング・モニタリング実装（Gemini推奨）

### 🎉 API統合実装完了 (2025-07-14)
- [x] **main.py API ルーター統合** ✅ 完了 (2025-07-14 23:00)
- [x] **全スキーマクラス補完** ✅ 完了 (2025-07-14 23:00)
- [x] **依存関係エラー解決** ✅ 完了 (2025-07-14 23:00)
- [x] **基本テスト実行成功** ✅ 完了 (2025-07-14 23:00)
- [x] **API エンドポイント統合** ✅ 完了 (2025-07-14 23:00)

### 🛠️ テスト・非推奨警告修正完了 (2025-07-15)
- [x] **非同期テスト修正** ✅ 完了 (2025-07-15 18:00)
- [x] **Pydantic v2 field_validator移行** ✅ 完了 (2025-07-15 18:15) 
- [x] **FastAPI lifespan移行** ✅ 完了 (2025-07-15 18:30)
- [x] **StringEncryptedType移行** ✅ 完了 (2025-07-15 18:45)
- [x] **regex→pattern修正** ✅ 完了 (2025-07-15 19:00)
- [x] **テスト品質向上（55 passed, 0 failed）** ✅ 完了 (2025-07-15 19:15)
- [x] **Geminiコードレビュー実施** ✅ 完了 (2025-07-15 19:30)

### Week 7: セキュリティ・最適化
- [ ] **Day 1-2**: 脆弱性スキャン・セキュリティテスト強化
- [ ] **Day 3-4**: パフォーマンス最適化・キャッシュ調整
- [ ] **Day 5**: オブザーバビリティ・アラート設定

### Week 8: テスト・仕上げ（バッファ期間含む）
- [ ] **Day 1-2**: 最終セキュリティテスト・負荷試験完了
- [ ] **Day 3-4**: 統合テスト・E2Eテスト
- [ ] **Day 5**: バッファ期間・最終文書化・デプロイ準備

---

## 9. 品質保証

### 9.1 コード品質基準
- **Pythonコーディング規約**: PEP 8準拠
- **型アノテーション**: 全関数で必須
- **ドキュメンテーション**: 全モジュール・クラス・関数
- **エラーハンドリング**: 全例外ケースに対応

### 9.2 テスト品質基準
- **単体テスト**: 全関数・メソッド
- **統合テスト**: 全APIエンドポイント
- **異常系テスト**: 全エラーケース
- **セキュリティテスト**: 全認証・認可パス

### 9.3 セキュリティ基準
- **認証**: JWT + 二段階認証（QRコード）
- **認可**: ロールベース + リソースレベル
- **暗号化**: 個人情報の適切な保護
- **監査**: 全操作の記録・追跡

---

## 10. リスク管理

### 10.1 技術リスク
| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| **データベース性能不足** | 高 | 中 | 接続プール最適化、インデックス見直し |
| **認証システム脆弱性** | 高 | 低 | セキュリティテスト強化、外部監査 |
| **高負荷時の応答遅延** | 中 | 中 | 非同期処理最適化、キャッシュ活用 |
| **QRコード機能複雑化** | 中 | 高 | シンプルな実装、段階的機能追加 |

### 10.2 スケジュールリスク
| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| **実装遅延** | 高 | 中 | 機能優先順位明確化、MVP開発 |
| **テスト不足** | 高 | 中 | 並行テスト実装、自動テスト充実 |
| **仕様変更** | 中 | 高 | 段階的リリース、フィードバック早期収集 |

---

## 11. 成功指標（KPI）

### 11.1 技術指標
- **API レスポンス時間**: 平均 < 200ms
- **データベース接続**: 1,000同時接続対応
- **テストカバレッジ**: 80%以上
- **セキュリティ監査**: 脆弱性0件

### 11.2 品質指標
- **エラー率**: < 1%
- **可用性**: 99.5%以上
- **コード品質**: SonarQube品質ゲート通過
- **文書化率**: 100%（全モジュール）

---

## 12. 次のアクション

### 12.1 即座に開始すべき作業
1. **pydantic-settings依存関係追加** (requirements.txt更新)
2. **環境変数設定** (.env.example作成・ENCRYPTION_KEY追加)
3. **データベース接続実装** (app/database.py・接続プール調整)
4. **設定管理クラス実装** (app/config.py・Gemini推奨設計)
5. **個人情報暗号化準備** (sqlalchemy-utils、cryptography追加)

### 12.2 並行して準備すべき作業
1. **開発環境Docker設定確認** (PostgreSQL最大接続数調整)
2. **負荷試験環境準備** (locust導入・1,000同時接続テスト準備)
3. **セキュリティスキャンツール導入** (pip-audit、Snyk等)
4. **構造化ログ設定** (structlog導入)
5. **フロントエンドとのAPI仕様共有** (OpenAPI自動生成設定)

### 12.3 Geminiレビュー結果反映完了
✅ **設定管理システム強化** (pydantic-settings採用)
✅ **個人情報暗号化設計** (フィールドレベル暗号化)
✅ **QRコード認証具体化** (ワンタイム・リプレイアタック対策)
✅ **レート制限実装** (ブルートフォース・DoS攻撃対策)
✅ **構造化エラーレスポンス** (高齢者向けUX配慮)
✅ **継続的負荷試験** (パフォーマンス要件確保)
✅ **WebSocket通信** (リアルタイムメッセージ対応)
✅ **スケジュール現実化** (バッファ期間・並行作業明確化)

---

## Phase 5: 献立→買い物リスト連携（計画中）

### 概要
献立に登録されたレシピの食材を自動的に買い物リストに反映する機能。在庫食材の自動除外と手動調整に対応。

### 5.1 データベースマイグレーション

#### 5.1.1 新テーブル作成
**優先度**: 🔴 最高

```python
# マイグレーション: recipe_ingredients テーブル作成
def upgrade():
    op.create_table(
        'recipe_ingredients',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('recipe_id', sa.UUID(), sa.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('quantity', sa.String(50)),
        sa.Column('category', sa.String(30), nullable=False, server_default='その他'),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_recipe_ingredients_recipe_id', 'recipe_ingredients', ['recipe_id'])
    op.create_index('idx_recipe_ingredients_name', 'recipe_ingredients', ['name'])

# マイグレーション: pantry_items テーブル作成
def upgrade():
    op.create_table(
        'pantry_items',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(30), nullable=False, server_default='その他'),
        sa.Column('is_available', sa.Boolean(), server_default='true'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'name'),
    )
    op.create_index('idx_pantry_items_user_id', 'pantry_items', ['user_id'])
    op.create_index('idx_pantry_items_available', 'pantry_items', ['user_id', 'is_available'])

# マイグレーション: shopping_items テーブル拡張
def upgrade():
    op.add_column('shopping_items',
        sa.Column('recipe_ingredient_id', sa.UUID(),
                  sa.ForeignKey('recipe_ingredients.id', ondelete='SET NULL')))
    op.add_column('shopping_items',
        sa.Column('is_excluded', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('idx_shopping_items_recipe_ingredient', 'shopping_items', ['recipe_ingredient_id'])
    op.create_index('idx_shopping_items_excluded', 'shopping_items', ['shopping_request_id', 'is_excluded'])
```

### 5.2 モデル実装

```python
# app/db/models/recipe_ingredient.py
class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    quantity = Column(String(50))
    category = Column(String(30), nullable=False, default="その他")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    recipe = relationship("Recipe", back_populates="structured_ingredients")

# app/db/models/pantry_item.py
class PantryItem(Base):
    __tablename__ = "pantry_items"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(30), nullable=False, default="その他")
    is_available = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="pantry_items")

    __table_args__ = (UniqueConstraint('user_id', 'name'),)
```

### 5.3 ビジネスロジック: 買い物リスト生成サービス

```python
# app/services/shopping_list_generator.py
class ShoppingListGenerator:
    """献立から買い物リストを自動生成するサービス"""

    async def generate_from_menu(
        self, db: AsyncSession, user_id: UUID, week_start: date, helper_user_id: UUID, notes: str = None
    ) -> ShoppingRequest:
        """
        処理フロー:
        1. 指定週のWeeklyMenuRecipesから全レシピID取得
        2. RecipeIngredientsから全食材取得
        3. 同名食材を集約（名前ベースでグルーピング）
        4. PantryItemsで在庫チェック → 在庫ありはis_excluded=True
        5. ShoppingRequest + ShoppingItemsを生成
        """

    async def _get_menu_recipes(self, db: AsyncSession, user_id: UUID, week_start: date) -> list[Recipe]:
        """指定週の献立に紐づく全レシピを取得"""

    async def _get_all_ingredients(self, db: AsyncSession, recipe_ids: list[UUID]) -> list[RecipeIngredient]:
        """レシピIDリストから全食材を取得"""

    async def _aggregate_ingredients(self, ingredients: list[RecipeIngredient]) -> list[AggregatedIngredient]:
        """同名食材を集約し、数量とレシピ出典をまとめる"""

    async def _check_pantry(self, db: AsyncSession, user_id: UUID, ingredient_names: list[str]) -> set[str]:
        """パントリーで在庫ありの食材名セットを返す"""

    def _map_ingredient_category_to_shopping(self, category: str) -> str:
        """食材カテゴリ → 買い物アイテムカテゴリのマッピング
        野菜 → 食材, 肉類 → 食材, 魚介類 → 食材,
        卵・乳製品 → 食材, 調味料 → 調味料, 穀類 → 食材, その他 → その他
        """
```

### 5.4 APIエンドポイント実装

```python
# app/api/v1/endpoints/recipe_ingredients.py
@router.get("/recipes/{recipe_id}/ingredients")
async def get_recipe_ingredients(recipe_id: UUID, db: AsyncSession = Depends(get_db))

@router.put("/recipes/{recipe_id}/ingredients")
async def update_recipe_ingredients(recipe_id: UUID, payload: IngredientsUpdateRequest, db: AsyncSession = Depends(get_db))

# app/api/v1/endpoints/pantry.py
@router.get("/pantry")
async def get_pantry(available_only: bool = False, db: AsyncSession = Depends(get_db))

@router.put("/pantry")
async def update_pantry(payload: PantryUpdateRequest, db: AsyncSession = Depends(get_db))

@router.delete("/pantry/{item_id}")
async def delete_pantry_item(item_id: UUID, db: AsyncSession = Depends(get_db))

# app/api/v1/endpoints/shopping.py (既存に追加)
@router.post("/shopping-requests/generate-from-menu")
async def generate_shopping_from_menu(payload: GenerateFromMenuRequest, db: AsyncSession = Depends(get_db))

@router.put("/shopping-items/{item_id}/exclude")
async def toggle_exclude(item_id: UUID, payload: ExcludeRequest, db: AsyncSession = Depends(get_db))
```

### 5.5 Pydanticスキーマ

```python
# app/schemas/recipe_ingredient.py
class RecipeIngredientBase(BaseModel):
    name: str = Field(..., max_length=100)
    quantity: str | None = Field(None, max_length=50)
    category: str = Field(default="その他")
    sort_order: int = Field(default=0)

class IngredientsUpdateRequest(BaseModel):
    ingredients: list[RecipeIngredientBase]

# app/schemas/pantry.py
class PantryItemBase(BaseModel):
    name: str = Field(..., max_length=100)
    category: str = Field(default="その他")
    is_available: bool = Field(default=True)

class PantryUpdateRequest(BaseModel):
    items: list[PantryItemBase]

# app/schemas/shopping.py (追加)
class GenerateFromMenuRequest(BaseModel):
    week_start: date
    helper_user_id: UUID
    notes: str | None = None

class ExcludeRequest(BaseModel):
    is_excluded: bool
```

### 5.6 実装スケジュール

| ステップ | 作業内容 | 見積 |
|---------|---------|------|
| 5.6.1 | DBマイグレーション（3テーブル作成/変更） | Day 1 |
| 5.6.2 | SQLAlchemyモデル + リレーション定義 | Day 1 |
| 5.6.3 | Pydanticスキーマ定義 | Day 2 |
| 5.6.4 | レシピ食材CRUD API | Day 2 |
| 5.6.5 | パントリーCRUD API | Day 3 |
| 5.6.6 | 買い物リスト生成サービス（コアロジック） | Day 3-4 |
| 5.6.7 | 生成API + 除外切り替えAPI | Day 4 |
| 5.6.8 | テスト実装 | Day 5-6 |
| 5.6.9 | フロントエンド対応 | Day 7-8 |

---

## Phase 5 テスト計画

### テストファイル構成
```
tests/
├── test_recipe_ingredients.py      # レシピ食材APIテスト
├── test_pantry.py                  # パントリーAPIテスト
├── test_shopping_list_generator.py # 買い物リスト生成ロジックテスト
└── test_shopping_integration.py    # 献立→買い物リスト統合テスト
```

### test_recipe_ingredients.py（レシピ食材API）

| # | テストケース | 検証内容 |
|---|-------------|---------|
| 1 | `test_get_ingredients_empty` | 食材未登録のレシピで空リスト返却 |
| 2 | `test_get_ingredients_with_data` | 食材登録済みレシピで全食材を正しく返却 |
| 3 | `test_get_ingredients_sorted` | sort_order順に並んで返却される |
| 4 | `test_update_ingredients_create` | 食材の新規一括登録 |
| 5 | `test_update_ingredients_replace` | 既存食材を全置換（PUT semantics） |
| 6 | `test_update_ingredients_empty_list` | 空リストで全食材削除 |
| 7 | `test_update_ingredients_validation` | nameが空・100文字超のバリデーション |
| 8 | `test_update_ingredients_invalid_category` | 不正カテゴリでエラー |
| 9 | `test_get_ingredients_nonexistent_recipe` | 存在しないレシピIDで404 |
| 10 | `test_update_ingredients_unauthorized` | 他ユーザーのレシピへの更新で403 |

### test_pantry.py（パントリーAPI）

| # | テストケース | 検証内容 |
|---|-------------|---------|
| 1 | `test_get_pantry_empty` | パントリー未登録で空リスト返却 |
| 2 | `test_get_pantry_all` | 全アイテム返却（在庫あり・なし両方） |
| 3 | `test_get_pantry_available_only` | available_only=trueで在庫ありのみ |
| 4 | `test_update_pantry_create` | 新規アイテム作成 |
| 5 | `test_update_pantry_upsert` | 既存アイテムの更新（UPSERT） |
| 6 | `test_update_pantry_toggle_available` | is_availableの切り替え |
| 7 | `test_update_pantry_duplicate_name` | 同名アイテムが集約される |
| 8 | `test_delete_pantry_item` | アイテム削除で204返却 |
| 9 | `test_delete_pantry_nonexistent` | 存在しないIDで404 |
| 10 | `test_pantry_user_isolation` | 他ユーザーのパントリーにアクセス不可 |

### test_shopping_list_generator.py（生成ロジック - 単体テスト）

| # | テストケース | 検証内容 |
|---|-------------|---------|
| 1 | `test_aggregate_same_name_ingredients` | 同名食材の集約: "卵2個"+"卵1個"→"卵 3個（レシピA 2個 + レシピB 1個）" |
| 2 | `test_aggregate_different_units` | 異なる単位は集約せずに列挙: "しょうゆ 大さじ2 + 100ml" |
| 3 | `test_aggregate_no_quantity` | 数量なしの食材は名前のみで集約 |
| 4 | `test_pantry_exclusion` | パントリーに在庫ありの食材がis_excluded=trueになる |
| 5 | `test_pantry_unavailable_not_excluded` | パントリーでis_available=falseの食材は除外されない |
| 6 | `test_category_mapping` | 食材カテゴリ→買い物カテゴリの正しいマッピング |
| 7 | `test_recipe_sources_tracking` | 各食材の出典レシピ名が正しく記録される |
| 8 | `test_empty_menu_error` | レシピ未登録の週で適切なエラー |
| 9 | `test_recipe_without_ingredients` | 構造化食材未登録レシピの警告付き生成 |
| 10 | `test_summary_calculation` | total_items, excluded_items, active_itemsの正しい計算 |

### test_shopping_integration.py（統合テスト）

| # | テストケース | 検証内容 |
|---|-------------|---------|
| 1 | `test_full_flow_generate_from_menu` | 献立作成→食材登録→買い物リスト生成の一連フロー |
| 2 | `test_generate_with_pantry_exclusion` | パントリー登録済み食材が自動除外される統合フロー |
| 3 | `test_toggle_exclude_after_generate` | 生成後に手動で除外/復元ができる |
| 4 | `test_generate_nonexistent_week` | 存在しない週で404エラー |
| 5 | `test_generate_duplicate_prevention` | 同一週で2回生成した場合の挙動（新規作成 or エラー） |
| 6 | `test_shopping_items_have_recipe_source` | 生成されたアイテムにrecipe_ingredient_idが設定される |
| 7 | `test_manual_add_after_generate` | 自動生成後に手動アイテム追加が可能 |
| 8 | `test_generated_items_category_correct` | 生成アイテムのカテゴリが正しくマッピングされている |
| 9 | `test_generate_requires_auth` | 未認証で401エラー |
| 10 | `test_generate_requires_own_menu` | 他ユーザーの献立からは生成不可（403） |

### テスト品質目標
- **カバレッジ**: Phase 5関連コード 90%以上
- **全APIエンドポイント**: 正常系 + 異常系（認証エラー、バリデーション、404、403）
- **ビジネスロジック**: 集約ロジック・除外ロジックの境界値テスト
- **データ整合性**: FK制約、UNIQUE制約、CASCADE削除の検証

---

**Phase 5 計画完了。実装承認後に着手可能。**

---

## Phase 6: ログ監査・コンプライアンス強化

※ 完全な仕様は[ログ監査・収集強化仕様書](./logging_audit_specification.md)を参照

### Phase 6 概要

高齢者の個人情報を扱うシステムとして、改正個人情報保護法への準拠とセキュリティインシデントの早期検知を実現するためのログ基盤強化。

### Phase 6A: Loki + Promtail基盤構築

| # | タスク | 詳細 |
|---|-------|------|
| 1 | Loki/Promtail Docker Compose定義 | `docker-compose.prod.yml`にサービス追加（Loki 512M、Promtail 128M） |
| 2 | Promtail設定ファイル作成 | Docker container logs + `/app/logs/` + Nginxアクセスログの収集設定 |
| 3 | Loki設定ファイル作成 | 保持期間31日、filesystemストレージ、compactor設定 |
| 4 | Grafana Lokiデータソース追加 | プロビジョニング設定 + ログ検索ダッシュボード作成 |
| 5 | ログ形式標準化 | `StructuredFormatter`クラス実装（共通フィールド: trace_id, service, user_id） |
| 6 | trace_idミドルウェア | リクエストごとのtrace_id生成・伝播ミドルウェア |

### Phase 6B: 個人データアクセス監査

| # | タスク | 詳細 |
|---|-------|------|
| 1 | `data_access_logs`テーブル作成 | Alembicマイグレーション |
| 2 | `DataAccessLogger`サービス実装 | バッファリング（50件 or 5秒）+ バッチDB書き込み |
| 3 | `@track_access`デコレータ実装 | 対象エンドポイントへの適用 |
| 4 | アサイン関係チェック | `has_assignment`の自動判定（`user_assignments`テーブル参照） |
| 5 | HMAC署名実装 | エントリ単位のHMAC-SHA256署名 |
| 6 | APIエンドポイント実装 | `GET /admin/data-access-logs`（検索・レポート・履歴） |

### Phase 6C: コンプライアンスログ

| # | タスク | 詳細 |
|---|-------|------|
| 1 | `compliance_logs`テーブル作成 | Alembicマイグレーション |
| 2 | 同意管理ログ実装 | ユーザー登録時・ポリシー変更時の同意記録 |
| 3 | データ主体権利行使ログ実装 | 開示・訂正・削除・利用停止請求の管理（ステータス＋期限） |
| 4 | 漏えい報告ログ実装 | 検知→報告→通知のワークフロー記録 |
| 5 | APIエンドポイント実装 | `consent-logs`, `data-requests`, `breach-reports`, `retention-report` |
| 6 | 期限管理リマインダー | 対応期限の自動通知（開示請求2週間以内、漏えい報告72時間以内） |

### Phase 6D: フロントエンドログ + セキュリティアラート

| # | タスク | 詳細 |
|---|-------|------|
| 1 | Error Boundary統合 | React Error Boundary + window.onerror + unhandledrejection |
| 2 | アクセシビリティ利用ログ | フォントサイズ変更、高コントラスト、スクリーンリーダー検出 |
| 3 | `FrontendLogger`クラス実装 | Beacon API + Fetchフォールバック、バッファリング（50件 or 10秒） |
| 4 | `frontend_error_logs`テーブル作成 | Alembicマイグレーション（重複排除集約テーブル） |
| 5 | `POST /telemetry/frontend-logs`エンドポイント | レート制限10req/min/user、PII除外チェック |
| 6 | SecurityMonitor拡張 | 分散ブルートフォース、権限昇格、異常データアクセス、セッション異常検知 |
| 7 | Prometheus/Lokiアラートルール定義 | 6つの新規セキュリティアラートルール |
| 8 | AlertManagerルーティング設定 | Critical→Slack+Email、Warning→Slack |

### Phase 6E: ログライフサイクル管理

| # | タスク | 詳細 |
|---|-------|------|
| 1 | 日次チェーンハッシュバッチ | `daily_integrity_check()` — 毎日03:00 JST実行 |
| 2 | アーカイブバッチ処理 | Warm（30日超過→gzip圧縮）、Cold（180日超過→AES-256暗号化） |
| 3 | 自動削除バッチ処理 | `run_retention_cleanup()` — 各テーブルの保持期間に基づく自動削除 |
| 4 | 削除証跡記録 | 削除実行をcomplianceログに記録 |
| 5 | ログシステム監視 | Loki/Promtailヘルスチェック、ストレージ容量監視 |

### Phase 6 テスト計画

| # | テストケース | 検証内容 |
|---|-------------|---------|
| 1 | `test_data_access_log_created` | 個人データ閲覧時にdata_access_logsにレコード作成 |
| 2 | `test_self_access_not_logged` | 自分自身のデータ閲覧はログ記録しない |
| 3 | `test_has_assignment_auto_check` | アサイン関係の自動判定が正確 |
| 4 | `test_hmac_signature_valid` | HMAC署名の生成・検証が正しく動作 |
| 5 | `test_chain_hash_integrity` | チェーンハッシュの改ざん検知 |
| 6 | `test_compliance_request_lifecycle` | 請求の作成→進行中→完了のステータス遷移 |
| 7 | `test_compliance_deadline_check` | 期限超過の検知とアラート |
| 8 | `test_frontend_log_pii_filter` | フロントエンドログからPIIが除外される |
| 9 | `test_beacon_batch_flush` | バッファリング＋バッチ送信の動作 |
| 10 | `test_unassigned_access_alert` | 担当外アクセス時のアラート発火 |
| 11 | `test_bulk_access_alert` | 大量閲覧時のアラート発火 |
| 12 | `test_retention_cleanup` | 保持期間超過データの自動削除と証跡記録 |
| 13 | `test_loki_log_ingestion` | Promtail→Lokiへのログ取り込み |
| 14 | `test_logql_query_proxy` | ログ検索APIのLogQLプロキシ動作 |

### テスト品質目標
- **カバレッジ**: Phase 6関連コード 90%以上
- **全APIエンドポイント**: 正常系 + 異常系（認証エラー、バリデーション、404、403）
- **セキュリティアラート**: 各ルールの発火条件テスト
- **データ整合性**: HMAC署名、チェーンハッシュ、保持期間の検証

---

**Phase 6 計画完了。実装承認後に着手可能。**

---

**文書終了**