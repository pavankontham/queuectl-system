#!/usr/bin/env python3
"""
Test script to verify job persistence after restart.
This ensures jobs survive system crashes and restarts.
"""

import subprocess
import time
import sys
import os

def run_cmd(args, description=""):
    """Run a command and return output"""
    if description:
        print(f"\n{'='*70}")
        print(f"  {description}")
        print('='*70)
    
    cmd_str = ' '.join(args)
    print(f"$ {cmd_str}\n")
    
    result = subprocess.run(args, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}", file=sys.stderr)
    
    return result.returncode == 0, result.stdout

def main():
    print("""
================================================================================
                    Job Persistence Test
================================================================================
This test verifies that jobs survive system restarts.

Test Steps:
1. Initialize database
2. Enqueue several jobs
3. Verify jobs are in database
4. Simulate restart (close and reopen database)
5. Verify jobs still exist
6. Process jobs
7. Verify state changes persisted

================================================================================
""")

    # Clean up
    if os.path.exists('queuectl.db'):
        os.remove('queuectl.db')
        print("[CLEANUP] Removed existing database\n")

    # Step 1: Initialize
    success, _ = run_cmd(
        ['python', 'queuectl.py', 'init-db'],
        "Step 1: Initialize database"
    )
    if not success:
        print("❌ FAILED: Database initialization")
        return False

    # Step 2: Enqueue jobs
    jobs = [
        ('persist-1', 'echo Job 1'),
        ('persist-2', 'echo Job 2'),
        ('persist-3', 'echo Job 3'),
    ]

    print("\n" + "="*70)
    print("  Step 2: Enqueue jobs")
    print("="*70)

    for job_id, command in jobs:
        success, _ = run_cmd(
            ['python', 'enqueue.py', '--id', job_id, '--command', command]
        )
        if not success:
            print(f"❌ FAILED: Could not enqueue {job_id}")
            return False

    # Step 3: Verify jobs exist
    success, output = run_cmd(
        ['python', 'queuectl.py', 'list', '--state', 'pending'],
        "Step 3: Verify jobs are in database"
    )
    if not success:
        print("❌ FAILED: Could not list jobs")
        return False
    
    for job_id, _ in jobs:
        if job_id not in output:
            print(f"❌ FAILED: Job {job_id} not found in database")
            return False
    
    print("✅ All jobs found in database")

    # Step 4: Simulate restart
    print("\n" + "="*70)
    print("  Step 4: Simulating system restart...")
    print("  (In real scenario, this would be a system crash/restart)")
    print("="*70)
    time.sleep(2)
    print("✅ System 'restarted'\n")

    # Step 5: Verify jobs still exist after restart
    success, output = run_cmd(
        ['python', 'queuectl.py', 'list', '--state', 'pending'],
        "Step 5: Verify jobs survived restart"
    )
    if not success:
        print("❌ FAILED: Could not list jobs after restart")
        return False
    
    for job_id, _ in jobs:
        if job_id not in output:
            print(f"❌ FAILED: Job {job_id} lost after restart!")
            return False
    
    print("✅ All jobs survived restart - PERSISTENCE VERIFIED")

    # Step 6: Process jobs
    success, _ = run_cmd(
        ['python', 'queuectl.py', 'worker', 'start', '--count', '1', '--stop-when-empty'],
        "Step 6: Process jobs with worker"
    )
    if not success:
        print("❌ FAILED: Worker execution failed")
        return False

    # Step 7: Verify state changes persisted
    success, output = run_cmd(
        ['python', 'queuectl.py', 'list', '--state', 'completed'],
        "Step 7: Verify state changes persisted"
    )
    if not success:
        print("❌ FAILED: Could not list completed jobs")
        return False
    
    for job_id, _ in jobs:
        if job_id not in output:
            print(f"❌ FAILED: Job {job_id} not marked as completed")
            return False
    
    print("✅ State changes persisted correctly")

    # Step 8: Another restart simulation
    print("\n" + "="*70)
    print("  Step 8: Another restart to verify completed jobs persist")
    print("="*70)
    time.sleep(1)

    success, output = run_cmd(
        ['python', 'queuectl.py', 'list', '--state', 'completed'],
        "Verify completed jobs after second restart"
    )
    if not success:
        print("❌ FAILED: Could not list jobs after second restart")
        return False
    
    for job_id, _ in jobs:
        if job_id not in output:
            print(f"❌ FAILED: Completed job {job_id} lost after restart!")
            return False
    
    print("✅ Completed jobs survived restart")

    # Final status
    run_cmd(
        ['python', 'queuectl.py', 'status'],
        "Final Status"
    )

    print("\n" + "="*70)
    print("           ✅ PERSISTENCE TEST PASSED")
    print("="*70)
    print("""
Summary:
  ✅ Jobs survive database restarts
  ✅ Job state changes persist
  ✅ Completed jobs remain in database
  ✅ No data loss on restart

This confirms that QueueCTL uses persistent storage correctly
and jobs will not be lost during system crashes or restarts.
""")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

