#!/usr/bin/env bash
# test_graphsync.sh — Start FastAPI service and trigger a sync operation

set -euo pipefail

VENV_DIR=".venv"
REQ_FILE="requirements.txt"
ENV_FILE=".env"
HOST="localhost"
PORT=8000
BASE_URL="http://${HOST}:${PORT}"
LOG_FILE="graphsync_test.log"

# 1. Create & activate venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "🛠️  Creating virtualenv..."
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

# 2. Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r "$REQ_FILE"

# 3. Load environment variables
if [ -f "$ENV_FILE" ]; then
  echo "🔑 Loading environment from $ENV_FILE"
  set -a
  # shellcheck disable=SC1091
  source "$ENV_FILE"
  set +a
else
  echo "⚠️  No $ENV_FILE found, using defaults."
fi

# 4. Start FastAPI microservice in the background
echo "🚀 Starting GraphSync microservice on $BASE_URL..."
uvicorn app:app --host 0.0.0.0 --port "$PORT" --log-level info > "$LOG_FILE" 2>&1 &
MS_PID=$!

# Ensure we clean up the service on exit
function cleanup {
  echo "🛑 Stopping microservice (PID: $MS_PID)..."
  kill $MS_PID 2>/dev/null || true
  echo "✅ Test completed"
}
# trap cleanup EXIT  # Commented out to keep service running

# 5. Wait for service to be ready
echo -n "⏳ Waiting for service to start"
until curl -s "$BASE_URL/health" >/dev/null; do
  echo -n "."
  sleep 1
  # Check if service is still running
  if ! kill -0 $MS_PID 2>/dev/null; then
    echo "❌ Service failed to start! Check $LOG_FILE for details."
    cat "$LOG_FILE"
    exit 1
  fi
  
done
echo " ready!"

# 6. Trigger the sync operation
echo "🔄 Triggering sync operation..."
SYNC_RESPONSE=$(curl -s -X POST "$BASE_URL/trigger" \
  -H "Content-Type: application/json" \
  -d '{"module_ids": [], "max_depth": null, "include_reverse": true}')

echo "📊 Sync response: $SYNC_RESPONSE"

# 7. Monitor logs for completion
echo "📋 Monitoring logs for completion..."
TIMEOUT=60
START_TIME=$(date +%s)

while true; do
  if grep -q "Sync task completed successfully" "$LOG_FILE"; then
    echo "✅ Sync task completed successfully!"
    echo "👉 Service is still running on $BASE_URL (PID: $MS_PID)"
    echo "👉 Use 'kill $MS_PID' to stop it when you're done"
    break
  fi
  
  if grep -q "Sync task failed" "$LOG_FILE"; then
    echo "❌ Sync task failed! Check $LOG_FILE for details."
    tail -n 20 "$LOG_FILE"
    exit 1
  fi
  
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  
  if [ $ELAPSED -gt $TIMEOUT ]; then
    echo "⏰ Timeout waiting for sync to complete!"
    tail -n 20 "$LOG_FILE"
    exit 1
  fi
  
  echo -n "."
  sleep 2
done