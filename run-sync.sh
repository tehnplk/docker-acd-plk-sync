#!/bin/sh
set -eu

if [ -f /app/.container_env ]; then
  . /app/.container_env
fi

export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
LOG_FILE="${SYNC_LOG_FILE:-$SCRIPT_DIR/sync.log}"
TMP_FILE="$(mktemp)"
PYTHON_BIN="${PYTHON_BIN:-/usr/local/bin/python}"

if [ -d "$LOG_FILE" ]; then
  LOG_FILE="$LOG_FILE/sync.log"
fi

cleanup() {
  rm -f "$TMP_FILE"
}

trap cleanup EXIT

mkdir -p "$(dirname "$LOG_FILE")"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] err (python runtime not found at $PYTHON_BIN)" >>"$LOG_FILE"
  exit 1
fi

CASE_COUNT="$("$PYTHON_BIN" - <<'PY'
import runpy

ns = runpy.run_path("/app/plk-acd-sync.py", run_name="__plk_sync__")
sql = ns["load_query"]()
rows = ns["run_query"](sql)
print(len(rows))
PY
)"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] sync start (${CASE_COUNT} cases)" >>"$LOG_FILE"

if "$PYTHON_BIN" "$SCRIPT_DIR/plk-acd-sync.py" >"$TMP_FILE" 2>&1; then
  SYNC_RESULT_COUNT="$("$PYTHON_BIN" - <<'PY' "$TMP_FILE"
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
print(len(data))
PY
)"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] sync end (${SYNC_RESULT_COUNT} cases added)" >>"$LOG_FILE"
else
  ERR_MSG="$(tail -n 1 "$TMP_FILE" | tr '\r\n' ' ' | sed 's/[[:space:]]*$//')"
  if [ -z "$ERR_MSG" ]; then
    ERR_MSG="sync failed"
  fi
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] err (${ERR_MSG})" >>"$LOG_FILE"
  cat "$TMP_FILE" >&2
  exit 1
fi
