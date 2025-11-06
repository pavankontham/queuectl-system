"""
Worker process for QueueCTL - executes jobs with retry logic
"""
import subprocess
import threading
import time
import signal
import sys
from typing import Optional, Dict
import db
import utils
import config_manager
import job_manager


# Global flag for graceful shutdown
shutdown_flag = threading.Event()
active_workers = []


class Worker:
    """Worker that processes jobs from the queue"""

    def __init__(self, worker_id: str, stop_when_empty: bool = False):
        self.worker_id = worker_id
        self.running = False
        self.current_job_id = None
        self.thread = None
        self.stop_when_empty = stop_when_empty
        self.idle_checks = 0
    
    def start(self):
        """Start the worker in a separate thread"""
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=False)
        self.thread.start()
    
    def stop(self):
        """Stop the worker gracefully"""
        self.running = False
    
    def join(self):
        """Wait for worker thread to finish"""
        if self.thread:
            self.thread.join()
    
    def _run(self):
        """Main worker loop"""
        poll_interval = config_manager.get_poll_interval()
        
        while self.running and not shutdown_flag.is_set():
            try:
                # Try to fetch and lock a job
                job = self._fetch_and_lock_job()
                
                if job:
                    self.current_job_id = job['id']
                    self._process_job(job)
                    self.current_job_id = None
                    self.idle_checks = 0  # Reset idle counter
                else:
                    # No job available
                    if self.stop_when_empty:
                        self.idle_checks += 1
                        # Stop if queue is empty for 3 consecutive checks
                        if self.idle_checks >= 3:
                            print(f"[{self.worker_id}] Queue empty, stopping...")
                            self.running = False
                            break
                    time.sleep(poll_interval)
            
            except Exception as e:
                print(f"[{self.worker_id}] Error in worker loop: {e}")
                time.sleep(poll_interval)
    
    def _fetch_and_lock_job(self) -> Optional[Dict]:
        """
        Atomically fetch and lock an eligible job
        """
        now = utils.now_iso()
        
        # Use a transaction to atomically select and lock a job
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find an eligible job
                cursor.execute(
                    """
                    SELECT id FROM jobs
                    WHERE state = 'pending' AND next_run_at <= ?
                    ORDER BY priority ASC, next_run_at ASC
                    LIMIT 1
                    """,
                    (now,)
                )
                
                result = cursor.fetchone()
                if not result:
                    return None
                
                job_id = result['id']
                
                # Lock the job
                cursor.execute(
                    """
                    UPDATE jobs
                    SET state = 'processing',
                        locked_by = ?,
                        locked_at = ?,
                        processing_started_at = ?,
                        updated_at = ?
                    WHERE id = ? AND state = 'pending'
                    """,
                    (self.worker_id, now, now, now, job_id)
                )
                
                if cursor.rowcount == 0:
                    # Job was taken by another worker
                    return None
                
                # Fetch the full job details
                cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
                job_row = cursor.fetchone()
                
                conn.commit()
                
                if job_row:
                    return dict(job_row)
                
                return None
        
        except Exception as e:
            print(f"[{self.worker_id}] Error fetching job: {e}")
            return None
    
    def _process_job(self, job: Dict):
        """Execute a job and handle the result"""
        job_id = job['id']
        command = job['command']
        timeout = job['timeout_seconds']
        
        print(f"[{self.worker_id}] Processing job {job_id}: {command}")
        
        try:
            # Execute the command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Save output to log files
            self._save_output(job, result.stdout, result.stderr)
            
            # Handle result
            if result.returncode == 0:
                self._handle_success(job, result.returncode)
            else:
                self._handle_failure(job, result.returncode, f"Command exited with code {result.returncode}")
        
        except subprocess.TimeoutExpired:
            print(f"[{self.worker_id}] Job {job_id} timed out after {timeout}s")
            self._handle_failure(job, -1, f"Job timed out after {timeout} seconds")
        
        except Exception as e:
            print(f"[{self.worker_id}] Job {job_id} failed with error: {e}")
            self._handle_failure(job, -1, str(e))

    def _save_output(self, job: Dict, stdout: str, stderr: str):
        """Save job output to log files"""
        try:
            if job['stdout_path']:
                with open(job['stdout_path'], 'a') as f:
                    f.write(f"\n=== Attempt {job['attempts'] + 1} at {utils.now_iso()} ===\n")
                    f.write(stdout)

            if job['stderr_path']:
                with open(job['stderr_path'], 'a') as f:
                    f.write(f"\n=== Attempt {job['attempts'] + 1} at {utils.now_iso()} ===\n")
                    f.write(stderr)
        except Exception as e:
            print(f"[{self.worker_id}] Failed to save output: {e}")

    def _handle_success(self, job: Dict, exit_code: int):
        """Handle successful job completion"""
        job_id = job['id']

        db.execute_update(
            """
            UPDATE jobs
            SET state = 'completed',
                exit_code = ?,
                processing_finished_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (exit_code, utils.now_iso(), utils.now_iso(), job_id)
        )

        print(f"[{self.worker_id}] Job {job_id} completed successfully")

    def _handle_failure(self, job: Dict, exit_code: int, error_message: str):
        """Handle job failure with retry logic"""
        job_id = job['id']
        attempts = job['attempts'] + 1
        max_retries = job['max_retries']

        print(f"[{self.worker_id}] Job {job_id} failed (attempt {attempts}/{max_retries}): {error_message}")

        if attempts >= max_retries:
            # Move to DLQ
            db.execute_update(
                """
                UPDATE jobs
                SET state = 'dead',
                    attempts = ?,
                    exit_code = ?,
                    last_error = ?,
                    processing_finished_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (attempts, exit_code, error_message, utils.now_iso(), utils.now_iso(), job_id)
            )
            print(f"[{self.worker_id}] Job {job_id} moved to DLQ after {attempts} attempts")
        else:
            # Retry with exponential backoff
            backoff_base = config_manager.get_backoff_base()
            delay = utils.calculate_backoff_delay(attempts, backoff_base)
            next_run_at = utils.add_seconds(utils.now_iso(), delay)

            db.execute_update(
                """
                UPDATE jobs
                SET state = 'pending',
                    attempts = ?,
                    exit_code = ?,
                    last_error = ?,
                    next_run_at = ?,
                    locked_by = NULL,
                    locked_at = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (attempts, exit_code, error_message, next_run_at, utils.now_iso(), job_id)
            )
            print(f"[{self.worker_id}] Job {job_id} will retry in {delay}s (attempt {attempts}/{max_retries})")


def start_workers(count: int, stop_when_empty: bool = False):
    """Start multiple worker processes"""
    global active_workers

    print(f"Starting {count} workers...")

    for i in range(count):
        worker_id = utils.generate_worker_id()
        worker = Worker(worker_id, stop_when_empty=stop_when_empty)
        worker.start()
        active_workers.append(worker)
        print(f"Started worker: {worker_id}")

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    if stop_when_empty:
        print(f"{count} workers started. Will stop when queue is empty.")
    else:
        print(f"{count} workers started. Press Ctrl+C to stop.")

    # Wait for all workers
    try:
        for worker in active_workers:
            worker.join()
    except KeyboardInterrupt:
        pass

    print("All workers stopped.")


def stop_workers():
    """Stop all active workers gracefully"""
    global active_workers

    if not active_workers:
        print("No active workers to stop.")
        return

    print(f"Gracefully stopping {len(active_workers)} workers...")
    shutdown_flag.set()

    for worker in active_workers:
        worker.stop()

    for worker in active_workers:
        worker.join()

    active_workers = []
    print("All workers stopped.")


def _signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\nReceived shutdown signal. Stopping workers...")
    stop_workers()
    sys.exit(0)


def get_active_worker_count() -> int:
    """Get count of active workers"""
    return len([w for w in active_workers if w.running])


def recover_stale_locks(timeout_minutes: int = 5):
    """
    Recover jobs that have been locked for too long (worker crashed)
    """
    cutoff_time = utils.add_seconds(utils.now_iso(), -timeout_minutes * 60)

    rowcount = db.execute_update(
        """
        UPDATE jobs
        SET state = 'pending',
            locked_by = NULL,
            locked_at = NULL,
            updated_at = ?
        WHERE state = 'processing' AND locked_at < ?
        """,
        (utils.now_iso(), cutoff_time)
    )

    if rowcount > 0:
        print(f"Recovered {rowcount} stale jobs")

    return rowcount

