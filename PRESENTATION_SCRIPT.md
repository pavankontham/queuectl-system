# QueueCTL - 3 Minute Presentation Script

## [0:00 - 0:20] Introduction (20 seconds)

"Hi everyone! Today I'm going to show you QueueCTL, a background job queue system I built using Python and SQLite. 

Think of it like a task manager for your computer - you can queue up jobs, and workers will process them in the background. It handles failures automatically with retry logic, and keeps everything persistent so nothing gets lost."

**[SHOW: GitHub repository page]**

---

## [0:20 - 0:50] Problem & Solution (30 seconds)

"The problem I wanted to solve was: how do you run background tasks reliably? What if a task fails? What if your program crashes?

My solution uses SQLite for persistence - so jobs survive crashes. I implemented atomic locking so multiple workers can run safely without processing the same job twice. And I added exponential backoff for retries - so if something fails, it waits 2 seconds, then 4, then 8, giving the system time to recover."

**[SHOW: Architecture diagram from README or draw on screen]**

---

## [0:50 - 1:30] Live Demo (40 seconds)

"Let me show you how it works. First, I'll initialize the database:"

```bash
python queuectl.py init-db
```

"Now I'll add a few jobs - one that succeeds, one that fails, and one with high priority:"

```bash
python enqueue.py --id success-job --command "echo Hello World"
python enqueue.py --id fail-job --command "exit 1" --max-retries 2
python enqueue.py --id priority-job --command "echo Important!" --priority 1
```

"Let's check the queue:"

```bash
python queuectl.py status
```

"Now I'll start 2 workers to process these jobs:"

```bash
python queuectl.py worker start --count 2 --stop-when-empty
```

**[SHOW: Workers processing jobs, retry logic in action]**

"See how the failed job retries automatically? And the high-priority job ran first."

---

## [1:30 - 2:10] Key Features (40 seconds)

"Let me highlight the key features I implemented:

**1. Atomic Job Locking** - Multiple workers can run safely. I use SQLite transactions to ensure only one worker grabs each job.

**2. Exponential Backoff** - Failed jobs retry with increasing delays: 2 seconds, 4 seconds, 8 seconds. This prevents hammering a failing service.

**3. Dead Letter Queue** - After max retries, jobs go to the DLQ for manual review. You can retry them later:"

```bash
python queuectl.py dlq list
python queuectl.py dlq retry fail-job
```

**4. Job Priority** - High-priority jobs run first.

**5. Job Timeout** - Jobs that run too long get killed automatically.

**6. Output Logging** - Every job's output is saved to files for debugging."

**[SHOW: Log files in logs/ directory]**

---

## [2:10 - 2:40] Technical Implementation (30 seconds)

"From a technical perspective, here's what I built:

**Database Layer** - SQLite with WAL mode for concurrent access. I have three tables: jobs, config, and metadata.

**Worker System** - Python threads that poll for jobs every second. Each worker runs jobs in subprocesses and captures the output.

**Retry Logic** - When a job fails, I calculate the next run time using: delay = 2^attempts. The job goes back to pending state and workers pick it up later.

**Lock Recovery** - If a worker crashes, I have a mechanism that detects stale locks and releases them automatically.

The whole system is about 1,200 lines of Python code, organized into clean modules."

**[SHOW: Project structure in IDE or GitHub]**

---

## [2:40 - 3:00] Conclusion (20 seconds)

"So that's QueueCTL! It's a production-ready job queue that handles all the edge cases - failures, crashes, retries, priorities.

The key things I learned building this were:
- SQLite is surprisingly powerful for concurrent systems
- Atomic operations are crucial to prevent race conditions
- Good retry logic makes systems much more reliable

The code is on GitHub, and I've included comprehensive documentation and demo scripts. Thanks for watching!"

**[SHOW: GitHub repository with README visible]**

---

## Tips for Recording:

1. **Practice the timing** - Aim for 2:45 to 3:00 total
2. **Screen recording setup**:
   - Terminal on one side
   - Code/GitHub on the other
   - Use a tool like OBS or Loom
3. **Prepare your terminal**:
   - Clear the database before starting
   - Have all commands ready in a text file to copy-paste
   - Use a large font size (16-18pt)
4. **Speaking tips**:
   - Speak clearly and at a moderate pace
   - Show enthusiasm - you built something cool!
   - Don't worry about being perfect, authenticity matters more
5. **Visual aids**:
   - Show the GitHub commit history (10 commits showing progression)
   - Show the README with architecture diagrams
   - Show the demo running with visible output

## Alternative: Shorter Version (2 minutes)

If you need to cut it down to 2 minutes, remove the "Technical Implementation" section and keep:
- Introduction (20s)
- Problem & Solution (30s)
- Live Demo (40s)
- Key Features (30s)
- Conclusion (20s)

Total: 2:20

Good luck with your presentation! 🎉

