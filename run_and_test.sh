#!/usr/bin/env bash
# run_and_test.sh — setup, launch FastAPI, hit /trigger, teardown

set -euo pipefail

VENV_DIR=".venv"
REQ_FILE="requirements.txt"
ENV_FILE=".env"
HOST="localhost"
PORT=8000
BASE_URL="http://${HOST}:${PORT}"

# 1. Create & activate venv
if [ ! -d "$VENV_DIR" ]; then
  echo "🛠️  Creating virtualenv..."
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

# 2. Install deps
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r "$REQ_FILE"

# 3. Load env
if [ -f "$ENV_FILE" ]; then
  echo "🔑 Loading environment from $ENV_FILE"
  set -a
  # shellcheck disable=SC1091
  source "$ENV_FILE"
  set +a
else
  echo "⚠️  No $ENV_FILE found, skipping."
fi

# 4. Start FastAPI microservice
echo "🚀 Starting microservice on $BASE_URL..."
uvicorn app:app --host 0.0.0.0 --port "$PORT" >/dev/null 2>&1 &
MS_PID=$!
trap "echo '🛑 Stopping microservice...'; kill $MS_PID" EXIT

# 5. Wait for service to be ready
echo -n "⏳ Waiting for service…"
until curl -s "$BASE_URL/docs" >/dev/null; do
  echo -n "."
  sleep 1
done
echo " ready!"

# 6. Send test /trigger request
echo "🎯 Testing POST ${BASE_URL}/trigger"
PAYLOAD=$(
  cat <<EOF
{
  "module_ids": [333],
  "stop_conditions": [[["category_id", "not in", [52]]]]
}
EOF
)
RESPONSE=$(curl -s -X POST "$BASE_URL/trigger" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

# 7. Print response
echo
echo "📬 Response from /trigger:"
echo "$RESPONSE" | python3 -m json.tool

# 8. Done (cleanup via trap)
echo "✅ Test complete."
