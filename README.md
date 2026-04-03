# Home Helper Management System

ホームヘルパー管理システム — 訪問介護のヘルパー、利用者（高齢者）、ケアマネージャーをつなぐWebアプリケーション

## 概要

訪問介護の現場で必要な業務（タスク管理、メッセージ、レシピ・献立管理、買い物リスト、QR認証など）をワンストップで管理できるシステムです。高齢者に配慮したUI/UX設計（WCAG 2.1 AA準拠、最小フォント18px）を採用しています。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Frontend | React 18, TypeScript, Vite, Chakra UI v3, Zustand, React Query |
| Database | PostgreSQL 15, Redis 7 |
| Auth | JWT (access/refresh tokens) + QR Code認証 |
| Infra | Docker Compose, Nginx (リバースプロキシ + SSL) |
| Testing | pytest (Backend), Vitest + Playwright (Frontend) |

## アーキテクチャ

```
         Internet
            |
    [Nginx :80/443]  ← SSL終端, レート制限
         /      \
  [Frontend]  [Backend :8000]  ← Gunicorn + Uvicorn workers
   (React)    (FastAPI)
                /      \
         [PostgreSQL]  [Redis]
          :5432        :6379
```

## プロジェクト構成

```
.
├── backend/                  # FastAPI バックエンド
│   ├── app/
│   │   ├── api/              # APIエンドポイント
│   │   ├── core/             # 設定, セキュリティ
│   │   ├── crud/             # データベース操作
│   │   ├── db/               # モデル定義
│   │   ├── schemas/          # Pydanticスキーマ
│   │   ├── services/         # ビジネスロジック
│   │   ├── websocket/        # WebSocket通信
│   │   └── sse/              # Server-Sent Events
│   ├── alembic/              # DBマイグレーション
│   ├── tests/                # テスト
│   ├── Dockerfile.prod       # 本番用マルチステージビルド
│   └── requirements.txt
├── frontend/                 # React フロントエンド
│   ├── src/
│   ├── e2e/                  # E2Eテスト (Playwright)
│   ├── Dockerfile.prod       # 本番用マルチステージビルド
│   └── package.json
├── nginx/                    # Nginxリバースプロキシ
│   ├── nginx.conf
│   ├── Dockerfile
│   └── ssl/                  # SSL証明書配置
├── docs/                     # 設計書・仕様書
│   ├── requirements_specification.md
│   ├── database_schema_design.md
│   ├── api_specification.md
│   └── operations/           # 運用ガイド
├── docker-compose.yml        # 開発環境
├── docker-compose.prod.yml   # 本番環境
└── deploy.sh                 # デプロイスクリプト
```

## セットアップ

### 開発環境 (Docker Compose)

```bash
# リポジトリクローン
git clone <repository-url>
cd helper-system

# 開発環境起動
docker compose up -d

# DBマイグレーション
docker compose exec backend alembic upgrade head

# シードデータ投入（任意）
docker compose exec backend python scripts/seed_users.py
```

アクセス:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/v1
- API Docs: http://localhost:8000/docs

### ローカル開発 (Docker不使用)

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# PostgreSQL, Redis を別途起動
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## テスト

```bash
# バックエンドテスト
cd backend
pytest

# フロントエンド単体テスト
cd frontend
npm test

# E2Eテスト
cd frontend
npx playwright test
```

## 本番デプロイ

```bash
# 初回デプロイ
./deploy.sh init

# アップデート
./deploy.sh update

# ステータス確認
./deploy.sh status

# ログ確認
./deploy.sh logs [service]

# DBバックアップ
./deploy.sh backup
```

詳細は [VPSデプロイ手順](docs/operations/vps-deployment-h.kokoro-shift.jp.md) を参照してください。

## 主な機能

| 機能 | 説明 |
|------|------|
| ユーザー管理 | 3ロール (高齢者/ヘルパー/ケアマネ)、STIモデル |
| QR認証 | 高齢者向けパスワードレスログイン |
| タスク管理 | ヘルパーの訪問タスク作成・管理 |
| メッセージ | リアルタイムチャット (WebSocket/SSE) |
| レシピ・献立 | レシピ登録、献立作成、栄養管理 |
| 買い物リスト | 献立からの自動生成、パントリー連携 |
| パントリー | 食材在庫管理 |

## ドキュメント

- [要件定義書](docs/requirements_specification.md)
- [データベース設計](docs/database_schema_design.md)
- [API仕様書](docs/api_specification.md)
- [バックエンド実装計画](docs/backend_implementation_plan.md)
- [フロントエンド実装計画](docs/frontend_implementation_plan.md)
- [セキュリティ仕様](docs/security_implementation_specification.md)
- [高齢者UI/UXガイドライン](docs/elderly_ui_ux_guidelines.md)
- [環境変数リファレンス](docs/ENVIRONMENT_VARIABLES.md)
- [Docker本番デプロイ](docs/DOCKER_DEPLOYMENT.md)

## ライセンス

Private