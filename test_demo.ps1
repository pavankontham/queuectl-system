# QueueCTL Demo Test Script (PowerShell)

Write-Host "=== QueueCTL Demo Test ===" -ForegroundColor Cyan
Write-Host ""

# Clean up previous test
Write-Host "Cleaning up previous test data..." -ForegroundColor Yellow
if (Test-Path "queuectl.db") { Remove-Item "queuectl.db" -Force }
if (Test-Path "logs") { Remove-Item "logs" -Recurse -Force }
New-Item -ItemType Directory -Path "logs" -Force | Out-Null

# Initialize database
Write-Host ""
Write-Host "1. Initializing database..." -ForegroundColor Green
python queuectl.py init-db

# Enqueue test jobs
Write-Host ""
Write-Host "2. Enqueuing test jobs..." -ForegroundColor Green

# Success job
python queuectl.py enqueue '{"id":"test-success","command":"echo Success Job","max_retries":3,"priority":1}'

# Failure job (will retry and go to DLQ)
python queuectl.py enqueue '{"id":"test-fail","command":"exit 1","max_retries":2,"priority":2}'

# Delayed job (5 seconds from now)
$delayedTime = (Get-Date).ToUniversalTime().AddSeconds(5).ToString("yyyy-MM-ddTHH:mm:ssZ")
python queuectl.py enqueue "{`"id`":`"test-delayed`",`"command`":`"echo Delayed Job`",`"run_at`":`"$delayedTime`"}"

# Timeout job
python queuectl.py enqueue '{"id":"test-timeout","command":"timeout /t 10","timeout_seconds":2,"max_retries":1}'

# Show status
Write-Host ""
Write-Host "3. Checking initial status..." -ForegroundColor Green
python queuectl.py status

# List jobs
Write-Host ""
Write-Host "4. Listing all jobs..." -ForegroundColor Green
python queuectl.py list

# Start workers in background
Write-Host ""
Write-Host "5. Starting 2 workers in background..." -ForegroundColor Green
$workerJob = Start-Job -ScriptBlock { 
    Set-Location $using:PWD
    python queuectl.py worker start --count 2 
}

# Wait for jobs to process
Write-Host ""
Write-Host "6. Waiting 15 seconds for jobs to process..." -ForegroundColor Green
Start-Sleep -Seconds 15

# Stop workers
Write-Host ""
Write-Host "7. Stopping workers..." -ForegroundColor Green
Stop-Job -Job $workerJob
Remove-Job -Job $workerJob -Force

# Show final status
Write-Host ""
Write-Host "8. Checking final status..." -ForegroundColor Green
python queuectl.py status

# List pending jobs
Write-Host ""
Write-Host "9. Listing pending jobs..." -ForegroundColor Green
python queuectl.py list --state pending

# List completed jobs
Write-Host ""
Write-Host "10. Listing completed jobs..." -ForegroundColor Green
python queuectl.py list --state completed

# Show DLQ
Write-Host ""
Write-Host "11. Showing Dead Letter Queue..." -ForegroundColor Green
python queuectl.py dlq list

# Retry from DLQ
Write-Host ""
Write-Host "12. Retrying a job from DLQ..." -ForegroundColor Green
python queuectl.py dlq retry test-fail

# Show status after retry
Write-Host ""
Write-Host "13. Status after DLQ retry..." -ForegroundColor Green
python queuectl.py status

# Show config
Write-Host ""
Write-Host "14. Showing configuration..." -ForegroundColor Green
python queuectl.py config get

# Update config
Write-Host ""
Write-Host "15. Updating configuration..." -ForegroundColor Green
python queuectl.py config set max-retries 5
python queuectl.py config set backoff-base 3
python queuectl.py config get

Write-Host ""
Write-Host "=== Demo Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check the logs/ directory for job output files." -ForegroundColor Yellow

