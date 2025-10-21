#!/usr/bin/env python3
"""
Fixes absolute path issues and missing config for Bytebot Mission Control.
Run this once inside VS Code (Kilo Code) to repair everything automatically.
"""

import os, json, subprocess

# --- 1. Locate base directories ---
base_dir = os.path.abspath(os.path.dirname(__file__))
ops_dir = os.path.join(base_dir, "ops")
config_dir = os.path.join(base_dir, "config")
health_py = os.path.join(ops_dir, "bytebot_health.py")
recovery_script = os.path.join(ops_dir, "recover_bytebot.sh")
config_file = os.path.join(config_dir, "health_config.json")

# --- 2. Ensure config folder + file exist ---
os.makedirs(config_dir, exist_ok=True)
if not os.path.exists(config_file):
    print("Creating minimal health_config.json ...")
    config = {
        "services": [
            "bytebot-agent",
            "bytebot-ui",
            "bytebot-desktop",
            "bytebot-infra-redis-1-1",
            "bytebot-infra-postgres-1-1",
            "bytebot-infra-chroma-1-1"
        ],
        "thresholds": {"restart_failures": 5, "cpu_max": 90, "mem_max": 90}
    }
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

# --- 3. Patch bytebot_health.py to use absolute recovery path ---
if os.path.exists(health_py):
    text = open(health_py).read()
    if "./ops/recover_bytebot.sh" in text or "ops/recover_bytebot.sh" in text:
        patched = []
        for line in text.splitlines():
            if "recover_bytebot.sh" in line and "subprocess.run" in line:
                patched.append(
                    'repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))\n'
                    'script_path = os.path.join(repo_root, "ops", "recover_bytebot.sh")\n'
                    'subprocess.run([script_path] + failed_service_names, check=True)'
                )
            else:
                patched.append(line)
        open(health_py, "w").write("\n".join(patched))
        print("Patched bytebot_health.py with absolute path.")
    else:
        print("bytebot_health.py already uses absolute path.")
else:
    print("WARNING: bytebot_health.py not found!")

# --- 4. Show summary ---
print("\n✅ Fix complete.")
print(f"Health monitor: {health_py}")
print(f"Recovery script: {recovery_script}")
print(f"Config file: {config_file}")

# Optional: restart the dashboard automatically
try:
    subprocess.run(["pkill", "-f", "dashboard/server.py"], check=False)
    subprocess.Popen(["python3", "dashboard/server.py"], cwd=base_dir)
    print("🔄 Restarted dashboard/server.py")
except Exception as e:
    print("Could not restart dashboard automatically:", e)