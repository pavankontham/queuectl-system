"""
Job manager for QueueCTL - handles job operations
"""
from typing import Optional, List, Dict, Any
import json
import db
import utils
import config_manager


def enqueue_job(job_data: dict) -> tuple:
    """
    Enqueue a new job. Returns (success, message, job_id)
    """
    # Validate job data
    is_valid, error_msg = utils.validate_job_data(job_data)
    if not is_valid:
        return False, error_msg, None
    
    job_id = job_data['id']
    command = job_data['command']
    
    # Get defaults from config
    max_retries = job_data.get('max_retries', config_manager.get_max_retries())
    priority = job_data.get('priority', 0)
    timeout_seconds = job_data.get('timeout_seconds', 30)
    
    # Determine next_run_at
    if 'run_at' in job_data:
        next_run_at = job_data['run_at']
    else:
        next_run_at = utils.now_iso()
    
    created_at = utils.now_iso()
    
    # Get log paths
    stdout_path, stderr_path = utils.get_log_paths(job_id)
    
    # Insert job
    try:
        db.execute_update(
            """
            INSERT INTO jobs (
                id, command, state, attempts, max_retries, 
                created_at, updated_at, next_run_at, priority,
                timeout_seconds, stdout_path, stderr_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id, command, 'pending', 0, max_retries,
                created_at, created_at, next_run_at, priority,
                timeout_seconds, stdout_path, stderr_path
            )
        )
        
        return True, f"Enqueued job {job_id} (state=pending, retries={max_retries}, priority={priority})", job_id
    
    except Exception as e:
        return False, f"Failed to enqueue job: {str(e)}", None


def get_job(job_id: str) -> Optional[Dict]:
    """Get a job by ID"""
    result = db.fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if result:
        return dict(result)
    return None


def list_jobs(state: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """List jobs, optionally filtered by state"""
    if state:
        query = "SELECT * FROM jobs WHERE state = ? ORDER BY priority ASC, next_run_at ASC LIMIT ?"
        results = db.execute_query(query, (state, limit))
    else:
        query = "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?"
        results = db.execute_query(query, (limit,))
    
    return [dict(row) for row in results]


def get_job_counts() -> Dict[str, int]:
    """Get count of jobs by state"""
    results = db.execute_query("SELECT state, COUNT(*) as count FROM jobs GROUP BY state")
    
    counts = {
        'total': 0,
        'pending': 0,
        'processing': 0,
        'completed': 0,
        'failed': 0,
        'dead': 0
    }
    
    for row in results:
        state = row['state']
        count = row['count']
        counts[state] = count
        counts['total'] += count
    
    return counts


def update_job_state(job_id: str, state: str, **kwargs) -> bool:
    """Update job state and other fields"""
    updates = ['state = ?', 'updated_at = ?']
    params = [state, utils.now_iso()]
    
    for key, value in kwargs.items():
        updates.append(f"{key} = ?")
        params.append(value)
    
    params.append(job_id)
    
    query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
    rowcount = db.execute_update(query, tuple(params))
    
    return rowcount > 0


def list_dlq_jobs(limit: int = 100) -> List[Dict]:
    """List jobs in Dead Letter Queue"""
    results = db.execute_query(
        "SELECT * FROM jobs WHERE state = 'dead' ORDER BY updated_at DESC LIMIT ?",
        (limit,)
    )
    return [dict(row) for row in results]


def retry_dlq_job(job_id: str) -> tuple:
    """
    Retry a job from DLQ. Returns (success, message)
    """
    job = get_job(job_id)
    
    if not job:
        return False, f"Job {job_id} not found"
    
    if job['state'] != 'dead':
        return False, f"Job {job_id} is not in DLQ (current state: {job['state']})"
    
    # Reset job for retry
    rowcount = db.execute_update(
        """
        UPDATE jobs 
        SET state = 'pending', 
            attempts = 0, 
            next_run_at = ?,
            updated_at = ?,
            locked_by = NULL,
            locked_at = NULL,
            last_error = NULL
        WHERE id = ?
        """,
        (utils.now_iso(), utils.now_iso(), job_id)
    )
    
    if rowcount > 0:
        return True, f"Retried job {job_id} from DLQ -> pending"
    else:
        return False, f"Failed to retry job {job_id}"

