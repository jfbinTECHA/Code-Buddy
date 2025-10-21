###############################################
# KILO EXECUTION CONTEXT: BYTEBOT ENV CHECK
# Validates OpenAI + Grok API credentials
###############################################

set -e

# === STEP 1: SET CONTEXT ===
BASE_DIR=~/bytebot/Code-Buddy/bytebotd
ENV_FILE="$BASE_DIR/docker/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "[FAIL] Environment file not found at $ENV_FILE"
  exit 1
else
  echo "[PASS] Environment file detected."
fi

# === STEP 2: LOAD VARIABLES ===
source "$ENV_FILE"

# === STEP 3: CHECK FOR MISSING KEYS ===
if [ -z "$OPENAI_API_KEY" ]; then
  echo "[FAIL] OPENAI_API_KEY is missing"
  exit 1
else
  echo "[PASS] OpenAI key loaded"
fi

if [ -z "$GROK_API_KEY" ]; then
  echo "[WARN] GROK_API_KEY not found (Grok integration optional)"
else
  echo "[PASS] Grok key loaded"
fi

# === STEP 4: VERIFY OPENAI CONNECTIVITY ===
echo "[INFO] Testing OpenAI API..."
if curl -s -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models \
  | grep -q '"id"'; then
  echo "[PASS] OpenAI API reachable."
else
  echo "[FAIL] OpenAI API unreachable or invalid key."
fi

# === STEP 5: VERIFY GROK CONNECTIVITY ===
echo "[INFO] Testing Grok API..."
if curl -s -H "Authorization: Bearer $GROK_API_KEY" https://api.x.ai/v1/models \
  | grep -q '"id"'; then
  echo "[PASS] Grok API reachable."
else
  echo "[WARN] Grok endpoint not responding (may be optional)."
fi

# === STEP 6: OUTPUT JSON LOG FOR KILO CODE ===
LOG_FILE="/tmp/kilo_env_status.json"
{
  echo '{'
  echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
  echo "  \"openai_key_present\": \"$( [ -n "$OPENAI_API_KEY" ] && echo true || echo false )\","
  echo "  \"grok_key_present\": \"$( [ -n "$GROK_API_KEY" ] && echo true || echo false )\","
  echo "  \"openai_connection\": \"$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models)\","
  echo "  \"grok_connection\": \"$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $GROK_API_KEY" https://api.x.ai/v1/models)\""
  echo '}'
} > "$LOG_FILE"

echo "[INFO] JSON log written to $LOG_FILE"

###############################################