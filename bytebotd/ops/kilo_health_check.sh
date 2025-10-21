#!/usr/bin/env bash
###############################################
# KILO EXECUTION CONTEXT: BYTEBOT SYSTEM HEALTH
# Checks Redis, Postgres, Chroma, Agent, UI, Desktop
###############################################

set -e

BASE_DIR=~/bytebot/Code-Buddy/bytebotd
cd "$BASE_DIR" || { echo "[FAIL] bytebotd not found"; exit 1; }

echo "[INFO] Starting Bytebot service health check..."

# === STEP 1: VERIFY DOCKER NETWORK ===
if docker network inspect bytebot_bytebot-network >/dev/null 2>&1; then
  echo "[PASS] Network detected: bytebot_bytebot-network"
else
  echo "[FAIL] Network missing"; exit 1;
fi

# === STEP 2: REDIS CHECK ===
if docker run --rm --network bytebot_bytebot-network redis:7 redis-cli -h infra-redis-1 ping | grep -q PONG; then
  echo "[PASS] Redis responding"
else
  echo "[FAIL] Redis unreachable"
fi

# === STEP 3: POSTGRES CHECK ===
if docker run --rm --network bytebot_bytebot-network postgres:16 pg_isready -h bytebot-postgres -p 5432 | grep -q "accepting connections"; then
  echo "[PASS] Postgres reachable"
else
  echo "[FAIL] Postgres not reachable"
fi

# === STEP 4: CHROMA CHECK ===
if curl -s http://infra-chroma-1:8001/api/v1/heartbeat | grep -q "true"; then
  echo "[PASS] Chroma responding"
else
  echo "[FAIL] Chroma endpoint offline"
fi

# === STEP 5: AGENT HEALTH ===
if curl -s http://localhost:9991/health | grep -q "ok"; then
  echo "[PASS] Agent healthy"
else
  echo "[FAIL] Agent not responding"
fi

# === STEP 6: DESKTOP HEALTH ===
if curl -s http://localhost:9990/ | grep -q "<html"; then
  echo "[PASS] Desktop serving HTTP"
else
  echo "[FAIL] Desktop service down"
fi

# === STEP 7: UI HEALTH ===
if curl -s http://localhost:9992/ | grep -q "<html"; then
  echo "[PASS] UI reachable"
else
  echo "[FAIL] UI not serving"
fi

# === STEP 8: WRITE JSON SUMMARY ===
LOG_FILE="/tmp/kilo_health_status.json"
{
  echo '{'
  echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
  echo "  \"redis\": \"$(docker run --rm --network bytebot_bytebot-network redis:7 redis-cli -h infra-redis-1 ping 2>/dev/null | grep -q PONG && echo up || echo down)\","
  echo "  \"postgres\": \"$(docker run --rm --network bytebot_bytebot-network postgres:16 pg_isready -h bytebot-postgres -p 5432 2>/dev/null | grep -q 'accepting connections' && echo up || echo down)\","
  echo "  \"chroma\": \"$(curl -s http://infra-chroma-1:8001/api/v1/heartbeat | grep -q 'true' && echo up || echo down)\","
  echo "  \"agent\": \"$(curl -s -o /dev/null -w '%{http_code}' http://localhost:9991/health)\","
  echo "  \"desktop\": \"$(curl -s -o /dev/null -w '%{http_code}' http://localhost:9990/)\","
  echo "  \"ui\": \"$(curl -s -o /dev/null -w '%{http_code}' http://localhost:9992/)\""
  echo '}'
} > "$LOG_FILE"

echo "[INFO] JSON health log written to $LOG_FILE"
###############################################