#!/bin/sh
set -e

# 引数が渡された場合（例: docker compose run --rm backend alembic upgrade head）は
# その引数を実行する。引数なしの起動時はデフォルトで gunicorn を起動。
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

exec gunicorn app.main:app \
    -w "${GUNICORN_WORKERS:-4}" \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --timeout 120 \
    --graceful-timeout 30
