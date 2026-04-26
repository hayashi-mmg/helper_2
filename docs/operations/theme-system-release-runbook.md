# テーマシステム リリース運用手順書

## 文書管理情報
- **文書番号**: THEME-OPS-001
- **版数**: 1.0
- **作成日**: 2026年4月22日
- **最終更新日**: 2026年4月22日
- **対象読者**: システム管理者 / DevOps 担当者
- **関連文書**:
  - [`docs/theme_system_specification.md`](../theme_system_specification.md)
  - [`docs/theme_system_implementation_plan.md`](../theme_system_implementation_plan.md) §6
  - [`docs/operations/deployment-guide.md`](./deployment-guide.md)

---

## 1. 目的と対象

本手順書は、テーマシステム(THEME-HHS-001)を**既存稼働システムに追加投入**する際の操作手順を定義する。新規デプロイ時は既存の `deployment-guide.md` に従い、本書は追加差分のみを記載する。

対象環境:
- ステージング環境 / 本番環境(VPS)

変更の性質:
- 純粋に追加のみ(既存テーブル / API への破壊変更なし)
- ダウンタイムなしマイグレーション(想定所要 1 秒未満)

---

## 2. 事前準備

### 2.1 チェックリスト

- [ ] リリース対象コミットが main にマージ済み
- [ ] ステージングでの動作確認が完了している(§5)
- [ ] データベースバックアップが 1 時間以内に取得済み
- [ ] `docker-compose.yml` / `backend/.env.production` の差分確認
- [ ] ロールバック判断者の連絡先を確認

### 2.2 バックアップ取得

```bash
# 本番 VPS で実行
docker-compose exec db pg_dump -U helper_user -d helper_db \
  -t system_settings \
  -t users \
  -F c -f /tmp/pre-theme-release-$(date +%Y%m%d-%H%M%S).dump

# ホストへコピーして検証
docker cp helper5_db_1:/tmp/pre-theme-release-*.dump ~/backups/
ls -lh ~/backups/pre-theme-release-*.dump
```

---

## 3. ステージング適用

### 3.1 デプロイ

```bash
cd /path/to/helper5
git fetch origin
git checkout <release_commit>

# バックエンドイメージ再ビルド
docker-compose build backend

# マイグレーション
docker-compose run --rm backend alembic upgrade head
```

### 3.2 マイグレーション確認

```bash
docker-compose exec db psql -U helper_user -d helper_db -c "\d themes"
docker-compose exec db psql -U helper_user -d helper_db -c "\d user_preferences"
docker-compose exec db psql -U helper_user -d helper_db -c \
  "SELECT theme_key, name, is_builtin, is_active FROM themes ORDER BY theme_key;"
docker-compose exec db psql -U helper_user -d helper_db -c \
  "SELECT setting_key, setting_value FROM system_settings WHERE setting_key='default_theme_id';"
```

期待値:
- `themes` テーブルに 4 レコード(`standard`, `high-contrast`, `warm`, `calm`)、すべて `is_builtin=true` / `is_active=true`
- `user_preferences` テーブルは空で存在
- `default_theme_id` = `"standard"`

### 3.3 サービス再起動

```bash
docker-compose up -d backend frontend
docker-compose logs --tail=50 backend | grep -iE "error|warn" || true
```

---

## 4. スモークテスト(6 項目)

### 4.1 公開既定テーマ取得

```bash
curl -s -o /dev/null -w "%{http_code} %{header_json}\n" \
  https://<host>/api/v1/themes/public/default
```

期待: `200`、レスポンス JSON の `theme_key` が `"standard"`、`Cache-Control: public, max-age=300` ヘッダあり

### 4.2 テーマ一覧(認証)

一般ユーザーでログインして `access_token` 取得後:

```bash
curl -s -H "Authorization: Bearer $TOKEN" https://<host>/api/v1/themes | jq '.themes | length'
```

期待: `4`

### 4.3 ユーザー設定取得 / 更新

```bash
# 取得(初期は null)
curl -s -H "Authorization: Bearer $TOKEN" https://<host>/api/v1/users/me/preferences

# テーマ変更
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"theme_id":"warm"}' \
  https://<host>/api/v1/users/me/preferences
```

期待: 取得は `{"theme_id":null,...}`、更新後は `"theme_id":"warm"`

### 4.4 フロントエンド動作確認

ブラウザで以下を確認:

1. 未ログインで `/login` を開く → システム既定テーマが適用されている
2. ログイン → ProfilePage → 「表示テーマ」セクションが表示
3. 別のテーマを選択 → トースト「テーマを変更しました」表示、全画面に即時反映
4. リロード → 選択状態が維持

### 4.5 管理者 CRUD

管理者ログインで以下を確認:

1. `/admin/themes` → 一覧に 4 プリセット + 操作ボタンが表示
2. 「新規登録」→ エディタでカスタムテーマ(例: `staging-test`)を作成 → 201 で保存成功
3. 一覧から編集 → 名前変更 → 200 で更新
4. 既定テーマを `warm` に変更 → 未ログインで `/login` を開くと新既定が適用
5. 既定を `standard` に戻す
6. カスタムテーマ削除 → 一覧から消える

### 4.6 バリデーション拒否

エディタでフォントサイズを `17` に変更 → クライアント側でエラー表示 + 保存ボタン無効化。サーバに送信しても 422。

---

## 5. 本番適用

ステージングでの §4 全項目が成功した後に実施。

### 5.1 手順

```bash
# 本番 VPS で
cd /opt/helper5
git fetch origin
git checkout <release_tag>

# バックアップ(§2.2)を再取得
./scripts/backup-pre-release.sh theme-release

# ビルド + マイグレーション
docker-compose -f docker-compose.production.yml build backend
docker-compose -f docker-compose.production.yml run --rm backend alembic upgrade head

# 段階再起動: backend → frontend
docker-compose -f docker-compose.production.yml up -d backend
# ヘルスチェック
curl -fs https://<prod-host>/api/v1/health || { echo "backend unhealthy"; exit 1; }

docker-compose -f docker-compose.production.yml up -d frontend
```

### 5.2 本番スモーク

§4.1〜§4.4 を本番 URL で実施(§4.5 / §4.6 は実管理者アカウントで)。

### 5.3 観測

- アクセスログで `GET /api/v1/themes/public/default` が 200 系のみであること
- エラーログに `theme` 関連のスタックトレースがないこと
- Grafana / Loki で 5xx 率が平常値であること

---

## 6. ロールバック手順

### 6.1 判断基準

以下のいずれかに該当したら即座にロールバック:

- バックエンドが起動後 1 分以内にクラッシュループ
- `/api/v1/health` が 5 分連続で失敗
- 既存の非テーマ系 API(auth / users / recipes 等)に回帰エラー発生
- 5xx 率が平常値の 5 倍を超える

### 6.2 DB ロールバック

`user_preferences` に格納されたユーザーのテーマ選択は downgrade で失われる点に注意。本番リリース直後であれば件数ゼロのため問題ない。

```bash
# テーマ関連のマイグレーションを 1 つ巻き戻す
docker-compose -f docker-compose.production.yml run --rm backend \
  alembic downgrade -1

# 確認
docker-compose exec db psql -U helper_user -d helper_db -c \
  "SELECT to_regclass('themes'), to_regclass('user_preferences');"
# 両方 NULL になれば成功
```

### 6.3 アプリロールバック

```bash
git checkout <previous_release_tag>
docker-compose -f docker-compose.production.yml build backend frontend
docker-compose -f docker-compose.production.yml up -d backend frontend
```

### 6.4 データ復旧(万が一 users / system_settings が破損した場合)

```bash
docker-compose exec -T db pg_restore -U helper_user -d helper_db \
  --clean --if-exists /tmp/pre-theme-release-<timestamp>.dump
```

---

## 7. 事後作業

### 7.1 リリースノート

以下のテンプレで社内通知:

```
【リリース通知】テーマシステム v1.0

■ 新機能
- ページデザインを選択できる「テーマ」機能
- プリセット 4 種: スタンダード / ハイコントラスト / 温もり / おだやか
- ProfilePage > 表示テーマ から各自変更可能

■ 管理者向け
- /admin/themes でカスタムテーマ登録・編集・削除
- システム既定テーマの変更

■ 既存機能への影響
- なし(追加のみ)

■ アクセシビリティ
- すべてのテーマが最小 18px フォント / WCAG 2.1 AA コントラスト / タッチ 44px 要件を満たす
```

### 7.2 監査ログ確認

リリース日を含む監査ログで、想定外の `theme.*` / `system.update_default_theme` が発生していないことを確認:

```bash
# 管理 API 経由
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://<host>/api/v1/admin/audit-logs?resource_type=theme" | jq '.audit_logs | length'
```

### 7.3 定期監視項目への追加

- `/api/v1/themes/public/default` のレスポンスタイム P95
- `themes.is_active=false` の割合(意図せぬ無効化検知)
- `user_preferences` テーブル件数の推移

---

## 8. よくある問題(FAQ)

### Q1. マイグレーション実行時に `relation "themes" already exists`

A. 既に適用済み。`alembic current` でリビジョンを確認。

### Q2. プリセットが投入されていない

A. マイグレーションの data migration が失敗した可能性。ログを確認し、必要に応じて手動投入:

```bash
docker-compose exec backend python -c "
import asyncio
from app.services.theme_presets import BUILTIN_PRESETS
from app.db.models.theme import Theme
from app.core.database import async_session
async def seed():
    async with async_session() as db:
        for key, name, desc, definition in BUILTIN_PRESETS:
            db.add(Theme(theme_key=key, name=name, description=desc, definition=definition, is_builtin=True, is_active=True))
        await db.commit()
asyncio.run(seed())
"
```

### Q3. 既存ユーザーのテーマが変わってしまった

A. 本機能投入前の `theme.ts` のハードコード値は `standard` プリセットと(色が若干異なるものの)互換。気になる場合は:
- `default_theme_id` を既存相当の近似プリセットに変更
- カスタムテーマとして「legacy」を登録し既定に指定

### Q4. カスタムテーマ登録時に毎回 422

A. WCAG コントラスト未達が大半。エディタ画面のコントラストバッジで基準値未達の項目を確認。

---

**文書終了**
