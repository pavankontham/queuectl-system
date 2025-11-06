#!/usr/bin/env python3
"""
Simple wrapper for enqueuing jobs - easier to use than dealing with shell quoting
Usage: python enqueue.py --id JOB_ID --command "COMMAND" [OPTIONS]
"""

import json
import subprocess
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Enqueue a job to QueueCTL')
    parser.add_argument('--id', required=True, help='Unique job ID')
    parser.add_argument('--command', required=True, help='Command to execute')
    parser.add_argument('--max-retries', type=int, help='Maximum retry attempts')
    parser.add_argument('--priority', type=int, help='Job priority (lower = higher priority)')
    parser.add_argument('--timeout', type=int, help='Timeout in seconds')
    parser.add_argument('--run-at', help='Schedule job at specific time (ISO format)')
    
    args = parser.parse_args()
    
    # Build job object
    job = {
        'id': args.id,
        'command': args.command
    }
    
    if args.max_retries is not None:
        job['max_retries'] = args.max_retries
    
    if args.priority is not None:
        job['priority'] = args.priority
    
    if args.timeout is not None:
        job['timeout_seconds'] = args.timeout
    
    if args.run_at is not None:
        job['run_at'] = args.run_at
    
    # Convert to JSON
    job_json = json.dumps(job)
    
    # Call queuectl
    result = subprocess.run(
        ['python', 'queuectl.py', 'enqueue', job_json],
        capture_output=True,
        text=True
    )
    
    print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()

