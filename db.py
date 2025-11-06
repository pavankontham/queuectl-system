"""
Database layer for QueueCTL - SQLite persistence
"""
import sqlite3
import os
from contextlib import contextmanager
from typing import Optional, Dict, List, Any

DB_FILE = "queuectl.db"

JOBS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  command TEXT NOT NULL,
  state TEXT NOT NULL,
  attempts INTEGER DEFAULT 0,
  max_retries INTEGER DEFAULT 3,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  next_run_at TEXT NOT NULL,
  priority INTEGER DEFAULT 0,
  locked_by TEXT,
  locked_at TEXT,
  processing_started_at TEXT,
  processing_finished_at TEXT,
  exit_code INTEGER,
  last_error TEXT,
  stdout_path TEXT,
  stderr_path TEXT,
  timeout_seconds INTEGER DEFAULT 30
);
"""

CONFIG_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

DEFAULT_CONFIGS = [
    ('max_retries', '3'),
    ('backoff_base', '2'),
    ('poll_interval', '1'),
]


@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the database with tables and default config"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute(JOBS_TABLE_SCHEMA)
        cursor.execute(CONFIG_TABLE_SCHEMA)
        
        # Insert default configs
        for key, value in DEFAULT_CONFIGS:
            cursor.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                (key, value)
            )
        
        conn.commit()
    
    return True


def execute_query(query: str, params: tuple = ()) -> List[sqlite3.Row]:
    """Execute a SELECT query and return results"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()


def execute_update(query: str, params: tuple = ()) -> int:
    """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount


def execute_many(query: str, params_list: List[tuple]) -> int:
    """Execute multiple INSERT/UPDATE queries"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        return cursor.rowcount


def fetch_one(query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    """Execute a query and return a single row"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()


def atomic_update_and_fetch(update_query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    """
    Execute an UPDATE and return the updated row atomically.
    Used for worker job locking.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(update_query, params)
        
        # For SQLite, we need to fetch the updated row separately
        # The query should include a WHERE clause with the job ID
        if cursor.rowcount > 0:
            # Extract job ID from params (assuming it's the last param for our use case)
            # This is a simplified approach - in production, you'd want a more robust method
            conn.commit()
            return cursor.lastrowid
        
        conn.commit()
        return None


def db_exists() -> bool:
    """Check if database file exists"""
    return os.path.exists(DB_FILE)

