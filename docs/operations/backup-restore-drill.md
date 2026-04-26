# 四半期リストア演習ランブック

## 目的

`docs/backup-restore.md` で定義した RPO 24時間 / **RTO 4時間** が実環境で達成可能であることを検証する。改正個人情報保護法対応 (data_access_logs / compliance_logs の3年保持) のため、リストア手順が機能しないと法令違反リスクが発生する。

**実施頻度**: 四半期ごと (1月・4月・7月・10月の第1週)
**所要時間**: 2〜3時間
**実施者**: 運用担当 (バックアップ担当 + アプリ担当 各1名)

---

## 事前準備

| 項目 | 内容 |
|------|------|
| テストホスト | 本番VPSとは別のホスト (開発VPS / ローカルマシン) |
| 必要ツール | `docker compose`, `aws cli`, `gunzip`, `psql` (PG15 client) |
| 認証情報 | Cloudflare R2 の AWS プロファイル `r2` (~/.aws/credentials) |
| 比較用本番値 | 実施前日に本番DBで主要テーブル件数を取得 (下記Phase 0) |

---

## Phase 0 — 本番ベースライン取得 (前日)

```bash
# 本番VPSで実行
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
    SELECT 'users' AS t, count(*) FROM users UNION ALL
    SELECT 'weekly_menus', count(*) FROM weekly_menus UNION ALL
    SELECT 'data_access_logs', count(*) FROM data_access_logs UNION ALL
    SELECT 'compliance_logs', count(*) FROM compliance_logs UNION ALL
    SELECT 'themes', count(*) FROM themes UNION ALL
    SELECT 'user_preferences', count(*) FROM user_preferences;
  " | tee baseline_$(date +%Y%m%d).txt
```

`baseline_YYYYMMDD.txt` を後述の比較で使用する。

---

## Phase 1 — 最新バックアップの取得 (タイマー開始)

> **タイマー開始**: ここから RTO 4時間の計測を開始

```bash
# Cloudflare R2 から最新DBダンプを取得
aws s3 ls s3://helper-backups-prod/backups/db/ --profile r2 \
  --endpoint-url=https://<account_id>.r2.cloudflarestorage.com \
  | sort | tail -3

# 最新ファイルをダウンロード
LATEST="backup_helper_prod_db_<YYYYMMDD>_<HHMMSS>.sql.gz"
aws s3 cp "s3://helper-backups-prod/backups/db/$LATEST" ./ \
  --profile r2 \
  --endpoint-url=https://<account_id>.r2.cloudflarestorage.com
```

✅ チェック: ダウンロード時間を記録

---

## Phase 2 — 整合性検証

```bash
# gzip整合性
gzip -t "$LATEST" && echo OK

# 必須テーブルが含まれていることを確認
gunzip -c "$LATEST" | grep -cE \
  'CREATE TABLE (public\.)?(users|themes|user_preferences|data_access_logs|compliance_logs|audit_logs)'
# → 期待値: 6
```

✅ チェック: 不足があれば即時 `verify-backup-tables.sh` の REQUIRED_TABLES と照合

---

## Phase 3 — テスト用 PostgreSQL にリストア

```bash
# 一時DBコンテナ起動
docker run -d --name pg-restore-drill \
  -e POSTGRES_USER=helper_user \
  -e POSTGRES_DB=helper_restore_test \
  -e POSTGRES_PASSWORD=drill_only \
  -p 15432:5432 \
  postgres:15-alpine

sleep 5

# リストア
gunzip -c "$LATEST" | docker exec -i pg-restore-drill \
  psql -U helper_user -d helper_restore_test
```

✅ チェック: エラーなく完了するか / 警告は許容するか判定

---

## Phase 4 — 行数比較

```bash
docker exec -i pg-restore-drill psql -U helper_user -d helper_restore_test -c "
  SELECT 'users' AS t, count(*) FROM users UNION ALL
  SELECT 'weekly_menus', count(*) FROM weekly_menus UNION ALL
  SELECT 'data_access_logs', count(*) FROM data_access_logs UNION ALL
  SELECT 'compliance_logs', count(*) FROM compliance_logs UNION ALL
  SELECT 'themes', count(*) FROM themes UNION ALL
  SELECT 'user_preferences', count(*) FROM user_preferences;
"
```

`baseline_YYYYMMDD.txt` と比較し、**誤差±5%以内** であることを確認 (バックアップ取得後の追記分は許容)。

✅ チェック: 主要テーブルの件数が想定範囲内

---

## Phase 5 — アプリ起動確認 (任意)

時間に余裕がある場合のみ。リストアしたDBに対してバックエンドを起動し、`/api/v1/healthz` と代表的な GET エンドポイント (例: `GET /api/v1/users/me`) が応答することを確認。

---

## Phase 6 — タイマー停止 / 後片付け

```bash
# 計測終了 (Phase 1 開始からの経過時間を記録)
docker stop pg-restore-drill && docker rm pg-restore-drill
rm "$LATEST"
```

✅ **RTO 4時間以内に Phase 4 完了したか**

---

## チェックリスト (実施記録)

実施結果を `docs/operations/restore-drill-log.md` に追記する。

```markdown
## YYYY-MM-DD 四半期リストア演習

- 実施者: <name1>, <name2>
- 対象バックアップ: backup_helper_prod_db_YYYYMMDD_HHMMSS.sql.gz
- DL所要: __分
- リストア所要: __分
- Phase 1〜4 合計: __時間__分 (RTO 4h: PASS / FAIL)
- 必須テーブル網羅: PASS / FAIL
- 行数差異: PASS (誤差__%) / FAIL
- 発見した問題: ____
- 改善アクション: ____
```

---

## 失敗時の即時対応

- **gzip破損 / リストア失敗**: 1日前のバックアップで再試行 → 連続失敗時は P1 インシデントとして `incident-response-guide.md` を発動
- **テーブル不足**: `verify-backup-tables.sh` の REQUIRED_TABLES と `backup.sh` の pg_dump 設定を緊急レビュー
- **行数差異が大きい**: アプリ側の論理削除や TRUNCATE 操作が無いか確認 → 必要なら追加バックアップ取得
