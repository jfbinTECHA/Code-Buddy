#!/usr/bin/env bash
###############################################
# KILO EXECUTION CONTEXT: BYTEBOT MASTER PIPELINE
# Stages: Env → Build → Deploy → Health → JSON Summary
###############################################

set -e

# Optional: --validate-only flag for dry-run validation only
if [[ "$1" == "--validate-only" ]]; then
  echo "[INFO] Running Dockerfile syntax validation only..."
  docker build --target base -f bytebotd/Dockerfile . > /dev/null && \
    echo "[PASS] Dockerfile syntax valid." || \
    echo "[FAIL] Dockerfile validation failed."
  exit 0
fi

BASE_DIR=~/bytebot/Code-Buddy/bytebotd
cd "$BASE_DIR" || { echo "[FAIL] bytebotd directory not found"; exit 1; }

# === STEP 1: ENVIRONMENT CHECK ===
echo "[INFO] Running environment validation..."
./ops/kilo_env_check.sh || { echo "[FAIL] Environment validation failed"; exit 1; }

# === STEP 2: BUILD IMAGE ===
echo "[INFO] Running Dockerfile lint dry-run..."
docker build --no-cache --target base -f bytebotd/Dockerfile . > /dev/null 2>&1 && \
  echo "[PASS] Dockerfile syntax validated." || \
  echo "[WARN] Dockerfile linting failed, continuing anyway."

echo "[INFO] Building bytebot:latest image..."
if [[ ! -d /home/sysop/bytebot/Code-Buddy/shared ]]; then
  echo "[FAIL] shared/ directory missing from build context"
  exit 1
fi
docker build -t bytebot:latest . && echo "[PASS] Docker image built successfully." || { echo "[FAIL] Docker build failed"; exit 1; }

# === STEP 3: START STACK ===
echo "[INFO] Launching Docker Compose stack..."
docker compose --env-file docker/.env up -d && echo "[PASS] Bytebot stack launched." || { echo "[FAIL] Compose startup failed"; exit 1; }

# === STEP 4: HEALTH CHECK ===
echo "[INFO] Running system health check..."
./ops/kilo_health_check.sh || echo "[WARN] Health check reported issues"

# === STEP 5: SELF-REPAIR LOGIC ===
HEALTH_LOG="/tmp/kilo_health_status.json"
if [ ! -f "$HEALTH_LOG" ]; then
  echo "[FAIL] Health log missing — cannot repair."
else
  echo "[INFO] Evaluating system health..."
  redis_status=$(grep -o '"redis": *"[^"]*"' "$HEALTH_LOG" | awk -F'"' '{print $4}')
  postgres_status=$(grep -o '"postgres": *"[^"]*"' "$HEALTH_LOG" | awk -F'"' '{print $4}')
  chroma_status=$(grep -o '"chroma": *"[^"]*"' "$HEALTH_LOG" | awk -F'"' '{print $4}')
  agent_status=$(grep -o '"agent": *"[^"]*"' "$HEALTH_LOG" | awk -F'"' '{print $4}')
  ui_status=$(grep -o '"ui": *"[^"]*"' "$HEALTH_LOG" | awk -F'"' '{print $4}')
  desktop_status=$(grep -o '"desktop": *"[^"]*"' "$HEALTH_LOG" | awk -F'"' '{print $4}')

  # --- Redis ---
  if [ "$redis_status" != "up" ]; then
    echo "[WARN] Redis unhealthy → restarting container..."
    docker restart infra-redis-1 || docker compose up -d infra-redis-1
  fi

  # --- Postgres ---
  if [ "$postgres_status" != "up" ]; then
    echo "[WARN] Postgres unhealthy → restarting container..."
    docker restart bytebot-postgres || docker compose up -d bytebot-postgres
  fi

  # --- Chroma ---
  if [ "$chroma_status" != "up" ]; then
    echo "[WARN] Chroma unhealthy → restarting container..."
    docker restart infra-chroma-1 || docker compose up -d infra-chroma-1
  fi

  # --- Agent ---
  if [ "$agent_status" != "200" ]; then
    echo "[WARN] Agent service unhealthy → restarting..."
    docker restart bytebot-agent || docker compose up -d bytebot-agent
  fi

  # --- Desktop ---
  if [ "$desktop_status" != "200" ]; then
    echo "[WARN] Desktop service unhealthy → restarting..."
    docker restart bytebot-desktop || docker compose up -d bytebot-desktop
  fi

  # --- UI ---
  if [ "$ui_status" != "200" ]; then
    echo "[WARN] UI service unhealthy → restarting..."
    docker restart bytebot-ui || docker compose up -d bytebot-ui
  fi
fi

# === STEP 6: RE-CHECK AFTER REPAIR ===
echo "[INFO] Running post-repair health check..."
./ops/kilo_health_check.sh

# === STEP 7: CONSOLIDATE JSON LOGS ===
PIPELINE_LOG="/tmp/kilo_pipeline_status.json"
ENV_LOG="/tmp/kilo_env_status.json"
HEALTH_LOG="/tmp/kilo_health_status.json"
MASTER_LOG="/tmp/kilo_master_status.json"

{
  echo '{'
  echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
  echo "  \"pipeline\": $(cat "$PIPELINE_LOG" 2>/dev/null || echo '{}'),"
  echo "  \"environment\": $(cat "$ENV_LOG" 2>/dev/null || echo '{}'),"
  echo "  \"health\": $(cat "$HEALTH_LOG" 2>/dev/null || echo '{}')"
  echo '}'
} > "$MASTER_LOG"

echo "[INFO] Consolidated JSON written to $MASTER_LOG"

# === STEP 6: FINAL SUMMARY ===
echo "[INFO] Bytebot master pipeline complete."
echo "[INFO] Dashboard: http://localhost:9992"
echo "[SUCCESS] Bytebot rebuild completed at $(date '+%Y-%m-%d %H:%M:%S')" \
  | tee -a /var/log/bytebot-startup.log

# Optional: Auto-prune builder cache weekly
tee /etc/systemd/system/docker-prune.timer > /dev/null <<'EOF'
[Unit]
Description=Weekly Docker builder cache cleanup

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
EOF

tee /etc/systemd/system/docker-prune.service > /dev/null <<'EOF'
[Unit]
Description=Clean Docker build cache

[Service]
Type=oneshot
ExecStart=/usr/bin/docker builder prune -f
EOF

systemctl enable --now docker-prune.timer

# Optional: Create logrotate rule for bytebot-startup.log
tee /etc/logrotate.d/bytebot > /dev/null <<'EOF'
/var/log/bytebot-startup.log {
    weekly
    rotate 8
    compress
    missingok
    notifempty
}
EOF
###############################################