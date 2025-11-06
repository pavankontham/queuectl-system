# Demo Commands - Copy & Paste for Video

Use these commands in order for your video demonstration.

## Setup (Before Recording)

```bash
# Clean up any existing data
rm queuectl.db
rm -r logs/

# Make sure you're in the right directory
cd "d:\placements\Flam\gpt - backend"
```

---

## Demo Script

### 1. Initialize Database
```bash
python queuectl.py init-db
```
**Say:** "First, I'll initialize the database."

---

### 2. Add Jobs
```bash
python enqueue.py --id success-job --command "echo Hello World"
```
**Say:** "Now I'll add a job that will succeed."

```bash
python enqueue.py --id fail-job --command "exit 1" --max-retries 2
```
**Say:** "Here's a job that will fail and retry twice."

```bash
python enqueue.py --id priority-job --command "echo Important!" --priority 1
```
**Say:** "And a high-priority job that should run first."

```bash
python enqueue.py --id timeout-job --command "timeout /t 10" --timeout 3
```
**Say:** "Finally, a job that will timeout after 3 seconds."

---

### 3. Check Status
```bash
python queuectl.py status
```
**Say:** "Let's see what's in the queue."

---

### 4. List Jobs
```bash
python queuectl.py list
```
**Say:** "Here are all the jobs. Notice the priority-job has priority 1."

---

### 5. Start Workers
```bash
python queuectl.py worker start --count 2 --stop-when-empty
```
**Say:** "Now I'll start 2 workers to process these jobs. They'll stop automatically when done."

**Wait for workers to finish (about 10-15 seconds)**

---

### 6. Check Final Status
```bash
python queuectl.py status
```
**Say:** "Let's see the final status. Some jobs completed, some failed."

---

### 7. Check Completed Jobs
```bash
python queuectl.py list --state completed
```
**Say:** "Here are the successful jobs."

---

### 8. Check Dead Letter Queue
```bash
python queuectl.py dlq list
```
**Say:** "And here are the jobs that failed after all retries."

---

### 9. Show Logs
```bash
ls logs/
```
**Say:** "Every job's output is saved to log files."

```bash
cat logs/success-job_out.txt
```
**Say:** "Here's the output from our successful job."

---

### 10. Retry from DLQ
```bash
python queuectl.py dlq retry fail-job
```
**Say:** "I can retry failed jobs from the DLQ."

```bash
python queuectl.py status
```
**Say:** "Now it's back in the pending queue."

---

### 11. Configuration
```bash
python queuectl.py config get
```
**Say:** "All settings are configurable and persistent."

```bash
python queuectl.py config set max-retries 5
```
**Say:** "I can change settings like max retries."

```bash
python queuectl.py config get
```
**Say:** "And it's saved in the database."

---

## Quick Demo (1 minute version)

If you want a faster demo, just use these commands:

```bash
# Setup
python queuectl.py init-db

# Add jobs
python enqueue.py --id job1 --command "echo Success"
python enqueue.py --id job2 --command "exit 1" --max-retries 2

# Check status
python queuectl.py status

# Process
python queuectl.py worker start --count 2 --stop-when-empty

# Results
python queuectl.py status
python queuectl.py dlq list
```

---

## Alternative: Use the Automated Demo

If you want to show everything at once:

```bash
python demo.py
```

This runs through all features automatically and shows the commands being executed.

---

## Tips for Recording

1. **Terminal Setup:**
   - Use a large font (16-18pt)
   - Clear terminal before each command: `cls` (Windows) or `clear` (Linux/Mac)
   - Use a clean terminal theme (dark background, light text)

2. **Pacing:**
   - Pause 2-3 seconds after each command output
   - Don't rush - let viewers read the output
   - Speak while commands are running

3. **What to Highlight:**
   - Point out the priority-job running first
   - Show the retry delays (2s, 4s)
   - Highlight the DLQ functionality
   - Show the log files

4. **Screen Layout:**
   - Terminal: 70% of screen
   - Code/GitHub: 30% of screen (optional)
   - Or full-screen terminal for simplicity

5. **Audio:**
   - Use a good microphone
   - Minimize background noise
   - Speak clearly and enthusiastically

Good luck! 🎬

