# API詳細仕様書

## 文書管理情報
- **文書番号**: API-SPEC-001
- **版数**: 1.1
- **作成日**: 2025年7月13日
- **最終更新日**: 2026年4月22日
- **設計者**: Claude Code + Gemini技術検証

### 改版履歴
| 版数 | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2025-07-13 | 初版 |
| 1.1 | 2026-04-22 | §16 テーマシステムAPI を追加（公開既定取得・一覧・詳細・ユーザー設定・管理者CRUD・既定変更） |

---

## 1. API概要

### 1.1 基本仕様
- **プロトコル**: HTTP/HTTPS (REST API)
- **データ形式**: JSON
- **文字エンコーディング**: UTF-8
- **ベースURL**: `https://api.helper-system.com/api/v1`
- **認証方式**: JWT (JSON Web Token)
- **バージョニング**: URLパスでのバージョン管理 (`/api/v1/`)

### 1.2 API設計原則
- RESTful設計に従ったリソースベースAPI
- HTTPステータスコードの適切な使用
- 統一されたエラーレスポンス形式
- OpenAPI 3.0仕様準拠
- 冪等性を考慮した設計

### 1.3 レート制���
- **認証済みユーザー**: 1,000リクエスト/時間
- **���認証**: 100リクエスト/時間
- **QRコード生成**: 10リクエスト/分
- **管理API（/admin/）**: 500リクエ��ト/時間
- **CSVインポート**: 5リクエスト/時間
- **一斉通知**: 10リクエスト/時間

---

## 2. 認証・認可

### 2.1 認証フロー

#### 2.1.1 ログイン
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**成功レスポンス (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "full_name": "田中太郎",
    "role": "senior"
  }
}
```

#### 2.1.2 トークンリフレッシュ
```http
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>
```

**成功レスポンス (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 1800
}
```

#### 2.1.3 ログアウト
```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

**成功レスポンス (200 OK)**:
```json
{
  "message": "Successfully logged out"
}
```

### 2.2 QRコード認証

#### 2.2.1 QRコード生成
```http
GET /api/v1/qr/generate/{user_id}
Authorization: Bearer <access_token>
```

**成功レスポンス (200 OK)**:
```json
{
  "qr_url": "https://api.helper-system.com/qr/abc123def456",
  "qr_code_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "expires_at": "2025-07-14T12:00:00Z",
  "purpose": "login"
}
```

#### 2.2.2 QRコード検証
```http
POST /api/v1/qr/validate
Content-Type: application/json

{
  "token": "abc123def456"
}
```

**成功レスポンス (200 OK)**:
```json
{
  "valid": true,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "purpose": "login",
  "redirect_url": "/dashboard",
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## 3. ユーザー管理API

### 3.1 ユーザー情報取得
```http
GET /api/v1/users/me
Authorization: Bearer <access_token>
```

**成功レスポンス (200 OK)**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "full_name": "田中太郎",
  "role": "senior",
  "phone": "090-1234-5678",
  "address": "東京都渋谷区...",
  "emergency_contact": "田中花子 (娘) 080-9876-5432",
  "medical_notes": "高血圧の薬を服用中",
  "care_level": 2,
  "is_active": true,
  "last_login_at": "2025-07-13T10:30:00Z",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### 3.2 ユーザー情報更新
```http
PUT /api/v1/users/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "full_name": "田中太郎",
  "phone": "090-1234-5678",
  "address": "東京都渋谷区新宿1-1-1",
  "emergency_contact": "田中花子 (娘) 080-9876-5432"
}
```

---

## 4. レシピ管理API

### 4.1 レシピ一覧取得
```http
GET /api/v1/recipes?category=和食&type=主菜&page=1&limit=20&search=鶏肉
Authorization: Bearer <access_token>
```

**クエリパラメーター**:
- `category`: 料理カテゴリ（和食, 洋食, 中華, その他）
- `type`: 料理タイプ（主菜, 副菜, 汁物, ご飯, その他）
- `difficulty`: 難易度（簡単, 普通, 難しい）
- `search`: 料理名での部分一致検索
- `page`: ページ番号（デフォルト: 1）
- `limit`: 1ページあたりの件数（デフォルト: 20, 最大: 100）

**成功レスポンス (200 OK)**:
```json
{
  "recipes": [
    {
      "id": "456e7890-e89b-12d3-a456-426614174001",
      "name": "鶏肉の照り焼き",
      "category": "和食",
      "type": "主菜",
      "difficulty": "普通",
      "cooking_time": 30,
      "ingredients": "鶏もも肉 300g, しょうゆ 大さじ2...",
      "instructions": "1. 鶏肉を一口大に切る...",
      "memo": "砂糖を少し多めに入れると美味しい",
      "recipe_url": "https://cookpad.com/recipe/123456",
      "created_at": "2025-07-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

### 4.2 レシピ詳細取得
```http
GET /api/v1/recipes/{recipe_id}
Authorization: Bearer <access_token>
```

### 4.3 レシピ作成
```http
POST /api/v1/recipes
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "鶏肉の照り焼き",
  "category": "和食",
  "type": "主菜",
  "difficulty": "普通",
  "cooking_time": 30,
  "ingredients": "鶏もも肉 300g, しょうゆ 大さじ2, みりん 大さじ2, 砂糖 大さじ1",
  "instructions": "1. 鶏肉を一口大に切る\n2. フライパンで焼く\n3. 調味料を加えて照りが出るまで煮詰める",
  "memo": "砂糖を少し多めに入れると美味しい",
  "recipe_url": "https://cookpad.com/recipe/123456"
}
```

**成功レスポンス (201 Created)**:
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "name": "鶏肉の照り焼き",
  "category": "和食",
  "type": "主菜",
  "difficulty": "普通",
  "cooking_time": 30,
  "ingredients": "鶏もも肉 300g, しょうゆ 大さじ2...",
  "instructions": "1. 鶏肉を一口大に切る...",
  "memo": "砂糖を少し多めに入れると美味しい",
  "recipe_url": "https://cookpad.com/recipe/123456",
  "created_at": "2025-07-13T12:00:00Z"
}
```

### 4.4 レシピ更新・削除
```http
PUT /api/v1/recipes/{recipe_id}
DELETE /api/v1/recipes/{recipe_id}
```

---

## 5. 献立管理API

### 5.1 週間献立取得
```http
GET /api/v1/menus/week?date=2025-07-13
Authorization: Bearer <access_token>
```

**成功レスポンス (200 OK)**:
```json
{
  "week_start": "2025-07-13",
  "menus": {
    "monday": {
      "breakfast": [
        {
          "recipe_type": "主菜",
          "recipe": {
            "id": "456e7890-e89b-12d3-a456-426614174001",
            "name": "目玉焼き",
            "cooking_time": 5
          }
        },
        {
          "recipe_type": "ご飯",
          "recipe": {
            "id": "456e7890-e89b-12d3-a456-426614174002",
            "name": "白ご飯",
            "cooking_time": 30
          }
        }
      ],
      "dinner": [
        {
          "recipe_type": "主菜",
          "recipe": {
            "id": "456e7890-e89b-12d3-a456-426614174003",
            "name": "鶏肉の照り焼き",
            "cooking_time": 30
          }
        },
        {
          "recipe_type": "副菜",
          "recipe": {
            "id": "456e7890-e89b-12d3-a456-426614174004",
            "name": "きんぴらごぼう",
            "cooking_time": 15
          }
        },
        {
          "recipe_type": "汁物",
          "recipe": {
            "id": "456e7890-e89b-12d3-a456-426614174005",
            "name": "わかめの味噌汁",
            "cooking_time": 10
          }
        }
      ]
    },
    "tuesday": { /* 同様の構造 */ }
    // ... 他の曜日
  },
  "summary": {
    "total_recipes": 14,
    "avg_cooking_time": 25,
    "category_distribution": {
      "和食": 10,
      "洋食": 3,
      "中華": 1
    }
  }
}
```

### 5.2 週間献立更新
```http
PUT /api/v1/menus/week
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "week_start": "2025-07-13",
  "menus": {
    "monday": {
      "breakfast": [
        {
          "recipe_id": "456e7890-e89b-12d3-a456-426614174001",
          "recipe_type": "主菜"
        }
      ],
      "dinner": [
        {
          "recipe_id": "456e7890-e89b-12d3-a456-426614174003",
          "recipe_type": "主菜"
        },
        {
          "recipe_id": "456e7890-e89b-12d3-a456-426614174004",
          "recipe_type": "副菜"
        }
      ]
    }
    // ... 他の曜日
  }
}
```

### 5.3 週間献立コピー
```http
POST /api/v1/menus/week/copy
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "source_week": "2025-07-06",
  "target_week": "2025-07-13"
}
```

### 5.4 週間献立クリア
```http
POST /api/v1/menus/week/clear
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "week_start": "2025-07-13"
}
```

---

## 6. 作業管理API（ヘルパー向け）

### 6.1 本日の作業取得
```http
GET /api/v1/tasks/today?user_id={senior_user_id}&date=2025-07-13
Authorization: Bearer <access_token>
```

**成功レスポンス (200 OK)**:
```json
{
  "date": "2025-07-13",
  "user_info": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "full_name": "田中太郎",
    "address": "東京都渋谷区新宿1-1-1",
    "phone": "090-1234-5678",
    "emergency_contact": "田中花子 (娘) 080-9876-5432",
    "medical_notes": "高血圧の薬を服用中",
    "care_level": 2
  },
  "schedule": {
    "start_time": "09:00",
    "end_time": "12:00",
    "total_minutes": 180
  },
  "meals": {
    "breakfast": [
      {
        "recipe": {
          "id": "456e7890-e89b-12d3-a456-426614174001",
          "name": "目玉焼き",
          "cooking_time": 5,
          "ingredients": "卵 2個, 塩 少々",
          "instructions": "フライパンで焼く"
        },
        "recipe_type": "主菜",
        "completed": false
      }
    ],
    "dinner": [
      {
        "recipe": {
          "id": "456e7890-e89b-12d3-a456-426614174003",
          "name": "鶏肉の照り焼き",
          "cooking_time": 30,
          "ingredients": "鶏もも肉 300g, しょうゆ 大さじ2...",
          "instructions": "1. 鶏肉を一口大に切る..."
        },
        "recipe_type": "主菜",
        "completed": false
      }
    ]
  },
  "regular_tasks": [
    {
      "id": "789e0123-e89b-12d3-a456-426614174006",
      "title": "洗濯",
      "description": "洗濯機を回して干す",
      "task_type": "cleaning",
      "estimated_minutes": 30,
      "priority": "medium",
      "completed": false
    },
    {
      "id": "789e0123-e89b-12d3-a456-426614174007", 
      "title": "掃除",
      "description": "リビングと台所の掃除",
      "task_type": "cleaning",
      "estimated_minutes": 45,
      "priority": "medium",
      "completed": false
    }
  ],
  "special_requests": [
    {
      "id": "789e0123-e89b-12d3-a456-426614174008",
      "title": "病院の予約確認",
      "description": "来週火曜日の整形外科の予約時間を確認",
      "task_type": "special",
      "priority": "high",
      "estimated_minutes": 15,
      "completed": false
    }
  ],
  "notes": "最近足腰が弱くなってきているので、転倒に注意してください。"
}
```

### 6.2 作業完了報告
```http
PUT /api/v1/tasks/{task_id}/complete
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "completed": true,
  "actual_minutes": 35,
  "notes": "洗濯は完了しました。天気が良かったので外に干しました。",
  "next_notes": "洗濯物は夕方に取り込む予定です。"
}
```

### 6.3 日報作成
```http
POST /api/v1/reports/daily
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "senior_user_id": "123e4567-e89b-12d3-a456-426614174000",
  "date": "2025-07-13",
  "completed_tasks": [
    "789e0123-e89b-12d3-a456-426614174006",
    "789e0123-e89b-12d3-a456-426614174007"
  ],
  "cooking_summary": {
    "breakfast_completed": true,
    "dinner_completed": true,
    "cooking_notes": "鶏肉の照り焼きは好評でした。"
  },
  "general_notes": "体調良好。散歩に行きたいとのことです。",
  "next_notes": "明日は天気が良ければ散歩に同行予定。",
  "total_time_minutes": 175
}
```

---

## 7. メッセージAPI

### 7.1 メッセージ一覧取得
```http
GET /api/v1/messages?partner_id={user_id}&limit=50&offset=0
Authorization: Bearer <access_token>
```

**成功レスポンス (200 OK)**:
```json
{
  "messages": [
    {
      "id": "abc12345-e89b-12d3-a456-426614174009",
      "sender_id": "123e4567-e89b-12d3-a456-426614174000",
      "receiver_id": "123e4567-e89b-12d3-a456-426614174001",
      "content": "明日の朝食の卵は半熟でお願いします。",
      "message_type": "normal",
      "is_read": true,
      "read_at": "2025-07-13T10:35:00Z",
      "created_at": "2025-07-13T10:30:00Z"
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 127,
    "has_more": true
  },
  "partner_info": {
    "id": "123e4567-e89b-12d3-a456-426614174001",
    "full_name": "佐藤花子",
    "role": "helper"
  }
}
```

### 7.2 メッセージ送信
```http
POST /api/v1/messages
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "receiver_id": "123e4567-e89b-12d3-a456-426614174001",
  "content": "明日の朝食の卵は半熟でお願いします。",
  "message_type": "normal"
}
```

### 7.3 メッセージ既読
```http
PUT /api/v1/messages/{message_id}/read
Authorization: Bearer <access_token>
```

---

## 8. 買い物管理API

### 8.1 買い物リスト取得
```http
GET /api/v1/shopping-list?status=pending
Authorization: Bearer <access_token>
```

**成功レスポンス (200 OK)**:
```json
{
  "requests": [
    {
      "id": "def45678-e89b-12d3-a456-426614174010",
      "request_date": "2025-07-13",
      "status": "pending",
      "notes": "なるべく新鮮なものをお願いします",
      "items": [
        {
          "id": "ghi78901-e89b-12d3-a456-426614174011",
          "item_name": "鶏もも肉",
          "category": "食材",
          "quantity": "300g",
          "memo": "国産のもの",
          "status": "pending"
        },
        {
          "id": "ghi78901-e89b-12d3-a456-426614174012",
          "item_name": "卵",
          "category": "食材", 
          "quantity": "1パック（10個入り）",
          "memo": "",
          "status": "pending"
        }
      ],
      "created_at": "2025-07-13T08:00:00Z"
    }
  ]
}
```

### 8.2 買い物依頼作成
```http
POST /api/v1/shopping-requests
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "senior_user_id": "123e4567-e89b-12d3-a456-426614174000",
  "request_date": "2025-07-14",
  "notes": "なるべく新鮮なものをお願いします",
  "items": [
    {
      "item_name": "鶏もも肉",
      "category": "食材",
      "quantity": "300g",
      "memo": "国産のもの"
    },
    {
      "item_name": "卵",
      "category": "食材",
      "quantity": "1パック（10個入り）",
      "memo": ""
    }
  ]
}
```

### 8.3 買い物アイテム更新
```http
PUT /api/v1/shopping-items/{item_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "purchased",
  "memo": "○○スーパーで購入。特売で安く買えました。"
}
```

### 8.4 献立から買い物リスト自動生成
```http
POST /api/v1/shopping-requests/generate-from-menu
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "week_start": "2025-07-13",
  "notes": "なるべく新鮮なものをお願いします"
}
```

**処理フロー**:
1. 指定週の `WeeklyMenuRecipes` から全レシピを取得
2. 各レシピの `RecipeIngredients` から食材を取得
3. 同名食材を集約（数量を合算表示）
4. `PantryItems` で在庫チェック → 在庫ありの食材は `is_excluded=true` で生成
5. `ShoppingRequest` + `ShoppingItems` を作成して返却（`helper_user_id` はログインユーザーのIDを自動設定）

**成功レスポンス (201 Created)**:
```json
{
  "id": "def45678-e89b-12d3-a456-426614174020",
  "request_date": "2025-07-13",
  "status": "pending",
  "notes": "なるべく新鮮なものをお願いします",
  "source_menu_week": "2025-07-13",
  "items": [
    {
      "id": "ghi78901-e89b-12d3-a456-426614174021",
      "item_name": "鶏もも肉",
      "category": "食材",
      "quantity": "600g（照り焼き300g + 親子丼300g）",
      "memo": "",
      "status": "pending",
      "is_excluded": false,
      "recipe_sources": ["鶏肉の照り焼き", "親子丼"]
    },
    {
      "id": "ghi78901-e89b-12d3-a456-426614174022",
      "item_name": "卵",
      "category": "食材",
      "quantity": "5個（目玉焼き2個 + 卵焼き2個 + 親子丼1個）",
      "memo": "",
      "status": "pending",
      "is_excluded": false,
      "recipe_sources": ["目玉焼き", "卵焼き", "親子丼"]
    },
    {
      "id": "ghi78901-e89b-12d3-a456-426614174023",
      "item_name": "しょうゆ",
      "category": "調味料",
      "quantity": "大さじ4（照り焼き大さじ2 + 親子丼大さじ2）",
      "memo": "",
      "status": "pending",
      "is_excluded": true,
      "excluded_reason": "pantry",
      "recipe_sources": ["鶏肉の照り焼き", "親子丼"]
    }
  ],
  "summary": {
    "total_items": 15,
    "excluded_items": 3,
    "active_items": 12
  },
  "created_at": "2025-07-13T08:00:00Z"
}
```

**エラーケース**:
- `404`: 指定週の献立が存在しない
- `400`: 献立にレシピが登録されていない
- `400`: 食材データ（RecipeIngredients）が未登録のレシピがある場合は警告付きで生成

### 8.5 買い物アイテム除外切り替え
```http
PUT /api/v1/shopping-items/{item_id}/exclude
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "is_excluded": true
}
```

**成功レスポンス (200 OK)**:
```json
{
  "id": "ghi78901-e89b-12d3-a456-426614174021",
  "item_name": "鶏もも肉",
  "is_excluded": true,
  "status": "pending"
}
```

---

## 8A. レシピ食材管理API

### 8A.1 レシピ食材一覧取得
```http
GET /api/v1/recipes/{recipe_id}/ingredients
Authorization: Bearer <access_token>
```

**成功レスポンス (200 OK)**:
```json
{
  "recipe_id": "456e7890-e89b-12d3-a456-426614174001",
  "recipe_name": "鶏肉の照り焼き",
  "ingredients": [
    {
      "id": "ing78901-e89b-12d3-a456-426614174001",
      "name": "鶏もも肉",
      "quantity": "300g",
      "category": "肉類",
      "sort_order": 1
    },
    {
      "id": "ing78901-e89b-12d3-a456-426614174002",
      "name": "しょうゆ",
      "quantity": "大さじ2",
      "category": "調味料",
      "sort_order": 2
    },
    {
      "id": "ing78901-e89b-12d3-a456-426614174003",
      "name": "みりん",
      "quantity": "大さじ2",
      "category": "調味料",
      "sort_order": 3
    },
    {
      "id": "ing78901-e89b-12d3-a456-426614174004",
      "name": "砂糖",
      "quantity": "大さじ1",
      "category": "調味料",
      "sort_order": 4
    }
  ]
}
```

### 8A.2 レシピ食材一括更新
```http
PUT /api/v1/recipes/{recipe_id}/ingredients
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "ingredients": [
    {
      "name": "鶏もも肉",
      "quantity": "300g",
      "category": "肉類",
      "sort_order": 1
    },
    {
      "name": "しょうゆ",
      "quantity": "大さじ2",
      "category": "調味料",
      "sort_order": 2
    }
  ]
}
```

**成功レスポンス (200 OK)**: 更新後の食材一覧（8A.1と同じ形式）

**処理**: 既存の食材を全削除して新しいリストで置き換え（PUT semantics）

---

## 8B. パントリー（在庫管理）API

### 8B.1 パントリー一覧取得
```http
GET /api/v1/pantry?available_only=true
Authorization: Bearer <access_token>
```

**クエリパラメーター**:
- `available_only`: `true` の場合、在庫ありのみ返却（デフォルト: false）

**成功レスポンス (200 OK)**:
```json
{
  "pantry_items": [
    {
      "id": "pan78901-e89b-12d3-a456-426614174001",
      "name": "しょうゆ",
      "category": "調味料",
      "is_available": true,
      "updated_at": "2025-07-13T08:00:00Z"
    },
    {
      "id": "pan78901-e89b-12d3-a456-426614174002",
      "name": "みりん",
      "category": "調味料",
      "is_available": true,
      "updated_at": "2025-07-12T10:00:00Z"
    },
    {
      "id": "pan78901-e89b-12d3-a456-426614174003",
      "name": "米",
      "category": "穀類",
      "is_available": true,
      "updated_at": "2025-07-10T12:00:00Z"
    }
  ],
  "total": 3
}
```

### 8B.2 パントリー一括更新
```http
PUT /api/v1/pantry
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "items": [
    {
      "name": "しょうゆ",
      "category": "調味料",
      "is_available": true
    },
    {
      "name": "みりん",
      "category": "調味料",
      "is_available": false
    }
  ]
}
```

**成功レスポンス (200 OK)**: 更新後のパントリー一覧（8B.1と同じ形式）

**処理**: UPSERT方式（`user_id` + `name` の一意制約でマッチ → 存在すれば更新、なければ作成）

### 8B.3 パントリーアイテム削除
```http
DELETE /api/v1/pantry/{item_id}
Authorization: Bearer <access_token>
```

**成功レスポンス (204 No Content)**

---

## 9. リアルタイム通信API

### 9.1 WebSocket接続（メッセージ）
```
WebSocket URL: wss://api.helper-system.com/ws/messages
Authorization: Bearer <access_token>
```

**接続メッセージ**:
```json
{
  "type": "connect",
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**新着メッセージ**:
```json
{
  "type": "new_message",
  "data": {
    "id": "abc12345-e89b-12d3-a456-426614174009",
    "sender_id": "123e4567-e89b-12d3-a456-426614174001",
    "sender_name": "佐藤花子",
    "content": "了解しました。半熟卵で準備します。",
    "message_type": "normal",
    "created_at": "2025-07-13T10:35:00Z"
  }
}
```

### 9.2 Server-Sent Events（進捗通知）
```
GET /api/v1/sse/task-updates
Authorization: Bearer <access_token>
Accept: text/event-stream
```

**作業完了通知**:
```
event: task_completed
data: {"task_id": "789e0123-e89b-12d3-a456-426614174006", "task_title": "洗濯", "completed_at": "2025-07-13T10:30:00Z", "helper_name": "佐藤花子"}

event: daily_report_submitted
data: {"date": "2025-07-13", "helper_name": "佐藤花子", "submitted_at": "2025-07-13T12:00:00Z"}
```

---

## 10. エラーハンドリング

### 10.1 統一エラーレスポンス形式
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "入力データに問題があります",
    "details": [
      {
        "field": "name",
        "message": "料理名は必須です"
      },
      {
        "field": "cooking_time",
        "message": "調理時間は1以上の数値を入力してください"
      }
    ],
    "request_id": "req_123456789",
    "timestamp": "2025-07-13T12:00:00Z"
  }
}
```

### 10.2 HTTPステータスコード
| コード | 意味 | 使用場面 |
|--------|------|----------|
| 200 | OK | 正常処理完了 |
| 201 | Created | リソース作成成功 |
| 204 | No Content | 削除成功 |
| 400 | Bad Request | 入力データエラー |
| 401 | Unauthorized | 認証エラー |
| 403 | Forbidden | 権限エラー |
| 404 | Not Found | リソース未存在 |
| 409 | Conflict | データ競合 |
| 422 | Unprocessable Entity | バリデーションエラー |
| 429 | Too Many Requests | レート制限 |
| 500 | Internal Server Error | サーバーエラー |

### 10.3 エラーコード一覧
| コード | 説明 |
|--------|------|
| `VALIDATION_ERROR` | 入力データのバリデーションエラー |
| `AUTHENTICATION_FAILED` | 認証失敗 |
| `INVALID_TOKEN` | 無効なトークン |
| `TOKEN_EXPIRED` | トークン有効期限切れ |
| `PERMISSION_DENIED` | 権限不足 |
| `RESOURCE_NOT_FOUND` | リソースが見つからない |
| `DUPLICATE_RESOURCE` | 重複データ |
| `RATE_LIMIT_EXCEEDED` | レート制限超過 |
| `EXTERNAL_SERVICE_ERROR` | 外部サービスエラー |
| `DATABASE_ERROR` | データベースエラー |
| `INTERNAL_ERROR` | 内部エラー |

---

## 11. セキュリティ仕様

### 11.1 JWT仕様
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "role": "senior",
    "exp": 1691928000,
    "iat": 1691926200,
    "jti": "jwt_123456789"
  }
}
```

### 11.2 リクエスト/レスポンスヘッダー
```http
# リクエストヘッダー
Authorization: Bearer <access_token>
Content-Type: application/json
User-Agent: HelperApp/1.0 (iOS 16.0)
X-Request-ID: req_123456789

# レスポンスヘッダー  
Content-Type: application/json; charset=utf-8
X-Request-ID: req_123456789
X-Rate-Limit-Remaining: 995
X-Rate-Limit-Reset: 1691928000
```

### 11.3 CORS設定
```http
Access-Control-Allow-Origin: https://helper-app.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type, X-Request-ID
Access-Control-Max-Age: 86400
```

---

## 12. 運用・監視

### 12.1 ヘルスチェック
```http
GET /api/v1/health
```

**成功レスポンス (200 OK)**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-07-13T12:00:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "external_apis": "healthy"
  },
  "metrics": {
    "active_connections": 245,
    "response_time_ms": 85,
    "error_rate": 0.02
  }
}
```

### 12.2 メトリクス
```http
GET /api/v1/metrics
Authorization: Bearer <admin_token>
```

---

## 13. OpenAPI仕様例

```yaml
openapi: 3.0.0
info:
  title: ホームヘルパー管理システム API
  version: 1.0.0
  description: 高齢者とヘルパーをつなぐ管理システムのAPI

servers:
  - url: https://api.helper-system.com/api/v1
    description: 本番環境
  - url: https://staging-api.helper-system.com/api/v1
    description: ステージング環境

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    User:
      type: object
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        full_name:
          type: string
        role:
          type: string
          enum: [senior, helper, care_manager]
      required:
        - id
        - email
        - full_name
        - role

paths:
  /auth/login:
    post:
      summary: ユーザーログイン
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                email:
                  type: string
                  format: email
                password:
                  type: string
              required:
                - email
                - password
      responses:
        '200':
          description: ログイン成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  refresh_token:
                    type: string
                  token_type:
                    type: string
                  expires_in:
                    type: integer
                  user:
                    $ref: '#/components/schemas/User'
```

---

## 14. 管理者用ユーザー管理API

> **詳細仕様**: `docs/admin_management_specification.md` を参照

### 14.1 エンドポイント一覧

管理APIは全て `/api/v1/admin/` プレフィックスを使用し、適切な権限チェックを行う。

#### ユーザーCRUD管理
| メソッド | エンドポイント | 権限 | 説明 |
|---------|-------------|------|------|
| `GET` | `/api/v1/admin/users` | `user:manage` | ユーザー一覧（検索・フィルタ・ページネーション） |
| `POST` | `/api/v1/admin/users` | `user:manage` | ユーザー作成（一時パスワード自動生成） |
| `GET` | `/api/v1/admin/users/{user_id}` | `user:manage` | ユーザー詳細（アサイン情報・ログイン履歴含む） |
| `PUT` | `/api/v1/admin/users/{user_id}` | `user:manage` | ユーザー情報更新 |
| `PUT` | `/api/v1/admin/users/{user_id}/deactivate` | `user:manage` | ユーザー無効化 |
| `PUT` | `/api/v1/admin/users/{user_id}/activate` | `user:manage` | ユーザー有効化 |
| `POST` | `/api/v1/admin/users/{user_id}/reset-password` | `user:manage` | パスワードリセット |

#### アサイン管理
| メソッド | エンドポイント | 権限 | 説明 |
|---------|-------------|------|------|
| `GET` | `/api/v1/admin/assignments` | `user:manage` | アサイン一覧 |
| `POST` | `/api/v1/admin/assignments` | `user:manage` | アサイン作成 |
| `GET` | `/api/v1/admin/assignments/{id}` | `user:manage` | アサイン詳細 |
| `PUT` | `/api/v1/admin/assignments/{id}` | `user:manage` | アサイン更新 |
| `DELETE` | `/api/v1/admin/assignments/{id}` | `user:manage` | アサイン終了（論理削除） |
| `GET` | `/api/v1/admin/users/{user_id}/assignments` | `user:manage` | 特定ユーザーのアサイン |
| `GET` | `/api/v1/assignments/my` | 認証済み | 自分のアサイン取得 |

#### 監査ログ
| メソッド | エンドポイント | 権限 | 説明 |
|---------|-------------|------|------|
| `GET` | `/api/v1/admin/audit-logs` | `system:admin` | 監査ログ一覧（フィルタ・ページネーション） |
| `GET` | `/api/v1/admin/audit-logs/{id}` | `system:admin` | 監査ログ詳細 |

#### レポート・ダッシュボード
| メソッド | エンドポイント | 権限 | 説明 |
|---------|-------------|------|------|
| `GET` | `/api/v1/admin/dashboard/stats` | `user:manage` | システム概要統計 |
| `GET` | `/api/v1/admin/reports/users` | `user:manage` | ユーザー統計レポート |
| `GET` | `/api/v1/admin/reports/assignments` | `user:manage` | アサイン統計レポート |
| `GET` | `/api/v1/admin/reports/tasks` | `report:read` | タスク完了統計 |
| `GET` | `/api/v1/admin/reports/activity` | `report:read` | ユーザーアクティビティ |

#### CSVインポート/エクスポート
| メソッド | エンドポイント | 権限 | 説明 |
|---------|-------------|------|------|
| `GET` | `/api/v1/admin/users/export` | `user:manage` | ユーザーCSVエクスポート |
| `POST` | `/api/v1/admin/users/import` | `system:admin` | ユーザーCSVインポート |
| `POST` | `/api/v1/admin/users/import/validate` | `system:admin` | CSVバリデーション（ドライラン） |

#### システム設定
| メソッド | エンドポイント | 権限 | 説明 |
|---------|-------------|------|------|
| `GET` | `/api/v1/admin/settings` | `system:admin` | 設定一覧 |
| `GET` | `/api/v1/admin/settings/{key}` | `system:admin` | 特定設定取得 |
| `PUT` | `/api/v1/admin/settings/{key}` | `system:admin` | 設定更新 |

#### 通知管理
| メソッド | エンドポイント | 権限 | 説明 |
|---------|-------------|------|------|
| `GET` | `/api/v1/notifications` | 認証済み | 自分の通知一覧 |
| `PUT` | `/api/v1/notifications/{id}/read` | 認証済み | 通知既読 |
| `PUT` | `/api/v1/notifications/read-all` | 認証済み | 全件既読 |
| `POST` | `/api/v1/admin/notifications/broadcast` | `system:admin` | 一斉通知 |
| `POST` | `/api/v1/admin/notifications/send` | `user:manage` | 個別通知 |

### 14.2 共通仕様

#### 認可チェック
全ての `/admin/` エンドポイントは以下の共通チェックを実施:
1. JWT認証トークンの検証
2. `is_active = true` の確認
3. エンドポイント固有の権限チェック（上表の「権限」カラム参照）

#### ビジネスロジックエラー
管理APIは既存のエラーレスポンス形式（12章参照）に加え、以下のエラーコードを返す:

| コード | HTTPステータス | 説明 |
|-------|--------------|------|
| `LAST_ADMIN_DEACTIVATION` | 409 | 最後のsystem_adminの無効化試行 |
| `DUPLICATE_ASSIGNMENT` | 409 | 同一helper+seniorのactiveアサインが既存 |
| `INVALID_ROLE_FOR_ASSIGNMENT` | 422 | アサイン対象のユーザーロールが不正 |
| `CSV_VALIDATION_ERROR` | 422 | CSVファイルのバリデーションエラー |
| `CSV_ROW_LIMIT_EXCEEDED` | 422 | CSVインポート行数上限超過 |

---

## 15. ログ監査・コンプライアンスAPI

※ 詳細仕様は[ログ監査・収集強化仕様書](./logging_audit_specification.md)を参照

### 15.1 個人データアクセスログAPI

| メソッド | エンドポイント | 権限 | 説明 |
|---------|-------------|------|------|
| `GET` | `/api/v1/admin/data-access-logs` | `system:admin` | データアクセスログ検索（フィルタ・ページネーション） |
| `GET` | `/api/v1/admin/data-access-logs/report` | `system:admin` | データアクセス集計レポート |
| `GET` | `/api/v1/admin/data-access-logs/user/{user_id}` | `system:admin` | 特定利用者のアクセス履歴 |

#### データアクセスログ検索
```http
GET /api/v1/admin/data-access-logs?target_user_id={uuid}&date_from=2026-04-01&date_to=2026-04-04&page=1&limit=50
Authorization: Bearer <access_token>
```

**クエリパラメータ**: `accessor_user_id`, `target_user_id`, `access_type` (read/write/export/delete), `resource_type`, `has_assignment` (boolean), `date_from`, `date_to`, `page`, `limit`

**成功レスポンス (200 OK)**:
```json
{
  "data_access_logs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "accessor_user_id": "123e4567-e89b-12d3-a456-426614174001",
      "accessor_email": "helper@example.com",
      "accessor_role": "helper",
      "target_user_id": "123e4567-e89b-12d3-a456-426614174002",
      "target_user_name": "田中花子",
      "access_type": "read",
      "resource_type": "user_profile",
      "data_fields": ["full_name", "phone", "medical_notes"],
      "endpoint": "/api/v1/users/123e4567-e89b-12d3-a456-426614174002",
      "http_method": "GET",
      "ip_address": "192.168.1.100",
      "has_assignment": true,
      "created_at": "2026-04-04T09:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1500,
    "total_pages": 30
  }
}
```

### 15.2 コンプライアンスAPI

| メソッド | エンドポイント | 権限 | 説明 |
|---------|-------------|------|------|
| `GET` | `/api/v1/admin/compliance/consent-logs` | `system:admin` | 同意ログ検索 |
| `GET` | `/api/v1/admin/compliance/data-requests` | `system:admin` | データ主体権利行使ログ一覧 |
| `POST` | `/api/v1/admin/compliance/data-requests` | `system:admin` | 権利行使請求の記録 |
| `PATCH` | `/api/v1/admin/compliance/data-requests/{id}` | `system:admin` | 請求ステータス更新 |
| `GET` | `/api/v1/admin/compliance/breach-reports` | `system:admin` | 漏えい報告一覧 |
| `POST` | `/api/v1/admin/compliance/breach-reports` | `system:admin` | 漏えい報告作成 |
| `GET` | `/api/v1/admin/compliance/retention-report` | `system:admin` | データ保持状況レポート |

#### データ主体権利行使請求の記録
```http
POST /api/v1/admin/compliance/data-requests
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "event_type": "disclosure_request",
  "target_user_id": "123e4567-e89b-12d3-a456-426614174002",
  "request_details": {
    "request_type": "disclosure",
    "requested_data": ["personal_info", "access_logs"],
    "identity_verified": true,
    "identity_method": "本人確認書類",
    "received_via": "書面"
  }
}
```

**成功レスポンス (201 Created)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "event_type": "disclosure_request",
  "target_user_id": "123e4567-e89b-12d3-a456-426614174002",
  "target_user_name": "田中花子",
  "status": "pending",
  "deadline_at": "2026-04-18T00:00:00Z",
  "created_at": "2026-04-04T10:00:00Z"
}
```

### 15.3 フロントエンドテレメトリAPI

| メソッド | エンドポイント | 権限 | 説明 |
|---------|-------------|------|------|
| `POST` | `/api/v1/telemetry/frontend-logs` | 認証不要 | フロントエンドログ受信（レート制限: 10req/min/ユーザー） |

```http
POST /api/v1/telemetry/frontend-logs
Content-Type: application/json

{
  "logs": [
    {
      "type": "js_error",
      "message": "Cannot read property 'name' of undefined",
      "stack": "TypeError: ...",
      "url": "/dashboard",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2026-04-04T10:00:00Z"
    }
  ],
  "client_timestamp": "2026-04-04T10:01:05Z"
}
```

**成功レスポンス (202 Accepted)**:
```json
{
  "accepted": true,
  "count": 1
}
```

### 15.4 ログ検索API（Lokiプロキシ）

| メソッド | エンドポイント | 権限 | 説明 |
|---------|-------------|------|------|
| `GET` | `/api/v1/admin/logs/search` | `system:admin` | Loki LogQLクエリプロキシ |

```http
GET /api/v1/admin/logs/search?query={job="security"}&start=2026-04-04T00:00:00Z&end=2026-04-04T23:59:59Z&limit=100
Authorization: Bearer <access_token>
```

---

## 16. テーマシステムAPI

ページデザイン（配色・書体・余白・角丸）をユーザー・システム単位で切替するためのAPI群。詳細仕様は [テーマシステム仕様書](./theme_system_specification.md) を参照。

### 16.1 既定テーマ取得（未認証可）
未ログイン画面（ログイン画面等）に適用するシステム既定テーマを取得する。

```http
GET /api/v1/themes/public/default
```

**成功レスポンス (200 OK)**:
```json
{
  "theme_key": "standard",
  "name": "スタンダード",
  "definition": {
    "schema_version": "1.0",
    "id": "standard",
    "name": "スタンダード",
    "colors": { "brand": { "500": "#1976d2" }, "semantic": { "success": "#2e7d32", "danger": "#d32f2f", "warn": "#ed6c02", "info": "#0288d1" }, "neutral": {} },
    "semanticTokens": { "bg.page": "{colors.neutral.50}", "text.primary": "{colors.neutral.900}" },
    "fonts": { "body": "Noto Sans JP, sans-serif", "heading": "Noto Sans JP, sans-serif", "baseSizePx": 18 },
    "radii": { "md": "0.5rem" },
    "density": "comfortable"
  }
}
```

**レート制限**: 未認証エンドポイントのため通常の未認証レート制限（100 req/h）を適用。CDN 層でのキャッシュ可。

### 16.2 テーマ一覧取得
```http
GET /api/v1/themes
Authorization: Bearer <access_token>
```

**クエリパラメータ**:
| 名称 | 型 | 必須 | 説明 |
|---|---|---|---|
| `is_builtin` | boolean | No | `true` で組込みのみ / `false` でカスタムのみ |
| `is_active` | boolean | No | 既定 `true`（選択可能なテーマのみ） |

**成功レスポンス (200 OK)**:
```json
{
  "themes": [
    { "theme_key": "standard", "name": "スタンダード", "description": "...", "is_builtin": true, "is_active": true, "preview_image_url": null },
    { "theme_key": "high-contrast", "name": "ハイコントラスト", "description": "...", "is_builtin": true, "is_active": true, "preview_image_url": null },
    { "theme_key": "warm", "name": "温もり", "description": "...", "is_builtin": true, "is_active": true, "preview_image_url": null },
    { "theme_key": "calm", "name": "おだやか", "description": "...", "is_builtin": true, "is_active": true, "preview_image_url": null }
  ]
}
```

### 16.3 テーマ詳細取得
```http
GET /api/v1/themes/{theme_key}
Authorization: Bearer <access_token>
```

**成功レスポンス (200 OK)**: 完全なテーマ定義 JSON を含むオブジェクト（§16.1 と同形式）。

**エラーレスポンス**:
- `404 Not Found` — 存在しないか `is_active=false`
- `410 Gone` — 削除済みのカスタムテーマ

### 16.4 自分の設定取得
```http
GET /api/v1/users/me/preferences
Authorization: Bearer <access_token>
```

**成功レスポンス (200 OK)**:
```json
{
  "theme_id": "warm",
  "font_size_override": null
}
```

**設計ポイント**:
- 未設定のキーは `null` で返却
- 将来の設定項目追加時もレスポンス形状は後方互換を維持

### 16.5 自分の設定更新
```http
PUT /api/v1/users/me/preferences
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "theme_id": "high-contrast"
}
```

**成功レスポンス (200 OK)**: 更新後の設定オブジェクト（§16.4 と同形式）。

**バリデーション**:
- `theme_id` は存在する `themes.theme_key` かつ `is_active=true` であること
- 不合格時 `422 Unprocessable Entity`

### 16.6 管理者: カスタムテーマ作成
```http
POST /api/v1/admin/themes
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "theme_key": "office-brand",
  "name": "事業所A ブランド",
  "description": "事業所A のコーポレートカラー",
  "definition": { /* ThemeDefinition JSON（theme_system_specification.md §3.1） */ },
  "is_active": true
}
```

**成功レスポンス (201 Created)**: 作成したテーマ。

**バリデーション**（サーバ側、違反時 `422`）:
- JSON スキーマ適合（`theme_system_specification.md` §3.1）
- `fonts.baseSizePx >= 18`
- 本文コントラスト比 `>= 4.5:1`（text.primary vs bg.page）
- ブランド上テキストコントラスト比 `>= 4.5:1`（text.onBrand vs colors.brand.500）
- `theme_key` 一意性（重複時 `409 Conflict`）

### 16.7 管理者: カスタムテーマ更新
```http
PUT /api/v1/admin/themes/{theme_key}
Authorization: Bearer <access_token>
Content-Type: application/json
```

**組込みテーマの制限**:
- `is_builtin=true` のテーマは `name` / `description` / `is_active` のみ更新可能
- `definition` / `theme_key` の更新は `409 Conflict`

**監査**: 変更前後の値が `audit_logs` に記録される。

### 16.8 管理者: カスタムテーマ削除
```http
DELETE /api/v1/admin/themes/{theme_key}
Authorization: Bearer <access_token>
```

**制約**:
- 組込みテーマの削除は不可（`409 Conflict`）
- 現在の `default_theme_id` に指定されているテーマは削除不可（`409 Conflict`）
- 削除するとそのテーマを選択中のユーザーには、次回取得時にシステム既定テーマへフォールバック

**成功レスポンス (204 No Content)**

### 16.9 管理者: システム既定テーマ設定
既存の §14 系管理者設定 API を再利用する。

```http
PUT /api/v1/admin/settings/default_theme_id
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "value": "warm"
}
```

**バリデーション**: 値が有効な `themes.theme_key` かつ `is_active=true` であること。

---

## 付録: 実装優先順位

### Phase 1: 基本認証・ユーザー管理
1. 認証API（ログイン・ログアウト・リフレッシュ）
2. ユーザー情報API
3. QRコード認証API

### Phase 2: コア機能
4. レシピ管理API
5. 献立管理API
6. 作業管理API

### Phase 3: コミュニケーション
7. メッセージAPI
8. リアルタイム通信（WebSocket・SSE）

### Phase 4: 付加機能
9. 買い物管理API
10. 通知機能
11. レポート機能

### Phase 5: 管理システム
12. ユーザーCRUD管理API + パスワードリセット
13. アサイン管理API + 監査ログAPI
14. レポート/ダッシュボードAPI + CSVインポート/エクスポート
15. システム設定API + 通知管理API

### Phase 6: ログ監査・コンプライアンス強化
16. データアクセスログAPI + フロントエンドテレメトリAPI
17. コンプライアンスAPI（同意ログ・権利行使・漏えい報告）
18. ログ検索API（Lokiプロキシ）

### Phase 7: テーマシステム
19. 公開既定テーマAPI + テーマ一覧・詳細API
20. ユーザー設定API（/users/me/preferences）
21. 管理者テーマCRUD API + 既定テーマ設定API

---

**文書終了**