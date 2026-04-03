#!/bin/sh
set -e

exec gunicorn app.main:app \
    -w "${GUNICORN_WORKERS:-4}" \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --timeout 120 \
    --graceful-timeout 30
