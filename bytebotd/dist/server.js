"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const child_process_1 = require("child_process");
const ws_1 = require("ws");
const node_fetch_1 = require("node-fetch");
const LOG_FILE = "/var/log/bytebot-startup.log";
const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL || "";
const DISCORD_BOT_TOKEN = process.env.NOMI_BOT_TOKEN || "";
const ALERT_CHANNEL_ID = process.env.DISCORD_ALERT_CHANNEL_ID || "";
const activeThreads = new Map();
const REOPEN_WINDOW_MS = 10 * 60 * 1000;
const wss = new ws_1.WebSocketServer({ port: 8787 });
const clients = [];
console.log("✅ Bytebot Ops WebSocket running on ws://localhost:8787");
console.log(`📜 Watching ${LOG_FILE}`);
wss.on("connection", (ws) => {
    clients.push(ws);
    ws.send(JSON.stringify({ type: "init", message: "Connected to Bytebot Ops feed" }));
    ws.on("close", () => clients.splice(clients.indexOf(ws), 1));
});
function extractContext(line) {
    const match = line.match(/\[(SUCCESS|FAIL)\]\s+([a-zA-Z0-9_-]+)/);
    return match ? match[2] : "general";
}
async function postToThread(threadId, content) {
    await (0, node_fetch_1.default)(`https://discord.com/api/v10/channels/${threadId}/messages`, {
        method: "POST",
        headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
    });
}
async function sendDiscordAlert(eventType, message) {
    const context = extractContext(message);
    const title = eventType === "FAIL"
        ? `❌ ${context} Build Failure`
        : eventType === "MAINTENANCE"
            ? `🧹 Maintenance Task`
            : `ℹ️ Bytebot Update`;
    const color = eventType === "FAIL" ? 0xed4245 : 0x99aab5;
    const msg = await (0, node_fetch_1.default)(`https://discord.com/api/v10/channels/${ALERT_CHANNEL_ID}/messages`, {
        method: "POST",
        headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
        body: JSON.stringify({
            embeds: [{ title, description: message, color, timestamp: new Date().toISOString() }],
        }),
    }).then((r) => r.json());
    const thread = await (0, node_fetch_1.default)(`https://discord.com/api/v10/channels/${ALERT_CHANNEL_ID}/messages/${msg.id}/threads`, {
        method: "POST",
        headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
        body: JSON.stringify({
            name: `${context} — Build Failure ${new Date().toLocaleTimeString()}`,
            auto_archive_duration: 1440,
        }),
    }).then((r) => r.json());
    return thread.id;
}
const tail = (0, child_process_1.spawn)("tail", ["-F", LOG_FILE]);
tail.stdout.on("data", async (data) => {
    const line = data.toString().trim();
    if (!/\[(SUCCESS|FAIL)\]/.test(line))
        return;
    const eventType = line.includes("[FAIL]") ? "FAIL" : "SUCCESS";
    const context = extractContext(line);
    const message = line.replace(/\[.*?\]\s*/, "");
    const now = Date.now();
    if (eventType === "FAIL") {
        const previous = activeThreads.get(context);
        let threadId;
        if (previous && now - previous.lastFailTime < REOPEN_WINDOW_MS) {
            await postToThread(previous.threadId, `⚠️ ${context} failed again at ${new Date().toLocaleTimeString()}`);
            await (0, node_fetch_1.default)(`https://discord.com/api/v10/channels/${previous.threadId}`, {
                method: "PATCH",
                headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
                body: JSON.stringify({ archived: false }),
            });
            threadId = previous.threadId;
            console.log(`🔁 Reopened existing thread for ${context}`);
        }
        else {
            threadId = await sendDiscordAlert("FAIL", line);
            console.log(`🆕 New failure thread created for ${context}`);
        }
        activeThreads.set(context, { threadId, lastFailTime: now });
    }
    if (eventType === "SUCCESS" && activeThreads.has(context)) {
        const entry = activeThreads.get(context);
        if (entry) {
            const { threadId } = entry;
            await postToThread(threadId, `✅ ${context} recovered — rebuild succeeded at ${new Date().toLocaleTimeString()}`);
            await (0, node_fetch_1.default)(`https://discord.com/api/v10/channels/${threadId}`, {
                method: "PATCH",
                headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
                body: JSON.stringify({ archived: true }),
            });
            activeThreads.delete(context);
            console.log(`✅ ${context} recovered and thread archived.`);
        }
    }
    for (const ws of clients) {
        ws.send(JSON.stringify({ type: "ops_update", payload: { eventType, context, message, time: new Date() } }));
    }
});
//# sourceMappingURL=server.js.map