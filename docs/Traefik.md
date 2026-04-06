# VPS Traefik リバースプロキシ

VPS上で複数のDockerコンテナを統合管理するためのTraefikリバースプロキシ構成。

## 構成概要

```
Internet
  │
  ├─ :80  (HTTP)  → HTTPS へリダイレクト
  └─ :443 (HTTPS) → Traefik → 各コンテナ
                        │
                        ├─ app-a.kokoro-shift.jp → コンテナA
                        ├─ app-b.kokoro-shift.jp → コンテナB
                        └─ ...
```

## ファイル構成

```
.
├── docker-compose.yml          # Traefik コンテナ定義
├── traefik.yml                 # 静的設定（エントリポイント、証明書、プロバイダ）
└── dynamic/
    └── middlewares.yml          # 動的設定（ミドルウェア定義）
```

## 機能

- **自動HTTPS**: Let's Encrypt による証明書自動取得・更新
- **HTTPリダイレクト**: 全HTTPリクエストをHTTPSへ転送
- **Docker連携**: ラベルベースで自動ルーティング（`exposedByDefault: false`）
- **セキュリティヘッダー**: HSTS, X-Frame-Options, XSS Protection 等
- **レート制限**: API用（10r/s）、認証用（3r/s）
- **Gzip圧縮**: SSE を除くレスポンスの圧縮
- **リクエスト制限**: ボディサイズ上限 10MB

## セットアップ

### 1. 起動

```bash
docker compose up -d
```

### 2. 他コンテナとの連携

他のコンテナからTraefikを経由するには、以下の設定を追加する。

**docker-compose.yml（連携先コンテナ側）:**

```yaml
services:
  app:
    image: your-app
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app.rule=Host(`app.kokoro-shift.jp`)"
      - "traefik.http.routers.app.entrypoints=websecure"
      - "traefik.http.routers.app.tls.certresolver=letsencrypt"
      # ミドルウェア適用例
      - "traefik.http.routers.app.middlewares=security-headers@file,gzip-compress@file"
    networks:
      - proxy

networks:
  proxy:
    external: true
```

> `proxy` ネットワークは本リポジトリの Traefik が作成する外部ネットワーク。連携先では `external: true` で参照する。

## ミドルウェア一覧

| 名前 | 種別 | 用途 |
|------|------|------|
| `security-headers@file` | ヘッダー | セキュリティレスポンスヘッダー付与 |
| `gzip-compress@file` | 圧縮 | Gzip圧縮（SSE除外） |
| `rate-limit-api@file` | レート制限 | API向け（10r/s, burst 20） |
| `rate-limit-auth@file` | レート制限 | 認証向け（3r/s, burst 5） |
| `request-body-limit@file` | バッファリング | リクエストボディ 10MB制限 |

## 運用情報

- **Traefik バージョン**: v3.1
- **証明書保存先**: Docker Volume `traefik_certs`
- **ログ**: WARN レベル、JSON形式（50MB × 5ファイルローテーション）
- **メモリ制限**: 256MB
- **ダッシュボード**: 有効（`insecure: false` — 外部公開なし）
