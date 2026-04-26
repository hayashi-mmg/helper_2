# テーマシステム 実装・テスト計画書

## 文書管理情報
- **文書番号**: THEME-IMPL-001
- **版数**: 1.0
- **作成日**: 2026年4月22日
- **最終更新日**: 2026年4月22日
- **前提仕様書**:
  - [`docs/theme_system_specification.md`](./theme_system_specification.md)(THEME-HHS-001)
  - [`docs/database_schema_design.md`](./database_schema_design.md) §3.20 / §3.21 / §3.22
  - [`docs/api_specification.md`](./api_specification.md) §16
  - [`docs/frontend_implementation_plan.md`](./frontend_implementation_plan.md) §3.1.0
  - [`docs/admin_management_specification.md`](./admin_management_specification.md) §12

---

## 1. 概要

### 1.1 目的
テーマシステム仕様書(THEME-HHS-001)に基づき、バックエンド・フロントエンド・テストを段階的に実装する。高齢者 UI 要件を満たした上で、ユーザー/管理者のテーマ切替機構を提供する。

### 1.2 スコープ
- バックエンド: DB マイグレーション、モデル、スキーマ、サービス、API、シード
- フロントエンド: 型定義、API クライアント、`ThemeProvider`、プリセット、ユーザー UI、管理者 UI
- テスト: バックエンド pytest(単体+結合)、フロントエンド Vitest(単体/コンポーネント)、Playwright(E2E)
- マイグレーション手順と本番リリース手順

### 1.3 スコープ外
- 事業所(テナント)スコープ(将来フェーズ)
- 多言語化対応(スキーマ拡張のみ残し実装は別フェーズ)
- 外部テーマストア連携

---

## 2. フェーズ構成とマイルストーン

| Phase | 名称 | 期間目安 | 成果物 |
|---|---|---|---|
| P1 | バックエンド基盤 | 3 日 | `themes` / `user_preferences` テーブル、モデル、プリセットシード |
| P2 | バックエンドバリデータ | 2 日 | `ThemeValidator` サービス、単体テスト |
| P3 | バックエンド API | 3 日 | §16 の 9 エンドポイント、結合テスト |
| P4 | フロントエンド基盤 | 2 日 | 型、API クライアント、プリセット定数、`buildSystem` |
| P5 | フロントエンド ThemeProvider | 2 日 | `ThemeProvider.tsx`、`uiStore` 更新、起動フロー統合 |
| P6 | ユーザー UI | 2 日 | ProfilePage テーマ選択セクション |
| P7 | 管理者 UI | 3 日 | `/admin/themes` 一覧・登録・編集画面 |
| P8 | E2E + 受入検証 | 2 日 | Playwright シナリオ、アクセシビリティ自動検査 |
| P9 | リリース | 1 日 | ステージング検証、本番デプロイ手順 |

**総期間目安**: 2.5〜3 週間(1 名想定)。P1〜P3 と P4 は一部並行可。

---

## 3. バックエンド実装計画

### 3.1 ディレクトリ配置
```
backend/
├── alembic/versions/
│   └── e4f5a6b7c8d9_add_theme_system.py          # (P1)
├── app/
│   ├── db/models/
│   │   ├── theme.py                              # (P1) Theme モデル
│   │   └── user_preference.py                    # (P1) UserPreference モデル
│   ├── schemas/
│   │   ├── theme.py                              # (P1/P2) ThemeDefinition, ThemeRead, ThemeCreate, ThemeUpdate
│   │   └── user_preference.py                    # (P1) UserPreferencesRead, UserPreferencesUpdate
│   ├── services/
│   │   ├── theme_validator.py                    # (P2) WCAG + schema
│   │   ├── theme_service.py                      # (P3) CRUD
│   │   └── preferences_service.py                # (P3) get/set
│   ├── crud/
│   │   ├── theme.py                              # (P3) SQL 操作
│   │   └── user_preference.py                    # (P3) SQL 操作
│   └── api/v1/endpoints/
│       ├── themes.py                             # (P3) 公開 + 認証 + admin エンドポイント
│       └── user_preferences.py                   # (P3) /users/me/preferences
└── tests/
    ├── test_theme_validator.py                   # (P2)
    ├── test_themes_api.py                        # (P3)
    ├── test_user_preferences_api.py              # (P3)
    └── test_admin_themes_api.py                  # (P3)
```

既存パターンへの準拠:
- モデルは `app/db/models/system_setting.py` と同様の命名・UUID 主キー・監査カラム
- API は `app/api/v1/endpoints/admin_system.py` の list/get/update 構造を踏襲
- テストは `tests/conftest.py` の `AsyncClient` フィクスチャを再利用

### 3.2 P1: DB マイグレーション、モデル、シード

#### 3.2.1 Alembic マイグレーション
`alembic/versions/e4f5a6b7c8d9_add_theme_system.py`:

- upgrade:
  1. `themes` テーブル作成(`database_schema_design.md` §3.20 の DDL)
  2. `user_preferences` テーブル作成(§3.21)
  3. プリセット 4 テーマの `INSERT ... ON CONFLICT (theme_key) DO UPDATE SET definition=EXCLUDED.definition, updated_at=CURRENT_TIMESTAMP`
  4. `system_settings` に `default_theme_id = "standard"` を `INSERT ... ON CONFLICT DO NOTHING`
- downgrade: 逆順で DROP(`system_settings.default_theme_id` の DELETE 含む)

プリセット定義の実体は `app/services/theme_presets.py` に Python dict として置き、マイグレーションから import して使用。フロントエンドとは値を二重管理することになるが、Single Source of Truth として JSON 別ファイル(`shared/presets/*.json`)を作成し、バックエンド・フロントエンド双方が import する案も検討(設定次第で任意)。

#### 3.2.2 SQLAlchemy モデル

`app/db/models/theme.py`:
```python
from sqlalchemy import String, Boolean, ForeignKey, DateTime, func, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import uuid

class Theme(Base):
    __tablename__ = "themes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    theme_key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        CheckConstraint("theme_key ~ '^[a-z0-9_-]{2,40}$'", name="ck_themes_key_format"),
    )
```

`app/db/models/user_preference.py`: `(user_id, preference_key)` UNIQUE、JSONB `preference_value`。

`app/db/models/__init__.py` に `Theme`、`UserPreference` を追加し、`conftest.py` の TRUNCATE リストにも追加。

#### 3.2.3 Pydantic スキーマ

`app/schemas/theme.py`:
- `ThemeDefinition`: `theme_system_specification.md` §3.1 と同形式の strict model(`schema_version: Literal["1.0"]`、`colors`, `fonts`, `radii`, `density: Literal["compact","comfortable","spacious"]` 等)
- `ThemeRead`: DB レコード → 公開用
- `ThemeSummary`: 一覧用(definition を除外、`preview_image_url` を含む)
- `ThemeCreate`: admin 入力用
- `ThemeUpdate`: admin 入力用(全項目 Optional、組込みは name/description/is_active のみ適用)

`app/schemas/user_preference.py`:
- `UserPreferencesRead`: `theme_id: str | None`, `font_size_override: str | None`
- `UserPreferencesUpdate`: 部分更新用

### 3.3 P2: ThemeValidator

`app/services/theme_validator.py`:

```python
def validate_theme_definition(definition: dict) -> None:
    """
    raises HTTPException(422) on failure with {detail: [{field, code, message}]}
    """
    # 1) Pydantic: ThemeDefinition(**definition)
    # 2) baseSizePx >= 18
    # 3) contrast(text.primary, bg.page) >= 4.5
    # 4) contrast(text.onBrand, colors.brand.500) >= 4.5
    # 5) contrast(border.focus, bg.page) >= 3
```

コントラスト比:
- WCAG 2.1 相対輝度式を `_relative_luminance(rgb)` で実装
- `contrast_ratio(a, b) = (max(La, Lb) + 0.05) / (min(La, Lb) + 0.05)`
- `#RRGGBB` → RGB パースと sRGB 補正

`semanticTokens` は `{colors.neutral.900}` 形式を受けるため、`resolve_token(ref, definition)` で実値を取得してからコントラストを計算する。未解決トークン(参照先不在)は `unresolved_token_reference` エラーコードで 422。

### 3.4 P3: API エンドポイント

#### 3.4.1 `/themes/public/default`(未認証)
`app/api/v1/endpoints/themes.py`:
```python
@router.get("/themes/public/default", response_model=ThemeRead)
async def get_public_default_theme(db: AsyncSession = Depends(get_db)):
    theme_key = await get_system_setting(db, "default_theme_id") or "standard"
    theme = await crud_theme.get_by_key(db, theme_key)
    if not theme or not theme.is_active:
        theme = await crud_theme.get_by_key(db, "standard")
    return ThemeRead.model_validate(theme)
```
レート制限: 既存の未認証用ミドルウェアを流用(100 req/h)。CDN キャッシュヘッダ(`Cache-Control: public, max-age=300`)を付与。

#### 3.4.2 認証ユーザー向け
- `GET /themes`: `is_builtin`/`is_active` クエリで絞込、`ThemeSummary[]`
- `GET /themes/{theme_key}`: `ThemeRead`
- `GET /users/me/preferences`: 未設定は `null` を返す(`app/api/v1/endpoints/user_preferences.py`)
- `PUT /users/me/preferences`: 部分更新。`theme_id` 指定時は `themes` に存在かつ `is_active=true` を確認し、UPSERT

#### 3.4.3 管理者向け
- `POST /admin/themes`: `ThemeCreate` → `ThemeValidator` → INSERT。`system_admin` 権限ガード(既存 `require_system_admin` デコレータ)
- `PUT /admin/themes/{theme_key}`: 組込みは `name`/`description`/`is_active` のみ。`definition` 変更時は再バリデーション
- `DELETE /admin/themes/{theme_key}`: `is_builtin=false` かつ `default_theme_id` に指定されていないこと。違反時 409
- `PUT /admin/settings/default_theme_id`: 既存 `admin_system.update_setting` を再利用。値検証で `themes.theme_key` 存在 + `is_active` を確認
- すべて `audit_logs` 記録(既存 `AuditLogMiddleware` or デコレータ)

#### 3.4.4 エラーコード一覧
| code | HTTP | 場面 |
|---|---|---|
| `THEME_NOT_FOUND` | 404 | 存在しない theme_key |
| `THEME_INACTIVE` | 404 | `is_active=false` を一般ユーザーが参照/設定 |
| `THEME_BUILTIN_IMMUTABLE` | 409 | 組込みの `definition`/`theme_key` 変更試行 |
| `THEME_BUILTIN_DELETE_FORBIDDEN` | 409 | 組込み削除試行 |
| `THEME_IN_USE_AS_DEFAULT` | 409 | 既定指定中の削除 |
| `THEME_KEY_CONFLICT` | 409 | 一意制約違反 |
| `THEME_VALIDATION_FAILED` | 422 | スキーマ/コントラスト/フォントサイズ違反 |

---

## 4. フロントエンド実装計画

### 4.1 ディレクトリ配置
```
frontend/src/
├── api/
│   ├── themes.ts                                 # (P4)
│   └── preferences.ts                            # (P4)
├── theme/
│   ├── index.ts                                  # 既存(standard 相当の値を preset として保持)
│   ├── buildSystem.ts                            # (P4) ThemeDefinition → Chakra system
│   ├── ThemeProvider.tsx                         # (P5)
│   ├── validateThemeDefinition.ts                # (P4) サーバと同ロジック(最低限)
│   └── presets/
│       ├── standard.ts                           # (P4)
│       ├── highContrast.ts                       # (P4)
│       ├── warm.ts                               # (P4)
│       └── calm.ts                               # (P4)
├── types/
│   ├── theme.ts                                  # (P4) ThemeDefinition, ThemeRead, ThemeSummary
│   └── preferences.ts                            # (P4)
├── stores/
│   └── uiStore.ts                                # (P5) themeId/pendingThemeId/setThemeId 拡張
├── pages/
│   ├── ProfilePage.tsx                           # (P6) テーマセクション追加
│   ├── AdminThemesPage.tsx                       # (P7) 一覧
│   └── AdminThemeEditorPage.tsx                  # (P7) 登録/編集
├── components/
│   └── theme/
│       ├── ThemeCard.tsx                         # (P6) プレビューカード
│       ├── ThemeSelector.tsx                     # (P6) ProfilePage 内で使用
│       ├── ThemePreview.tsx                      # (P7) 管理者向け縮小プレビュー
│       └── ContrastBadge.tsx                     # (P7) 比率バッジ
└── __tests__/
    ├── theme/
    │   ├── buildSystem.test.ts                   # (P4)
    │   ├── ThemeProvider.test.tsx                # (P5)
    │   ├── ThemeSelector.test.tsx                # (P6)
    │   └── AdminThemeEditor.test.tsx             # (P7)
    └── e2e/
        ├── theme-switch.spec.ts                  # (P8) Playwright
        └── admin-theme-crud.spec.ts              # (P8)
```

### 4.2 P4: 型、API クライアント、プリセット、buildSystem

#### 4.2.1 types/theme.ts
```typescript
export interface ThemeDefinition {
  schema_version: "1.0"
  id: string
  name: string
  description?: string
  colors: { brand: Record<string,string>; semantic: { success: string; danger: string; warn: string; info: string }; neutral: Record<string,string> }
  semanticTokens?: Partial<Record<"bg.page"|"bg.card"|"bg.subtle"|"text.primary"|"text.secondary"|"text.onBrand"|"border.default"|"border.focus", string>>
  fonts: { body: string; heading: string; mono?: string; baseSizePx: number }
  radii: { sm?: string; md?: string; lg?: string; full?: string }
  density: "compact"|"comfortable"|"spacious"
  meta?: { previewImageUrl?: string; tags?: string[] }
}
export interface ThemeRead {
  theme_key: string
  name: string
  description?: string
  definition: ThemeDefinition
  is_builtin: boolean
  is_active: boolean
}
export interface ThemeSummary {
  theme_key: string; name: string; description?: string; is_builtin: boolean; is_active: boolean; preview_image_url?: string
}
```

#### 4.2.2 API クライアント
`api/themes.ts`:
```typescript
export const themesApi = {
  getPublicDefault: () => client.get<ThemeRead>("/themes/public/default"),
  list: (params?: { is_builtin?: boolean; is_active?: boolean }) => client.get<{themes: ThemeSummary[]}>("/themes", { params }),
  get: (key: string) => client.get<ThemeRead>(`/themes/${key}`),
  // admin
  create: (body: Omit<ThemeRead, "is_builtin">) => client.post<ThemeRead>("/admin/themes", body),
  update: (key: string, body: Partial<ThemeRead>) => client.put<ThemeRead>(`/admin/themes/${key}`, body),
  remove: (key: string) => client.delete(`/admin/themes/${key}`),
  setDefault: (themeKey: string) => client.put(`/admin/settings/default_theme_id`, { value: themeKey }),
}
```

`api/preferences.ts`:
```typescript
export const preferencesApi = {
  getMine: () => client.get<UserPreferencesRead>("/users/me/preferences"),
  updateMine: (body: UserPreferencesUpdate) => client.put<UserPreferencesRead>("/users/me/preferences", body),
}
```

#### 4.2.3 プリセット
`theme/presets/standard.ts` ほか、`ThemeDefinition` リテラル。本ファイルはフロントエンド単体での起動時フォールバック専用で、正式な値は DB を優先する。

#### 4.2.4 buildSystem
`theme/buildSystem.ts`: `ThemeDefinition` を受け取り `@chakra-ui/react` v3 の `createSystem(defaultConfig, defineConfig({...}))` を返す。マッピング規則は `frontend_implementation_plan.md` §3.1.0 の表に従う。

### 4.3 P5: ThemeProvider と uiStore

- `ThemeProvider.tsx`: `frontend_implementation_plan.md` §3.1.0 のコードをそのまま実装
- `stores/uiStore.ts`: `themeId: string | null`、`pendingThemeId`、`setThemeId` を追加。旧 `theme` フィールドの LocalStorage 値があれば起動時に一度だけマッピング(`high-contrast` は同名プリセットへ、`dark`/`light` は `standard` へ)
- `main.tsx`: `<ThemeProvider>` で `<App>` をラップ。`QueryClientProvider` と `AuthProvider` の内側、`ChakraProvider` の外側になるように配置

### 4.4 P6: ProfilePage テーマ選択セクション

`pages/ProfilePage.tsx` に `<section aria-labelledby="theme-heading">` を追加:
- 見出し「表示テーマ」(h2、fontSize `xl`)
- `ThemeSelector` コンポーネント: `themesApi.list()` → ラジオグループで `ThemeCard` を並列表示
- 選択変更時は `preferencesApi.updateMine({ theme_id })` + React Query `invalidateQueries(['preferences','me'])` + `invalidateQueries(['themes', newId])`
- 楽観的更新: `pendingThemeId` を設定し、成功時 `themeId` に反映、失敗時ロールバック + トースト
- アクセシビリティ: ラジオボタン 44×44 px 以上、キーボード操作可(Arrow キーで選択移動)、`aria-describedby` で概要説明

### 4.5 P7: 管理者 UI

#### 4.5.1 AdminThemesPage(`/admin/themes`)
- フィルタ: 組込み/カスタム、有効/無効
- 表: theme_key, name, is_builtin, is_active, updated_at, 操作(編集/削除/有効切替/既定設定)
- 「新規登録」ボタン → `AdminThemeEditorPage(new)` へ遷移
- 現在の既定テーマをヘッダに表示(クリックで変更モーダル)

#### 4.5.2 AdminThemeEditorPage(`/admin/themes/new` / `/admin/themes/:key/edit`)
- 左: JSON エディタ(Monaco Editor もしくは textarea + `JSON.stringify(null, 2)`)
- 右: 縮小プレビュー(`<ThemePreview>` が `buildSystem` + `ChakraProvider` でミニ UI を描画)
- 下部: `ContrastBadge` で本文・ブランド・境界のコントラスト比をリアルタイム表示
- 保存ボタン押下時:
  - クライアント側で `validateThemeDefinition()` を実行し明らかな不備を即表示
  - 通過したらサーバへ POST/PUT。サーバの 422 詳細を JSON エディタのフィールド位置にマーク
- 組込みテーマ編集時は `definition` 欄を readonly 化、`name`/`description`/`is_active` のみ編集可

### 4.6 ルーティング
`App.tsx` のルート定義:
```tsx
<Route path="/admin/themes" element={<RequireAdmin><AdminThemesPage /></RequireAdmin>} />
<Route path="/admin/themes/new" element={<RequireAdmin><AdminThemeEditorPage mode="new" /></RequireAdmin>} />
<Route path="/admin/themes/:themeKey/edit" element={<RequireAdmin><AdminThemeEditorPage mode="edit" /></RequireAdmin>} />
```

---

## 5. テスト計画

### 5.1 テストピラミッド
```
         ┌──────────┐
         │  E2E (P8)│   ~6 シナリオ(Playwright)
         ├──────────┤
         │結合 (P3) │   ~30 テスト(pytest + AsyncClient)
         ├──────────┤
         │単体 (P2,P4,P5) │   ~60+ テスト
         └──────────┘
```

### 5.2 バックエンドテスト

#### 5.2.1 単体: `tests/test_theme_validator.py`
対象: `services/theme_validator.py`。
- 正常系: 各プリセット 4 種が合格する
- スキーマエラー: `schema_version != "1.0"` / 必須欠落 / 不正な `density`
- フォントサイズ: `baseSizePx = 17` は 422
- コントラスト: 既知の組合せで計算結果をアサート(white/black = 21.0 等)
- セマンティックトークン参照: 未解決参照(`{colors.xxx.999}`)は 422
- ブランド/境界のコントラスト個別チェック

境界値表:
| 項目 | 失敗ケース | 成功ケース |
|---|---|---|
| baseSizePx | 17 | 18 |
| text vs bg コントラスト | 4.49 | 4.50 |
| onBrand vs brand.500 | 4.49 | 4.50 |
| border.focus vs bg.page | 2.99 | 3.00 |

#### 5.2.2 結合: `tests/test_themes_api.py`
対象: 公開+認証 API。フィクスチャは既存 `client`(AsyncClient) と `db` を使用。
- `GET /themes/public/default`: 未認証で 200、`standard` が返る
- `GET /themes/public/default`: `default_theme_id` を `warm` に変更すると `warm` が返る
- `GET /themes/public/default`: `default_theme_id` を `is_active=false` のテーマにしてもフォールバックする
- `GET /themes`: 認証必須 401、認証付きで 4 プリセット返る、`is_builtin=false` フィルタで空配列
- `GET /themes/{key}`: 存在 200、不存在 404、非アクティブ 404
- `GET /users/me/preferences`: 未設定時 `theme_id=null`
- `PUT /users/me/preferences`: 既存キー更新、新規キー作成、存在しない `theme_id` は 422、非アクティブ `theme_id` は 422

#### 5.2.3 結合: `tests/test_admin_themes_api.py`
- 権限: 非管理者は 403
- POST: 正常登録 201、重複 409、バリデーション失敗 422
- PUT(カスタム): 正常更新、`definition` 変更時の再バリデーション
- PUT(組込み): `name` 更新 200、`definition` 変更 409、`theme_key` 変更 409
- DELETE(カスタム): 200、既定指定中は 409
- DELETE(組込み): 409
- `PUT /admin/settings/default_theme_id`: 存在しないキー 422、非アクティブ 422、成功時 `system_settings` が更新される
- 監査: 各変更が `audit_logs` に 1 レコード追加されていること

### 5.3 フロントエンドテスト

#### 5.3.1 単体: `__tests__/theme/buildSystem.test.ts`
- ThemeDefinition → Chakra `system` への写像検証(tokens.colors.brand.500 が期待値)
- semanticTokens 解決の検証
- baseSizePx が globalCss の font-size に反映される

#### 5.3.2 単体: `__tests__/theme/validateThemeDefinition.test.ts`
- サーバ側 validator と同等のテスト群(フロント側は事前チェック用で厳密性はサーバ優先)

#### 5.3.3 コンポーネント: `__tests__/theme/ThemeProvider.test.tsx`
- 未ログイン: `/themes/public/default` を叩く(MSW でモック)
- ログイン + prefs あり: `/users/me/preferences` と `/themes/{id}` を叩き、Chakra に該当テーマが反映される
- 取得失敗時: `standard` プリセットにフォールバック + コンソール警告

#### 5.3.4 コンポーネント: `__tests__/theme/ThemeSelector.test.tsx`
- ラジオで選択 → `updateMine` が呼ばれる
- 失敗時: トースト表示 + `themeId` がロールバック
- キーボード: ArrowDown/Up で選択移動、Enter で確定

#### 5.3.5 コンポーネント: `__tests__/theme/AdminThemeEditor.test.tsx`
- 新規登録: JSON → 保存 → `themesApi.create` が期待 payload で呼ばれる
- サーバ 422: エラーがフォームにマークされる
- 組込み編集: `definition` 欄が readonly

### 5.4 E2E (Playwright)
`frontend/e2e/` に新設(既存が無ければプロジェクトに `@playwright/test` 導入)。

| シナリオ | 概要 |
|---|---|
| theme-switch | 一般ユーザーでログイン → ProfilePage → テーマ変更 → ヘッダ/ボタン色が変わることを確認 |
| admin-theme-crud | 管理者でログイン → カスタムテーマ登録 → 一覧で確認 → 編集 → 削除 |
| default-theme-change | 管理者で既定テーマ変更 → ログアウト → ログイン画面に新既定が適用 |
| a11y-contrast | 各プリセット適用状態で axe-core を走らせ、WCAG 2.1 AA 違反なしをアサート |
| fallback | `/themes/{key}` で 404 を返すモックを使い、フォールバックが機能 |
| invalid-theme-reject | 管理者 UI で baseSizePx=17 を入れて保存 → サーバ 422 がフォームに表示 |

### 5.5 アクセシビリティ自動検査
- `vitest + axe` のコンポーネントテスト: ThemeSelector、ThemeCard、管理者フォーム
- Playwright シナリオ内で `@axe-core/playwright` により各テーマ適用後のページに対し違反チェック

### 5.6 テスト実行コマンド
```bash
# バックエンド
cd backend && pytest tests/test_theme_validator.py tests/test_themes_api.py tests/test_user_preferences_api.py tests/test_admin_themes_api.py -v

# フロントエンド 単体/コンポーネント
cd frontend && npm run test -- theme/

# フロントエンド E2E
cd frontend && npm run test:e2e -- theme-switch admin-theme-crud
```

CI (GitHub Actions 等) の統合はプロジェクト既存ワークフローに sub-matrix として追加。

---

## 6. リリース手順

### 6.1 ステージング
1. マイグレーション適用(`alembic upgrade head`)
2. プリセット 4 種と `default_theme_id` のシードが DB に存在することを確認
3. 公開エンドポイントを未認証で叩き 200 + `standard` が返ることを確認
4. フロントエンドをビルド・デプロイ
5. 動作確認: 未ログイン、ログイン、ProfilePage 変更、管理者 CRUD、既定変更
6. axe CI で違反なしを確認

### 6.2 本番
1. メンテナンス通知の必要性を判断(ダウンタイムなしマイグレーションのため基本不要)
2. Alembic `upgrade head` 実行(所要 < 1 秒想定、データ件数少数)
3. バックエンド先行デプロイ → フロント後追いデプロイ
4. スモークテスト: `/themes/public/default` が 200 を返すこと、既存ユーザーでログイン後 ProfilePage を開けること
5. ロールバック手順: `alembic downgrade -1` + 旧バージョンの再デプロイ

### 6.3 データ安全性
- `themes` / `user_preferences` は初回マイグレーションで新規作成のみ。既存データへの破壊変更なし
- `system_settings` への `INSERT ... ON CONFLICT DO NOTHING` で既設との衝突を避ける
- ロールバック時、`user_preferences` に格納された `theme_id` は downgrade で失われるため、事前に `pg_dump -t themes -t user_preferences` を取得

---

## 7. リスクと緩和策

| リスク | 影響 | 緩和策 |
|---|---|---|
| Chakra v3 `createSystem` の動的再生成でフリッカー発生 | UX 低下 | `key={themeId}` での再マウントは避け、`system` オブジェクトのみ差替え。過渡状態は `pendingThemeId` で吸収 |
| プリセット定義のバックエンド/フロントエンド二重管理で乖離 | 表示不整合 | プリセット値は常に DB を真として扱う。フロント側プリセットはフォールバック専用で起動時の最短表示用のみ |
| コントラスト比計算の実装バグ | 不正なテーマを登録/拒否してしまう | WCAG 公式サンプル値(white/black 21.0、mid-gray 4.5 近傍)の既知ペアでユニットテストを網羅 |
| 未ログインで `/themes/public/default` が 500 を返す | 起動不能 | ThemeProvider 側で try/catch しフロント `standard` プリセットにフォールバック。エラーは telemetry 送信 |
| 大量カスタムテーマ登録によるサイズ肥大 | DB 肥大 | `definition` サイズ上限 16KB を CHECK で強制、管理画面でも件数上限(例: 50 件)を緩やかに設ける |
| 管理者の誤操作で `default_theme_id` を不正値に設定 | 全ユーザーに影響 | サーバ側バリデーション + 監査ログで復旧可能に。UI 側も選択肢をテーマ一覧から選ばせる(自由入力不可) |

---

## 8. 受入基準(Definition of Done)

- すべての §5 テストが CI で緑
- axe-core で P0/P1 違反なし
- 4 プリセットがマイグレーション後に自動投入され、`/themes` で取得可能
- 一般ユーザーが ProfilePage からテーマを選択し、リロードなしで全画面に反映される
- 管理者がカスタムテーマを登録・編集・削除・既定指定できる
- 組込みテーマの `definition` 編集・削除が 409 で拒否される
- 18px 未満または WCAG 違反のテーマが 422 で拒否される
- 未ログイン画面にシステム既定テーマが適用される
- 監査ログにテーマ関連の変更が全件残る
- ステージングで 6 系統のスモークテストがすべて成功

---

## 9. 実装タスク一覧(進捗追跡用)

### バックエンド
- [ ] B1-1: Alembic マイグレーション作成(`e4f5a6b7c8d9_add_theme_system`)
- [ ] B1-2: `Theme` / `UserPreference` モデル
- [ ] B1-3: `theme_presets.py`(4 種のプリセット JSON)
- [ ] B1-4: Pydantic `ThemeDefinition` / `ThemeRead` / `ThemeCreate` / `ThemeUpdate`
- [ ] B1-5: Pydantic `UserPreferencesRead` / `UserPreferencesUpdate`
- [ ] B2-1: `ThemeValidator.validate_theme_definition`
- [ ] B2-2: コントラスト比ユーティリティ(`_relative_luminance`, `contrast_ratio`)
- [ ] B2-3: `test_theme_validator.py`(正常系+境界値+プリセット往復)
- [ ] B3-1: `crud/theme.py` / `crud/user_preference.py`
- [ ] B3-2: `api/v1/endpoints/themes.py`(公開+認証+admin)
- [ ] B3-3: `api/v1/endpoints/user_preferences.py`
- [ ] B3-4: ルーター登録(`api/v1/__init__.py`)
- [ ] B3-5: `test_themes_api.py`
- [ ] B3-6: `test_user_preferences_api.py`
- [ ] B3-7: `test_admin_themes_api.py`
- [ ] B3-8: 監査ログフック組込

### フロントエンド
- [ ] F4-1: `types/theme.ts`, `types/preferences.ts`
- [ ] F4-2: `api/themes.ts`, `api/preferences.ts`
- [ ] F4-3: `theme/presets/*.ts`(4 種)
- [ ] F4-4: `theme/buildSystem.ts`
- [ ] F4-5: `theme/validateThemeDefinition.ts`
- [ ] F4-6: `buildSystem.test.ts`
- [ ] F5-1: `theme/ThemeProvider.tsx`
- [ ] F5-2: `stores/uiStore.ts` 更新、LocalStorage 互換処理
- [ ] F5-3: `main.tsx` で Provider 組込
- [ ] F5-4: `ThemeProvider.test.tsx`
- [ ] F6-1: `components/theme/ThemeCard.tsx`
- [ ] F6-2: `components/theme/ThemeSelector.tsx`
- [ ] F6-3: `ProfilePage.tsx` テーマセクション追加
- [ ] F6-4: `ThemeSelector.test.tsx`
- [ ] F7-1: `pages/AdminThemesPage.tsx`
- [ ] F7-2: `pages/AdminThemeEditorPage.tsx`
- [ ] F7-3: `components/theme/ThemePreview.tsx`
- [ ] F7-4: `components/theme/ContrastBadge.tsx`
- [ ] F7-5: ルーティング追加(`App.tsx`)
- [ ] F7-6: `AdminThemeEditor.test.tsx`
- [ ] F8-1: Playwright シナリオ 6 本
- [ ] F8-2: axe-core 統合

### リリース
- [ ] R-1: ステージング適用と 6 スモーク実施
- [ ] R-2: 本番適用
- [ ] R-3: リリースノート記載(管理者向け運用手順含む)

**文書終了**
