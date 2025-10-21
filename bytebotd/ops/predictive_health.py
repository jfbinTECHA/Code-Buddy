#!/usr/bin/env python3
"""
Bytebot Predictive Health Analysis
Foundation for ML-powered anomaly detection and failure prediction
"""

import csv
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

def run_command(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def extract_recovery_events():
    """Extract recovery events from logs for analysis"""
    try:
        # Get recovery events from logs
        stdout, stderr, code = run_command("grep 'restarting affected containers' /tmp/bytebot-recovery.log")
        if code != 0:
            return []

        events = []
        for line in stdout.split('\n'):
            if line.strip():
                # Extract timestamp from log format [YYYY-MM-DD HH:MM:SS]
                if '[' in line and ']' in line:
                    timestamp_str = line.split('[')[1].split(']')[0]
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        events.append(timestamp)
                    except ValueError:
                        continue

        return sorted(events)
    except Exception as e:
        print(f"Error extracting recovery events: {e}")
        return []

def calculate_metrics(events):
    """Calculate basic predictive metrics from recovery events"""
    if len(events) < 2:
        return {
            "total_events": len(events),
            "avg_interval_hours": None,
            "failure_rate_per_day": None,
            "trend": "insufficient_data"
        }

    # Calculate intervals between events
    intervals = []
    for i in range(1, len(events)):
        interval = events[i] - events[i-1]
        intervals.append(interval.total_seconds() / 3600)  # Convert to hours

    avg_interval = sum(intervals) / len(intervals)
    failure_rate_per_day = 24 / avg_interval if avg_interval > 0 else 0

    # Simple trend analysis (are intervals getting shorter?)
    if len(intervals) >= 3:
        recent_avg = sum(intervals[-3:]) / 3
        earlier_avg = sum(intervals[:3]) / min(3, len(intervals))
        if recent_avg < earlier_avg * 0.8:  # 20% decrease
            trend = "worsening"
        elif recent_avg > earlier_avg * 1.2:  # 20% increase
            trend = "improving"
        else:
            trend = "stable"
    else:
        trend = "analyzing"

    return {
        "total_events": len(events),
        "avg_interval_hours": round(avg_interval, 2),
        "failure_rate_per_day": round(failure_rate_per_day, 2),
        "trend": trend,
        "last_event": events[-1].isoformat() if events else None
    }

def save_dataset(events, filename="/tmp/recovery_events.csv"):
    """Save recovery events to CSV for future ML analysis"""
    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'event_type'])
            for event in events:
                writer.writerow([event.isoformat(), 'recovery_triggered'])
        print(f"Dataset saved to {filename}")
    except Exception as e:
        print(f"Error saving dataset: {e}")

def predict_next_failure(metrics):
    """Simple prediction based on historical patterns"""
    if not metrics["avg_interval_hours"]:
        return "Cannot predict - insufficient data"

    # Simple exponential smoothing prediction
    next_failure = datetime.now() + timedelta(hours=metrics["avg_interval_hours"])

    if metrics["trend"] == "worsening":
        confidence = "High risk - failure rate increasing"
    elif metrics["trend"] == "improving":
        confidence = "Low risk - failure rate decreasing"
    else:
        confidence = "Moderate risk - stable pattern"

    return f"Next potential failure: {next_failure.strftime('%Y-%m-%d %H:%M:%S')} ({confidence})"

def main():
    """Main predictive analysis function"""
    print("🧮 Bytebot Predictive Health Analysis")
    print("=" * 50)

    # Extract events
    events = extract_recovery_events()
    print(f"📊 Found {len(events)} recovery events in logs")

    if not events:
        print("❌ No recovery events found for analysis")
        return

    # Calculate metrics
    metrics = calculate_metrics(events)
    print("\n📈 Health Metrics:")
    print(f"  Total recovery events: {metrics['total_events']}")
    print(f"  Average interval: {metrics['avg_interval_hours']} hours")
    print(f"  Failure rate: {metrics['failure_rate_per_day']} per day")
    print(f"  Trend: {metrics['trend']}")
    if metrics['last_event']:
        print(f"  Last event: {metrics['last_event']}")

    # Generate prediction
    prediction = predict_next_failure(metrics)
    print(f"\n🔮 Prediction: {prediction}")

    # Save dataset for future ML analysis
    save_dataset(events)

    print("\n💡 Recommendations:")
    if metrics["trend"] == "worsening":
        print("  ⚠️  System health is deteriorating - consider manual intervention")
    elif metrics["failure_rate_per_day"] > 2:
        print("  ⚠️  High failure rate detected - investigate root causes")
    else:
        print("  ✅ System appears stable")

if __name__ == "__main__":
    main()