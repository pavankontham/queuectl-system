# QueueCTL - Project Summary

## What I Built

QueueCTL is a background job queue system that I developed using Python and SQLite. It's designed to handle asynchronous task processing with features like automatic retries, worker management, and persistent storage.

## Why I Built It This Way

### Technology Choices

**Python**: I chose Python because it's great for system utilities and has excellent libraries for subprocess management and CLI building.

**SQLite**: Instead of using Redis or PostgreSQL, I went with SQLite because:
- No separate server to set up
- Built-in ACID transactions prevent race conditions
- Perfect for single-machine deployments
- Jobs persist automatically

**Click**: For the CLI, Click made it easy to create a clean command structure with proper help text and validation.

### Architecture Decisions

**Polling vs Push**: I implemented a polling system where workers check for jobs every second. While this adds a small delay, it's much simpler than setting up a pub/sub system and more reliable.

**Threading vs Multiprocessing**: I used threads instead of processes because:
- Most jobs are shell commands (I/O-bound, not CPU-bound)
- Lighter on memory
- Easier to coordinate with shared database access

**Exponential Backoff**: For retries, I implemented exponential backoff (2^attempts) to avoid hammering failing services while still giving jobs a fair chance.

## Key Features

### Core Functionality
- **Job Queue**: Add jobs via CLI with JSON or Python wrapper
- **Worker Pool**: Run multiple workers concurrently
- **Automatic Retry**: Failed jobs retry with exponential backoff
- **Dead Letter Queue**: Permanently failed jobs go to DLQ for manual review
- **Persistent Storage**: Everything stored in SQLite
- **Status Monitoring**: Real-time view of queue and workers

### Extra Features I Added
- **Job Priority**: High-priority jobs run first
- **Job Timeout**: Kill jobs that run too long
- **Scheduled Jobs**: Run jobs at specific times
- **Output Logging**: Capture stdout/stderr for every job
- **Lock Recovery**: Recover from worker crashes
- **Graceful Shutdown**: Workers finish current job before stopping
- **Auto-stop Workers**: Workers can exit when queue is empty
- **Persistent Config**: All settings stored in database

## How It Works

### Job Lifecycle
1. Job is enqueued with "pending" state
2. Worker picks it up and marks it "processing"
3. Worker runs the command in a subprocess
4. On success: mark "completed"
5. On failure: retry with exponential backoff
6. After max retries: move to "dead" (DLQ)

### Worker Locking
To prevent multiple workers from processing the same job, I implemented atomic locking:
1. Worker queries for pending jobs
2. Worker attempts to UPDATE the job with its worker ID
3. Only one worker succeeds (thanks to SQLite transactions)
4. That worker processes the job

This means you can safely run as many workers as you want.

### Retry Algorithm
```
delay = 2 ^ attempts
next_run_at = current_time + delay
```

So failures retry after 2s, 4s, 8s, etc.

## Project Structure

```
queuectl/
├── queuectl.py           # CLI interface (Click commands)
├── db.py                 # Database layer (SQLite operations)
├── job_manager.py        # Job CRUD operations
├── worker.py             # Worker logic and job execution
├── config_manager.py     # Configuration management
├── utils.py              # Helper functions
├── enqueue.py            # Convenience wrapper for Windows
├── demo.py               # Automated demo script
├── test_demo.sh          # Bash demo script
├── test_demo.ps1         # PowerShell demo script
├── logs/                 # Job output logs
└── README.md             # Full documentation
```

## Testing

I created a comprehensive demo script (`demo.py`) that automatically tests:
- Job enqueuing
- Worker execution
- Retry logic with exponential backoff
- Dead Letter Queue
- Configuration management
- Job timeout
- Job priority
- Output logging

All tests pass successfully.

## Challenges & Solutions

**Challenge 1: Race Conditions**
Multiple workers could grab the same job. 
*Solution*: Atomic UPDATE with WHERE clause in a transaction.

**Challenge 2: Worker Crashes**
Workers could crash and leave jobs stuck in "processing".
*Solution*: Lock recovery mechanism that checks for stale locks on startup.

**Challenge 3: Windows Quote Escaping**
PowerShell makes JSON input painful.
*Solution*: Created `enqueue.py` wrapper that builds JSON internally.

## What I Learned

- SQLite is surprisingly powerful for concurrent access with WAL mode
- Atomic operations are crucial for distributed systems (even on one machine)
- Good CLI design makes a huge difference in usability
- Exponential backoff is essential for retry logic
- Testing edge cases (crashes, timeouts) is important

## Future Improvements

If I had more time, I'd add:
- Job dependencies (job B waits for job A)
- Web dashboard for monitoring
- Job cancellation
- Cron-like recurring jobs
- Distributed worker support

## Conclusion

This project taught me a lot about building reliable background job systems. The key insights were:
1. Keep it simple - SQLite is often enough
2. Atomic operations prevent race conditions
3. Graceful degradation (retry, DLQ) is important
4. Good documentation and demos matter

The system is production-ready for single-machine deployments and handles all the edge cases I could think of.

