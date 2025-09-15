#!/usr/bin/env bash
# Simple start/stop/status script for env sync backend + frontend
# Usage: manage_env_sync.sh start|stop|status [LAN_IP] [TOKEN]

ROOT="$(cd "$(dirname "$0")/../../../" && pwd)"  # repo root (ATLA_Campaign)
# locations (match on-disk layout where the server lives under Mycelium/scripts/Python)
FRONTEND_DIR="$ROOT/Mycelium/scripts/frontend"
BACKEND="$ROOT/Mycelium/scripts/Python/env_sync_server.py"
BACKEND_LOG="$ROOT/Mycelium/scripts/Python/env_sync_server.log"
BACKEND_PID="$ROOT/Mycelium/scripts/Python/env_sync_server.pid"
FRONTEND_PID="$FRONTEND_DIR/server.pid"
FRONTEND_LOG="$FRONTEND_DIR/server.log"

LAN_IP="$2"
TOKEN="$3"

if [ -z "$LAN_IP" ]; then
  # try common wifi interface
  LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || true)
  if [ -z "$LAN_IP" ]; then
    LAN_IP=0.0.0.0
  fi
fi

cmd="$1"
case "$cmd" in
  start)
    echo "Starting backend on $LAN_IP:9001"
    (cd "$ROOT" && MYCELIUM_SYNC_TOKEN="$TOKEN" nohup python3 "$BACKEND" --host "$LAN_IP" --port 9001 > "$BACKEND_LOG" 2>&1 & echo $! > "$BACKEND_PID")
    sleep 0.2
    if [ -f "$BACKEND_PID" ]; then
      echo "backend pid: $(cat "$BACKEND_PID")"
    fi

    echo "Starting frontend on $LAN_IP:8000"
    (cd "$FRONTEND_DIR" && nohup python3 -m http.server 8000 --bind 0.0.0.0 > "$FRONTEND_LOG" 2>&1 & echo $! > "$FRONTEND_PID")
    sleep 0.2
    if [ -f "$FRONTEND_PID" ]; then
      echo "frontend pid: $(cat "$FRONTEND_PID")"
    fi
    ;;
  stop)
    if [ -f "$BACKEND_PID" ]; then
      echo "Stopping backend $(cat "$BACKEND_PID")"
      kill "$(cat "$BACKEND_PID")" 2>/dev/null || true
      rm -f "$BACKEND_PID"
    fi
    if [ -f "$FRONTEND_PID" ]; then
      echo "Stopping frontend $(cat "$FRONTEND_PID")"
      kill "$(cat "$FRONTEND_PID")" 2>/dev/null || true
      rm -f "$FRONTEND_PID"
    fi
    ;;
  status)
    echo "backend:"
    if [ -f "$BACKEND_PID" ]; then
      pid=$(cat "$BACKEND_PID")
      ps -p $pid -o pid,cmd || echo "not running"
    else
      echo "no pid file"
    fi
    echo "frontend:"
    if [ -f "$FRONTEND_PID" ]; then
      pid=$(cat "$FRONTEND_PID")
      ps -p $pid -o pid,cmd || echo "not running"
    else
      echo "no pid file"
    fi
    ;;
  *)
    echo "Usage: $0 start|stop|status [LAN_IP] [TOKEN]"
    exit 2
    ;;
esac

exit 0
