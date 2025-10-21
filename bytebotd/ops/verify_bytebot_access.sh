#!/usr/bin/env bash
# Bytebot Access Verifier & Auto-Patcher
# ------------------------------------------------------
# Ensures both localhost and Docker-internal hostnames are reachable.

set -e

AGENT_PORT=9991
HOST_ENTRY="127.0.0.1 bytebot-agent"

echo "🔍 Checking Bytebot Agent connectivity..."
echo

# 1️⃣ External health check
echo "➡️  Testing external API: http://localhost:${AGENT_PORT}/health"
LOCAL_STATUS=$(curl -s -m 3 http://localhost:${AGENT_PORT}/health || true)

if echo "$LOCAL_STATUS" | grep -q '"status":"ok"'; then
    echo "✅ External (localhost) agent reachable."
else
    echo "❌ External (localhost) agent not reachable or unhealthy."
fi

# 2️⃣ Internal hostname check
echo
echo "➡️  Testing internal API: http://bytebot-agent:${AGENT_PORT}/health"
INTERNAL_STATUS=$(curl -s -m 3 http://bytebot-agent:${AGENT_PORT}/health || true)

if echo "$INTERNAL_STATUS" | grep -q '"status":"ok"'; then
    echo "✅ Internal (bytebot-agent) hostname reachable."
else
    echo "⚠️  Internal (bytebot-agent) not reachable — checking /etc/hosts..."

    # 3️⃣ Patch /etc/hosts if missing
    if ! grep -q "bytebot-agent" /etc/hosts; then
        echo "🛠️  Adding missing mapping to /etc/hosts..."
        echo "$HOST_ENTRY" | sudo tee -a /etc/hosts >/dev/null
        echo "✅ Added 'bytebot-agent' → localhost mapping."
        echo "🔁 Rechecking..."
        sleep 1
        INTERNAL_STATUS=$(curl -s -m 3 http://bytebot-agent:${AGENT_PORT}/health || true)
        if echo "$INTERNAL_STATUS" | grep -q '"status":"ok"'; then
            echo "✅ Internal access fixed and working!"
        else
            echo "❌ Still cannot reach internal agent — check Docker DNS or bridge network."
        fi
    else
        echo "ℹ️  Mapping already exists in /etc/hosts."
    fi
fi

echo
echo "------------------------------------------------------"
echo "🧩 Bytebot Access Verification Complete"
echo "External: $LOCAL_STATUS"
echo "Internal: $INTERNAL_STATUS"
echo "------------------------------------------------------"