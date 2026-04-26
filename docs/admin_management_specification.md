# ユーザーアカウント管理システム仕様書

## 文書管理情報
- **文書番号**: ADMIN-SPEC-001
- **版数**: 1.1
- **作成日**: 2026年4月4日
- **最終更新日**: 2026年4月22日
- **設計者**: Claude Code

### 改版履歴
| 版数 | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2026-04-04 | 初版 |
| 1.1 | 2026-04-22 | §12 テーマ管理 を追加、実装優先順位に Phase 5: テーマ管理 を追加 |

---

## 1. 概要

### 1.1 目的
本仕様書は、ホームヘルパー管理システムにおける**ユーザーアカウント管理機能**の詳細仕様を定義する。システム管理者（system_admin）およびケアマネージャー（care_manager）が利用するユーザー管理・アサイン管理・監査・レポート等の管理機能を網羅的に規定する。

### 1.2 スコープ
| 機能領域 | 説明 |
|---------|------|
| ユーザーCRUD管理 | ユーザーの作成・一覧・詳細・編集・無効化/有効化 |
| パスワード管理 | 管理者によるパスワードリセット |
| アサイン管理 | ヘルパー⇔利用者のアサインメント管理 |
| 監査ログ | 管理操作の記録と閲覧 |
| レポート/ダッシュボード | 利用統計・タスク完了率・稼働状況の可視化 |
| CSVインポート/エクスポート | ユーザーデータの一括操作 |
| システム設定管理 | システムパラメータの管理 |
| 通知管理 | 一斉通知・個別通知の送信と管理 |

### 1.3 対象ユーザー

| ロール | 管理機能へのアクセス |
|-------|-------------------|
| **system_admin**（システム管理者） | 全管理機能にフルアクセス |
| **care_manager**（ケアマネージャー） | 担当ユーザーの閲覧、レポート参照、限定CSV出力 |
| **helper**（ホームヘルパー） | 管理機能へのアクセス不可（自分のアサイン情報のみ閲覧可） |
| **senior**（利用者） | 管理機能へのアクセス不可（自分のアサイン情報のみ閲覧可） |

### 1.4 用語定義

| 用語 | 定義 |
|-----|------|
| system_admin | システム全体を管理するシステム管理者ロール |
| アサインメント | ヘルパーと利用者の担当関係 |
| 無効化（deactivate） | ユーザーアカウントを論理的に停止する操作（物理削除は行わない） |
| 監査ログ | システム上の管理操作を時系列で記録したもの |
| ブロードキャスト | 全ユーザーまたはロール単位への一斉通知 |

---

## 2. システム管理者（system_admin）ロール定義

### 2.1 ロールの位置づけ
```
system_admin（システム管理者）
  └── 全システム管理権限
care_manager（ケアマネージャー）
  └── 担当範囲内の閲覧・レポート権限
helper（ホームヘルパー）
  └── 自分のアサイン・タスクのみ
senior（利用者）
  └── 自分のデータのみ
```

system_adminは既存の3ロール（senior, helper, care_manager）に加えて新設されるロールであり、システム全体のユーザー管理・設定管理・監査を担当する。

### 2.2 権限範囲

| 権限カテゴリ | 具体的な操作 |
|------------|------------|
| ユーザー管理 | ユーザーの作成・一覧・詳細表示・編集・無効化/有効化・パスワードリセット |
| アサイン管理 | ヘルパー⇔利用者のアサイン作成・編集・削除 |
| 監査ログ | 全ログの閲覧・検索 |
| レポート | 全体統計・ダッシュボードの閲覧 |
| CSV操作 | ユーザーデータのインポート・エクスポート |
| システム設定 | システムパラメータの閲覧・変更 |
| 通知管理 | 一斉通知の送信・個別通知の送信 |

### 2.3 初期アカウント作成方法
system_adminの初期アカウントは**APIではなくCLIコマンドまたはマイグレーションシード**で作成する。これはブートストラップ問題（管理者を作成するために管理者が必要）を回避するためである。

```bash
# CLIコマンドによる初期管理者作成
python -m app.cli create-admin \
  --email admin@helper-system.com \
  --full-name "システム管理者" \
  --password <secure_password>
```

### 2.4 system_adminのアカウント管理ポリシー
- system_adminアカウントは**最低1つ以上のアクティブアカウント**が存在しなければならない
- 最後のsystem_adminアカウントの無効化は禁止（システムロック防止）
- system_adminのパスワードは**90日ごとの変更を推奨**
- 初回ログイン時にパスワード変更を強制
- system_admin操作は全て監査ログに記録

---

## 3. ユーザーCRUD管理

### 3.1 ユーザー一覧・検索

#### 3.1.1 エンドポイント
```http
GET /api/v1/admin/users
Authorization: Bearer <access_token>
```

#### 3.1.2 検索条件（クエリパラメーター）
| パラメーター | 型 | 説明 | 例 |
|------------|---|------|---|
| `role` | string | ロールでフィルタ | `senior`, `helper`, `care_manager`, `system_admin` |
| `is_active` | boolean | アクティブ状態でフィルタ | `true`, `false` |
| `search` | string | 氏名・メールアドレスの部分一致検索 | `田中` |
| `created_from` | date | 作成日の範囲指定（開始） | `2026-01-01` |
| `created_to` | date | 作成日の範囲指定（終了） | `2026-03-31` |
| `page` | integer | ページ番号（デフォルト: 1） | `1` |
| `limit` | integer | 1ページあたりの件数（デフォルト: 20, 最大: 100） | `20` |
| `sort_by` | string | ソート対象カラム | `created_at`, `full_name`, `email`, `role` |
| `sort_order` | string | ソート順 | `asc`, `desc` |

#### 3.1.3 一覧表示項目
| 項目 | 説明 |
|-----|------|
| id | ユーザーID（UUID） |
| email | メールアドレス |
| full_name | 氏名 |
| role | ロール |
| is_active | アクティブ状態 |
| last_login_at | 最終ログイン日時 |
| created_at | 作成日時 |

#### 3.1.4 レスポンス例
```json
{
  "users": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "email": "tanaka@example.com",
      "full_name": "田中太郎",
      "role": "senior",
      "is_active": true,
      "last_login_at": "2026-04-03T10:30:00+09:00",
      "created_at": "2025-09-01T00:00:00+09:00"
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

### 3.2 ユーザー作成

#### 3.2.1 エンドポイント
```http
POST /api/v1/admin/users
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 3.2.2 リクエストボディ

**共通必須項目**:
| 項目 | 型 | 必須 | 説明 |
|-----|---|------|------|
| `email` | string | 必須 | メールアドレス（一意制約） |
| `full_name` | string | 必須 | 氏名（最大100文字） |
| `role` | string | 必須 | ロール（senior/helper/care_manager/system_admin） |
| `phone` | string | 任意 | 電話番号 |
| `address` | string | 任意 | 住所 |

**senior（利用者）固有項目**:
| 項目 | 型 | 必須 | 説明 |
|-----|---|------|------|
| `emergency_contact` | string | 推奨 | 緊急連絡先 |
| `medical_notes` | string | 任意 | 医療メモ |
| `care_level` | integer | 任意 | 要介護度（1〜5） |

**helper（ヘルパー）固有項目**:
| 項目 | 型 | 必須 | 説明 |
|-----|---|------|------|
| `certification_number` | string | 推奨 | 資格番号 |
| `specialization` | string[] | 任意 | 専門分野 |

#### 3.2.3 初期パスワード生成ルール
- ユーザー作成時にパスワードは指定しない
- システムが**一時パスワード**を自動生成する（英数字記号混合、12文字以上）
- 一時パスワードは作成完了レスポンスに含まれる（初回のみ表示）
- ユーザーは初回ログイン時にパスワード変更を強制される

#### 3.2.4 レスポンス例
```json
{
  "id": "789e0123-e89b-12d3-a456-426614174000",
  "email": "suzuki@example.com",
  "full_name": "鈴木花子",
  "role": "helper",
  "is_active": true,
  "temporary_password": "Xk9#mP2$vL5n",
  "created_at": "2026-04-04T12:00:00+09:00",
  "message": "一時パスワードを安全にユーザーに伝達してください。初回ログイン時にパスワード変更が必要です。"
}
```

### 3.3 ユーザー詳細表示

#### 3.3.1 エンドポイント
```http
GET /api/v1/admin/users/{user_id}
Authorization: Bearer <access_token>
```

#### 3.3.2 レスポンス項目

**基本情報**:
| 項目 | 説明 |
|-----|------|
| id | ユーザーID |
| email | メールアドレス |
| full_name | 氏名 |
| role | ロール |
| phone | 電話番号 |
| address | 住所 |
| is_active | アクティブ状態 |
| last_login_at | 最終ログイン日時 |
| created_at | 作成日時 |
| updated_at | 更新日時 |

**ロール別追加情報**:
- senior: emergency_contact, medical_notes, care_level
- helper: certification_number, specialization

**アサイン情報**: 現在のアクティブなアサインメント一覧

**最近のログイン履歴**: 直近10件のログイン記録

#### 3.3.3 レスポンス例
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "tanaka@example.com",
  "full_name": "田中太郎",
  "role": "senior",
  "phone": "090-1234-5678",
  "address": "東京都渋谷区...",
  "emergency_contact": "田中花子 (娘) 080-9876-5432",
  "medical_notes": "高血圧の薬を服用中",
  "care_level": 2,
  "is_active": true,
  "last_login_at": "2026-04-03T10:30:00+09:00",
  "created_at": "2025-09-01T00:00:00+09:00",
  "updated_at": "2026-03-15T14:20:00+09:00",
  "assignments": [
    {
      "id": "aaa11111-...",
      "helper": {
        "id": "bbb22222-...",
        "full_name": "鈴木花子"
      },
      "status": "active",
      "visit_frequency": "週3回",
      "start_date": "2025-10-01"
    }
  ],
  "recent_logins": [
    {
      "logged_in_at": "2026-04-03T10:30:00+09:00",
      "ip_address": "192.168.1.100",
      "method": "password"
    }
  ]
}
```

### 3.4 ユーザー編集

#### 3.4.1 エンドポイント
```http
PUT /api/v1/admin/users/{user_id}
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 3.4.2 編集可能項目
| 項目 | 説明 | 制約 |
|-----|------|------|
| full_name | 氏名 | 最大100文字 |
| phone | 電話番号 | - |
| address | 住所 | - |
| email | メールアドレス | 一意制約チェック |
| role | ロール | ロール変更ルール適用（3.4.3参照） |
| emergency_contact | 緊急連絡先（senior） | - |
| medical_notes | 医療メモ（senior） | - |
| care_level | 要介護度（senior） | 1〜5 |
| certification_number | 資格番号（helper） | - |
| specialization | 専門分野（helper） | - |

#### 3.4.3 ロール変更のルール
- ロール変更はsystem_adminのみ実行可能
- ロール変更時は既存のアサインメントを見直す必要がある旨の**警告を返す**
- senior → helper: seniorのアサイン（利用者側）は自動で非アクティブ化
- helper → senior: helperのアサイン（ヘルパー側）は自動で非アクティブ化
- → care_manager/system_admin: 既存アサインは全て非アクティブ化
- 変更前後のロールが同一の場合はエラー

### 3.5 ユーザー無効化/有効化

#### 3.5.1 無効化エンドポイント
```http
PUT /api/v1/admin/users/{user_id}/deactivate
Authorization: Bearer <access_token>
```

#### 3.5.2 無効化時の影響
- `is_active` を `false` に設定
- ログイン不可（JWT検証時にis_activeチェック）
- 既存のアクティブセッション（JWTトークン）を全て無効化（トークンブラックリスト登録）
- アクティブなアサインメントのステータスを `inactive` に変更
- 無効化理由をメタデータとして監査ログに記録

#### 3.5.3 有効化エンドポイント
```http
PUT /api/v1/admin/users/{user_id}/activate
Authorization: Bearer <access_token>
```

#### 3.5.4 有効化時の復元処理
- `is_active` を `true` に設定
- アサインメントは**自動復元しない**（手動でアサインを再設定する必要がある）
- 有効化後、ユーザーは通常通りログイン可能

### 3.6 パスワードリセット

#### 3.6.1 エンドポイント
```http
POST /api/v1/admin/users/{user_id}/reset-password
Authorization: Bearer <access_token>
```

#### 3.6.2 管理者によるリセットフロー
1. system_adminがリセットAPIを呼び出す
2. システムが新しい一時パスワードを生成
3. ユーザーの既存セッションを全て無効化
4. レスポンスに一時パスワードを含めて返す
5. system_adminが安全な方法でユーザーに一時パスワードを伝達
6. ユーザーは次回ログイン時にパスワード変更を強制される

#### 3.6.3 レスポンス例
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "temporary_password": "Rn7$kW3#pM9x",
  "message": "パスワードがリセットされました。一時パスワードを安全にユーザーに伝達してください。",
  "sessions_invalidated": true
}
```

---

## 4. ヘルパー⇔利用者アサイン管理

### 4.1 アサイン一覧表示

#### 4.1.1 管理者用エンドポイント
```http
GET /api/v1/admin/assignments
Authorization: Bearer <access_token>
```

**クエリパラメーター**:
| パラメーター | 型 | 説明 |
|------------|---|------|
| `helper_id` | UUID | ヘルパーIDでフィルタ |
| `senior_id` | UUID | 利用者IDでフィルタ |
| `status` | string | ステータスでフィルタ（active/inactive/pending） |
| `page` | integer | ページ番号 |
| `limit` | integer | 件数 |

#### 4.1.2 自分のアサイン取得
```http
GET /api/v1/assignments/my
Authorization: Bearer <access_token>
```

ヘルパーの場合は担当利用者一覧、利用者の場合は担当ヘルパー一覧を返す。

#### 4.1.3 レスポンス例
```json
{
  "assignments": [
    {
      "id": "aaa11111-e89b-12d3-a456-426614174000",
      "helper": {
        "id": "bbb22222-...",
        "full_name": "鈴木花子",
        "certification_number": "H-12345"
      },
      "senior": {
        "id": "ccc33333-...",
        "full_name": "田中太郎",
        "care_level": 2
      },
      "assigned_by": {
        "id": "ddd44444-...",
        "full_name": "佐藤管理者"
      },
      "status": "active",
      "visit_frequency": "週3回",
      "preferred_days": [1, 3, 5],
      "preferred_time_start": "09:00",
      "preferred_time_end": "12:00",
      "notes": "午前中の訪問を希望",
      "start_date": "2025-10-01",
      "end_date": null,
      "created_at": "2025-09-28T10:00:00+09:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 95,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

### 4.2 アサイン作成

#### 4.2.1 エンドポイント
```http
POST /api/v1/admin/assignments
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 4.2.2 リクエストボディ
```json
{
  "helper_id": "bbb22222-e89b-12d3-a456-426614174000",
  "senior_id": "ccc33333-e89b-12d3-a456-426614174000",
  "visit_frequency": "週3回",
  "preferred_days": [1, 3, 5],
  "preferred_time_start": "09:00",
  "preferred_time_end": "12:00",
  "start_date": "2026-04-07",
  "end_date": null,
  "notes": "午前中の訪問を希望"
}
```

#### 4.2.3 バリデーションルール
- `helper_id` は role=helper のアクティブユーザーであること
- `senior_id` は role=senior のアクティブユーザーであること
- 同じhelper_id + senior_idの組み合わせでstatus=activeのアサインが既に存在しないこと
- `preferred_days` は 1（月曜）〜7（日曜）の配列
- `start_date` は過去日付も許可（既存関係の登録用）
- `end_date` が指定された場合、`start_date` 以降であること

### 4.3 アサイン編集

```http
PUT /api/v1/admin/assignments/{assignment_id}
Authorization: Bearer <access_token>
Content-Type: application/json
```

編集可能項目: visit_frequency, preferred_days, preferred_time_start, preferred_time_end, start_date, end_date, notes, status

**注意**: helper_id, senior_idは変更不可。変更する場合は既存アサインを終了し、新しいアサインを作成する。

### 4.4 アサイン終了/削除

```http
DELETE /api/v1/admin/assignments/{assignment_id}
Authorization: Bearer <access_token>
```

- 物理削除ではなく、statusを `inactive` に変更し、end_dateを当日に設定する
- 関連するタスクには影響しない（既に作成されたタスクはそのまま残る）

### 4.5 特定ユーザーのアサイン取得

```http
GET /api/v1/admin/users/{user_id}/assignments
Authorization: Bearer <access_token>
```

指定ユーザーに関連する全アサインメント（active/inactive含む）を取得。

### 4.6 ケアマネージャーのアサイン閲覧権限
care_managerは以下の条件で閲覧可能:
- 自分がassigned_byとして作成したアサイン
- 将来的にcare_manager ⇔ 担当エリアの仕組みを導入する場合は拡張可能

---

## 5. 監査ログ

### 5.1 ログ記録対象アクション一覧

| アクション | resource_type | 説明 |
|-----------|--------------|------|
| `user.create` | user | ユーザー作成 |
| `user.update` | user | ユーザー情報更新 |
| `user.deactivate` | user | ユーザー無効化 |
| `user.activate` | user | ユーザー有効化 |
| `user.role_change` | user | ロール変更 |
| `user.password_reset` | user | パスワードリセット |
| `assignment.create` | assignment | アサイン作成 |
| `assignment.update` | assignment | アサイン更新 |
| `assignment.delete` | assignment | アサイン終了 |
| `setting.update` | system_setting | システム設定変更 |
| `notification.broadcast` | notification | 一斉通知送信 |
| `notification.send` | notification | 個別通知送信 |
| `csv.import` | user | CSVインポート |
| `csv.export` | user | CSVエクスポート |
| `auth.login_success` | auth | ログイン成功 |
| `auth.login_failure` | auth | ログイン失敗 |
| `auth.logout` | auth | ログアウト |

### 5.2 ログ検索・フィルタ

#### 5.2.1 エンドポイント
```http
GET /api/v1/admin/audit-logs
Authorization: Bearer <access_token>
```

**クエリパラメーター**:
| パラメーター | 型 | 説明 |
|------------|---|------|
| `user_id` | UUID | 操作実行者でフィルタ |
| `action` | string | アクション種別でフィルタ |
| `resource_type` | string | リソース種別でフィルタ |
| `resource_id` | UUID | 対象リソースIDでフィルタ |
| `date_from` | datetime | 期間開始 |
| `date_to` | datetime | 期間終了 |
| `page` | integer | ページ番号 |
| `limit` | integer | 件数（デフォルト: 50） |

#### 5.2.2 レスポンス例
```json
{
  "audit_logs": [
    {
      "id": "eee55555-e89b-12d3-a456-426614174000",
      "user_id": "ddd44444-...",
      "user_email": "admin@helper-system.com",
      "user_role": "system_admin",
      "action": "user.create",
      "resource_type": "user",
      "resource_id": "789e0123-...",
      "changes": {
        "email": {"new": "suzuki@example.com"},
        "full_name": {"new": "鈴木花子"},
        "role": {"new": "helper"}
      },
      "metadata": {
        "ip_address": "192.168.1.50",
        "user_agent": "Mozilla/5.0..."
      },
      "created_at": "2026-04-04T12:00:00+09:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1250,
    "total_pages": 25,
    "has_next": true,
    "has_prev": false
  }
}
```

#### 5.2.3 監査ログ詳細取得
```http
GET /api/v1/admin/audit-logs/{log_id}
Authorization: Bearer <access_token>
```

### 5.3 ログ保持期間ポリシー
- 監査ログは**6ヶ月間**保持する（database_schema_design.mdのデータ保持期間に準拠）
- 6ヶ月経過したログは自動削除（バッチ処理）
- 監査ログはAPIからの削除・更新を**一切許可しない**（改ざん防止）

### 5.4 ログデータ構造
```
audit_logs テーブル
├── id (UUID) — 一意識別子
├── user_id (UUID, nullable) — 操作実行者ID
├── user_email (VARCHAR) — 非正規化（ユーザー削除後も保持）
├── user_role (VARCHAR) — 非正規化
├── action (VARCHAR) — アクション種別
├── resource_type (VARCHAR) — リソース種別
├── resource_id (UUID, nullable) — 対象リソースID
├── changes (JSONB) — 変更内容（old/new値）
├── metadata (JSONB) — 付加情報（IPアドレス等）
└── created_at (TIMESTAMP) — 記録日時
```

---

## 6. レポート・ダッシュボード

### 6.1 管理者ダッシュボード（system_admin）

#### 6.1.1 システム概要統計
```http
GET /api/v1/admin/dashboard/stats
Authorization: Bearer <access_token>
```

**レスポンス**:
```json
{
  "total_users": 150,
  "users_by_role": {
    "senior": 80,
    "helper": 50,
    "care_manager": 15,
    "system_admin": 5
  },
  "active_users": 140,
  "inactive_users": 10,
  "new_users_this_month": 12,
  "active_assignments": 95,
  "tasks_completed_this_week": 230,
  "login_count_today": 85,
  "generated_at": "2026-04-04T12:00:00+09:00"
}
```

#### 6.1.2 ユーザー統計レポート
```http
GET /api/v1/admin/reports/users
Authorization: Bearer <access_token>
```

クエリパラメーター: `period` (weekly/monthly/quarterly)

**レスポンス**: ロール別ユーザー数推移、新規登録数推移、無効化数推移

#### 6.1.3 アサイン統計レポート
```http
GET /api/v1/admin/reports/assignments
Authorization: Bearer <access_token>
```

**レスポンス**: アクティブアサイン数、ヘルパー1人あたりの平均担当利用者数、アサインなし利用者数

### 6.2 ケアマネージャーダッシュボード

#### 6.2.1 担当利用者サマリー
care_managerが閲覧可能なレポート。自分が作成したアサインに関連するユーザーの情報のみ表示。

```http
GET /api/v1/admin/reports/tasks
Authorization: Bearer <access_token>
```

**レスポンス**: タスク完了率、未完了タスク一覧、期限超過タスク数

#### 6.2.2 ヘルパー稼働状況
```http
GET /api/v1/admin/reports/activity
Authorization: Bearer <access_token>
```

**レスポンス**: ヘルパー別ログイン頻度、タスク完了数、直近のアクティビティ

---

## 7. CSVインポート/エクスポート

### 7.1 エクスポート

#### 7.1.1 エンドポイント
```http
GET /api/v1/admin/users/export
Authorization: Bearer <access_token>
```

#### 7.1.2 クエリパラメーター
検索条件はユーザー一覧（3.1.2）と同一のフィルタパラメーターを使用可能。

#### 7.1.3 出力フォーマット
- 形式: CSV（RFC 4180準拠）
- 文字コード: UTF-8 with BOM（日本語環境のExcel互換性のため）
- Content-Type: `text/csv; charset=utf-8`
- Content-Disposition: `attachment; filename="users_export_20260404.csv"`

#### 7.1.4 出力カラム
```csv
ID,メールアドレス,氏名,ロール,電話番号,住所,緊急連絡先,要介護度,資格番号,専門分野,アクティブ,最終ログイン,作成日
```

#### 7.1.5 権限による制限
- system_admin: 全ユーザーをエクスポート可能
- care_manager: 自分が作成したアサインに関連するユーザーのみ

### 7.2 インポート

#### 7.2.1 エンドポイント
```http
POST /api/v1/admin/users/import
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

#### 7.2.2 CSVテンプレート定義
```csv
メールアドレス,氏名,ロール,電話番号,住所,緊急連絡先,要介護度,資格番号,専門分野
suzuki@example.com,鈴木花子,helper,090-1111-2222,東京都新宿区...,,,H-12345,調理;介護
```

**必須カラム**: メールアドレス, 氏名, ロール
**任意カラム**: その他すべて

#### 7.2.3 バリデーションルール
- メールアドレスの形式チェック
- メールアドレスの一意性チェック（既存ユーザーとの重複）
- ロールの有効値チェック（senior/helper/care_manager/system_admin）
- care_levelの範囲チェック（1〜5）
- 1回のインポートは**最大500件**まで

#### 7.2.4 ドライランモード（事前検証）
```http
POST /api/v1/admin/users/import/validate
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

実際のインポートは行わず、バリデーション結果のみ返す。

**レスポンス例**:
```json
{
  "total_rows": 50,
  "valid_rows": 47,
  "error_rows": 3,
  "errors": [
    {
      "row": 5,
      "field": "email",
      "value": "invalid-email",
      "message": "メールアドレスの形式が不正です"
    },
    {
      "row": 12,
      "field": "email",
      "value": "tanaka@example.com",
      "message": "このメールアドレスは既に登録されています"
    },
    {
      "row": 30,
      "field": "role",
      "value": "admin",
      "message": "無効なロールです。有効値: senior, helper, care_manager, system_admin"
    }
  ],
  "preview": [
    {
      "row": 1,
      "email": "suzuki@example.com",
      "full_name": "鈴木花子",
      "role": "helper",
      "status": "new"
    }
  ]
}
```

#### 7.2.5 エラーハンドリング
- バリデーションエラーがある場合、**エラー行を除く正常行のみインポート**するか、**全件中止**するかをリクエストパラメーターで選択可能
- パラメーター: `on_error=skip`（エラー行スキップ）または `on_error=abort`（全件中止、デフォルト）
- インポート結果は監査ログに記録（件数、エラー件数含む）

---

## 8. システム設定管理

### 8.1 設定カテゴリ
| カテゴリ | 説明 |
|---------|------|
| `general` | 一般設定 |
| `security` | セキュリティ関連設定 |
| `notification` | 通知関連設定 |
| `system` | システム運用設定 |

### 8.2 設定項目一覧

| 設定キー | カテゴリ | デフォルト値 | 説明 | 機密 |
|---------|---------|------------|------|------|
| `password_min_length` | security | 8 | パスワード最小文字数 | No |
| `password_require_special_char` | security | true | 特殊文字必須 | No |
| `max_login_attempts` | security | 3 | 最大ログイン試行回数 | No |
| `account_lockout_duration_minutes` | security | 30 | アカウントロック時間（分） | No |
| `session_timeout_minutes` | security | 30 | セッションタイムアウト（分） | No |
| `admin_session_timeout_minutes` | security | 15 | 管理者セッションタイムアウト（分） | No |
| `maintenance_mode` | system | false | メンテナンスモード | No |
| `maintenance_message` | system | "" | メンテナンスメッセージ | No |
| `default_care_level` | general | null | デフォルト要介護度 | No |
| `notification_enabled` | notification | true | 通知機能の有効/無効 | No |
| `email_notification_enabled` | notification | false | メール通知の有効/無効 | No |
| `max_assignments_per_helper` | general | 10 | ヘルパー1人あたりの最大担当利用者数 | No |
| `csv_import_max_rows` | system | 500 | CSVインポート最大行数 | No |
| `audit_log_retention_days` | system | 180 | 監査ログ保持日数 | No |

### 8.3 設定管理エンドポイント

#### 設定一覧取得
```http
GET /api/v1/admin/settings
Authorization: Bearer <access_token>
```

#### 特定設定取得
```http
GET /api/v1/admin/settings/{setting_key}
Authorization: Bearer <access_token>
```

#### 設定更新
```http
PUT /api/v1/admin/settings/{setting_key}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "value": 10
}
```

### 8.4 設定変更フロー
1. system_adminが設定変更APIを呼び出す
2. 値のバリデーション（型チェック、範囲チェック）
3. 変更を適用
4. 監査ログに記録（変更前値・変更後値）
5. 変更結果を返す

**注意**: 設定はマイグレーションシードで初期値を投入する。APIから新規設定の追加・削除はできない（更新のみ）。

---

## 9. 通知管理

### 9.1 通知タイプ

| タイプ | 説明 | 使用場面 |
|-------|------|---------|
| `system` | システム通知 | メンテナンス告知、システム更新情報 |
| `assignment` | アサイン通知 | アサイン作成・変更時 |
| `task` | タスク通知 | タスク割り当て・完了時 |
| `message` | メッセージ通知 | 新着メッセージ到着時 |
| `alert` | アラート | 重要な警告（アカウントロック等） |
| `admin` | 管理者通知 | 管理者からの個別連絡 |

### 9.2 通知の優先度

| 優先度 | 説明 | UIでの表示 |
|-------|------|-----------|
| `low` | 低 | 通常表示 |
| `normal` | 通常 | 通常表示 |
| `high` | 高 | 強調表示 |
| `urgent` | 緊急 | ポップアップ表示 |

### 9.3 自分の通知取得
```http
GET /api/v1/notifications
Authorization: Bearer <access_token>
```

クエリパラメーター: `is_read` (true/false), `type`, `page`, `limit`

### 9.4 通知の既読処理

#### 個別既読
```http
PUT /api/v1/notifications/{notification_id}/read
Authorization: Bearer <access_token>
```

#### 全件既読
```http
PUT /api/v1/notifications/read-all
Authorization: Bearer <access_token>
```

### 9.5 一斉通知（ブロードキャスト）
```http
POST /api/v1/admin/notifications/broadcast
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "システムメンテナンスのお知らせ",
  "body": "4月10日 02:00〜06:00の間、システムメンテナンスを実施します。",
  "notification_type": "system",
  "priority": "high",
  "target_roles": ["senior", "helper", "care_manager"]
}
```

`target_roles`を指定することで、特定のロールのみに通知を送信可能。省略時は全ユーザーに送信。

### 9.6 個別通知送信
```http
POST /api/v1/admin/notifications/send
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "パスワードリセットのご案内",
  "body": "パスワードがリセットされました。次回ログイン時に新しいパスワードを設定してください。",
  "notification_type": "admin",
  "priority": "high"
}
```

### 9.7 通知テンプレート
以下の操作は自動的に通知を生成する:

| トリガー | 通知先 | テンプレート |
|---------|-------|------------|
| ユーザー作成 | 作成されたユーザー | 「アカウントが作成されました」 |
| アサイン作成 | helper, senior | 「新しいアサインメントが設定されました」 |
| アサイン終了 | helper, senior | 「アサインメントが終了しました」 |
| パスワードリセット | 対象ユーザー | 「パスワードがリセットされました」 |
| アカウント無効化 | 対象ユーザー | 「アカウントが無効化されました」 |
| アカウント有効化 | 対象ユーザー | 「アカウントが有効化されました」 |

---

## 10. 画面仕様

### 10.1 管理画面レイアウト
管理画面は既存のフロントエンド（React + Chakra UI v3）と統一されたデザインで実装する。

```
┌──────────────────────────────────────────────────┐
│  ヘッダー（ロゴ、ユーザー名、通知アイコン、ログアウト） │
├──────────┬───────────────────────────────────────┤
│          │                                       │
│ サイド    │  メインコンテンツエリア                   │
│ ナビ     │                                       │
│          │  ・ダッシュボード                        │
│ ・ダッシュ │  ・ユーザー一覧/詳細                    │
│   ボード  │  ・アサイン管理                         │
│ ・ユーザー │  ・監査ログ                            │
│   管理   │  ・レポート                             │
│ ・アサイン │  ・システム設定                         │
│   管理   │  ・通知管理                             │
│ ・監査ログ│                                       │
│ ・レポート│                                       │
│ ・設定   │                                       │
│ ・通知   │                                       │
│          │                                       │
└──────────┴───────────────────────────────────────┘
```

### 10.2 ユーザー管理画面
- **一覧画面**: テーブル形式、検索バー、フィルタ（ロール/ステータス）、ソート、ページネーション、「新規作成」ボタン
- **詳細画面**: タブ形式（基本情報/アサイン情報/ログイン履歴）、編集ボタン、無効化/有効化ボタン、パスワードリセットボタン
- **作成/編集画面**: フォーム形式、ロール選択で入力項目が動的に変わる

### 10.3 アサイン管理画面
- **一覧画面**: テーブル形式、ヘルパー/利用者でフィルタ、ステータスフィルタ
- **作成画面**: ヘルパー選択（検索付きドロップダウン）、利用者選択、スケジュール設定

### 10.4 監査ログ画面
- 時系列リスト、フィルタ（操作者/アクション/期間）、詳細モーダル

### 10.5 ダッシュボード画面
- カード形式で主要KPI表示（ユーザー数、アクティブアサイン数、タスク完了数）
- グラフ（ユーザー数推移、タスク完了率推移）

### 10.6 システム設定画面
- カテゴリ別タブ、設定項目のインライン編集

---

## 11. エラーハンドリング

### 11.1 バリデーションエラー (422 Unprocessable Entity)
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "入力値にエラーがあります",
    "details": [
      {
        "field": "email",
        "message": "有効なメールアドレスを入力してください"
      }
    ]
  }
}
```

### 11.2 権限エラー (403 Forbidden)
```json
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "この操作を実行する権限がありません"
  }
}
```

### 11.3 ビジネスロジックエラー (409 Conflict)
```json
{
  "error": {
    "code": "BUSINESS_RULE_VIOLATION",
    "message": "最後のシステム管理者アカウントを無効化することはできません"
  }
}
```

### 11.4 リソース未発見 (404 Not Found)
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "指定されたユーザーが見つかりません"
  }
}
```

---

## 12. テーマ管理

詳細仕様は [テーマシステム仕様書](./theme_system_specification.md) を参照。本節は管理画面としての要件を定義する。

### 12.1 機能スコープ
system_admin のみ利用可能。以下の操作を提供する。

- プリセット/カスタム含む全テーマの一覧表示
- カスタムテーマの新規登録・編集・削除
- 組込みテーマの有効/無効切替（削除・定義編集は不可、名称・説明のみ変更可）
- システム既定テーマの指定（未ログイン画面およびユーザー未設定時に適用）
- プレビュー表示（定義 JSON から簡易プレビューを描画）

### 12.2 画面構成
| 画面 | パス | 主な要素 |
|---|---|---|
| テーマ一覧 | `/admin/themes` | フィルタ（組込み/カスタム、有効/無効）、一覧カード、「新規登録」ボタン、「既定テーマ」表示 |
| テーマ登録 | `/admin/themes/new` | JSON エディタ、必須フィールドフォーム、リアルタイムプレビュー、保存時のバリデーションエラー表示 |
| テーマ編集 | `/admin/themes/{theme_key}/edit` | 登録画面と同構成（組込みは編集可能フィールドを制限） |
| 既定テーマ設定 | テーマ一覧内のモーダル | `default_theme_id` の変更フォーム |

### 12.3 バリデーション要件
以下は**サーバ側で実施**し、クライアント側はサーバレスポンスを受けてエラー表示する。

- JSON スキーマ適合（`theme_system_specification.md` §3.1）
- 本文フォントサイズ ≥ 18px
- コントラスト比（WCAG 2.1 AA）: 本文 ≥ 4.5:1、ブランド上テキスト ≥ 4.5:1、非テキスト UI 要素 ≥ 3:1
- `theme_key` 一意性
- サイズ上限 16KB

### 12.4 監査
テーマの登録・編集・削除、および既定テーマ変更は `audit_logs` に以下の形で記録する。

| action | resource_type | resource_id | メタ |
|---|---|---|---|
| `theme.create` | `theme` | `theme_key` | 定義 JSON（必要に応じサニタイズ） |
| `theme.update` | `theme` | `theme_key` | 変更前後の差分 |
| `theme.delete` | `theme` | `theme_key` | 削除時のスナップショット |
| `system.update_default_theme` | `system_setting` | `default_theme_id` | 変更前後の値 |

### 12.5 エラーレスポンス
- `422 Unprocessable Entity` — バリデーション不合格（詳細は §11.1 形式で返す）
- `409 Conflict` — 組込みテーマの削除、`theme_key` 重複、既定テーマに指定中の削除
- `404 Not Found` — 存在しない `theme_key`

### 12.6 関連エンドポイント
[`api_specification.md`](./api_specification.md) §16 参照。

---

## 13. 実装優先順位

### Phase 1: 基盤（最優先）
1. DBマイグレーション: users.role CHECK制約に `system_admin` 追加、`audit_logs` テーブル作成
2. RBAC更新: 新権限・ロールマッピング
3. ユーザーCRUD API（一覧・作成・詳細・編集・無効化/有効化）
4. パスワードリセットAPI
5. 監査ログ書き込み（ミドルウェア/デコレータ）
6. 初期system_adminアカウント作成CLI

### Phase 2: アサイン・監査
1. DBマイグレーション: `user_assignments` テーブル作成
2. アサインCRUD API
3. 監査ログ閲覧API
4. care_managerのアサインベースアクセス制御

### Phase 3: レポート・CSV
1. ダッシュボード統計API
2. レポートAPI
3. CSVエクスポートAPI
4. CSVインポート（バリデーション + 実行）

### Phase 4: 設定・通知
1. DBマイグレーション: `system_settings`、`notifications` テーブル作成
2. システム設定CRUD API
3. 通知API
4. ケアマネージャーダッシュボード

### Phase 5: テーマ管理
1. DBマイグレーション: `themes`、`user_preferences` テーブル作成
2. プリセットテーマのシード投入（`standard` / `high-contrast` / `warm` / `calm`）
3. 公開既定テーマAPI、テーマ一覧/詳細API
4. ユーザー設定API（`/users/me/preferences`）
5. 管理者テーマCRUD API、既定テーマ変更API
6. フロントエンド `ThemeProvider` 導入、ProfilePage のテーマ選択UI
7. Admin テーマ管理画面（§12）
