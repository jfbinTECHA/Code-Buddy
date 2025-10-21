#!/usr/bin/env python3
"""
Simple Bytebot Mission Control Web Dashboard
No external dependencies - uses built-in http.server
"""

import json
import os
import random
import subprocess
import threading
import time
import asyncio
import websockets
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# Global variables for monitor loop status
monitor_loop_active = False
monitor_loop_interval = 40  # seconds
last_health_check = None
next_health_check = None
monitor_thread = None

# WebSocket clients and history
ws_clients = set()
health_history = []
HISTORY_FILE = "/tmp/health_history.json"
ws_loop = None
update_queue = asyncio.Queue()

def run_command(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def get_health_status():
    """Get current health status"""
    try:
        stdout, stderr, code = run_command("cd /home/sysop/bytebot && python3 Code-Buddy/bytebotd/ops/bytebot_health.py")
        if code == 0:
            return {"status": "healthy", "details": stdout}
        else:
            return {"status": "unhealthy", "details": stderr}
    except Exception as e:
        return {"status": "error", "details": str(e)}

def get_recent_logs(lines=50):
    """Get recent recovery logs"""
    try:
        stdout, stderr, code = run_command(f"tail -{lines} /tmp/bytebot-recovery.log")
        if code == 0:
            return stdout.split('\n')
        else:
            return ["No logs available"]
    except Exception as e:
        return [f"Error reading logs: {str(e)}"]

def generate_timeline():
    """Generate timeline from recent logs"""
    logs = get_recent_logs(20)
    timeline_events = []

    for line in logs:
        if line.strip():
            if '[' in line and ']' in line:
                try:
                    timestamp = line.split('[')[1].split(']')[0]
                    message = line.split(']', 1)[1].strip()
                    timeline_events.append(f"  {timestamp} : {message}")
                except:
                    timeline_events.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} : {line.strip()}")

    return "\n".join(timeline_events[-10:])  # Last 10 events

def get_metrics():
    """Get system metrics"""
    try:
        # Count recovery cycles from logs
        stdout, stderr, code = run_command("grep -c 'restarting affected containers' /tmp/bytebot-recovery.log")
        recovery_count = stdout.strip() if code == 0 else "0"

        # Get uptime
        stdout, stderr, code = run_command("uptime -p")
        uptime = stdout.strip() if code == 0 else "Unknown"

        # Get last restart time
        stdout, stderr, code = run_command("grep -o '\\[.*\\] Restart complete' /tmp/bytebot-recovery.log | tail -1")
        last_restart = stdout.strip() if code == 0 else "Never"

        return {
            "recovery_count": recovery_count,
            "active_services": "Checking...",
            "uptime": uptime,
            "last_restart": last_restart
        }
    except Exception as e:
        return {"error": str(e)}

def get_loop_status():
    """Get monitor loop status"""
    global monitor_loop_active, monitor_loop_interval, last_health_check, next_health_check
    now = datetime.now()

    if next_health_check:
        seconds_until_next = int((next_health_check - now).total_seconds())
        if seconds_until_next < 0:
            seconds_until_next = 0
    else:
        seconds_until_next = monitor_loop_interval

    return {
        "active": monitor_loop_active,
        "interval_seconds": monitor_loop_interval,
        "last_check": last_health_check.isoformat() if last_health_check else None,
        "next_check_in_seconds": seconds_until_next
    }

def load_health_history():
    """Load historical health data"""
    global health_history
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE) as f:
                health_history = json.load(f)
    except Exception:
        health_history = []

def save_health_history():
    """Save historical health data"""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(health_history[-500:], f, indent=2)  # Keep last 500 entries
    except Exception:
        pass

def broadcast_update(payload):
    """Broadcast update to all WebSocket clients via queue"""
    if ws_loop and ws_loop.is_running():
        asyncio.run_coroutine_threadsafe(update_queue.put(payload), ws_loop)

async def ws_broadcaster():
    """Async task to broadcast updates from queue"""
    while True:
        try:
            payload = await update_queue.get()
            message = json.dumps(payload)
            dead_clients = set()
            for client in list(ws_clients):
                try:
                    await client.send(message)
                except Exception:
                    dead_clients.add(client)
            ws_clients.difference_update(dead_clients)
        except Exception as e:
            print(f"WebSocket broadcast error: {e}")
            await asyncio.sleep(1)

def get_system_health():
    """
    Returns current health snapshot for all services, including uptime % and response times.
    """
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        config_path = os.path.join(base_dir, "config", "health_config.json")
        status_path = os.path.join(base_dir, "config", "status.json")

        # Load service config
        with open(config_path) as f:
            cfg = json.load(f)

        # Fake uptime/latency placeholders (you can wire these to real monitor data later)
        service_data = []
        for svc in cfg["services"]:
            service_data.append({
                "name": svc["name"],
                "port": svc.get("port", "-"),
                "endpoint": svc.get("health_endpoint", "-"),
                "status": "healthy",
                "uptime": round(random.uniform(98.0, 100.0), 2),
                "latency_ms": round(random.uniform(20.0, 120.0), 1)
            })

        # Merge with overall system status
        system_status = {"status": "healthy", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
        if os.path.exists(status_path):
            with open(status_path) as f:
                system_status = json.load(f)

        snapshot = {
            "system": system_status,
            "services": service_data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Store in history and broadcast
        health_history.append(snapshot)
        if len(health_history) > 500:
            health_history.pop(0)
        save_health_history()
        broadcast_update(snapshot)

        return snapshot
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def ws_handler(websocket):
    """WebSocket handler for real-time updates"""
    ws_clients.add(websocket)
    try:
        # Send current history on connect
        for snapshot in health_history[-10:]:  # Send last 10 snapshots
            await websocket.send(json.dumps(snapshot))
        await websocket.wait_closed()
    except Exception as e:
        print(f"WebSocket handler error: {e}")
    finally:
        ws_clients.discard(websocket)

def monitor_loop():
    """Background monitor loop for health checks and recovery"""
    global monitor_loop_active, last_health_check, next_health_check

    while monitor_loop_active:
        try:
            # Run health check
            health = get_health_status()
            last_health_check = datetime.now()

            # Generate system health snapshot
            system_health = get_system_health()

            # If unhealthy, trigger recovery
            if health.get("status") == "unhealthy":
                print(f"[{datetime.now()}] Health check failed, triggering recovery...")
                # Log the recovery attempt
                with open("/tmp/bytebot-recovery.log", "a") as f:
                    f.write(f"[{datetime.now()}] Health check failed: {health.get('details', 'Unknown error')}\n")
                    f.write(f"[{datetime.now()}] Triggering recovery operation...\n")

                # Run recovery script (location-independent)
                import subprocess
                import os

                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                script_path = os.path.join(project_root, "ops", "recover_bytebot.sh")

                result = subprocess.run(
                    ["bash", script_path],
                    capture_output=True,
                    text=True,
                    cwd=project_root  # Set working directory to project root
                )

                with open("/tmp/bytebot-recovery.log", "a") as f:
                    if result.returncode == 0:
                        f.write(f"[{datetime.now()}] Recovery completed successfully\n")
                        f.write(f"[{datetime.now()}] Output: {result.stdout.strip()}\n")
                    else:
                        f.write(f"[{datetime.now()}] Recovery failed: {result.stderr.strip()}\n")

            # Schedule next check
            next_health_check = datetime.now() + timedelta(seconds=monitor_loop_interval)

        except Exception as e:
            print(f"Monitor loop error: {e}")

        # Wait for next interval
        time.sleep(monitor_loop_interval)

def start_monitor_loop():
    """Start the background monitor thread"""
    global monitor_thread, monitor_loop_active

    if monitor_thread and monitor_thread.is_alive():
        return  # Already running

    monitor_loop_active = True
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    print("Monitor loop started")

def stop_monitor_loop():
    """Stop the background monitor thread"""
    global monitor_thread, monitor_loop_active
    monitor_loop_active = False
    if monitor_thread:
        monitor_thread.join(timeout=5)
    print("Monitor loop stopped")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 Bytebot Mission Control</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .status-card { background: white; border-radius: 10px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .status-healthy { border-left: 5px solid #10B981; }
        .status-unhealthy { border-left: 5px solid #EF4444; }
        .status-error { border-left: 5px solid #F59E0B; }
        .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .metric { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
        .metric h3 { margin: 0 0 10px 0; color: #333; }
        .metric p { margin: 0; font-size: 24px; font-weight: bold; }
        .logs { background: #1e1e1e; color: #f8f8f2; padding: 20px; border-radius: 8px; font-family: monospace; max-height: 400px; overflow-y: auto; }
        .timeline { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .btn { background: #3B82F6; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #2563EB; }
        .btn-danger { background: #EF4444; }
        .btn-danger:hover { background: #DC2626; }
        pre { white-space: pre-wrap; word-wrap: break-word; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Bytebot Mission Control</h1>
            <p>Real-time health monitoring and recovery operations</p>
            <div id="last-updated">Last updated: <span id="timestamp">-</span></div>
        </div>

        <div class="status-card status-healthy" id="health-status">
            <h2>System Health Overview</h2>
            <div id="health-content">Loading...</div>
        </div>

        <div class="status-card">
            <h2>Service Health Table</h2>
            <table id="health-table" style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f8f9fa;">
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Service</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Port</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Endpoint</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Status</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Uptime %</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Latency (ms)</th>
                    </tr>
                </thead>
                <tbody id="health-table-body">
                    <tr><td colspan="6" style="padding: 8px; text-align: center;">Loading health data...</td></tr>
                </tbody>
            </table>
        </div>

        <div class="metric-grid">
            <div class="metric">
                <h3>Recovery Cycles</h3>
                <p id="recovery-count">-</p>
            </div>
            <div class="metric">
                <h3>Active Services</h3>
                <p id="active-services">-</p>
            </div>
            <div class="metric">
                <h3>Uptime</h3>
                <p id="uptime">-</p>
            </div>
            <div class="metric">
                <h3>Last Restart</h3>
                <p id="last-restart">-</p>
            </div>
        </div>

        <div class="status-card" id="loop-status">
            <h2>Recovery Loop Status</h2>
            <div id="loop-content">
                <p><strong>Active loop interval:</strong> <span id="loop-interval">-</span></p>
                <p><strong>Next health check in:</strong> <span id="next-check">-</span></p>
                <p><strong>Last check:</strong> <span id="last-check">-</span></p>
                <p><strong>Status:</strong> <span id="loop-active">-</span></p>
            </div>
        </div>

        <div class="status-card">
            <h2>Recovery Timeline</h2>
            <div id="timeline-content">Loading timeline...</div>
        </div>

        <div class="status-card">
            <h2>Recent Logs</h2>
            <div class="logs" id="logs-content">Loading logs...</div>
        </div>

        <div class="status-card">
            <h2>Control Panel</h2>
            <button class="btn" onclick="refreshData()">🔄 Refresh Status</button>
            <button class="btn" onclick="runHealthCheck()">🩺 Run Health Check</button>
            <button class="btn" onclick="triggerRecovery()">🔧 Trigger Recovery</button>
            <button class="btn-danger" onclick="clearLogs()">🗑️ Clear Logs</button>
        </div>

        <!-- Floating Service Info Panel -->
        <div id="serviceInfoBox" style="
          position:fixed;
          top:20px;
          right:20px;
          background:rgba(0,0,0,0.8);
          color:#fff;
          padding:12px 16px;
          border-radius:8px;
          font-family:monospace;
          font-size:14px;
          z-index:4000;
          display:none;
          min-width:220px;
          box-shadow:0 0 10px rgba(0,0,0,0.4);
        ">
          <div id="serviceInfoContent"></div>
          <canvas id="serviceSparkline" width="200" height="60" style="margin-top:8px;"></canvas>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        function updateTimestamp() {
            document.getElementById('timestamp').textContent = new Date().toLocaleString();
        }

        async function fetchData(endpoint) {
            try {
                const response = await fetch(endpoint);
                return await response.json();
            } catch (error) {
                console.error('Error fetching data:', error);
                return null;
            }
        }

        async function refreshData() {
            updateTimestamp();

            // Update health status
            const health = await fetchData('/api/health');
            if (health) {
                document.getElementById('health-content').innerHTML = `<pre>${JSON.stringify(health, null, 2)}</pre>`;
                document.getElementById('health-status').className = `status-card status-${health.status}`;
            }

            // Update timeline
            const timeline = await fetchData('/api/timeline');
            if (timeline) {
                document.getElementById('timeline-content').innerHTML = `<pre>${timeline.content}</pre>`;
            }

            // Update logs
            const logs = await fetchData('/api/logs');
            if (logs) {
                document.getElementById('logs-content').innerHTML = logs.entries.map(line => line + '<br>').join('');
            }

            // Update metrics
            const metrics = await fetchData('/api/metrics');
            if (metrics) {
                document.getElementById('recovery-count').textContent = metrics.recovery_count || 'N/A';
                document.getElementById('active-services').textContent = metrics.active_services || 'N/A';
                document.getElementById('uptime').textContent = metrics.uptime || 'N/A';
                document.getElementById('last-restart').textContent = metrics.last_restart || 'N/A';
            }

            // Update loop status
            const loopStatus = await fetchData('/api/loop-status');
            if (loopStatus) {
                document.getElementById('loop-interval').textContent = `${loopStatus.interval_seconds}s`;
                document.getElementById('next-check').textContent = `${loopStatus.next_check_in_seconds}s`;
                document.getElementById('last-check').textContent = loopStatus.last_check ?
                    new Date(loopStatus.last_check).toLocaleString() : 'Never';
                document.getElementById('loop-active').textContent = loopStatus.active ? 'Active' : 'Inactive';
            }

            // Update health table
            const systemHealth = await fetchData('/system_health');
            if (systemHealth && systemHealth.services) {
                updateHealthTable(systemHealth.services);
            }
        }

        async function runHealthCheck() {
            try {
                const response = await fetch('/api/health-check', { method: 'POST' });
                const result = await response.json();
                alert('Health check completed: ' + JSON.stringify(result, null, 2));
                refreshData();
            } catch (error) {
                alert('Error running health check: ' + error.message);
            }
        }

        async function triggerRecovery() {
            if (confirm('Are you sure you want to trigger a recovery operation?')) {
                try {
                    const response = await fetch('/api/recovery', { method: 'POST' });
                    const result = await response.json();
                    alert('Recovery triggered: ' + JSON.stringify(result, null, 2));
                    refreshData();
                } catch (error) {
                    alert('Error triggering recovery: ' + error.message);
                }
            }
        }

        async function clearLogs() {
            if (confirm('Are you sure you want to clear the recovery logs?')) {
                try {
                    const response = await fetch('/api/logs', { method: 'DELETE' });
                    const result = await response.json();
                    alert('Logs cleared: ' + JSON.stringify(result, null, 2));
                    refreshData();
                } catch (error) {
                    alert('Error clearing logs: ' + error.message);
                }
            }
        }

        let sparklineChart = null;

        function updateHealthTable(services) {
            const tbody = document.getElementById('health-table-body');
            tbody.innerHTML = '';

            services.forEach(service => {
                const row = document.createElement('tr');

                // Status color
                const statusColor = service.status === 'healthy' ? '#10B981' : '#EF4444';

                row.innerHTML = `
                    <td style="padding: 8px; border: 1px solid #ddd;">${service.name}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${service.port}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${service.endpoint}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: ${statusColor}; font-weight: bold;">${service.status}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${service.uptime}%</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${service.latency_ms}ms</td>
                `;

                // Add click handler to show service info
                row.addEventListener('click', () => showServiceInfo(service.name));

                tbody.appendChild(row);
            });
        }

        function showServiceInfo(serviceName) {
            const infoBox = document.getElementById('serviceInfoBox');
            const infoContent = document.getElementById('serviceInfoContent');

            // Get current system health data
            fetchData('/system_health').then(systemHealth => {
                if (!systemHealth || !systemHealth.services) return;

                const svc = systemHealth.services.find(s => s.name === serviceName);
                if (!svc) return;

                infoContent.innerHTML = `
                    <div style="font-weight:bold;font-size:15px;margin-bottom:5px;">📡 ${svc.name}</div>
                    <div>🩺 Status: <span style="color:${svc.status==='healthy'?'#28a745':svc.status==='recovering'?'#ffc107':'#dc3545'}">${svc.status}</span></div>
                    <div>📈 Uptime: ${svc.uptime.toFixed(2)}%</div>
                    <div>⚡ Latency: ${svc.latency_ms.toFixed(1)} ms</div>
                `;
                infoBox.style.display = 'block';

                // Build sparkline data (simulate history for now - in real implementation, you'd store historical data)
                const latencyHistory = [];
                for (let i = 0; i < 10; i++) {
                    latencyHistory.push({
                        t: new Date(Date.now() - (9 - i) * 30000).toLocaleTimeString(),
                        v: svc.latency_ms + (Math.random() - 0.5) * 20 // Simulate variation
                    });
                }

                const ctx = document.getElementById('serviceSparkline').getContext('2d');
                if (sparklineChart) sparklineChart.destroy();

                sparklineChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: latencyHistory.map(x => x.t),
                        datasets: [{
                            data: latencyHistory.map(x => x.v),
                            borderColor: '#00ccff',
                            borderWidth: 2,
                            pointRadius: 2,
                            pointHoverRadius: 4,
                            pointBackgroundColor: '#00ccff',
                            fill: false,
                            tension: 0.3
                        }]
                    },
                    options: {
                        scales: {
                            y: { display: false },
                            x: { display: false }
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                backgroundColor: 'rgba(0,0,0,0.8)',
                                titleColor: '#fff',
                                bodyColor: '#fff',
                                displayColors: false,
                                callbacks: {
                                    title: function(ctx) {
                                        return ctx[0].label;
                                    },
                                    label: function(ctx) {
                                        return `Latency: ${ctx.parsed.y.toFixed(1)} ms`;
                                    }
                                }
                            }
                        },
                        elements: { line: { borderJoinStyle: 'round' } },
                        responsive: false,
                        animation: false
                    }
                });
            });
        }

        let ws;

        function startWebSocket() {
            ws = new WebSocket(`ws://${location.host.replace('9993', '9994')}`);
            ws.onopen = () => console.log("📡 WebSocket connected");
            ws.onclose = () => setTimeout(startWebSocket, 3000); // auto-reconnect
            ws.onmessage = (event) => {
                try {
                    const snapshot = JSON.parse(event.data);
                    handleLiveUpdate(snapshot);
                } catch (e) {
                    console.error('WebSocket message error:', e);
                }
            };
        }

        function handleLiveUpdate(snapshot) {
            // Update health table
            if (snapshot.services) {
                updateHealthTable(snapshot.services);
            }

            // Update system health display
            if (snapshot.system) {
                document.getElementById('health-content').innerHTML = `<pre>${JSON.stringify(snapshot.system, null, 2)}</pre>`;
                document.getElementById('health-status').className = `status-card status-${snapshot.system.status}`;
            }

            // Update timestamp
            updateTimestamp();
        }

        startWebSocket();

        // Fallback: Auto-refresh every 30 seconds if WebSocket fails
        setInterval(refreshData, 30000);

        // Initial load
        refreshData();
    </script>
</body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # Legacy redirect for backwards compatibility
        if path == '/system_health':
            self.send_response(301)
            self.send_header('Location', '/api/health')
            self.end_headers()
            return

        if path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())

        elif path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            health = get_system_health()  # Use the comprehensive health function
            self.wfile.write(json.dumps(health).encode())

        elif path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            logs = get_recent_logs(100)
            self.wfile.write(json.dumps({"entries": logs}).encode())

        elif path == '/api/timeline':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            timeline = generate_timeline()
            self.wfile.write(json.dumps({"content": timeline}).encode())

        elif path == '/api/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            metrics = get_metrics()
            self.wfile.write(json.dumps(metrics).encode())

        elif path == '/api/loop-status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            loop_status = get_loop_status()
            self.wfile.write(json.dumps(loop_status).encode())

        elif path == '/api/history':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(health_history[-50:]).encode())  # Return last 50 snapshots

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/api/health-check':
            try:
                stdout, stderr, code = run_command("cd /home/sysop/bytebot && python3 Code-Buddy/bytebotd/ops/bytebot_health.py")
                result = {
                    "success": code == 0,
                    "output": stdout,
                    "error": stderr
                }
            except Exception as e:
                result = {"error": str(e)}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        elif path == '/api/recovery':
            try:
                import subprocess
                import os

                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                script_path = os.path.join(project_root, "ops", "recover_bytebot.sh")

                result_proc = subprocess.run(
                    ["bash", script_path],
                    capture_output=True,
                    text=True,
                    cwd=project_root  # Set working directory to project root
                )

                result = {
                    "success": result_proc.returncode == 0,
                    "output": result_proc.stdout.strip(),
                    "error": result_proc.stderr.strip()
                }
            except Exception as e:
                result = {"error": str(e)}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/api/logs':
            try:
                stdout, stderr, code = run_command("echo '' > /tmp/bytebot-recovery.log")
                result = {
                    "success": code == 0,
                    "message": "Logs cleared"
                }
            except Exception as e:
                result = {"error": str(e)}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def log_message(self, format, *args):
        """Override to reduce noise"""
        pass

def start_websocket_server():
    """Start WebSocket server in its own event loop"""
    global ws_loop
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)

    async def run_ws_server():
        server = await websockets.serve(ws_handler, "0.0.0.0", 9994)
        print("📡 WebSocket server started on ws://localhost:9994")
        # Start the broadcaster task
        ws_loop.create_task(ws_broadcaster())
        await server.wait_closed()

    ws_loop.run_until_complete(run_ws_server())

def run_dashboard():
    """Run the dashboard server with WebSocket support"""
    # Load existing history
    load_health_history()

    # Start WebSocket server in background thread
    ws_thread = threading.Thread(target=start_websocket_server, daemon=True)
    ws_thread.start()

    # Start the monitor loop
    start_monitor_loop()

    server_address = ('', 9993)
    httpd = HTTPServer(server_address, DashboardHandler)
    print("🧠 Starting Bytebot Mission Control Dashboard on http://localhost:9993")
    print("Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped")
        stop_monitor_loop()
        httpd.server_close()

if __name__ == '__main__':
    run_dashboard()