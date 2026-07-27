#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/.textfitai-local-server.pid"
FOUND=0

stop_pid() {
  local pid="$1"

  if [[ -z "$pid" ]]; then
    return
  fi

  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "Stopping TextFitAI local server process $pid"
    kill "$pid" >/dev/null 2>&1 || true
    FOUND=1
  fi
}

if [[ -f "$PID_FILE" ]]; then
  stop_pid "$(cat "$PID_FILE")"
  rm -f "$PID_FILE"
fi

while IFS= read -r pid; do
  stop_pid "$pid"
done < <(pgrep -f "python.*uvicorn main:app --host 127\\.0\\.0\\.1 --port 80[0-9][0-9]" 2>/dev/null || true)

if [[ "$FOUND" -eq 0 ]]; then
  echo "No TextFitAI local preview servers found."
fi
