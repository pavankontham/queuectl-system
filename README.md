# QueueCTL

A CLI-based background job queue system I built using Python and SQLite. Think of it as a lightweight task queue that can handle background jobs, retry failures, and manage worker processes - all from the command line.

## What It Does

This system lets you:
- **Enqueue jobs** - Add tasks to a queue with custom settings
- **Run workers** - Spin up multiple workers to process jobs concurrently
- **Handle failures** - Automatically retry failed jobs with exponential backoff
- **Manage dead jobs** - Move permanently failed jobs to a Dead Letter Queue
- **Prioritize work** - Execute high-priority jobs first
- **Schedule jobs** - Run jobs at specific times
- **Set timeouts** - Kill jobs that run too long
- **Track everything** - Log all job outputs and monitor status
- **Configure easily** - Persistent settings stored in the database
- **Recover gracefully** - Handle worker crashes and shutdowns properly

## Tech Stack

I kept the tech stack simple and focused:
- **Python 3.10+** - Main language
- **SQLite** - Lightweight database for persistence
- **Click** - CLI framework for clean command structure
- **Standard library** - subprocess, threading, sqlite3, datetime, json

No heavy dependencies or complex setup required.

## Getting Started

### What You Need

- Python 3.10 or higher
- pip (comes with Python)

### Setup

```bash
# Install the only dependency (Click)
pip install -r requirements.txt

# Initialize the database
python queuectl.py init-db
```

That's it! You're ready to go.

## How to Use

### First Time Setup

```bash
python queuectl.py init-db
```

This creates the SQLite database with all necessary tables.

### Adding Jobs to the Queue

**Method 1: Python wrapper (easier, especially on Windows)**

```bash
# Basic job
python enqueue.py --id job1 --command "echo Hello World"

# Job with custom settings
python enqueue.py --id job2 --command "python script.py" --max-retries 5 --priority 1 --timeout 60

# Scheduled job
python enqueue.py --id job3 --command "echo Delayed" --run-at "2025-11-06T12:00:00Z"
```

**Method 2: Direct JSON (if you prefer)**

```bash
# Basic job
python queuectl.py enqueue '{"id":"job1","command":"echo Hello World"}'

# Job with custom settings
python queuectl.py enqueue '{"id":"job2","command":"python script.py","max_retries":5,"priority":1,"timeout_seconds":60}'

# Scheduled/delayed job
python queuectl.py enqueue '{"id":"job3","command":"echo Delayed","run_at":"2025-11-06T12:00:00Z"}'
```

> **Windows users**: If using PowerShell, the `enqueue.py` wrapper is much easier than dealing with quote escaping.

### Running Workers

Workers are what actually process the jobs. You can run as many as you want:

```bash
# Single worker
python queuectl.py worker start

# Multiple workers (they'll work in parallel)
python queuectl.py worker start --count 3

# Workers that auto-stop when done
python queuectl.py worker start --count 2 --stop-when-empty
```

To stop workers, just press `Ctrl+C` - they'll finish their current job and shut down gracefully. Or use:

```bash
python queuectl.py worker stop
```

### Monitoring

Check what's happening:

```bash
python queuectl.py status
```

You'll see something like:
```
[QUEUE STATUS]
  Total jobs: 10
  Pending: 3
  Processing: 2
  Completed: 4
  Failed: 0
  Dead Letter Queue: 1

[WORKERS]
  Active: 3
```

### Viewing Jobs

```bash
# See all jobs
python queuectl.py list

# Filter by state
python queuectl.py list --state pending
python queuectl.py list --state completed

# Limit output
python queuectl.py list --limit 10
```

### Dead Letter Queue

When jobs fail too many times, they go to the DLQ. You can check them and retry if needed:

```bash
# See what failed
python queuectl.py dlq list

# Give a job another chance
python queuectl.py dlq retry job_id
```

### Changing Settings

All settings are stored in the database, so they persist across restarts:

```bash
# View current settings
python queuectl.py config get

# Change settings
python queuectl.py config set max-retries 5
python queuectl.py config set backoff-base 3
python queuectl.py config set poll-interval 2
```

## How It Works

### Job Lifecycle

Here's how jobs move through the system:

```
pending → processing → completed
    ↓          ↓
    ↓      failed → pending (retry)
    ↓          ↓
    └──────→ dead (DLQ)
```

- **pending**: Job is waiting in the queue
- **processing**: A worker picked it up and is running it
- **completed**: Job finished successfully (exit code 0)
- **failed**: Job failed but will retry (temporary state)
- **dead**: Job failed too many times, moved to DLQ

### Database Schema

#### Jobs Table

```sql
CREATE TABLE jobs (
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
```

#### Config Table

```sql
CREATE TABLE config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

### How Workers Avoid Conflicts

I implemented atomic locking to prevent multiple workers from grabbing the same job:

1. Worker looks for jobs where `state='pending' AND next_run_at <= NOW()`
2. Worker tries to lock the job with an UPDATE in a transaction
3. Only one worker succeeds (thanks to SQLite's transaction isolation)
4. That worker processes the job
5. Worker updates the job state when done

This means you can safely run as many workers as you want without worrying about duplicate processing.

### Retry Logic

When a job fails, it doesn't give up immediately. The retry delay grows exponentially:

```python
delay = backoff_base ** attempts
next_run_at = current_time + delay
```

For example, with `backoff_base=2`:
- First failure → retry in 2 seconds
- Second failure → retry in 4 seconds
- Third failure → retry in 8 seconds
- After max_retries → give up and move to DLQ

This prevents hammering a failing service while still giving jobs a fair chance to succeed.

### DLQ Handling

Jobs are moved to the Dead Letter Queue when:
- `attempts >= max_retries`
- State is set to `'dead'`

Jobs can be retried from DLQ:
- Resets `attempts` to 0
- Sets `state` to `'pending'`
- Sets `next_run_at` to current time

### Lock Timeout Recovery

If a worker crashes while processing a job:
- Job remains in `'processing'` state with old `locked_at` timestamp
- Recovery mechanism checks for stale locks (default: 5 minutes)
- Stale jobs are reset to `'pending'` state
- Another worker can pick them up

### Job Output Logging

Each job execution logs output to:
- `logs/{job_id}_out.txt` - stdout
- `logs/{job_id}_err.txt` - stderr

Each attempt is timestamped in the log files.

## Project Structure

```
queuectl/
├── queuectl.py           # Main CLI entrypoint
├── db.py                 # SQLite database layer
├── job_manager.py        # Job operations (enqueue, list, DLQ)
├── worker.py             # Worker process and job execution
├── config_manager.py     # Configuration management
├── utils.py              # Utility functions (timestamps, validation)
├── enqueue.py            # Python wrapper for easy job enqueuing
├── requirements.txt      # Python dependencies
├── demo.py               # Automated demo script (recommended)
├── test_demo.sh          # Demo test script (Bash)
├── test_demo.ps1         # Demo test script (PowerShell)
├── logs/                 # Job output logs
├── queuectl.db           # SQLite database (created after init)
└── README.md             # This file
```

## Testing It Out

### Quick Demo

I've included a demo script that shows off all the features:

```bash
python demo.py
```

This will automatically:
- Set up the database
- Add different types of jobs (some that succeed, some that fail, some that timeout)
- Start workers that process everything
- Show retry behavior with exponential backoff
- Demonstrate the Dead Letter Queue
- Show configuration management
- Display all the logs

It's the fastest way to see everything in action.

**Alternative shell scripts:**

```bash
# Linux/Mac
chmod +x test_demo.sh
./test_demo.sh

# Windows PowerShell
.\test_demo.ps1
```

### Manual Testing

If you want to test specific features yourself:

**1. Basic job execution:**
```bash
python enqueue.py --id test1 --command "echo Hello World"
python queuectl.py worker start --count 1 --stop-when-empty
```

**2. Retry behavior:**
```bash
python enqueue.py --id fail-test --command "exit 1" --max-retries 3
python queuectl.py worker start --count 1 --stop-when-empty
# Watch it retry with increasing delays
```

**3. Dead Letter Queue:**
```bash
# After a job fails completely
python queuectl.py dlq list
python queuectl.py dlq retry fail-test
```

**4. Timeout handling:**
```bash
python enqueue.py --id timeout-test --command "sleep 30" --timeout 5
python queuectl.py worker start --count 1 --stop-when-empty
# Job will be killed after 5 seconds
```

**5. Priority ordering:**
```bash
python enqueue.py --id low-priority --command "echo Low" --priority 10
python enqueue.py --id high-priority --command "echo High" --priority 1
python queuectl.py worker start --count 1 --stop-when-empty
# High priority runs first
```

## Configuration Options

| Key | Default | Description |
|-----|---------|-------------|
| `max_retries` | 3 | Maximum retry attempts before moving to DLQ |
| `backoff_base` | 2 | Base for exponential backoff calculation |
| `poll_interval` | 1 | Worker polling interval in seconds |

## Design Decisions

### Why SQLite?

I chose SQLite over something like Redis or PostgreSQL because:
- **Zero setup** - No separate database server to install or manage
- **Atomic operations** - Built-in transaction support prevents race conditions
- **Persistent by default** - Jobs survive crashes and restarts
- **Good enough** - For a single-machine queue, SQLite handles the load just fine

The tradeoff is that this won't scale to multiple machines, but for most use cases, that's not needed.

### Why Polling Instead of Events?

Workers poll the database every second (configurable) instead of using an event-driven approach:
- **Simpler** - No need for pub/sub or message brokers
- **More reliable** - Can't miss events due to network issues
- **Easier to debug** - Straightforward flow to follow

The downside is a slight delay (up to 1 second) before jobs start, but that's acceptable for most background tasks.

### Why Threading?

I used Python threads instead of multiprocessing:
- **Lighter weight** - Less memory overhead
- **Easier coordination** - Shared database connection pool
- **Works well here** - Most jobs are shell commands (I/O-bound), not CPU-intensive Python code

The Python GIL isn't an issue since workers spend most of their time waiting for subprocesses.

## Known Limitations

This is a single-machine queue system, so it doesn't have:
- Distributed deployment across multiple servers
- Job dependencies or workflow DAGs
- Job cancellation (once a job starts, it runs to completion)
- Real-time progress tracking
- Authentication or authorization
- Web UI (it's CLI-only)

These could be added later if needed, but I kept the scope focused on core functionality.

## Possible Improvements

Some ideas for future versions:
- Add job dependencies (job B waits for job A)
- Support job cancellation
- Add a simple web dashboard
- Implement cron-like recurring jobs
- Store job results in the database
- Add metrics and monitoring hooks

## Demo Video: 
[Watch Here]([https://drive.google.com/file/d/1XsO6lQsndcLBvuJRci0Aze_adxsdfZQZ/view?usp=sharing])
https://drive.google.com/file/d/1XsO6lQsndcLBvuJRci0Aze_adxsdfZQZ/view?usp=sharing


---

Built with Python, SQLite, and way too much coffee ☕

