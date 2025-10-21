#!/usr/bin/env bash
# Bytebot Mission Control - Auto Diagnostic Script
# Checks dashboard container, ports, and dependencies

set -e

echo "🧠 Bytebot Mission Control Diagnostic"
echo "====================================="

# Step 1: Detect docker-compose
if ! command -v docker &>/dev/null; then
  echo "❌ Docker is not installed or not in PATH."
  exit 1
fi

if ! docker compose version &>/dev/null; then
  echo "⚠️  Docker Compose plugin missing. Install with:"
  echo "    sudo apt install docker-compose-plugin"
  exit 1
fi

# Step 2: Detect dashboard container
DASHBOARD=$(docker ps --format '{{.Names}}' | grep -E 'bytebot|dashboard' || true)
if [ -z "$DASHBOARD" ]; then
  echo "❌ Dashboard container not running."
  echo "➡️  Attempting to start via Docker Compose..."
  docker compose up -d
  sleep 5
  DASHBOARD=$(docker ps --format '{{.Names}}' | grep -E 'bytebot|dashboard' || true)
fi

# Step 3: Check port binding
if ! sudo lsof -i :9993 &>/dev/null; then
  echo "⚠️  Port 9993 not bound. Dashboard may have failed startup."
else
  echo "✅ Port 9993 is active."
fi

# Step 4: Container status
if [ -n "$DASHBOARD" ]; then
  echo "📦 Checking container logs for $DASHBOARD..."
  docker logs --tail 20 "$DASHBOARD" | tee /tmp/dashboard_logs.txt

  if grep -qi "ModuleNotFoundError" /tmp/dashboard_logs.txt; then
    echo "❌ Missing Python module detected — rebuilding container..."
    docker compose build --no-cache bytebot-dashboard
    docker compose up -d
  elif grep -qi "OSError: \[Errno 98\]" /tmp/dashboard_logs.txt; then
    echo "⚠️ Port conflict detected. Restarting dashboard container..."
    docker compose restart bytebot-dashboard
  elif grep -qi "docker: 'compose' is not a docker command" /tmp/dashboard_logs.txt; then
    echo "⚠️ Inside-container Docker CLI missing. Install it with:"
    echo "    apt-get update && apt-get install -y docker-ce-cli"
  else
    echo "✅ No critical errors detected."
  fi
else
  echo "❌ Dashboard container still missing after restart."
fi

# Step 5: Test connectivity
echo "🌐 Testing dashboard HTTP endpoint..."
if curl -s http://localhost:9993/api/health >/dev/null; then
  echo "✅ Dashboard API reachable at http://localhost:9993/api/health"
else
  echo "❌ Dashboard API unreachable. Check logs above."
fi

echo "====================================="
echo "🩺 Diagnostic complete."