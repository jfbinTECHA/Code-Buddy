#!/usr/bin/env python3
"""
Update Bytebot status badge JSON file
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def run_command(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def check_health():
    """Check overall system health"""
    try:
        # Check if health endpoint is responding
        stdout, stderr, code = run_command("curl -s http://localhost:9991/health")
        if code == 0 and stdout.strip() == '{"status":"ok"}':
            return "healthy", "All systems operational"
        else:
            return "degraded", "Health check failed"
    except Exception as e:
        return "unknown", f"Error: {str(e)}"

def get_service_status():
    """Get detailed service status"""
    try:
        stdout, stderr, code = run_command("cd /home/sysop/bytebot && python3 Code-Buddy/bytebotd/ops/bytebot_health.py")
        if code == 0:
            # Count healthy vs unhealthy services
            lines = stdout.split('\n')
            healthy = 0
            total = 0

            for line in lines:
                if 'bytebot-' in line.lower() or 'postgres' in line.lower() or 'redis' in line.lower() or 'chroma' in line.lower():
                    total += 1
                    if 'ok' in line.lower() or 'healthy' in line.lower() or 'up' in line.lower():
                        healthy += 1

            if total == 0:
                return "unknown", "No services detected"

            health_ratio = healthy / total
            if health_ratio == 1.0:
                return "healthy", f"All {total} services OK"
            elif health_ratio >= 0.5:
                return "degraded", f"{healthy}/{total} services OK"
            else:
                return "unhealthy", f"Only {healthy}/{total} services OK"
        else:
            return "unhealthy", "Health check script failed"
    except Exception as e:
        return "unknown", f"Status check error: {str(e)}"

def update_status_badge():
    """Update the status badge JSON file"""
    try:
        # Get overall health
        health_status, health_message = check_health()

        # Get detailed service status
        service_status, service_message = get_service_status()

        # Determine final status and color
        if health_status == "healthy" and service_status in ["healthy", "degraded"]:
            final_status = "healthy"
            color = "brightgreen"
            message = service_message
        elif service_status == "degraded":
            final_status = "degraded"
            color = "yellow"
            message = service_message
        else:
            final_status = "unhealthy"
            color = "red"
            message = health_message

        # Create badge JSON
        badge_data = {
            "schemaVersion": 1,
            "label": "Bytebot Health",
            "message": message,
            "color": color,
            "cacheSeconds": 300
        }

        # Write to file
        status_file = Path("/home/sysop/bytebot/docs/status.json")
        with open(status_file, 'w') as f:
            json.dump(badge_data, f, indent=2)

        print(f"Updated status badge: {final_status} - {message}")

    except Exception as e:
        print(f"Error updating status badge: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    update_status_badge()