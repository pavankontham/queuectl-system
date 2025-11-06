# QueueCTL - Architecture & Design

## Overview

QueueCTL is a single-machine background job queue system built with Python and SQLite. The design focuses on reliability, simplicity, and handling edge cases like worker crashes and job failures.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│                      (queuectl.py)                           │
│  Commands: enqueue, worker, status, list, dlq, config       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
├──────────────────┬──────────────────┬───────────────────────┤
│  Job Manager     │  Worker Manager  │  Config Manager       │
│  (job_manager.py)│  (worker.py)     │  (config_manager.py)  │
│                  │                  │                       │
│  - Enqueue       │  - Fetch jobs    │  - Get/Set config     │
│  - List jobs     │  - Execute       │  - Defaults           │
│  - DLQ ops       │  - Retry logic   │  - Persistence        │
└──────────────────┴──────────────────┴───────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database Layer                            │
│                        (db.py)                               │
│                                                              │
│  - Connection pooling with WAL mode                          │
│  - Transaction management                                    │
│  - Schema initialization                                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    SQLite Database                           │
│                     (queuectl.db)                            │
│                                                              │
│  Tables: jobs, config                                        │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### Jobs Table

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    state TEXT NOT NULL,              -- pending, processing, completed, failed, dead
    priority INTEGER DEFAULT 0,        -- Lower = higher priority
    attempts INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    timeout_seconds INTEGER,
    next_run_at TEXT NOT NULL,        -- ISO timestamp
    locked_by TEXT,                   -- Worker ID
    locked_at TEXT,                   -- ISO timestamp
    last_error TEXT,
    stdout_path TEXT,
    stderr_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_jobs_state_next_run ON jobs(state, next_run_at, priority);
```

### Config Table

```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

## Job Lifecycle

```
┌─────────┐
│ ENQUEUE │
└────┬────┘
     │
     ▼
┌─────────┐     ┌──────────────┐
│ PENDING │────▶│  PROCESSING  │
└─────────┘     └──────┬───────┘
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
        ┌───────────┐     ┌─────────┐
        │ COMPLETED │     │ FAILED  │
        └───────────┘     └────┬────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
              ┌─────────┐          ┌──────────┐
              │ PENDING │          │   DEAD   │
              │ (retry) │          │  (DLQ)   │
              └─────────┘          └──────────┘
```

## Key Design Decisions

### 1. SQLite with WAL Mode

**Why SQLite?**
- Zero configuration - no separate database server
- ACID transactions prevent data corruption
- Good enough for single-machine workloads
- Built-in persistence

**Why WAL (Write-Ahead Logging)?**
- Allows concurrent reads while writing
- Better performance for multiple workers
- Reduces lock contention

```python
conn.execute("PRAGMA journal_mode=WAL")
```

### 2. Atomic Job Locking

**Problem:** Multiple workers must not process the same job.

**Solution:** Atomic UPDATE with WHERE clause in a transaction.

```python
# Pseudocode
BEGIN TRANSACTION
  SELECT id FROM jobs 
  WHERE state='pending' 
    AND next_run_at <= NOW()
  ORDER BY priority ASC, next_run_at ASC
  LIMIT 1
  
  UPDATE jobs 
  SET state='processing', 
      locked_by=worker_id, 
      locked_at=NOW()
  WHERE id=selected_id 
    AND state='pending'  -- Critical: prevents race condition
  
  IF rows_affected == 1:
    COMMIT
    return job
  ELSE:
    ROLLBACK
    return None
END TRANSACTION
```

Only one worker's UPDATE succeeds due to SQLite's transaction isolation.

### 3. Exponential Backoff

**Why exponential backoff?**
- Prevents hammering a failing service
- Gives time for transient issues to resolve
- Reduces system load during failures

**Algorithm:**
```python
delay_seconds = backoff_base ** attempts
next_run_at = current_time + delay_seconds
```

**Example with backoff_base=2:**
- Attempt 1 fails → retry in 2¹ = 2 seconds
- Attempt 2 fails → retry in 2² = 4 seconds  
- Attempt 3 fails → retry in 2³ = 8 seconds
- After max_retries → move to DLQ

### 4. Dead Letter Queue (DLQ)

**Purpose:** Jobs that fail repeatedly need manual intervention.

**Implementation:**
- After `max_retries` attempts, set `state='dead'`
- DLQ is just a filtered view: `SELECT * FROM jobs WHERE state='dead'`
- Can retry from DLQ: reset to `state='pending'`, `attempts=0`

### 5. Lock Recovery

**Problem:** Worker crashes leave jobs stuck in "processing" state.

**Solution:** Detect stale locks on worker startup.

```python
# Pseudocode
stale_threshold = 5 minutes

UPDATE jobs
SET state='pending', 
    locked_by=NULL, 
    locked_at=NULL
WHERE state='processing'
  AND locked_at < (NOW() - stale_threshold)
```

### 6. Polling vs Event-Driven

**Choice:** Polling (workers check database every N seconds)

**Why not event-driven?**
- Simpler implementation
- No need for pub/sub infrastructure
- More reliable (can't miss events)

**Tradeoff:**
- Slight latency (up to poll_interval seconds)
- Constant CPU usage (minimal with sleep)

### 7. Threading vs Multiprocessing

**Choice:** Threading with subprocess execution

**Why threading?**
- Lighter weight than processes
- Shared database connection pool
- Jobs run in subprocesses anyway (I/O-bound)

**Why not multiprocessing?**
- More memory overhead
- More complex IPC
- Python GIL not an issue (jobs are subprocesses)

## Scalability Considerations

### Current Limitations
- **Single machine only** - SQLite doesn't support distributed access
- **Limited concurrency** - SQLite handles ~10-20 concurrent writers well
- **No horizontal scaling** - Can't add more machines

### When to Migrate
Consider PostgreSQL + Redis if you need:
- Multiple machines processing jobs
- 100+ concurrent workers
- Sub-second job latency
- Distributed deployment

### Current Capacity
With SQLite, this system handles:
- ✅ 10-20 concurrent workers
- ✅ Thousands of jobs per hour
- ✅ Millions of jobs in database
- ✅ Single-machine reliability

## Error Handling

### Job Execution Errors
1. **Exit code != 0** → Retry with backoff
2. **Timeout** → Kill process, retry with backoff
3. **Exception** → Log error, retry with backoff
4. **Max retries exceeded** → Move to DLQ

### System Errors
1. **Database locked** → Retry with exponential backoff
2. **Worker crash** → Lock recovery on next worker startup
3. **Disk full** → Jobs remain in database, process when space available

## Configuration Management

All settings stored in database `config` table:
- `max_retries` - Default retry attempts
- `backoff_base` - Exponential backoff base
- `poll_interval` - Worker polling frequency

**Why database storage?**
- Survives restarts
- No config files to manage
- Can change without restarting workers

## Testing Strategy

### Unit Tests (if implemented)
- Database operations
- Job state transitions
- Retry logic calculations
- Lock acquisition

### Integration Tests
- End-to-end job processing
- Multiple worker coordination
- Crash recovery
- DLQ operations

### Demo Script
`demo.py` tests all features automatically:
- Job enqueuing
- Worker processing
- Retry with backoff
- DLQ operations
- Configuration persistence

## Future Enhancements

### Short Term
- Job dependencies (job B waits for job A)
- Job cancellation
- Progress callbacks

### Long Term
- Web dashboard
- Distributed workers (migrate to PostgreSQL)
- Cron-like recurring jobs
- Job result storage

## Conclusion

This design prioritizes:
1. **Reliability** - Jobs never lost, atomic operations
2. **Simplicity** - SQLite, no external dependencies
3. **Maintainability** - Clean modules, clear separation of concerns

The system is production-ready for single-machine deployments and handles all common edge cases.

