#!/usr/bin/env bash
#
# deploy-vps.sh - ローカル → VPS デプロイラッパー
#
# ローカルマシンから ssh 経由で本番VPSにアクセスし、
# VPS側の ./deploy.sh update を実行するラッパースクリプト。
#
# 実際のデプロイ処理 (バックアップ・ビルド・マイグレーション・再起動・通知)
# は VPS 上の deploy.sh が担当する。本スクリプトはローカル事前チェック
# (uncommitted/未push) + SSH呼出し + ヘルスチェック + サマリ表示が責務。
#
# 使い方:
#   ./scripts/deploy-vps.sh <host>                  # 通常デプロイ
#   ./scripts/deploy-vps.sh <host> --dry-run        # 実行内容の確認のみ
#   ./scripts/deploy-vps.sh <host> --no-deploy      # git pull のみ、デプロイなし
#   ./scripts/deploy-vps.sh <host> --skip-backup    # pre-deploy backup を省略
#   ./scripts/deploy-vps.sh <host> --force          # uncommitted無視で強行
#
# 例:
#   ./scripts/deploy-vps.sh deploy@h.kokoro-shift.jp
#   ./scripts/deploy-vps.sh deploy@h.kokoro-shift.jp --dry-run
#
# 環境変数:
#   VPS_PORT     SSHポート (default: 22)
#   DEPLOY_DIR   VPS側のリポジトリパス (default: /home/haya/projects/helper_2)
#   GIT_BRANCH   デプロイ対象ブランチ (default: main)
#   HEALTH_URL   ヘルスチェックURL (default: https://<host>/api/v1/health)
#
# 前提条件:
#   - VPS に SSH 鍵認証で接続可能
#   - VPS 側にリポジトリが clone 済み (DEPLOY_DIR)
#   - VPS 側に .env.production が設定済み
#   - VPS 側で ./deploy.sh init 済み (初回はこれを別途手動実行)
#
set -euo pipefail

# ─── 設定 ────────────────────────────────────────────
VPS_PORT="${VPS_PORT:-22}"
DEPLOY_DIR="${DEPLOY_DIR:-/home/haya/projects/helper_2}"
GIT_BRANCH="${GIT_BRANCH:-main}"
HEALTH_URL="${HEALTH_URL:-}"

# ─── フラグ解析 ──────────────────────────────────────
VPS_HOST=""
DRY_RUN=false
NO_DEPLOY=false
SKIP_BACKUP=false
FORCE=false
for arg in "$@"; do
    case "$arg" in
        --dry-run)     DRY_RUN=true ;;
        --no-deploy)   NO_DEPLOY=true ;;
        --skip-backup) SKIP_BACKUP=true ;;
        --force)       FORCE=true ;;
        --help|-h)
            sed -n '3,30p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        -*)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
        *)
            VPS_HOST="$arg"
            ;;
    esac
done

if [[ -z "${VPS_HOST}" ]]; then
    echo "Usage: $0 <host> [--dry-run] [--no-deploy] [--skip-backup] [--force]" >&2
    echo "Example: $0 deploy@h.kokoro-shift.jp" >&2
    exit 1
fi

# ヘルスチェックURLの自動推測 (host 部分のみ取り出して https://<host>/api/v1/health)
if [[ -z "$HEALTH_URL" ]]; then
    HOST_ONLY="${VPS_HOST##*@}"
    HEALTH_URL="https://${HOST_ONLY}/api/v1/health"
fi

SSH_OPTS="-o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -p ${VPS_PORT}"

# ─── ヘルパー ────────────────────────────────────────
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; exit 1; }
step()  { echo -e "\n\033[1;36m>>> $*\033[0m"; }

ssh_cmd() {
    if $DRY_RUN; then
        echo "  [DRY-RUN] ssh ${SSH_OPTS} ${VPS_HOST} \"$*\""
    else
        # shellcheck disable=SC2086
        ssh ${SSH_OPTS} "${VPS_HOST}" "$@"
    fi
}

# ─── 1. ローカル事前チェック ─────────────────────────
step "1. ローカル事前チェック"

if ! git rev-parse --git-dir &>/dev/null; then
    error "git リポジトリではありません"
fi

# 未コミットの変更
if ! git diff --quiet HEAD 2>/dev/null; then
    warn "未コミットの変更があります:"
    git diff --stat
    echo ""
    if $FORCE; then
        warn "--force 指定: uncommitted変更を無視して続行"
    else
        read -rp "未コミットの変更を無視してデプロイしますか? [y/N] " ans
        [[ "$ans" =~ ^[Yy] ]] || error "先にコミットしてください"
    fi
fi

# リモートに push 済みか
LOCAL_HEAD=$(git rev-parse HEAD)
REMOTE_HEAD=$(git rev-parse "origin/${GIT_BRANCH}" 2>/dev/null || echo "unknown")

if [[ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]]; then
    warn "ローカルの HEAD がリモートと異なります"
    info "  Local:  ${LOCAL_HEAD:0:8}"
    info "  Remote: ${REMOTE_HEAD:0:8}"
    echo ""
    read -rp "先に git push しますか? [Y/n] " ans
    if [[ ! "$ans" =~ ^[Nn] ]]; then
        info "git push origin ${GIT_BRANCH}..."
        if ! $DRY_RUN; then
            git push origin "${GIT_BRANCH}"
        else
            echo "  [DRY-RUN] git push origin ${GIT_BRANCH}"
        fi
        ok "Push 完了"
        REMOTE_HEAD=$(git rev-parse "origin/${GIT_BRANCH}" 2>/dev/null || echo "$LOCAL_HEAD")
    fi
fi

ok "ローカルチェック完了 (${LOCAL_HEAD:0:8})"

# ─── 2. VPS 接続チェック ─────────────────────────────
step "2. VPS 接続チェック"

if ! $DRY_RUN; then
    ssh_cmd "echo 'SSH OK'" >/dev/null || error "VPS に接続できません: ${VPS_HOST}"
fi
ok "SSH 接続: ${VPS_HOST}:${VPS_PORT}"

# ─── 3. VPS 側 git fetch & 差分プレビュー ──────────────
step "3. VPS 側で fetch と差分確認"

ssh_cmd "cd ${DEPLOY_DIR} && git fetch origin && \
    echo '=== 新規取込み予定 ===' && \
    git log --oneline HEAD..origin/${GIT_BRANCH} | head -20 && \
    echo '=== 現在のVPS側 HEAD ===' && \
    git rev-parse --short HEAD"

# ─── 4. デプロイ実行 (--no-deploy ならスキップ) ────────
if $NO_DEPLOY; then
    step "4. デプロイスキップ (--no-deploy 指定)"
    info "git pull のみ実行..."
    ssh_cmd "cd ${DEPLOY_DIR} && git pull origin ${GIT_BRANCH}"
    ok "pull 完了 (再起動なし)"
    echo ""
    info "デプロイサマリ:"
    info "  ホスト:   ${VPS_HOST}"
    info "  ブランチ: ${GIT_BRANCH}"
    info "  コミット: ${LOCAL_HEAD:0:8}"
    info "  モード:   --no-deploy (pull のみ)"
    exit 0
fi

step "4. VPS 側で ./deploy.sh update を実行"

# 既存 deploy.sh のフラグを組み立て (--force / --skip-backup)
DEPLOY_FLAGS=""
$FORCE       && DEPLOY_FLAGS="$DEPLOY_FLAGS --force"
$SKIP_BACKUP && DEPLOY_FLAGS="$DEPLOY_FLAGS --skip-backup"

info "ssh -> cd ${DEPLOY_DIR} && ./deploy.sh update${DEPLOY_FLAGS}"
DEPLOY_FAILED=false
if ! ssh_cmd "cd ${DEPLOY_DIR} && ./deploy.sh update${DEPLOY_FLAGS}"; then
    DEPLOY_FAILED=true
    warn "VPS側のデプロイが非0終了"
fi

# ─── 5. ヘルスチェック ───────────────────────────────
step "5. ヘルスチェック"

if ! $DRY_RUN; then
    info "10秒待機..."
    sleep 10
fi

# 5-1. VPS側 deploy.sh status
ssh_cmd "cd ${DEPLOY_DIR} && ./deploy.sh status" || warn "status コマンドが失敗"

# 5-2. 公開エンドポイントのヘルスチェック
HTTP_OK=false
if ! $DRY_RUN; then
    info "ヘルスチェック: ${HEALTH_URL}"
    if curl -sfk --max-time 10 "${HEALTH_URL}" >/dev/null; then
        ok "公開エンドポイント応答OK"
        HTTP_OK=true
    else
        warn "公開エンドポイントが応答しません: ${HEALTH_URL}"
    fi
else
    echo "  [DRY-RUN] curl -sfk ${HEALTH_URL}"
fi

# 5-3. デプロイ履歴の直近を表示
ssh_cmd "cd ${DEPLOY_DIR} && ./deploy.sh history 3" || true

# ─── 完了サマリ ──────────────────────────────────────
echo ""
if $DEPLOY_FAILED; then
    warn "デプロイは非0終了 — 上記ログ確認 / 必要なら ./deploy.sh rollback"
elif ! $HTTP_OK && ! $DRY_RUN; then
    warn "デプロイは完了したが公開エンドポイントが応答していない"
else
    ok "デプロイ完了"
fi

echo ""
echo "デプロイサマリ:"
echo "  ホスト:       ${VPS_HOST}"
echo "  デプロイ先:   ${DEPLOY_DIR}"
echo "  ブランチ:     ${GIT_BRANCH}"
echo "  コミット:     ${LOCAL_HEAD:0:8}"
echo "  Healthcheck:  $($HTTP_OK && echo '✓ OK' || echo '✗ NG/未確認')"
echo "  Deploy:       $($DEPLOY_FAILED && echo '✗ FAILED' || echo '✓ OK')"
echo ""
echo "確認コマンド:"
echo "  ssh ${SSH_OPTS} ${VPS_HOST} 'cd ${DEPLOY_DIR} && ./deploy.sh status'"
echo "  ssh ${SSH_OPTS} ${VPS_HOST} 'cd ${DEPLOY_DIR} && ./deploy.sh logs backend'"
echo "  ssh ${SSH_OPTS} ${VPS_HOST} 'cd ${DEPLOY_DIR} && ./deploy.sh history 10'"
echo ""
echo "ロールバックが必要な場合:"
echo "  ssh ${SSH_OPTS} ${VPS_HOST} 'cd ${DEPLOY_DIR} && ./deploy.sh rollback'"

# 失敗時は非0で終了
$DEPLOY_FAILED && exit 1 || exit 0
