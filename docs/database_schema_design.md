# データベーススキーマ設計書

## 文書管理情報
- **文書番号**: DB-DESIGN-001
- **版数**: 1.0
- **作成日**: 2025年7月13日
- **最終更新日**: 2025年7月13日
- **設計者**: Claude Code + Gemini技術検証

---

## 1. 設計概要

### 1.1 データベース仕様
- **DBMS**: PostgreSQL 15以上
- **ORM**: SQLAlchemy (非同期対応)
- **マイグレーション**: Alembic
- **文字エンコーディング**: UTF-8
- **タイムゾーン**: Asia/Tokyo

### 1.2 性能要件
- **同時接続数**: 1,000接続対応
- **レスポンス時間**: 一般的なクエリ < 100ms
- **データ保持期間**: 利用者データ3年、ログ6ヶ月

### 1.3 設計方針
- **正規化**: 第3正規形を基本とし、性能要件に応じて非正規化
- **ユーザー管理**: STI（シングルテーブル継承）でrole管理
- **外部キー**: 参照整合性を厳密に管理
- **インデックス**: 検索性能とデータ更新性能のバランス考慮

---

## 2. ERD（エンティティ関係図）

### 2.1 概要図
```
Users (利用者・ヘルパー・ケアマネージャー)
  ├─ 1:N ─ Recipes (レシピ)
  ├─ 1:N ─ WeeklyMenus (週間献立)
  ├─ 1:N ─ Tasks (作業)
  ├─ 1:N ─ Messages (送信者として)
  ├─ 1:N ─ Messages (受信者として)
  ├─ 1:N ─ ShoppingRequests (買い物依頼)
  ├─ 1:N ─ PantryItems (パントリー/在庫管理)
  └─ 1:N ─ QRTokens (QRコードトークン)

WeeklyMenus (週間献立)
  └─ N:M ─ Recipes (レシピ) [WeeklyMenuRecipes経由]

Recipes (レシピ)
  └─ 1:N ─ RecipeIngredients (レシピ食材)

ShoppingRequests (買い物依頼)
  └─ 1:N ─ ShoppingItems (買い物アイテム)
                └─ N:1 ─ RecipeIngredients (献立由来の食材追跡)

Tasks (作業)
  ├─ 1:N ─ TaskCompletions (作業完了記録)
  └─ N:1 ─ Users (ヘルパー)
  └─ N:1 ─ Users (利用者)

【献立→買い物リスト連携フロー】
WeeklyMenus → WeeklyMenuRecipes → Recipes → RecipeIngredients
  → (集約・パントリー除外) → ShoppingRequests + ShoppingItems
```

---

## 3. テーブル定義

### 3.1 Users（ユーザー）
**STI方式でユーザー種別を統合管理**

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('senior', 'helper', 'care_manager')),
    
    -- 基本情報
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    
    -- 利用者固有情報
    emergency_contact VARCHAR(100),
    medical_notes TEXT,
    care_level INTEGER CHECK (care_level BETWEEN 1 AND 5),
    
    -- ヘルパー固有情報
    certification_number VARCHAR(50),
    specialization TEXT[],
    
    -- システム情報
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_users_role_active ON users(role, is_active);
```

### 3.2 Recipes（レシピ）

```sql
CREATE TABLE recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- レシピ基本情報
    name VARCHAR(100) NOT NULL,
    category VARCHAR(20) NOT NULL CHECK (category IN ('和食', '洋食', '中華', 'その他')),
    type VARCHAR(20) NOT NULL CHECK (type IN ('主菜', '副菜', '汁物', 'ご飯', 'その他')),
    difficulty VARCHAR(10) NOT NULL CHECK (difficulty IN ('簡単', '普通', '難しい')),
    cooking_time INTEGER NOT NULL CHECK (cooking_time > 0),
    
    -- レシピ詳細
    ingredients TEXT,
    instructions TEXT,
    memo TEXT,
    recipe_url TEXT,
    
    -- システム情報
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_recipes_user_id ON recipes(user_id);
CREATE INDEX idx_recipes_category ON recipes(category);
CREATE INDEX idx_recipes_type ON recipes(type);
CREATE INDEX idx_recipes_category_type ON recipes(category, type);
CREATE INDEX idx_recipes_difficulty ON recipes(difficulty);
CREATE INDEX idx_recipes_name_gin ON recipes USING gin(to_tsvector('japanese', name));
```

### 3.3 WeeklyMenus（週間献立）

```sql
CREATE TABLE weekly_menus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 献立期間
    week_start DATE NOT NULL,
    
    -- システム情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, week_start)
);

-- インデックス
CREATE INDEX idx_weekly_menus_user_id ON weekly_menus(user_id);
CREATE INDEX idx_weekly_menus_week_start ON weekly_menus(week_start);
CREATE INDEX idx_weekly_menus_user_week ON weekly_menus(user_id, week_start);
```

### 3.4 WeeklyMenuRecipes（週間献立-レシピ中間テーブル）

```sql
CREATE TABLE weekly_menu_recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    weekly_menu_id UUID NOT NULL REFERENCES weekly_menus(id) ON DELETE CASCADE,
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    
    -- 献立詳細
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7), -- 1=月曜, 7=日曜
    meal_type VARCHAR(10) NOT NULL CHECK (meal_type IN ('breakfast', 'dinner')),
    recipe_type VARCHAR(20) NOT NULL CHECK (recipe_type IN ('主菜', '副菜', '汁物', 'ご飯', 'その他')),
    
    -- システム情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(weekly_menu_id, day_of_week, meal_type, recipe_type)
);

-- インデックス
CREATE INDEX idx_weekly_menu_recipes_menu_id ON weekly_menu_recipes(weekly_menu_id);
CREATE INDEX idx_weekly_menu_recipes_recipe_id ON weekly_menu_recipes(recipe_id);
CREATE INDEX idx_weekly_menu_recipes_day_meal ON weekly_menu_recipes(day_of_week, meal_type);
```

### 3.5 Tasks（作業）

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    senior_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    helper_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- 作業情報
    title VARCHAR(100) NOT NULL,
    description TEXT,
    task_type VARCHAR(20) NOT NULL CHECK (task_type IN ('cooking', 'cleaning', 'shopping', 'special')),
    priority VARCHAR(10) NOT NULL DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
    estimated_minutes INTEGER,
    
    -- スケジュール
    scheduled_date DATE NOT NULL,
    scheduled_start_time TIME,
    scheduled_end_time TIME,
    
    -- ステータス
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    
    -- システム情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_tasks_senior_user_id ON tasks(senior_user_id);
CREATE INDEX idx_tasks_helper_user_id ON tasks(helper_user_id);
CREATE INDEX idx_tasks_scheduled_date ON tasks(scheduled_date);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_helper_date_status ON tasks(helper_user_id, scheduled_date, status);
```

### 3.6 TaskCompletions（作業完了記録）

```sql
CREATE TABLE task_completions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    helper_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 完了情報
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    actual_minutes INTEGER,
    notes TEXT,
    
    -- 次回申し送り
    next_notes TEXT,
    
    -- システム情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_task_completions_task_id ON task_completions(task_id);
CREATE INDEX idx_task_completions_helper_id ON task_completions(helper_user_id);
CREATE INDEX idx_task_completions_completed_at ON task_completions(completed_at);
```

### 3.7 Messages（メッセージ）

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- メッセージ内容
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'normal' CHECK (message_type IN ('normal', 'urgent', 'system')),
    
    -- 既読管理
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP WITH TIME ZONE,
    
    -- システム情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_messages_receiver_id ON messages(receiver_id);
CREATE INDEX idx_messages_conversation ON messages(sender_id, receiver_id, created_at);
CREATE INDEX idx_messages_unread ON messages(receiver_id, is_read, created_at);
```

### 3.8 ShoppingRequests（買い物依頼）

```sql
CREATE TABLE shopping_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    senior_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    helper_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 依頼情報
    request_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'completed', 'cancelled')),
    notes TEXT,
    
    -- システム情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_shopping_requests_senior_id ON shopping_requests(senior_user_id);
CREATE INDEX idx_shopping_requests_helper_id ON shopping_requests(helper_user_id);
CREATE INDEX idx_shopping_requests_status ON shopping_requests(status);
CREATE INDEX idx_shopping_requests_date ON shopping_requests(request_date);
```

### 3.9 ShoppingItems（買い物アイテム）

```sql
CREATE TABLE shopping_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shopping_request_id UUID NOT NULL REFERENCES shopping_requests(id) ON DELETE CASCADE,

    -- アイテム情報
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(30) NOT NULL DEFAULT 'その他' CHECK (category IN ('食材', '調味料', '日用品', '医薬品', 'その他')),
    quantity VARCHAR(50),
    memo TEXT,

    -- 献立連携（献立から自動生成された場合に設定）
    recipe_ingredient_id UUID REFERENCES recipe_ingredients(id) ON DELETE SET NULL,
    is_excluded BOOLEAN NOT NULL DEFAULT false,  -- 除外フラグ（在庫あり等の理由で除外）

    -- ステータス
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'purchased', 'unavailable')),

    -- システム情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_shopping_items_request_id ON shopping_items(shopping_request_id);
CREATE INDEX idx_shopping_items_category ON shopping_items(category);
CREATE INDEX idx_shopping_items_status ON shopping_items(status);
CREATE INDEX idx_shopping_items_recipe_ingredient ON shopping_items(recipe_ingredient_id);
CREATE INDEX idx_shopping_items_excluded ON shopping_items(shopping_request_id, is_excluded);
```

### 3.10 RecipeIngredients（レシピ食材）

**献立から買い物リストを自動生成するための構造化された食材データ**

```sql
CREATE TABLE recipe_ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,

    -- 食材情報
    name VARCHAR(100) NOT NULL,           -- 食材名（例: 鶏もも肉）
    quantity VARCHAR(50),                  -- 数量（例: 300g, 大さじ2）
    category VARCHAR(30) NOT NULL DEFAULT 'その他'
        CHECK (category IN ('野菜', '肉類', '魚介類', '卵・乳製品', '調味料', '穀類', 'その他')),
    sort_order INTEGER DEFAULT 0,

    -- システム情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);
CREATE INDEX idx_recipe_ingredients_name ON recipe_ingredients(name);
CREATE INDEX idx_recipe_ingredients_category ON recipe_ingredients(category);
```

### 3.11 PantryItems（パントリー/在庫管理）

**利用者が手元にある食材を管理し、買い物リスト生成時に自動除外するためのテーブル**

```sql
CREATE TABLE pantry_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 食材情報
    name VARCHAR(100) NOT NULL,           -- 食材名
    category VARCHAR(30) NOT NULL DEFAULT 'その他'
        CHECK (category IN ('野菜', '肉類', '魚介類', '卵・乳製品', '調味料', '穀類', 'その他')),
    is_available BOOLEAN DEFAULT true,    -- 在庫あり/なし

    -- システム情報
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, name)
);

-- インデックス
CREATE INDEX idx_pantry_items_user_id ON pantry_items(user_id);
CREATE INDEX idx_pantry_items_available ON pantry_items(user_id, is_available);
```

### 3.12 QRTokens（QRコードトークン）

```sql
CREATE TABLE qr_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- トークン情報
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    purpose VARCHAR(20) NOT NULL DEFAULT 'login' CHECK (purpose IN ('login', 'task_access', 'emergency')),
    
    -- 有効期限・使用制限
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_used BOOLEAN DEFAULT false,
    used_at TIMESTAMP WITH TIME ZONE,
    max_uses INTEGER DEFAULT 1,
    use_count INTEGER DEFAULT 0,
    
    -- アクセス制限
    allowed_ip_addresses INET[],
    
    -- システム情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_qr_tokens_token_hash ON qr_tokens(token_hash);
CREATE INDEX idx_qr_tokens_user_id ON qr_tokens(user_id);
CREATE INDEX idx_qr_tokens_expires_at ON qr_tokens(expires_at);
CREATE INDEX idx_qr_tokens_purpose ON qr_tokens(purpose);
```

---

## 4. パフォーマンス最適化

### 4.1 接続プーリング設定
**1,000同時接続対応のための必須設定**

```python
# database.py（SQLAlchemy設定例）
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/helper_db"

# 接続プール設定
engine = create_async_engine(
    DATABASE_URL,
    # プール設定（重要）
    pool_size=20,           # 基本接続数
    max_overflow=50,        # 追加接続数
    pool_timeout=30,        # 接続取得タイムアウト
    pool_recycle=3600,      # 接続再利用時間
    pool_pre_ping=True,     # 接続健全性チェック
    
    # パフォーマンス設定
    echo=False,             # SQLログ（本番ではFalse）
    future=True
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
```

### 4.2 インデックス戦略

#### 4.2.1 複合インデックス
頻繁に組み合わせ検索されるカラムに複合インデックスを設定：

```sql
-- ヘルパーの当日作業取得
CREATE INDEX idx_tasks_helper_date_status ON tasks(helper_user_id, scheduled_date, status);

-- 利用者の週間献立取得
CREATE INDEX idx_weekly_menus_user_week ON weekly_menus(user_id, week_start);

-- 未読メッセージ取得
CREATE INDEX idx_messages_unread ON messages(receiver_id, is_read, created_at);

-- レシピカテゴリ・タイプ検索
CREATE INDEX idx_recipes_category_type ON recipes(category, type);
```

#### 4.2.2 全文検索インデックス
レシピ名検索のためのGINインデックス：

```sql
-- PostgreSQL日本語全文検索
CREATE INDEX idx_recipes_name_gin ON recipes USING gin(to_tsvector('japanese', name));

-- 使用例
SELECT * FROM recipes 
WHERE to_tsvector('japanese', name) @@ plainto_tsquery('japanese', '鶏肉 照り焼き');
```

### 4.3 クエリ最適化指針

#### 4.3.1 N+1問題対策
SQLAlchemyでのeager loading活用：

```python
# N+1問題を避ける書き方例
from sqlalchemy.orm import selectinload

# 週間献立とレシピを一度に取得
weekly_menu = await session.execute(
    select(WeeklyMenu)
    .options(selectinload(WeeklyMenu.recipes))
    .where(WeeklyMenu.user_id == user_id, WeeklyMenu.week_start == week_start)
)
```

#### 4.3.2 重いクエリの特定
定期的な性能監視：

```sql
-- スロークエリ監視（PostgreSQL設定）
ALTER SYSTEM SET log_min_duration_statement = 1000; -- 1秒以上のクエリをログ
SELECT pg_reload_conf();

-- 実行計画確認
EXPLAIN ANALYZE SELECT ...;
```

---

## 5. データベース運用

### 5.1 バックアップ戦略

```bash
# 日次自動バックアップ（cron設定例）
0 2 * * * pg_dump -h localhost -U helper_user helper_db | gzip > /backup/helper_db_$(date +\%Y\%m\%d).sql.gz

# 保持期間設定（30日間）
find /backup -name "helper_db_*.sql.gz" -mtime +30 -delete
```

### 5.2 マイグレーション管理

```python
# Alembicマイグレーション例
"""add user role column

Revision ID: 001
Revises: 
Create Date: 2025-07-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='senior'))
    op.create_check_constraint('ck_users_role', 'users', "role IN ('senior', 'helper', 'care_manager')")

def downgrade():
    op.drop_constraint('ck_users_role', 'users')
    op.drop_column('users', 'role')
```

### 5.3 監視・メンテナンス

```sql
-- 接続数監視
SELECT count(*) FROM pg_stat_activity;

-- テーブルサイズ監視
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- インデックス使用状況
SELECT schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
ORDER BY idx_scan;
```

---

## 6. セキュリティ考慮事項

### 6.1 アクセス制御

```sql
-- ロールベースアクセス制御
CREATE ROLE helper_app_user LOGIN PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE helper_db TO helper_app_user;
GRANT USAGE ON SCHEMA public TO helper_app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO helper_app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO helper_app_user;
```

### 6.2 データ保護

```sql
-- 機密情報の部分マスキング（必要に応じて）
CREATE OR REPLACE FUNCTION mask_phone_number(phone TEXT) 
RETURNS TEXT AS $$
BEGIN
    RETURN CASE 
        WHEN phone IS NULL THEN NULL
        WHEN LENGTH(phone) >= 10 THEN 
            SUBSTRING(phone FROM 1 FOR 3) || '****' || SUBSTRING(phone FROM LENGTH(phone)-3)
        ELSE phone
    END;
END;
$$ LANGUAGE plpgsql;
```

---

## 7. まとめ

### 7.1 設計のポイント
- **STI方式**でユーザー管理を統一し、保守性を向上
- **中間テーブル**で複雑な献立組み合わせを柔軟に表現
- **適切なインデックス**で1,000同時接続に対応
- **UUID主キー**でセキュリティと分散処理に配慮

### 7.2 実装順序推奨
1. **Users, Recipes** - 基本エンティティ
2. **WeeklyMenus, WeeklyMenuRecipes** - 献立機能
3. **RecipeIngredients** - レシピ食材（構造化データ）
4. **Tasks, TaskCompletions** - 作業管理
5. **Messages** - コミュニケーション
6. **ShoppingRequests, ShoppingItems** - 買い物機能
7. **PantryItems** - パントリー/在庫管理
8. **QRTokens** - QRコード機能

### 7.3 注意点
- マイグレーション実行前は必ずバックアップ
- インデックス追加時は本番環境の負荷を考慮
- 定期的な `VACUUM ANALYZE` でパフォーマンス維持

---

**文書終了**