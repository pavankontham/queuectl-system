# QueueCTL - Quick Reference Card

## Installation & Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python queuectl.py init-db
```

---

## Common Commands

### Enqueue Jobs

```bash
# Simple job
python enqueue.py --id job1 --command "echo Hello"

# With options
python enqueue.py --id job2 --command "python script.py" \
  --max-retries 5 \
  --priority 1 \
  --timeout 30
```

### Manage Workers

```bash
# Start workers (run continuously)
python queuectl.py worker start --count 2

# Start workers (stop when empty)
python queuectl.py worker start --count 2 --stop-when-empty

# Stop workers (Ctrl+C or in another terminal)
python queuectl.py worker stop
```

### Monitor Queue

```bash
# Overall status
python queuectl.py status

# List all jobs
python queuectl.py list

# List by state
python queuectl.py list --state pending
python queuectl.py list --state completed
python queuectl.py list --state failed
```

### Dead Letter Queue

```bash
# List failed jobs
python queuectl.py dlq list

# Retry a job
python queuectl.py dlq retry <job_id>

# Retry all DLQ jobs
python queuectl.py dlq retry-all
```

### Configuration

```bash
# View all settings
python queuectl.py config get

# View specific setting
python queuectl.py config get max-retries

# Update setting
python queuectl.py config set max-retries 5
python queuectl.py config set backoff-base 3
python queuectl.py config set poll-interval 2
```

---

## Job States

- **pending** - Waiting to be processed
- **processing** - Currently being executed
- **completed** - Successfully finished
- **failed** - Failed but will retry
- **dead** - Failed after max retries (in DLQ)

---

## Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `max-retries` | 3 | Max retry attempts before DLQ |
| `backoff-base` | 2 | Base for exponential backoff (2^attempts) |
| `poll-interval` | 1 | Worker polling interval (seconds) |

---

## Job JSON Format

```json
{
  "id": "unique-job-id",
  "command": "echo Hello",
  "max_retries": 3,
  "priority": 0,
  "timeout_seconds": 60,
  "run_at": "2024-12-01T10:00:00"
}
```

**Required:** `id`, `command`  
**Optional:** `max_retries`, `priority`, `timeout_seconds`, `run_at`

---

## Retry Logic

Failed jobs retry with exponential backoff:

```
Attempt 1 fails → retry in 2^1 = 2 seconds
Attempt 2 fails → retry in 2^2 = 4 seconds
Attempt 3 fails → retry in 2^3 = 8 seconds
After max_retries → move to DLQ
```

---

## Output Logs

Job outputs are saved to `logs/` directory:
- `<job_id>_out.txt` - stdout
- `<job_id>_err.txt` - stderr

---

## Demo Script

```bash
# Run automated demo
python demo.py

# Or use shell scripts
./test_demo.sh          # Linux/Mac
.\test_demo.ps1         # Windows PowerShell
```

---

## Troubleshooting

### Database locked error
- SQLite is in use by another process
- Wait a moment and try again
- Or stop all workers first

### Workers not picking up jobs
- Check `next_run_at` - job might be scheduled for future
- Check job state - should be "pending"
- Check worker logs for errors

### Job stuck in "processing"
- Worker might have crashed
- Restart workers - lock recovery will reset the job

---

## File Structure

```
queuectl/
├── queuectl.py          # Main CLI
├── db.py                # Database layer
├── job_manager.py       # Job operations
├── worker.py            # Worker logic
├── config_manager.py    # Config management
├── utils.py             # Utilities
├── enqueue.py           # Helper script
├── demo.py              # Demo script
├── queuectl.db          # SQLite database (created on init)
└── logs/                # Job output logs (created automatically)
```

---

## Tips

1. **Use `--stop-when-empty`** for batch processing
2. **Set priority** for important jobs (lower number = higher priority)
3. **Set timeout** for jobs that might hang
4. **Check logs/** for debugging failed jobs
5. **Use DLQ** to review and retry failed jobs manually

---

## Help

Every command has help text:

```bash
python queuectl.py --help
python queuectl.py worker --help
python queuectl.py worker start --help
python enqueue.py --help
```

---

## GitHub Repository

https://github.com/pavankontham/queuectl-system

For full documentation, see `README.md`

