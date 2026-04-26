# テーマシステム仕様書

## 文書管理情報
- **文書番号**: THEME-HHS-001
- **版数**: 1.0
- **作成日**: 2026年4月22日
- **最終更新日**: 2026年4月22日
- **設計者**: Home Helper Management System 開発チーム
- **関連文書**:
  - `docs/requirements_specification.md` §4.4.8（機能要件）
  - `docs/database_schema_design.md` §3.20 / §3.21（データモデル）
  - `docs/api_specification.md` §16（API）
  - `docs/frontend_implementation_plan.md` §2.2 / §3.1（実装）
  - `docs/elderly_ui_ux_guidelines.md` §2.4（アクセシビリティ制約）
  - `docs/admin_management_specification.md` §12（管理画面）

### 改版履歴
| 版数 | 日付 | 変更内容 | 担当 |
|---|---|---|---|
| 1.0 | 2026-04-22 | 新規作成（WordPress 風テーマ切替機構を定義） | 開発チーム |

---

## 1. 概要

### 1.1 目的
WordPress のテーマシステムに類似した仕組みを導入し、**ページデザイン（カラーパレット・タイポグラフィ・余白密度・角丸・コンポーネント装飾）をテーマ単位で一括切替**できるようにする。従来は `frontend/src/theme.ts` にハードコードされた単一テーマのみで、ユーザー・事業所ごとの見た目切替が不可能だった課題を解決する。

### 1.2 スコープ
- プリセットテーマ（システム組込み）とカスタムテーマ（管理者登録）の両立
- ユーザーごとのテーマ選択と永続化
- システム既定テーマの管理者設定
- いかなるテーマでも高齢者向け UI 要件（最小フォント 18px、WCAG 2.1 AA コントラスト比、タッチターゲット 44px）を下回らないバリデーション

### 1.3 スコープ外
- 画面レイアウト自体の差替え（サイドバー位置変更・ページ構造の変更等、WP の「テンプレート」に相当する概念）
- 言語・タイムゾーン等の一般的なユーザー設定（別途 `user_preferences` テーブルで扱う）
- 外部テーマストア・外部からのテーマパッケージ取込

### 1.4 用語定義
| 用語 | 定義 |
|---|---|
| テーマ（Theme） | 配色・書体・角丸・密度・セマンティックトークンの集合体を定義した JSON |
| テーマ定義（Theme Definition） | テーマの実体となる JSON スキーマ |
| プリセットテーマ（Builtin Theme） | システムに組込まれ、マイグレーションシードで投入される削除不可のテーマ |
| カスタムテーマ（Custom Theme） | 管理者が API 経由で登録・編集・削除できるテーマ |
| 有効テーマ（Effective Theme） | ログインユーザーに最終的に適用されるテーマ（解決後） |
| セマンティックトークン | `bg.page` / `text.primary` など、役割を示す色名トークン |

---

## 2. アーキテクチャ

### 2.1 全体構成
```
┌───────────────────────────────────────────────┐
│  DB                                           │
│  ┌───────────┐   ┌──────────────────┐          │
│  │ themes    │   │ user_preferences │          │
│  └─────┬─────┘   └────────┬─────────┘          │
│        │                  │                    │
└────────┼──────────────────┼────────────────────┘
         │                  │
┌────────┼──────────────────┼────────────────────┐
│  Backend (FastAPI)                             │
│  ┌─────────────────┐  ┌─────────────────────┐  │
│  │ /themes API     │  │ /users/me/preferences│  │
│  │ /admin/themes   │  │                      │  │
│  └─────────────────┘  └─────────────────────┘  │
└────────┬─────────────────────────┬─────────────┘
         │                         │
┌────────┼─────────────────────────┼─────────────┐
│  Frontend (React + Chakra v3)                  │
│  ┌─────────────────────────────────────────┐   │
│  │ ThemeProvider                           │   │
│  │  - fetch themes / user prefs            │   │
│  │  - resolve effective theme              │   │
│  │  - createSystem() を動的構築             │   │
│  │  - ChakraProvider に注入                 │   │
│  └─────────────────────────────────────────┘   │
└────────────────────────────────────────────────┘
```

### 2.2 適用優先順位
有効テーマは以下の順で解決される。

1. **ユーザー設定**（`user_preferences.theme_id`）— ログインユーザー固有
2. **システム既定**（`system_settings.default_theme_id`）— 管理者設定
3. **フォールバック**（`standard`）— 上記が解決不能な場合

将来、事業所（テナント）スコープが導入された際は「ユーザー > 事業所 > システム」の順に拡張する。

---

## 3. テーマ定義（Theme Definition）

### 3.1 JSON スキーマ
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ThemeDefinition",
  "type": "object",
  "required": ["schema_version", "id", "name", "colors", "fonts", "radii", "density"],
  "properties": {
    "schema_version": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "pattern": "^[a-z0-9_-]{2,40}$" },
    "name": { "type": "string", "maxLength": 60 },
    "description": { "type": "string", "maxLength": 240 },
    "author": { "type": "string", "maxLength": 60 },
    "colors": {
      "type": "object",
      "required": ["brand", "semantic", "neutral"],
      "properties": {
        "brand": {
          "type": "object",
          "description": "ブランドカラー 50-900 スケール",
          "patternProperties": {
            "^(50|100|200|300|400|500|600|700|800|900)$": {
              "type": "string", "pattern": "^#[0-9a-fA-F]{6}$"
            }
          }
        },
        "semantic": {
          "type": "object",
          "required": ["success", "danger", "warn", "info"],
          "properties": {
            "success": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
            "danger":  { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
            "warn":    { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
            "info":    { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" }
          }
        },
        "neutral": {
          "type": "object",
          "description": "背景・テキスト等の中立色 50-900 スケール"
        }
      }
    },
    "semanticTokens": {
      "type": "object",
      "description": "Chakra semantic tokens に写像される役割名→色参照",
      "properties": {
        "bg.page":        { "type": "string" },
        "bg.card":        { "type": "string" },
        "bg.subtle":      { "type": "string" },
        "text.primary":   { "type": "string" },
        "text.secondary": { "type": "string" },
        "text.onBrand":   { "type": "string" },
        "border.default": { "type": "string" },
        "border.focus":   { "type": "string" }
      }
    },
    "fonts": {
      "type": "object",
      "required": ["body", "heading"],
      "properties": {
        "body":    { "type": "string" },
        "heading": { "type": "string" },
        "mono":    { "type": "string" },
        "baseSizePx": {
          "type": "integer", "minimum": 18,
          "description": "本文基準サイズ。18 未満は不可（高齢者UI制約）"
        }
      }
    },
    "radii": {
      "type": "object",
      "properties": {
        "sm": { "type": "string" },
        "md": { "type": "string" },
        "lg": { "type": "string" },
        "full": { "type": "string" }
      }
    },
    "density": {
      "type": "string", "enum": ["compact", "comfortable", "spacious"],
      "description": "余白密度。compact でもタッチターゲット 44px は維持"
    },
    "meta": {
      "type": "object",
      "properties": {
        "previewImageUrl": { "type": "string", "format": "uri" },
        "tags": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

### 3.2 サーバ側バリデーション要件
テーマ登録・更新時に以下をすべて満たすこと。違反時は `422 Unprocessable Entity`。

| チェック項目 | 条件 | 根拠 |
|---|---|---|
| スキーマ適合 | 上記 JSON スキーマに適合 | 型安全性 |
| 本文フォントサイズ | `fonts.baseSizePx ≥ 18` | `elderly_ui_ux_guidelines.md` §2.1 |
| コントラスト比（本文） | `text.primary` vs `bg.page` ≥ 4.5:1 | WCAG 2.1 AA |
| コントラスト比（ブランド） | `text.onBrand` vs `colors.brand.500` ≥ 4.5:1 | WCAG 2.1 AA |
| コントラスト比（境界） | `border.focus` vs `bg.page` ≥ 3:1 | WCAG 2.1 AA (非テキスト要素) |
| カラーパレット網羅 | `brand` に 500 を含む | 必須トークン |
| ID 重複 | 同じ `id` の既存テーマがない | 一意性 |

コントラスト比計算には WCAG 2.1 相対輝度式を用いる。実装は `backend/app/services/theme_validator.py` に配置予定。

---

## 4. プリセットテーマ（初期搭載）

マイグレーションシードで投入される。`themes.is_builtin=true` かつ削除・編集不可（管理者は有効/無効のみ切替可能）。

| id | name | 用途 | 特徴 |
|---|---|---|---|
| `standard` | スタンダード | 既定 | 現行 `theme.ts` 相当。青系ブランド。システムフォールバック |
| `high-contrast` | ハイコントラスト | 弱視・高齢者視認性重視 | 黒白主体、border 太め、コントラスト比 ≥ 7:1 |
| `warm` | 温もり | 居宅介護の温かみ表現 | 橙系ブランド、クリーム背景 |
| `calm` | おだやか | 長時間閲覧用 | 低彩度・緑系、余白広め |

将来拡張:
- 季節テーマ（春・夏・秋・冬）— タグ `season` でカテゴリ化
- 事業所ブランドテーマ — 事業所固有のロゴ・ブランドカラー適用（別フェーズ）

---

## 5. 適用フロー

### 5.1 起動〜ログイン〜切替
```
[ブラウザ起動]
    │
    ├─ (未ログイン) ──→ GET /api/v1/themes/public/default
    │                   → システム既定テーマ取得
    │                   → ChakraProvider に適用
    │
    ├─ [ログイン完了]
    │      │
    │      ├─ GET /api/v1/users/me/preferences
    │      │   → theme_id 取得
    │      │
    │      ├─ GET /api/v1/themes/{theme_id}
    │      │   → 定義取得（React Query でキャッシュ）
    │      │
    │      └─ ThemeProvider が createSystem() を再構築 → Chakra へ再注入
    │
    └─ [ユーザーがテーマを変更]
           │
           ├─ PUT /api/v1/users/me/preferences { "theme_id": "..." }
           ├─ React Query invalidation → 再フェッチ
           └─ ChakraProvider 再レンダリング（全画面に即時反映）
```

### 5.2 切替時の挙動
- 切替は**即時反映**（リロード不要）
- 切替中は前テーマを維持（フリッカー回避のため適用は原子的に行う）
- 切替成功時に画面右上にトースト通知（本文 18px 以上）
- 切替失敗時（ネットワーク等）は前テーマにロールバックし、エラートースト表示

---

## 6. データモデル（概要）

詳細定義は `database_schema_design.md` §3.20 / §3.21 を参照。

### 6.1 `themes` テーブル
- `id UUID PK`
- `theme_key VARCHAR(40) UNIQUE` — URL 安全な識別子
- `name VARCHAR(60)`
- `description TEXT`
- `definition JSONB` — §3.1 のスキーマに準拠
- `is_builtin BOOLEAN` — 組込みか
- `is_active BOOLEAN` — 一覧で選択可能か
- `created_by UUID FK users(id) NULL` — 組込みは NULL
- 監査カラム（`created_at`, `updated_at`）

### 6.2 `user_preferences` テーブル
汎用 key-value 形式（将来の言語・通知設定等も同テーブルで扱う）。

- `id UUID PK`
- `user_id UUID FK users(id) ON DELETE CASCADE`
- `preference_key VARCHAR(60)` — 例: `theme_id`, `locale`, `notification_channel`
- `preference_value JSONB`
- `UNIQUE(user_id, preference_key)`
- 監査カラム

### 6.3 `system_settings` への追加キー
- `default_theme_id` — プリセットまたはカスタムテーマの `theme_key`。初期値 `"standard"`

---

## 7. API（概要）

詳細リクエスト/レスポンスは `api_specification.md` §16 を参照。

| メソッド | パス | 認可 | 用途 |
|---|---|---|---|
| GET | `/api/v1/themes/public/default` | 不要 | 未ログイン用の既定テーマ取得 |
| GET | `/api/v1/themes` | 認証済 | 有効な全テーマ一覧 |
| GET | `/api/v1/themes/{theme_key}` | 認証済 | テーマ詳細 |
| GET | `/api/v1/users/me/preferences` | 認証済 | 自分の設定取得（`theme_id` 含む） |
| PUT | `/api/v1/users/me/preferences` | 認証済 | 自分の設定更新 |
| POST | `/api/v1/admin/themes` | system_admin | カスタムテーマ登録 |
| PUT | `/api/v1/admin/themes/{theme_key}` | system_admin | カスタムテーマ更新（組込みは name/description/is_active のみ可） |
| DELETE | `/api/v1/admin/themes/{theme_key}` | system_admin | カスタムテーマ削除（組込みは不可、409） |
| PUT | `/api/v1/admin/settings/default_theme_id` | system_admin | システム既定テーマ変更 |

---

## 8. フロントエンド実装方針

### 8.1 ThemeProvider
`frontend/src/theme/ThemeProvider.tsx` を新設し、以下を担う:

1. 未ログイン時は `/themes/public/default` を取得
2. ログイン後は `useQuery(['preferences','me'])` と `useQuery(['themes', themeId])` を並列実行
3. 取得した定義を Chakra v3 `createSystem(defaultConfig, defineConfig({ theme: ... }))` で動的構築
4. `ChakraProvider value={system}` を子孫に提供

### 8.2 `useUIStore`（Zustand）拡張
既存 `UIState` を以下に置換（`frontend_implementation_plan.md` §2.2.1 で反映）:

```typescript
interface UIState {
  isLoading: boolean
  notifications: Notification[]
  themeId: string | null          // 追加: 有効テーマID（null のときは未ロード）
  pendingThemeId: string | null   // 追加: 切替中の楽観的反映用
  fontSize: 'normal' | 'large' | 'x-large'
  setThemeId: (id: string) => void
  setFontSize: (size: string) => void
}
```

`theme: 'light' | 'dark' | 'high-contrast'` は廃止し、テーマ ID に一本化する（互換性マイグレーションは 8.4 参照）。

### 8.3 テーマ選択 UI
- ProfilePage に「表示テーマ」セクションを追加（プレビュー画像カード、ラジオグループ）
- 管理者には Admin に「テーマ管理」画面（§12 参照）

### 8.4 互換性
- 既存の `frontend/src/theme.ts` は `standard` プリセットの定義を書き出すだけの役割に縮小
- LocalStorage に残る旧 `theme: light|dark|high-contrast` 値は起動時に一度だけマッピング（`dark` は当面未対応として `standard` にフォールバック、`high-contrast` は `high-contrast` プリセットへ）し、以後は API 側の値を正とする

---

## 9. アクセシビリティ制約

いかなるテーマでも下記を下回ってはならない。違反はサーバ側バリデーション（§3.2）で 422、フロント側 `ThemeProvider` でも二重チェックし不合格時はフォールバックテーマを使用する。

| 項目 | 基準 | 出典 |
|---|---|---|
| 本文フォントサイズ | ≥ 18px | `elderly_ui_ux_guidelines.md` §2.1 |
| 本文色対背景コントラスト | ≥ 4.5:1 | WCAG 2.1 AA |
| 非テキスト UI 要素コントラスト | ≥ 3:1 | WCAG 2.1 AA |
| タッチターゲット最小サイズ | 44×44 px | `elderly_ui_ux_guidelines.md` §3.1 |
| フォーカスリング | 2px 以上、コントラスト比 3:1 以上 | WCAG 2.1 AA |

---

## 10. 管理者機能

詳細は `admin_management_specification.md` §12 を参照。

- テーマ一覧表示（組込み/カスタム、有効/無効フィルタ）
- カスタムテーマの新規登録（JSON 直接入力 + プレビュー）
- カスタムテーマの編集・削除
- 組込みテーマの有効/無効切替（削除は不可）
- システム既定テーマの指定
- すべての変更は `audit_logs` に記録

---

## 11. マイグレーション・シード

### 11.1 テーブル作成
Alembic マイグレーションで `themes` / `user_preferences` を作成（`database_schema_design.md` §3.20 / §3.21 の DDL を使用）。

### 11.2 プリセット投入
Alembic データマイグレーション `seed_builtin_themes` で §4 の 4 テーマを投入。`theme_key` をキーに冪等 (`INSERT ... ON CONFLICT DO UPDATE`) とし、組込みテーマのアップデートを将来のデプロイで反映できるようにする。

### 11.3 既定値投入
`system_settings` に `default_theme_id = "standard"` を `INSERT ON CONFLICT DO NOTHING` で投入する。

---

## 12. 非機能要件

| 項目 | 要件 |
|---|---|
| 応答時間 | `/themes`, `/themes/{id}`, `/users/me/preferences` は P95 < 150ms |
| キャッシュ | フロントは React Query で 5 分キャッシュ、管理者更新時は `invalidateQueries` |
| サイズ上限 | `themes.definition` JSONB は 16KB まで |
| セキュリティ | カスタムテーマの文字列フィールドはサーバ側でサニタイズ（HTML/スクリプト混入防止） |
| 監査 | テーマ登録・更新・削除・既定変更は `audit_logs` に記録 |
| 国際化 | テーマ `name`, `description` は現状日本語単一言語。将来の多言語化余地を残すため `{ "ja": "...", "en": "..." }` 形式の JSON を許容（バリデーションは将来拡張） |

---

## 13. 実装優先順位（参考）

| Phase | 内容 |
|---|---|
| 1 | DB テーブル作成、プリセット投入、公開既定テーマ API、`ThemeProvider` のフロント導入 |
| 2 | ユーザー設定 API、ProfilePage のテーマ選択 UI |
| 3 | 管理者テーマ CRUD、Admin 管理画面、システム既定の管理者変更 UI |
| 4 | プレビュー画像対応、季節テーマ、将来の事業所スコープ対応 |

実装コードは別タスクで着手する。本書は仕様書レベルの定義である。
