#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
MAX_PORT="${MAX_PORT:-8010}"
PID_FILE="$ROOT_DIR/.textfitai-local-server.pid"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

port_is_open() {
  local port="$1"
  ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

wait_for_server() {
  local url="$1"
  local attempts=40

  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done

  return 1
}

if ! command_exists python3; then
  echo "python3 is required but was not found."
  exit 1
fi

if ! command_exists curl; then
  echo "curl is required but was not found."
  exit 1
fi

if ! command_exists lsof; then
  echo "lsof is required but was not found."
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "Installing backend dependencies..."
python -m pip install -r "$BACKEND_DIR/requirements.txt"

while ! port_is_open "$PORT"; do
  if [[ "$PORT" -ge "$MAX_PORT" ]]; then
    echo "No open port found between ${PORT} and ${MAX_PORT}."
    exit 1
  fi
  PORT=$((PORT + 1))
done

URL="http://$HOST:$PORT"
echo "Starting TextFitAI at $URL"

cd "$BACKEND_DIR"
python -m uvicorn main:app --host "$HOST" --port "$PORT" &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

cleanup() {
  if kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -f "$PID_FILE"
}

trap cleanup EXIT INT TERM

if ! wait_for_server "$URL"; then
  echo "Server did not become ready at $URL"
  exit 1
fi

if command_exists open; then
  open "$URL"
else
  echo "Open this URL in your browser: $URL"
fi

echo "TextFitAI is running. Press Ctrl+C here to stop it."
wait "$SERVER_PID"
