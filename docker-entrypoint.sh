#!/bin/sh
set -eu

/usr/local/bin/python - <<'PY'
import os
import pathlib
import shlex

keys = [
    "API_URL",
    "DB_TYPE",
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "SECRET_KEY",
    "SYNC_LOG_FILE",
    "TZ",
    "PYTHON_BIN",
]

lines = []
for key in keys:
    value = os.environ.get(key)
    if value is not None:
        lines.append(f"export {key}={shlex.quote(value)}")

pathlib.Path("/app/.container_env").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

/app/run-sync.sh
exec cron -f
