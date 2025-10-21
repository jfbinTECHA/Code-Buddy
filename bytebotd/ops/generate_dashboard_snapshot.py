#!/usr/bin/env python3
"""
Generate static HTML snapshot of Bytebot Mission Control dashboard for GitHub Pages
"""

import sys
import os
from pathlib import Path

# Add the ops directory to Python path
sys.path.append(str(Path(__file__).parent))

from generate_overview import get_health_status, get_recent_logs
from datetime import datetime

def get_recent_logs_simple(lines=20):
    """Get recent recovery logs (simplified version)"""
    try:
        stdout, stderr, code = run_command(f"tail -{lines} /tmp/bytebot-recovery.log")
        if code == 0:
            return stdout.split('\n')
        else:
            return ["No logs available"]
    except Exception as e:
        return [f"Error reading logs: {str(e)}"]

def generate_dashboard_snapshot():
    """Generate a static HTML snapshot of the dashboard"""

    # Get current system data
    health = get_health_status()
    logs = get_recent_logs_simple(20)

    # Determine status class (health is a string from generate_overview.py)
    status_class = 'healthy' if 'healthy' in health.lower() or 'ok' in health.lower() else 'unhealthy'

    # Generate HTML
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Bytebot Mission Control - Static Snapshot</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .status {{ padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .healthy {{ background: #d4edda; border: 1px solid #c3e6cb; }}
        .unhealthy {{ background: #f8d7da; border: 1px solid #f5c6cb; }}
        .logs {{ background: #f8f9fa; padding: 15px; border-radius: 5px; font-family: monospace; }}
    </style>
</head>
<body>
    <h1>🧠 Bytebot Mission Control - Static Snapshot</h1>
    <p><em>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</em></p>

    <div class="status {status_class}">
        <h2>System Health: {status_class.upper()}</h2>
        <pre>{health}</pre>
    </div>

    <h2>Recent Recovery Logs</h2>
    <div class="logs">
        {''.join([f'{line}<br>' for line in logs])}
    </div>

    <p><small>This is a static snapshot. For real-time monitoring, visit the live dashboard at http://localhost:9993</small></p>
</body>
</html>'''

    # Write to file
    output_path = Path('/home/sysop/bytebot/docs/dashboard.html')
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Generated dashboard snapshot at {output_path}")

if __name__ == "__main__":
    generate_dashboard_snapshot()