#!/bin/bash
# Bytebot Recovery Script - Updated for Compose-prefixed container names

echo "[Bytebot Ops] triggered recovery at $(date)"

# Detect actual container names dynamically
POSTGRES=$(docker ps --format '{{.Names}}' | grep 'postgres' | head -n 1)
REDIS=$(docker ps --format '{{.Names}}' | grep 'redis' | head -n 1)
CHROMA=$(docker ps --format '{{.Names}}' | grep 'chroma' | head -n 1)

# Fallback if no match found
if [ -z "$POSTGRES" ] && [ -z "$REDIS" ] && [ -z "$CHROMA" ]; then
    echo "No services specified, restarting all..."
    docker restart $(docker ps -q)
else
    echo "Restarting services:"
    [ -n "$POSTGRES" ] && echo "  - $POSTGRES" && docker restart "$POSTGRES"
    [ -n "$REDIS" ] && echo "  - $REDIS" && docker restart "$REDIS"
    [ -n "$CHROMA" ] && echo "  - $CHROMA" && docker restart "$CHROMA"
fi

echo "✅ Recovery operation complete"