#!/usr/bin/env bash
# ============================================================
#  Bytebot Ops Verification Utility
#  Usage: verify_ops.sh [--json]
# ============================================================

set -e

JSON=false
for arg in "$@"; do
  case "$arg" in
    --json|-j) JSON=true ;;
  esac
done

# --- Gather data ---
# 1. Docker prune timer
TIMER_STATUS=$(systemctl list-timers docker-prune.timer --no-pager 2>/dev/null | tail -n1 | awk '{print $1, $2, $3, $4, $5}' || echo "inactive")

# 2. Last successful build log
LAST_BUILD=$(grep '\[SUCCESS\]' /var/log/bytebot-startup.log 2>/dev/null | tail -n 1 | cut -d']' -f2- | xargs || echo "No successful build found")

# 3. Active containers
CONTAINER_COUNT=$(docker ps -q | wc -l)
CONTAINER_LIST=$(docker ps --format '{{.Names}}' | tr '\n' ',' | sed 's/,$//')

# --- Compute high-level status ---
if [[ "$CONTAINER_COUNT" -ge 3 ]]; then
  STATUS="OK"
elif [[ "$CONTAINER_COUNT" -ge 1 ]]; then
  STATUS="WARN"
else
  STATUS="ERROR"
fi

# --- Output ---
if $JSON; then
  jq -n \
    --arg status "$STATUS" \
    --arg timer "$TIMER_STATUS" \
    --arg last_build "$LAST_BUILD" \
    --arg containers "$CONTAINER_LIST" \
    --argjson count "$CONTAINER_COUNT" \
    '{
      status: $status,
      metrics: {
        docker_prune_timer: $timer,
        last_build: $last_build,
        active_containers: $count,
        container_names: ($containers | split(","))
      }
    }'
else
  echo "=== Bytebot Ops Status ==="
  echo "Overall Status: $STATUS"
  echo "Timer: $TIMER_STATUS"
  echo "Last Build: $LAST_BUILD"
  echo "Active Containers: $CONTAINER_COUNT"
  echo "Container Names: $CONTAINER_LIST"
fi