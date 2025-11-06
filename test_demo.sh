#!/bin/bash
# QueueCTL Demo Test Script

echo "=== QueueCTL Demo Test ==="
echo ""

# Clean up previous test
echo "Cleaning up previous test data..."
rm -f queuectl.db
rm -rf logs
mkdir -p logs

# Initialize database
echo ""
echo "1. Initializing database..."
python queuectl.py init-db

# Enqueue test jobs
echo ""
echo "2. Enqueuing test jobs..."

# Success job
python queuectl.py enqueue '{"id":"test-success","command":"echo Success Job","max_retries":3,"priority":1}'

# Failure job (will retry and go to DLQ)
python queuectl.py enqueue '{"id":"test-fail","command":"exit 1","max_retries":2,"priority":2}'

# Delayed job
DELAYED_TIME=$(date -u -d "+5 seconds" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v+5S +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || python -c "from datetime import datetime, timedelta; print((datetime.utcnow() + timedelta(seconds=5)).isoformat() + 'Z')")
python queuectl.py enqueue "{\"id\":\"test-delayed\",\"command\":\"echo Delayed Job\",\"run_at\":\"$DELAYED_TIME\"}"

# Timeout job
python queuectl.py enqueue '{"id":"test-timeout","command":"sleep 10","timeout_seconds":2,"max_retries":1}'

# Show status
echo ""
echo "3. Checking initial status..."
python queuectl.py status

# List jobs
echo ""
echo "4. Listing all jobs..."
python queuectl.py list

# Start workers in background
echo ""
echo "5. Starting 2 workers in background..."
python queuectl.py worker start --count 2 &
WORKER_PID=$!

# Wait for jobs to process
echo ""
echo "6. Waiting 15 seconds for jobs to process..."
sleep 15

# Stop workers
echo ""
echo "7. Stopping workers..."
kill -SIGTERM $WORKER_PID 2>/dev/null || kill $WORKER_PID 2>/dev/null
wait $WORKER_PID 2>/dev/null

# Show final status
echo ""
echo "8. Checking final status..."
python queuectl.py status

# List pending jobs
echo ""
echo "9. Listing pending jobs..."
python queuectl.py list --state pending

# List completed jobs
echo ""
echo "10. Listing completed jobs..."
python queuectl.py list --state completed

# Show DLQ
echo ""
echo "11. Showing Dead Letter Queue..."
python queuectl.py dlq list

# Retry from DLQ
echo ""
echo "12. Retrying a job from DLQ..."
python queuectl.py dlq retry test-fail

# Show status after retry
echo ""
echo "13. Status after DLQ retry..."
python queuectl.py status

# Show config
echo ""
echo "14. Showing configuration..."
python queuectl.py config get

# Update config
echo ""
echo "15. Updating configuration..."
python queuectl.py config set max-retries 5
python queuectl.py config set backoff-base 3
python queuectl.py config get

echo ""
echo "=== Demo Complete ==="
echo ""
echo "Check the logs/ directory for job output files."

