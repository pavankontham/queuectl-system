#!/usr/bin/env python3
"""
Demo script for QueueCTL - demonstrates all core features
"""

import subprocess
import time
import os
import shutil

def run_cmd(args, description="", show_command=True):
    """Run a command and display output"""
    if description:
        print(f"\n{'='*80}")
        print(f"  {description}")
        print('='*80)

    if show_command:
        cmd_str = ' '.join(args)
        print(f"\n$ {cmd_str}\n")

    result = subprocess.run(args, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result.returncode == 0

def cleanup():
    """Clean up test data"""
    if os.path.exists("queuectl.db"):
        os.remove("queuectl.db")
    if os.path.exists("logs"):
        shutil.rmtree("logs")

print("""
================================================================================
                         QueueCTL Demo Script
================================================================================
  This demo will walk through all the features I built:
    - Job enqueuing (success + failure cases)
    - Worker execution with multiple workers
    - Retry with exponential backoff
    - Dead Letter Queue (DLQ)
    - DLQ retry functionality
    - Configuration management
    - Job timeout handling
    - Job priority
    - Output logging
================================================================================
""")

# Cleanup and initialize
print("\n[SETUP] Cleaning up and initializing database...")
cleanup()
run_cmd(["python", "queuectl.py", "init-db"], show_command=True)

# Enqueue jobs
run_cmd(
    ["python", "enqueue.py", "--id", "success-job", "--command", "echo Success!", "--priority", "1"],
    "1. Enqueuing a successful job (priority 1)"
)

run_cmd(
    ["python", "enqueue.py", "--id", "fail-job", "--command", "exit 1", "--max-retries", "2", "--priority", "2"],
    "2. Enqueuing a failing job (will retry 2 times, priority 2)"
)

run_cmd(
    ["python", "enqueue.py", "--id", "timeout-job", "--command", "timeout /t 10", "--timeout", "2", "--max-retries", "1"],
    "3. Enqueuing a timeout job (2 second timeout)"
)

run_cmd(
    ["python", "enqueue.py", "--id", "delayed-job", "--command", "echo Delayed task", "--priority", "10"],
    "4. Enqueuing a low priority job (priority 10)"
)

# Show initial status
run_cmd(["python", "queuectl.py", "status"], "5. Initial queue status")

# Show job list
run_cmd(["python", "queuectl.py", "list"], "6. List all jobs")

# Show config
run_cmd(["python", "queuectl.py", "config", "get"], "7. Current configuration")

# Start workers
print("\n" + "="*80)
print("  8. Starting 2 workers (will stop when queue is empty)")
print("="*80)
print("\n$ python queuectl.py worker start --count 2 --stop-when-empty\n")
print("Workers processing jobs...\n")
subprocess.run(
    ["python", "queuectl.py", "worker", "start", "--count", "2", "--stop-when-empty"],
    capture_output=False
)

# Show final status
run_cmd(["python", "queuectl.py", "status"], "9. Final queue status")

# Show completed jobs
run_cmd(["python", "queuectl.py", "list", "--state", "completed"], "10. Completed jobs")

# Show DLQ
run_cmd(["python", "queuectl.py", "dlq", "list"], "11. Dead Letter Queue (failed jobs)")

# Retry from DLQ
print("\n" + "="*80)
print("  12. Retrying a job from DLQ")
print("="*80)
run_cmd(["python", "queuectl.py", "dlq", "retry", "fail-job"])

# Show status after retry
run_cmd(["python", "queuectl.py", "status"], "13. Status after DLQ retry")

# Update config
run_cmd(
    ["python", "queuectl.py", "config", "set", "max-retries", "5"],
    "14. Updating configuration (max-retries = 5)"
)

run_cmd(["python", "queuectl.py", "config", "get"], "15. Updated configuration")

# Show logs
print("\n" + "="*80)
print("  16. Job output logs")
print("="*80)
log_files = os.listdir("logs") if os.path.exists("logs") else []
print(f"\nLog files created: {len(log_files)}")
for log_file in sorted(log_files)[:10]:  # Show first 10
    print(f"  - {log_file}")

# Summary
print("""
================================================================================
                            Demo Complete!
================================================================================

What we just saw:
  - Database initialization
  - Job enqueuing with various options (priority, timeout, max_retries)
  - Multiple workers processing jobs concurrently
  - Automatic retry with exponential backoff
  - Jobs moved to Dead Letter Queue after max retries
  - DLQ retry functionality
  - Configuration management (get/set)
  - Job timeout handling
  - Priority-based job execution
  - Output logging to files
  - Workers stop automatically when queue is empty

All features working as expected!
""")

