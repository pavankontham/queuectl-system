"""
Utility functions for QueueCTL
"""
from datetime import datetime, timedelta
import os
import uuid


def now_iso() -> str:
    """Return current UTC time in ISO format"""
    return datetime.utcnow().isoformat() + 'Z'


def parse_iso(iso_string: str) -> datetime:
    """Parse ISO format string to datetime"""
    # Remove 'Z' suffix if present
    if iso_string.endswith('Z'):
        iso_string = iso_string[:-1]
    return datetime.fromisoformat(iso_string)


def is_past(iso_string: str) -> bool:
    """Check if given ISO timestamp is in the past"""
    return parse_iso(iso_string) <= datetime.utcnow()


def add_seconds(iso_string: str, seconds: int) -> str:
    """Add seconds to an ISO timestamp"""
    dt = parse_iso(iso_string)
    new_dt = dt + timedelta(seconds=seconds)
    return new_dt.isoformat() + 'Z'


def calculate_backoff_delay(attempts: int, backoff_base: int) -> int:
    """Calculate exponential backoff delay in seconds"""
    return backoff_base ** attempts


def generate_job_id() -> str:
    """Generate a unique job ID"""
    return str(uuid.uuid4())


def generate_worker_id() -> str:
    """Generate a unique worker ID"""
    return f"worker-{uuid.uuid4().hex[:8]}"


def get_log_paths(job_id: str) -> tuple:
    """Get stdout and stderr log file paths for a job"""
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    stdout_path = os.path.join(logs_dir, f"{job_id}_out.txt")
    stderr_path = os.path.join(logs_dir, f"{job_id}_err.txt")
    
    return stdout_path, stderr_path


def format_timestamp(iso_string: str) -> str:
    """Format ISO timestamp for display"""
    if not iso_string:
        return "N/A"
    return iso_string


def validate_job_data(job_data: dict) -> tuple:
    """
    Validate job data and return (is_valid, error_message)
    """
    if not job_data.get('id'):
        return False, "Job 'id' is required"
    
    if not job_data.get('command'):
        return False, "Job 'command' is required"
    
    # Validate priority if present
    if 'priority' in job_data:
        try:
            priority = int(job_data['priority'])
            if priority < 0:
                return False, "Job 'priority' must be non-negative"
        except (ValueError, TypeError):
            return False, "Job 'priority' must be an integer"
    
    # Validate max_retries if present
    if 'max_retries' in job_data:
        try:
            max_retries = int(job_data['max_retries'])
            if max_retries < 0:
                return False, "Job 'max_retries' must be non-negative"
        except (ValueError, TypeError):
            return False, "Job 'max_retries' must be an integer"
    
    # Validate timeout_seconds if present
    if 'timeout_seconds' in job_data:
        try:
            timeout = int(job_data['timeout_seconds'])
            if timeout <= 0:
                return False, "Job 'timeout_seconds' must be positive"
        except (ValueError, TypeError):
            return False, "Job 'timeout_seconds' must be an integer"
    
    # Validate run_at if present
    if 'run_at' in job_data:
        try:
            parse_iso(job_data['run_at'])
        except Exception:
            return False, "Job 'run_at' must be a valid ISO timestamp"
    
    return True, None


def format_duration(start_iso: str, end_iso: str) -> str:
    """Calculate and format duration between two timestamps"""
    if not start_iso or not end_iso:
        return "N/A"
    
    try:
        start = parse_iso(start_iso)
        end = parse_iso(end_iso)
        duration = end - start
        
        total_seconds = int(duration.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    except Exception:
        return "N/A"

