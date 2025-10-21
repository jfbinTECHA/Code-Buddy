#!/usr/bin/env python3
"""
Kilo Dashboard — HTML + JSON + WebSocket live updates + Restart controls
- HTTP (port 9993): "/" (HTML), "/json" (raw JSON), "/restart?svc=<name>"
- WebSocket (port 9994): broadcasts the latest JSON every 5s and on actions
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json, os, time, html, urllib.parse, subprocess, threading, asyncio
import websockets

LOG_PATH = "/tmp/kilo_master_status.json"
LOG_FILE = "/var/log/kilo-dashboard.log"
SERVICES = ["infra-redis-1", "bytebot-postgres", "infra-chroma-1",
            "bytebot-agent", "bytebot-desktop", "bytebot-ui"]
ENV_PATH = os.path.expanduser("~/bytebot/Code-Buddy/bytebotd/docker/.env")

def read_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k,v = line.strip().split("=",1)
                    env[k]=v
    return env

def write_env(env_dict):
    with open(ENV_PATH,"w") as f:
        for k,v in env_dict.items():
            f.write(f"{k}={v}\n")

# -------------------------
# helpers
# -------------------------
def load_status():
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH) as f:
                return json.load(f)
        except Exception as e:
            return {"status": f"error_loading_json: {e}", "timestamp": ts_utc()}
    return {"status": "no_log_found", "timestamp": ts_utc()}

def ts_utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def restart_service(name):
    stamp = ts_utc()
    log = f"[{stamp}] Restart requested: {name}\n"
    try:
        subprocess.run(["docker", "restart", name], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log += f" -> restarted via: docker restart {name}\n"
    except subprocess.CalledProcessError:
        subprocess.run(["docker", "compose", "up", "-d", name])
        log += f" -> fallback: docker compose up -d {name}\n"
    with open(LOG_FILE, "a") as f:
        f.write(log)
    return log

# -------------------------
# WebSocket broadcaster (async)
# -------------------------
WS_PORT = 9994
_ws_clients = set()
_ws_loop = None

async def ws_handler(websocket):
    _ws_clients.add(websocket)
    try:
        # send immediately on connect
        await websocket.send(json.dumps(load_status()))
        async for _ in websocket:  # keep alive; we don't expect client messages
            pass
    finally:
        _ws_clients.discard(websocket)

async def ws_broadcast(payload: dict):
    if not _ws_clients:
        return
    msg = json.dumps(payload)
    await asyncio.gather(*[ws.send(msg) for ws in list(_ws_clients)], return_exceptions=True)

async def ws_publisher():
    # periodic push of the latest status
    while True:
        try:
            await ws_broadcast(load_status())
        except Exception:
            pass
        await asyncio.sleep(5)

def start_ws_server():
    global _ws_loop
    _ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_ws_loop)
    async def run_server():
        server = await websockets.serve(ws_handler, "0.0.0.0", WS_PORT)
        print(f"[INFO] Kilo WS server on ws://localhost:{WS_PORT}")
        await server.wait_closed()
    _ws_loop.create_task(ws_publisher())
    _ws_loop.run_until_complete(run_server())

def trigger_ws_push_now():
    # safe trigger from HTTP thread
    if _ws_loop and _ws_loop.is_running():
        asyncio.run_coroutine_threadsafe(ws_broadcast(load_status()), _ws_loop)

# -------------------------
# HTTP server (HTML + JSON + restart)
# -------------------------
class KiloHandler(BaseHTTPRequestHandler):
    def _send(self, code=200, ctype="text/html"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/update_keys":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body)
                openai = payload.get("OPENAI_API_KEY", "").strip()
                grok = payload.get("GROK_API_KEY", "").strip()
            except Exception:
                self.send_error(400, "Bad JSON")
                return

            # basic validation
            updated = []
            env_path = os.path.expanduser("~/bytebot/Code-Buddy/bytebotd/docker/.env")
            lines = []
            if os.path.exists(env_path):
                with open(env_path) as f:
                    lines = f.readlines()
            new_lines = []
            for line in lines:
                if line.startswith("OPENAI_API_KEY=") and openai:
                    new_lines.append(f"OPENAI_API_KEY={openai}\n")
                    updated.append("OpenAI")
                elif line.startswith("GROK_API_KEY=") and grok:
                    new_lines.append(f"GROK_API_KEY={grok}\n")
                    updated.append("Grok")
                else:
                    new_lines.append(line)
            with open(env_path, "w") as f:
                f.writelines(new_lines)

            # restart agent container only
            if updated:
                subprocess.run(["docker","compose","restart","bytebot-agent"])
                msg = f"[INFO] Updated: {', '.join(updated)} key(s) & restarted agent."
            else:
                msg = "[WARN] No valid keys provided."

            with open(LOG_FILE, "a") as f: f.write(msg + "\n")
            trigger_ws_push_now()
            self._send(200, "text/plain")
            self.wfile.write(msg.encode())
            return

        # --- trigger full environment validation ---
        if parsed.path == "/validate":
            import subprocess
            log = "[INFO] Validation triggered manually via dashboard.\n"
            try:
                subprocess.run(
                    ["bash", "ops/kilo_env_check.sh"],
                    cwd="/home/sysop/bytebot/Code-Buddy/bytebotd",
                    check=True
                )
                msg = "[PASS] Environment validation complete. See /tmp/kilo_env_status.json"
                log += msg + "\n"
            except subprocess.CalledProcessError:
                msg = "[FAIL] Validation script returned an error. Check /tmp/kilo_env_status.json"
                log += msg + "\n"

            with open(LOG_FILE, "a") as f:
                f.write(log)
            trigger_ws_push_now()

            self._send(200, "text/plain")
            self.wfile.write(msg.encode())
            return

        # --- trigger full pipeline run ---
        if parsed.path == "/run_pipeline":
            import subprocess
            log = "[INFO] Full pipeline run triggered via dashboard.\n"
            self._send(200, "text/plain")
            self.wfile.write(b"[INFO] Pipeline started; check logs for updates...")

            # Run the master script asynchronously so HTTP doesn't hang
            def _run_pipeline():
                try:
                    proc = subprocess.Popen(
                        ["bash", "ops/kilo_master.sh"],
                        cwd="/home/sysop/bytebot/Code-Buddy/bytebotd",
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )
                    for line in proc.stdout:
                        # Write each line to the dashboard log
                        with open(LOG_FILE, "a") as f:
                            f.write(line)
                        # Broadcast snippets live to WebSocket clients
                        try:
                            asyncio.run_coroutine_threadsafe(
                                ws_broadcast({"pipeline_log": line.strip()}), _ws_loop
                            )
                        except Exception:
                            pass
                    proc.wait()
                    asyncio.run_coroutine_threadsafe(
                        ws_broadcast({"pipeline_done": True}), _ws_loop
                    )
                except Exception as e:
                    with open(LOG_FILE, "a") as f:
                        f.write(f"[FAIL] Pipeline crashed: {e}\n")

            threading.Thread(target=_run_pipeline, daemon=True).start()
            return

        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/env":
            length = int(self.headers.get("Content-Length",0))
            payload = json.loads(self.rfile.read(length))
            env = read_env()
            changed=False

            # add/update/remove based on payload
            for k,v in payload.items():
                if v == "":  # empty string means delete
                    if k in env:
                        del env[k]
                        changed=True
                else:
                    if env.get(k)!=v:
                        env[k]=v
                        changed=True

            if changed:
                write_env(env)
                subprocess.run(["docker","compose","restart","bytebot-agent"])
                msg="[PASS] Environment updated & agent restarted."
                trigger_ws_push_now()
            else:
                msg="[INFO] No changes applied."

            self._send(200, "text/plain")
            self.wfile.write(msg.encode())
            return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.strip("/")
        query = urllib.parse.parse_qs(parsed.query)
        data = load_status()

        if path == "env":
            env = read_env()
            self._send(200,"application/json")
            self.wfile.write(json.dumps(env,indent=2).encode())
            return

        # restart endpoint
        if path == "restart" and "svc" in query:
            svc = query["svc"][0]
            if svc in SERVICES:
                restart_service(svc)
                # push an immediate WS update so UI flips live
                trigger_ws_push_now()
                self._send(200, "text/plain")
                self.wfile.write(f"[INFO] Restart triggered for {svc}".encode())
                return
            self._send(400, "text/plain")
            self.wfile.write(f"[ERROR] Unknown service: {svc}".encode())
            return

        # raw JSON
        if path == "json":
            self._send(200, "application/json")
            self.wfile.write(json.dumps(data, indent=2).encode())
            return

        # HTML dashboard (with WS client)
        self._send()
        ts = html.escape(data.get("timestamp", "unknown"))
        env = data.get("environment", {})
        health = data.get("health", {})

        def badge(state):
            good = {"up", "200", "ok", "true"}
            color = "limegreen" if str(state).lower() in good else "red"
            return f"<span style='color:{color};'>{html.escape(str(state))}</span>"

        rows = ""
        for svc, state in health.items():
            rows += (
                f"<tr><th>{html.escape(svc.title())}</th>"
                f"<td class='st' data-svc='{html.escape(svc)}'>{badge(state)}</td>"
                f"<td><a href='/restart?svc={svc}'><button>Restart</button></a></td></tr>"
            )

        body = f"""
        <html><head>
        <title>Kilo Dashboard (Live)</title>
        <style>
          body {{ background:#111; color:#eee; font-family:monospace; }}
          h1 {{ color:#0ff; }}
          table {{ border-collapse:collapse; width:80%; }}
          td,th {{ padding:6px 10px; border-bottom:1px solid #333; }}
          button {{ background:#0ff; color:#000; border:none; padding:4px 8px; cursor:pointer; }}
          button:hover {{ background:#fff; }}
          a {{ color:#0ff; }}
          input {{ background:#222; color:#eee; border:1px solid #333; padding:2px; }}
        </style>
        </head><body>
        <h1>Kilo Dashboard — Bytebot System (Live)</h1>
        <p>Last Update: <span id="ts">{ts}</span> | <a href="/json">Raw JSON</a></p>

        <h2>Validation</h2>
        <button id="valBtn" onclick="runValidation()">Validate Now</button>
        <span id="valMsg"></span>

        <h2>Full Pipeline</h2>
        <button id="pipeBtn" onclick="runPipeline()">Run Full Pipeline</button>
        <div id="pipeLog" style="background:#000;color:#0f0;font-family:monospace;
        padding:6px;height:200px;overflow:auto;border:1px solid #333;"></div>

        <h2>API Key Console</h2>
        <form id="keyform" onsubmit="return updateKeys(event)">
          <label>OpenAI Key:</label>
          <input id="openai" type="password" size="50" placeholder="sk-..." />
          <br/>
          <label>Grok Key:</label>
          <input id="grok" type="password" size="50" placeholder="xai-..." />
          <br/>
          <button type="submit">Save</button>
          <span id="saveStatus"></span>
        </form>

        <h2>Environment Console</h2>
        <div id="envTable"></div>
        <button onclick="addRow()">+ Add Variable</button>
        <button onclick="saveEnv()">Save Changes</button>
        <span id="envMsg"></span>

        <h2>Environment</h2>
        <table id="env">
          <tr><th>OpenAI Key</th><td id="env-openai">{badge(env.get('openai_key_present'))}</td></tr>
          <tr><th>Grok Key</th><td id="env-grok">{badge(env.get('grok_key_present'))}</td></tr>
          <tr><th>OpenAI Conn</th><td id="env-openai-conn">{badge(env.get('openai_connection'))}</td></tr>
          <tr><th>Grok Conn</th><td id="env-grok-conn">{badge(env.get('grok_connection'))}</td></tr>
        </table>

        <h2>Health</h2>
        <table id="health">
          {rows}
        </table>

        <script>
        function colorize(v) {{
          const good = new Set(['up','200','ok','true']);
          const s = String(v).toLowerCase();
          const col = good.has(s) ? 'limegreen' : 'red';
          return `<span style="color:${{col}};">${{v}}</span>`;
        }}
        function applyStatus(data) {{
          if (!data) return;
          const ts = data.timestamp || 'unknown';
          document.getElementById('ts').textContent = ts;

          const env = data.environment || {{}};
          const health = data.health || {{}};

          const map = [
            ['env-openai', env.openai_key_present],
            ['env-grok', env.grok_key_present],
            ['env-openai-conn', env.openai_connection],
            ['env-grok-conn', env.grok_connection],
          ];
          for (const [id,val] of map) {{
            const el = document.getElementById(id);
            if (el) el.innerHTML = colorize(val);
          }}

          // update each service row cell with class 'st'
          document.querySelectorAll('td.st').forEach(td => {{
            const svc = td.getAttribute('data-svc');
            if (svc in health) td.innerHTML = colorize(health[svc]);
          }});
        }}

        async function runValidation(){{
          document.getElementById('valMsg').textContent='[INFO] Running validation...';
          const res = await fetch('/validate', {{method:'POST'}});
          const txt = await res.text();
          document.getElementById('valMsg').textContent = txt;
        }}

        async function runPipeline(){{
          const logBox=document.getElementById('pipeLog');
          logBox.textContent='[INFO] Pipeline started...';
          await fetch('/run_pipeline',{{method:'POST'}});
        }}

        async function updateKeys(ev){{
          ev.preventDefault();
          const payload = {{
            OPENAI_API_KEY: document.getElementById('openai').value,
            GROK_API_KEY: document.getElementById('grok').value
          }};
          const res = await fetch('/update_keys', {{
            method:'POST', headers:{{'Content-Type':'application/json'}},
            body: JSON.stringify(payload)
          }});
          const msg = await res.text();
          document.getElementById('saveStatus').textContent = msg;
        }}

        async function loadEnv(){{
          const data=await fetch('/env').then(r=>r.json());
          const tbl=['<table><tr><th>Key</th><th>Value</th><th></th></tr>'];
          for(const [k,v] of Object.entries(data)){{
            tbl.push(`<tr><td><input value="${k}" class="ek"></td>
                      <td><input value="${v}" class="ev"></td>
                      <td><button onclick="delRow(this)">x</button></td></tr>`);
          }}
          tbl.push('</table>');
          document.getElementById('envTable').innerHTML=tbl.join('');
        }}
        function addRow(){{
          const t=document.querySelector('#envTable table');
          t.insertAdjacentHTML('beforeend',"<tr><td><input class='ek'></td><td><input class='ev'></td><td><button onclick='delRow(this)'>x</button></td></tr>");
        }}
        function delRow(btn){{ btn.closest('tr').remove(); }}

        async function saveEnv(){{
          const keys=document.querySelectorAll('.ek');
          const vals=document.querySelectorAll('.ev');
          const obj={{}};
          for(let i=0;i<keys.length;i++){{
            const k=keys[i].value.trim();
            const v=vals[i].value.trim();
            if(k) obj[k]=v;
          }}
          const res=await fetch('/env',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(obj)}});
          document.getElementById('envMsg').textContent=await res.text();
        }}
        loadEnv();

        // WebSocket client
        (function() {{
          const url = `ws://` + window.location.hostname + `:9994`;
          let ws;
          function connect() {{
            ws = new WebSocket(url);
            ws.onmessage = (e) => {{
              try {{
                const data = JSON.parse(e.data);
                applyStatus(data);
                if (data.pipeline_log){{
                  const logBox=document.getElementById('pipeLog');
                  if(logBox){{
                    logBox.textContent += "\n" + data.pipeline_log;
                    logBox.scrollTop = logBox.scrollHeight;
                  }}
                }}
                if (data.pipeline_done){{
                  const logBox=document.getElementById('pipeLog');
                  if(logBox){{
                    logBox.textContent += "\n[INFO] Pipeline completed.";
                  }}
                }}
              }} catch {{ }}
            }};
            ws.onclose = () => setTimeout(connect, 2000); // auto-reconnect
          }}
          connect();
        }})();
        </script>

        </body></html>
        """
        self.wfile.write(body.encode())

if __name__ == "__main__":
    # start WS server in a background thread
    t = threading.Thread(target=start_ws_server, daemon=True)
    t.start()

    # start HTTP server
    httpd = HTTPServer(("0.0.0.0", 9993), KiloHandler)
    print("[INFO] Kilo Dashboard running on http://localhost:9993  (WS on :9994)")
    httpd.serve_forever()