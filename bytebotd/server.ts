import { spawn } from "child_process";
import WebSocket, { WebSocketServer } from "ws";
import fetch from "node-fetch";

const LOG_FILE = "/var/log/bytebot-startup.log";
const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL || "";
const DISCORD_BOT_TOKEN = process.env.NOMI_BOT_TOKEN || "";
const ALERT_CHANNEL_ID = process.env.DISCORD_ALERT_CHANNEL_ID || "";

// Track active threads per component
const activeThreads = new Map<string, { threadId: string; lastFailTime: number }>();
const REOPEN_WINDOW_MS = 10 * 60 * 1000; // 10 minutes

const wss = new WebSocketServer({ port: 8787 });
const clients: WebSocket[] = [];

console.log("✅ Bytebot Ops WebSocket running on ws://localhost:8787");
console.log(`📜 Watching ${LOG_FILE}`);

wss.on("connection", (ws) => {
  clients.push(ws);
  ws.send(JSON.stringify({ type: "init", message: "Connected to Bytebot Ops feed" }));
  ws.on("close", () => clients.splice(clients.indexOf(ws), 1));
});

function extractContext(line: string): string {
  const match = line.match(/\[(SUCCESS|FAIL)\]\s+([a-zA-Z0-9_-]+)/);
  return match ? match[2] : "general";
}

async function postToThread(threadId: string, content: string) {
  await fetch(`https://discord.com/api/v10/channels/${threadId}/messages`, {
    method: "POST",
    headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}

async function sendDiscordAlert(eventType: string, message: string): Promise<string | undefined> {
  const context = extractContext(message);
  const title =
    eventType === "FAIL"
      ? `❌ ${context} Build Failure`
      : eventType === "MAINTENANCE"
      ? `🧹 Maintenance Task`
      : `ℹ️ Bytebot Update`;
  const color = eventType === "FAIL" ? 0xed4245 : 0x99aab5;

  const msg = await fetch(`https://discord.com/api/v10/channels/${ALERT_CHANNEL_ID}/messages`, {
    method: "POST",
    headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      embeds: [{ title, description: message, color, timestamp: new Date().toISOString() }],
    }),
  }).then((r) => r.json()) as any;

  const thread = await fetch(
    `https://discord.com/api/v10/channels/${ALERT_CHANNEL_ID}/messages/${msg.id}/threads`,
    {
      method: "POST",
      headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        name: `${context} — Build Failure ${new Date().toLocaleTimeString()}`,
        auto_archive_duration: 1440,
      }),
    }
  ).then((r) => r.json()) as any;

  return thread.id;
}

const tail = spawn("tail", ["-F", LOG_FILE]);
tail.stdout.on("data", async (data) => {
  const line = data.toString().trim();
  if (!/\[(SUCCESS|FAIL)\]/.test(line)) return;

  const eventType = line.includes("[FAIL]") ? "FAIL" : "SUCCESS";
  const context = extractContext(line);
  const message = line.replace(/\[.*?\]\s*/, "");
  const now = Date.now();

  if (eventType === "FAIL") {
    const previous = activeThreads.get(context);
    let threadId;
    if (previous && now - previous.lastFailTime < REOPEN_WINDOW_MS) {
      await postToThread(previous.threadId, `⚠️ ${context} failed again at ${new Date().toLocaleTimeString()}`);
      await fetch(`https://discord.com/api/v10/channels/${previous.threadId}`, {
        method: "PATCH",
        headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
        body: JSON.stringify({ archived: false }),
      });
      threadId = previous.threadId;
      console.log(`🔁 Reopened existing thread for ${context}`);
    } else {
      threadId = await sendDiscordAlert("FAIL", line);
      console.log(`🆕 New failure thread created for ${context}`);
    }
    activeThreads.set(context, { threadId, lastFailTime: now });
  }

  if (eventType === "SUCCESS" && activeThreads.has(context)) {
    const entry = activeThreads.get(context);
    if (entry) {
      const { threadId } = entry;
      await postToThread(
        threadId,
        `✅ ${context} recovered — rebuild succeeded at ${new Date().toLocaleTimeString()}`
      );
      await fetch(`https://discord.com/api/v10/channels/${threadId}`, {
        method: "PATCH",
        headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
        body: JSON.stringify({ archived: true }),
      });
      activeThreads.delete(context);
      console.log(`✅ ${context} recovered and thread archived.`);
    }
  }

  // Notify dashboard clients
  for (const ws of clients) {
    ws.send(JSON.stringify({ type: "ops_update", payload: { eventType, context, message, time: new Date() } }));
  }
});