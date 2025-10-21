#!/usr/bin/env python3
"""
Bytebot Overview Generator
Auto-generates docs/bytebot-overview.md with current system status
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def run_command(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def get_health_status():
    """Get current health status from bytebot_health.py"""
    try:
        # Run health check script
        stdout, stderr, code = run_command("cd /home/sysop/bytebot && python3 Code-Buddy/bytebotd/ops/bytebot_health.py")

        if code == 0:
            # Try to parse as JSON first
            try:
                health_data = json.loads(stdout)
                return format_health_json(health_data)
            except json.JSONDecodeError:
                # Fall back to text formatting
                return format_health_text(stdout)
        else:
            return f"❌ Health check failed: {stderr}"
    except Exception as e:
        return f"❌ Error getting health status: {str(e)}"

def format_health_json(data):
    """Format health data from JSON"""
    lines = ["### Current Health Status (JSON)", ""]
    lines.append("| Service | Status | Details |")
    lines.append("|---------|--------|---------|")

    for service, info in data.items():
        if isinstance(info, dict):
            status = info.get('status', 'unknown')
            details = info.get('details', '')
        else:
            status = str(info)
            details = ""

        emoji = "🟢" if status.lower() in ['ok', 'healthy', 'up'] else "🔴"
        lines.append(f"| {service} | {emoji} {status} | {details} |")

    return "\n".join(lines)

def format_health_text(text):
    """Format health data from text output"""
    lines = ["### Current Health Status (Text)", ""]
    lines.append("```")
    lines.append(text)
    lines.append("```")
    return "\n".join(lines)

def get_recent_logs():
    """Get recent recovery logs"""
    try:
        stdout, stderr, code = run_command("tail -20 /tmp/bytebot-recovery.log")
        if code == 0:
            return stdout
        else:
            return "No recent logs available"
    except Exception as e:
        return f"Error reading logs: {str(e)}"

def generate_overview():
    """Generate the complete overview markdown"""

    # Get current health status
    health_status = get_health_status()

    # Get recent logs for timeline
    recent_logs = get_recent_logs()

    # Current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Read the template
    template_path = Path("/home/sysop/bytebot/docs/bytebot-overview.md")
    if not template_path.exists():
        print("Error: Template file not found")
        sys.exit(1)

    with open(template_path, 'r') as f:
        content = f.read()

    # Replace placeholders
    content = content.replace("<!-- SYSTEM HEALTH STATUS WILL BE AUTO-INSERTED HERE -->", health_status)
    content = content.replace("*This overview is auto-generated. Last updated: $(date)*", f"*This overview is auto-generated. Last updated: {timestamp}*")

    # Update timeline with recent events
    timeline_content = generate_timeline_from_logs(recent_logs)
    content = content.replace("""```mermaid
timeline
  title Bytebot Recovery Loop Events
  2025-10-20 : Health check failed (Redis)
  2025-10-20 : Auto-restart triggered
  2025-10-20 : Containers recovered
  2025-10-21 : Healthy state maintained
  2025-10-21 : Continuous monitoring active
```""", timeline_content)

    return content

def generate_timeline_from_logs(logs):
    """Generate timeline from recent logs"""
    lines = logs.strip().split('\n')
    timeline_events = []

    for line in lines[-10:]:  # Last 10 events
        if line.strip():
            # Extract timestamp and message
            if '[' in line and ']' in line:
                try:
                    timestamp = line.split('[')[1].split(']')[0]
                    message = line.split(']', 1)[1].strip()
                    timeline_events.append(f"  {timestamp} : {message}")
                except:
                    timeline_events.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} : {line.strip()}")

    if not timeline_events:
        timeline_events = [
            "  2025-10-21 : System monitoring active",
            "  2025-10-21 : Recovery service running"
        ]

    timeline_content = """```mermaid
timeline
  title Bytebot Recovery Loop Events"""

    for event in timeline_events[-8:]:  # Last 8 events
        timeline_content += "\n" + event

    timeline_content += "\n```"

    return timeline_content

def main():
    """Main function"""
    try:
        overview_content = generate_overview()

        # Write to output
        output_path = Path("/home/sysop/bytebot/docs/bytebot-overview.md")
        with open(output_path, 'w') as f:
            f.write(overview_content)

        print(f"Successfully generated overview at {output_path}")

    except Exception as e:
        print(f"Error generating overview: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()