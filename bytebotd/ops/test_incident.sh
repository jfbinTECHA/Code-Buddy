#!/bin/bash

# Test script to simulate random [FAIL] and [SUCCESS] events for ops monitoring
# Logs to /var/log/bytebot-startup.log to trigger the WebSocket and Discord pipeline

LOG_FILE="/var/log/bytebot-startup.log"
COMPONENTS=("bytebot-desktop" "bytebot-agent" "bytebot-ui" "Docker" "Kubernetes" "Database")

echo "🚀 Starting ops incident simulation..."
echo "📜 Logging to $LOG_FILE"
echo "⏹️  Press Ctrl+C to stop"

while true; do
  # Randomly choose event type
  EVENT_TYPES=("[FAIL]" "[SUCCESS]")
  EVENT_TYPE=${EVENT_TYPES[$RANDOM % ${#EVENT_TYPES[@]}]}

  # Randomly choose component
  COMPONENT=${COMPONENTS[$RANDOM % ${#COMPONENTS[@]}]}

  # Generate random message
  if [ "$EVENT_TYPE" = "[FAIL]" ]; then
    MESSAGES=("build checksum error" "container startup failed" "health check timeout" "network connection lost" "disk space critical")
  else
    MESSAGES=("rebuild completed" "service restarted" "health check passed" "deployment successful" "cache cleared")
  fi
  MESSAGE=${MESSAGES[$RANDOM % ${#MESSAGES[@]}]}

  # Log the event
  LOG_ENTRY="$EVENT_TYPE $COMPONENT $MESSAGE"
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Simulating: $LOG_ENTRY"
  echo "sys" | sudo -S sh -c "echo '$LOG_ENTRY' >> '$LOG_FILE'"

  # Wait random interval (2-6 seconds)
  SLEEP_TIME=$((RANDOM % 5 + 2))
  sleep $SLEEP_TIME
done