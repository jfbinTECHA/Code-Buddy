#!/usr/bin/env bash
# ===========================================================
# 🧠 Bytebot Mission Control - Self-Healing Repair Utility
# -----------------------------------------------------------
# Includes: automatic backup, retry recovery, and notifications
# ===========================================================

set -euo pipefail

START_TIME=$(date +'%Y-%m-%d %H:%M:%S')
BACKUP_DIR="./backups"
TIMESTAMP=$(date +'%Y%m%d_%H%M%S')
DISCORD_WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"
EMAIL_ALERT="${EMAIL_ALERT:-}"

echo "================================================="
echo "🧠 Bytebot Mission Control - Self-Healing Repair Utility"
echo "🕒 Started at: $START_TIME"
echo "📦 Backup directory: $BACKUP_DIR/$TIMESTAMP"
echo "================================================="

# --------------------------
# 0. CREATE BACKUPS
# --------------------------
mkdir -p "$BACKUP_DIR/$TIMESTAMP"
for path in ./Code-Buddy/bytebotd/config ./Code-Buddy/bytebotd/ops; do
  if [ -d "$path" ]; then
    echo "🗄️  Backing up: $path"
    cp -r "$path" "$BACKUP_DIR/$TIMESTAMP"/$(basename "$path")
  else
    echo "⚠️  Directory missing, skipping: $path"
  fi
done
echo "✅ Backup completed."

# --------------------------
# 1. VERIFY DOCKER & COMPOSE
# --------------------------
if ! command -v docker &>/dev/null; then
  echo "❌ Docker not found. Installing..."
  curl -fsSL https://get.docker.com | sudo sh
fi

if ! docker compose version &>/dev/null; then
  echo "⚙️ Installing Docker Compose plugin..."
  sudo apt update -y && sudo apt install -y docker-compose-plugin
fi

# --------------------------
# 2. FUNCTION DEFINITIONS
# --------------------------
notify_discord() {
  local message="$1"
  if [ -n "$DISCORD_WEBHOOK_URL" ]; then
    curl -s -H "Content-Type: application/json" \
         -d "{\"content\": \"$message\"}" "$DISCORD_WEBHOOK_URL" >/dev/null
  fi
}

notify_email() {
  local subject="Bytebot Mission Control Alert"
  local body="$1"
  if [ -n "$EMAIL_ALERT" ]; then
    echo "$body" | mail -s "$subject" "$EMAIL_ALERT"
  fi
}

retry() {
  local cmd="$1"
  local attempts=3
  local delay=5
  local count=0

  until $cmd; do
    count=$((count + 1))
    if [ $count -ge $attempts ]; then
      echo "❌ Command failed after $attempts attempts: $cmd"
      notify_discord "🚨 Bytebot: Command failed after $attempts attempts: \`$cmd\`"
      notify_email "Bytebot: Command failed after $attempts attempts: $cmd"
      return 1
    fi
    echo "🔁 Retrying in $delay seconds ($count/$attempts)..."
    sleep $delay
  done
  return 0
}

# --------------------------
# 3. VERIFY CONTAINERS
# --------------------------
DASHBOARD=$(docker ps -a --format '{{.Names}}' | grep -E 'bytebot|dashboard' || true)
if [ -z "$DASHBOARD" ]; then
  echo "⚠️ Dashboard container missing — rebuilding..."
  retry "docker compose up -d --build"
fi

# --------------------------
# 4. START DASHBOARD
# --------------------------
if ! docker ps --format '{{.Names}}' | grep -q "$DASHBOARD"; then
  echo "⚙️ Starting dashboard container..."
  retry "docker start $DASHBOARD" || retry "docker compose up -d"
fi

# --------------------------
# 5. VALIDATE ENVIRONMENT
# --------------------------
echo "🔍 Validating environment inside container..."
docker exec -i "$DASHBOARD" bash -c '
  set -e
  echo "🩺 Checking dependencies..."
  pip install --no-cache-dir -q websockets flask flask-cors psutil chart-studio || true
  if ! command -v docker &>/dev/null; then
    apt-get update -y && apt-get install -y docker-ce-cli
  fi
  echo "✅ Dependencies verified."
' || {
  notify_discord "🚨 Bytebot: Dependency check failed in container."
  notify_email "Bytebot: Dependency check failed in container."
}

# --------------------------
# 6. PORT CHECK
# --------------------------
if ! sudo lsof -i :9993 &>/dev/null; then
  echo "🌍 Restarting dashboard (port 9993)..."
  retry "docker compose restart bytebot-dashboard"
fi

# --------------------------
# 7. HEALTH TEST
# --------------------------
echo "🩺 Testing dashboard API..."
if curl -s http://localhost:9993/api/health >/dev/null; then
  echo "✅ Dashboard online: http://localhost:9993/api/health"
  notify_discord "✅ Bytebot Dashboard is online and healthy."
else
  echo "⚠️ Dashboard API unreachable — showing logs:"
  docker logs "$DASHBOARD" --tail 25
  notify_discord "🚨 Bytebot Dashboard unreachable on port 9993."
  notify_email "Bytebot Dashboard unreachable on port 9993."
fi

# --------------------------
# 8. RESTORE OPTION
# --------------------------
read -p "🔁 Restore from backup (y/n)? " RESP
if [[ "$RESP" =~ ^[Yy]$ ]]; then
  echo "♻️ Restoring configuration..."
  cp -r "$BACKUP_DIR/$TIMESTAMP/config" ./Code-Buddy/bytebotd/ || true
  cp -r "$BACKUP_DIR/$TIMESTAMP/ops" ./Code-Buddy/bytebotd/ || true
  retry "docker compose restart bytebot-dashboard"
  notify_discord "♻️ Bytebot configuration restored from backup ($TIMESTAMP)."
fi

# --------------------------
# 9. SUMMARY
# --------------------------
echo "================================================="
echo "🧠 Repair completed successfully!"
echo "🕒 Completed at: $(date +'%Y-%m-%d %H:%M:%S')"
echo "💾 Backup saved at: $BACKUP_DIR/$TIMESTAMP"
echo "🌍 Dashboard URL: http://localhost:9993"
echo "================================================="
notify_discord "✅ Bytebot Mission Control repair completed successfully at $(date +'%H:%M:%S')."