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
- **データ保持期間**: 利用者データ3年、データアクセスログ3年、コンプライアンスログ3年、監査ログ6ヶ月、フロントエンドエラーログ90日

### 1.3 設計方針
- **正規化**: 第3正規形を基本とし、性能要件に応じて非正規化
- **ユーザー管理**: STI（シングルテーブル継承）でrole管理
- **外部キー**: 参照整合性を厳密に管理
- **インデックス**: 検索性能とデータ更新性能のバランス考慮

---

## 2. ERD（エンティティ関係図）

### 2.1 概要図
```
Users (利用者・ヘルパー・ケアマネージャー・システム管理者)
  ├─ 1:N ─ Recipes (レシピ)
  ├─ 1:N ─ WeeklyMenus (週間献立)
  ├─ 1:N ─ Tasks (作業)
  ├─ 1:N ─ Messages (送信者として)
  ├─ 1:N ─ Messages (受信者として)
  ├─ 1:N ─ ShoppingRequests (買い物依頼)
  ├─ 1:N ─ PantryItems (パントリー/在庫管理)
  ├─ 1:N ─ QRTokens (QRコードトークン)
  ├─ 1:N ─ AuditLogs (監査ログ・操作者として)
  ├─ 1:N ─ UserAssignments (アサイン・ヘルパーとして)
  ├─ 1:N ─ UserAssignments (アサイン・利用者として)
  ├─ 1:N ─ Notifications (通知)
  └─ 1:N ─ SystemSettings (設定・更新者として)

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

UserAssignments (ヘルパー⇔利用者アサイン)
  ├─ N:1 ─ Users (ヘルパー)
  ├─ N:1 ─ Users (利用者)
  └─ N:1 ─ Users (アサイン作成者)

AuditLogs (監査ログ)
  └─ N:1 ─ Users (操作者)

DataAccessLogs (個人データアクセスログ)
  ├─ N:1 ─ Users (アクセス者)
  └─ N:1 ─ Users (アクセス対象者)

ComplianceLogs (コンプライアンスログ)
  ├─ N:1 ─ Users (対象者)
  └─ N:1 ─ Users (対応者)

FrontendErrorLogs (フロントエンドエラーログ集約)
  └─ 独立テーブル（PII無し）

Notifications (通知)
  └─ N:1 ─ Users (通知先)

SystemSettings (システム設定)
  └─ N:1 ─ Users (更新者)

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
    role VARCHAR(20) NOT NULL CHECK (role IN ('senior', 'helper', 'care_manager', 'system_admin')),
    
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

### 3.13 AuditLogs（監査ログ）
**管理操作の監査証跡を記録**

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 操作者情報（非正規化：ユーザー削除後も保持）
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    user_role VARCHAR(20),
    
    -- 操作内容
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    
    -- 変更詳細
    changes JSONB,
    metadata JSONB,
    
    -- 記録日時
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_user_action_date ON audit_logs(user_id, action, created_at);
```

**主要アクション**: `user.create`, `user.update`, `user.deactivate`, `user.activate`, `user.role_change`, `user.password_reset`, `assignment.create`, `assignment.update`, `assignment.delete`, `setting.update`, `auth.login_success`, `auth.login_failure`

**設計ポイント**:
- `user_email`, `user_role` は非正規化。ユーザー削除後もログを保持するため
- `changes` はJSONB形式で `{"field": {"old": "旧値", "new": "新値"}}` を格納
- `metadata` にIPアドレス、ユーザーエージェント等を格納
- 保持期間: 6ヶ月（自動削除バッチ処理で対応）

### 3.14 UserAssignments（ヘルパー⇔利用者アサイン）
**ヘルパーと利用者の担当関係を管理**

```sql
CREATE TABLE user_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- アサイン関係
    helper_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    senior_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_by UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    
    -- ステータス
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'pending')),
    
    -- スケジュール情報
    visit_frequency VARCHAR(50),
    preferred_days INTEGER[],
    preferred_time_start TIME,
    preferred_time_end TIME,
    notes TEXT,
    
    -- 期間
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    
    -- システム情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_user_assignments_helper ON user_assignments(helper_id);
CREATE INDEX idx_user_assignments_senior ON user_assignments(senior_id);
CREATE INDEX idx_user_assignments_status ON user_assignments(status);
CREATE INDEX idx_user_assignments_assigned_by ON user_assignments(assigned_by);
CREATE INDEX idx_user_assignments_active ON user_assignments(helper_id, senior_id) WHERE status = 'active';
```

**設計ポイント**:
- `helper_id` は role=helper、`senior_id` は role=senior のユーザーを参照
- `assigned_by` はアサインを作成したsystem_admin/care_managerを記録
- `preferred_days` は 1（月曜）〜7（日曜）の配列
- 同一helper_id + senior_idのactiveアサインは部分一意インデックスで制約

### 3.15 SystemSettings（システム設定）
**システム設定パラメーターのKey-Value管理**

```sql
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 設定識別
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value JSONB NOT NULL,
    
    -- メタデータ
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    description TEXT,
    is_sensitive BOOLEAN DEFAULT false,
    
    -- 更新者
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_system_settings_key ON system_settings(setting_key);
CREATE INDEX idx_system_settings_category ON system_settings(category);
```

**設計ポイント**:
- `setting_value` はJSONB形式で柔軟な型の値を格納
- `is_sensitive` が true の場合、UI表示時にマスキング
- 初期値はマイグレーションシードで投入（APIからの新規追加・削除は不可）

### 3.16 Notifications（通知）
**ユーザーへの通知を管理**

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 通知先
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 通知内容
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    notification_type VARCHAR(30) NOT NULL
        CHECK (notification_type IN ('system', 'assignment', 'task', 'message', 'alert', 'admin')),
    priority VARCHAR(10) NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    
    -- 参照リンク
    reference_type VARCHAR(50),
    reference_id UUID,
    
    -- 既読状態
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP WITH TIME ZONE,
    
    -- システム情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read, created_at);
CREATE INDEX idx_notifications_type ON notifications(notification_type);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
```

**設計ポイント**:
- `reference_type` + `reference_id` で関連リソース（アサイン、タスク等）へのリンクを実現
- 未読通知の高速取得のために `(user_id, is_read, created_at)` の複合インデックス

### 3.17 DataAccessLogs（個人データアクセスログ）
**利用者の個人情報に対する全アクセスを記録**

※ 詳細仕様は[ログ監査・収集強化仕様書](./logging_audit_specification.md) セクション3を参照

```sql
CREATE TABLE data_access_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 誰がアクセスしたか（WHO）
    accessor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    accessor_email VARCHAR(255) NOT NULL,
    accessor_role VARCHAR(20) NOT NULL,
    
    -- 誰のデータか（WHOSE）
    target_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    target_user_name VARCHAR(255) NOT NULL,
    
    -- 何にアクセスしたか（WHAT）
    access_type VARCHAR(20) NOT NULL
        CHECK (access_type IN ('read', 'write', 'export', 'delete')),
    resource_type VARCHAR(50) NOT NULL,
    data_fields TEXT[],
    
    -- どのようにアクセスしたか（HOW）
    endpoint VARCHAR(200) NOT NULL,
    http_method VARCHAR(10) NOT NULL,
    ip_address INET NOT NULL,
    user_agent TEXT,
    
    -- アクセスコンテキスト
    has_assignment BOOLEAN NOT NULL DEFAULT false,
    access_purpose VARCHAR(100),
    
    -- ログ完全性
    log_hash VARCHAR(64),
    
    -- 記録日時
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_data_access_target ON data_access_logs(target_user_id, created_at);
CREATE INDEX idx_data_access_accessor ON data_access_logs(accessor_user_id, created_at);
CREATE INDEX idx_data_access_type ON data_access_logs(access_type, resource_type);
CREATE INDEX idx_data_access_created ON data_access_logs(created_at);
CREATE INDEX idx_data_access_unassigned ON data_access_logs(has_assignment, created_at)
    WHERE has_assignment = false;
```

**設計ポイント**:
- `audit_logs`とは別テーブル。ボリューム差（数千件/日 vs 数百件/日）、スキーマ差、保持期間差（3年 vs 6ヶ月）のため分離
- `accessor_email`, `accessor_role`, `target_user_name` は非正規化（`audit_logs`と同一パターン）
- `has_assignment = false` の部分インデックスにより、担当外アクセスの異常検知を高速化
- 保持期間: **3年**（改正個人情報保護法の記録保管義務）
- `log_hash` はHMAC-SHA256によるエントリ単位の完全性検証用

### 3.18 ComplianceLogs（コンプライアンスログ）
**改正個人情報保護法対応の記録管理**

※ 詳細仕様は[ログ監査・収集強化仕様書](./logging_audit_specification.md) セクション5を参照

```sql
CREATE TABLE compliance_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- イベント種別
    event_type VARCHAR(50) NOT NULL
        CHECK (event_type IN (
            'consent_given', 'consent_withdrawn',
            'disclosure_request', 'correction_request',
            'deletion_request', 'usage_stop_request',
            'breach_detected', 'breach_reported_ppc', 'breach_notified_user',
            'retention_expired', 'data_deleted',
            'third_party_provision'
        )),
    
    -- 対象者
    target_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    target_user_name VARCHAR(255),
    
    -- 操作者（管理者）
    handled_by UUID REFERENCES users(id) ON DELETE SET NULL,
    handler_email VARCHAR(255),
    
    -- 請求・イベント詳細
    request_details JSONB NOT NULL,
    
    -- ステータス管理
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'completed', 'rejected')),
    
    -- 期限管理
    deadline_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 対応結果
    response_details JSONB,
    
    -- ログ完全性
    log_hash VARCHAR(64),
    
    -- 記録日時
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_compliance_event_type ON compliance_logs(event_type);
CREATE INDEX idx_compliance_target ON compliance_logs(target_user_id, created_at);
CREATE INDEX idx_compliance_status ON compliance_logs(status) WHERE status != 'completed';
CREATE INDEX idx_compliance_deadline ON compliance_logs(deadline_at) WHERE status = 'pending';
CREATE INDEX idx_compliance_created ON compliance_logs(created_at);
```

**設計ポイント**:
- 保持期間: **3年**（法定保管義務）
- `status != 'completed'` の部分インデックスにより、未対応案件の検索を高速化
- `deadline_at` で対応期限を管理（開示請求は2週間以内、漏えい報告は72時間以内）
- `request_details`/`response_details` はJSONBで、イベント種別ごとに異なる詳細を柔軟に格納

### 3.19 FrontendErrorLogs（フロントエンドエラーログ集約）
**フロントエンドのエラーを重複排除して集約保存**

```sql
CREATE TABLE frontend_error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- エラー識別
    error_type VARCHAR(30) NOT NULL
        CHECK (error_type IN ('js_error', 'unhandled_rejection', 'render_error', 'network_error')),
    message TEXT NOT NULL,
    stack_hash VARCHAR(64) NOT NULL,      -- スタックトレースのSHA-256ハッシュ（重複排除用）
    component_name VARCHAR(100),
    
    -- 発生状況
    url VARCHAR(500) NOT NULL,
    user_agent_category VARCHAR(50),       -- ブラウザカテゴリ（Chrome, Safari, etc.）
    
    -- 集約情報
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 影響範囲
    affected_user_count INTEGER NOT NULL DEFAULT 1,
    
    -- 記録日時
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE UNIQUE INDEX idx_frontend_error_dedup ON frontend_error_logs(stack_hash, url);
CREATE INDEX idx_frontend_error_type ON frontend_error_logs(error_type, last_seen_at);
CREATE INDEX idx_frontend_error_count ON frontend_error_logs(occurrence_count DESC);
CREATE INDEX idx_frontend_error_created ON frontend_error_logs(created_at);
```

**設計ポイント**:
- `stack_hash` + `url` の一意インデックスで重複排除。同一エラーは `occurrence_count` を加算
- 個別のエラーイベントはLokiに保存し、このテーブルはトレンド分析用の集約データ
- 保持期間: **90日**
- PII（個人識別情報）は一切格納しない

---

## 7. まとめ

### 7.1 設計のポイント
- **STI方式**でユーザー管理を統一し、保守性を向上（senior/helper/care_manager/system_adminの4ロール）
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
9. **AuditLogs, UserAssignments** - 管理機能（ユーザー管理・アサイン管理）
10. **SystemSettings, Notifications** - システム設定・通知機能
11. **DataAccessLogs, ComplianceLogs, FrontendErrorLogs** - ログ監査・コンプライアンス強化（[ログ監査・収集強化仕様書](./logging_audit_specification.md)参照）

### 7.3 注意点
- マイグレーション実行前は必ずバックアップ
- インデックス追加時は本番環境の負荷を考慮
- 定期的な `VACUUM ANALYZE` でパフォーマンス維持

---

**文書終了**