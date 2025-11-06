#!/usr/bin/env python3
"""
QueueCTL - Production-grade CLI background job queue system
"""
import click
import json
import sys
import db
import job_manager
import worker
import config_manager
import utils


@click.group()
def cli():
    """QueueCTL - Background job queue management system"""
    pass


@cli.command()
def init_db():
    """Initialize the database"""
    if db.db_exists():
        click.echo("Database already exists at queuectl.db")
        if not click.confirm("Do you want to reinitialize it?"):
            return
    
    db.init_db()
    click.echo("[OK] Database initialized successfully at queuectl.db")


@cli.command()
@click.argument('job_json')
def enqueue(job_json):
    """
    Enqueue a new job
    
    Example: queuectl enqueue '{"id":"job1","command":"echo Hello"}'
    """
    if not db.db_exists():
        click.echo("Error: Database not initialized. Run 'queuectl init-db' first.", err=True)
        sys.exit(1)
    
    try:
        job_data = json.loads(job_json)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON: {e}", err=True)
        sys.exit(1)
    
    success, message, job_id = job_manager.enqueue_job(job_data)
    
    if success:
        click.echo(message)
    else:
        click.echo(f"Error: {message}", err=True)
        sys.exit(1)


@cli.group()
def worker_group():
    """Worker management commands"""
    pass


@worker_group.command(name='start')
@click.option('--count', default=1, help='Number of workers to start')
@click.option('--stop-when-empty', is_flag=True, help='Stop workers when queue is empty')
def worker_start(count, stop_when_empty):
    """Start worker processes"""
    if not db.db_exists():
        click.echo("Error: Database not initialized. Run 'queuectl init-db' first.", err=True)
        sys.exit(1)

    if count < 1:
        click.echo("Error: Worker count must be at least 1", err=True)
        sys.exit(1)

    # Recover any stale locks before starting
    worker.recover_stale_locks()

    worker.start_workers(count, stop_when_empty=stop_when_empty)


@worker_group.command(name='stop')
def worker_stop():
    """Stop all active workers gracefully"""
    worker.stop_workers()


@cli.command()
def status():
    """Show queue status"""
    if not db.db_exists():
        click.echo("Error: Database not initialized. Run 'queuectl init-db' first.", err=True)
        sys.exit(1)
    
    counts = job_manager.get_job_counts()
    active_workers = worker.get_active_worker_count()
    
    click.echo("\n[QUEUE STATUS]")
    click.echo(f"  Total jobs: {counts['total']}")
    click.echo(f"  Pending: {counts['pending']}")
    click.echo(f"  Processing: {counts['processing']}")
    click.echo(f"  Completed: {counts['completed']}")
    click.echo(f"  Failed: {counts['failed']}")
    click.echo(f"  Dead Letter Queue: {counts['dead']}")
    click.echo("\n[WORKERS]")
    click.echo(f"  Active: {active_workers}")
    click.echo()


@cli.command()
@click.option('--state', help='Filter by state (pending/processing/completed/failed/dead)')
@click.option('--limit', default=50, help='Maximum number of jobs to display')
def list(state, limit):
    """List jobs"""
    if not db.db_exists():
        click.echo("Error: Database not initialized. Run 'queuectl init-db' first.", err=True)
        sys.exit(1)
    
    jobs = job_manager.list_jobs(state=state, limit=limit)
    
    if not jobs:
        click.echo("No jobs found.")
        return
    
    # Print header
    click.echo(f"\n{'ID':<20} {'STATE':<12} {'ATT':<4} {'MAX':<4} {'NEXT_RUN_AT':<25} {'COMMAND':<40}")
    click.echo("-" * 105)
    
    # Print jobs
    for job in jobs:
        job_id = job['id'][:18]
        state_str = job['state']
        attempts = job['attempts']
        max_retries = job['max_retries']
        next_run = utils.format_timestamp(job['next_run_at'])[:24]
        command = job['command'][:38]
        
        click.echo(f"{job_id:<20} {state_str:<12} {attempts:<4} {max_retries:<4} {next_run:<25} {command:<40}")

    click.echo()


@cli.group()
def dlq():
    """Dead Letter Queue management"""
    pass


@dlq.command(name='list')
@click.option('--limit', default=50, help='Maximum number of jobs to display')
def dlq_list(limit):
    """List jobs in Dead Letter Queue"""
    if not db.db_exists():
        click.echo("Error: Database not initialized. Run 'queuectl init-db' first.", err=True)
        sys.exit(1)

    jobs = job_manager.list_dlq_jobs(limit=limit)

    if not jobs:
        click.echo("No jobs in Dead Letter Queue.")
        return

    # Print header
    click.echo(f"\n{'ID':<20} {'ATT':<4} {'MAX':<4} {'LAST_ERROR':<60}")
    click.echo("-" * 88)

    # Print jobs
    for job in jobs:
        job_id = job['id'][:18]
        attempts = job['attempts']
        max_retries = job['max_retries']
        last_error = (job['last_error'] or 'N/A')[:58]

        click.echo(f"{job_id:<20} {attempts:<4} {max_retries:<4} {last_error:<60}")

    click.echo()


@dlq.command(name='retry')
@click.argument('job_id')
def dlq_retry(job_id):
    """Retry a job from Dead Letter Queue"""
    if not db.db_exists():
        click.echo("Error: Database not initialized. Run 'queuectl init-db' first.", err=True)
        sys.exit(1)

    success, message = job_manager.retry_dlq_job(job_id)

    if success:
        click.echo(message)
    else:
        click.echo(f"Error: {message}", err=True)
        sys.exit(1)


@cli.group()
def config():
    """Configuration management"""
    pass


@config.command(name='get')
@click.argument('key', required=False)
def config_get(key):
    """Get configuration value(s)"""
    if not db.db_exists():
        click.echo("Error: Database not initialized. Run 'queuectl init-db' first.", err=True)
        sys.exit(1)

    if key:
        # Get specific config
        normalized_key = config_manager.normalize_config_key(key)
        value = config_manager.get_config(normalized_key)

        if value is None:
            click.echo(f"Error: Config key '{key}' not found", err=True)
            sys.exit(1)

        click.echo(f"{key}: {value}")
    else:
        # Get all configs
        configs = config_manager.get_all_configs()

        if not configs:
            click.echo("No configuration found.")
            return

        click.echo("\n[CONFIGURATION]")
        for key, value in sorted(configs.items()):
            display_key = config_manager.denormalize_config_key(key)
            click.echo(f"  {display_key}: {value}")
        click.echo()


@config.command(name='set')
@click.argument('key')
@click.argument('value')
def config_set(key, value):
    """Set configuration value"""
    if not db.db_exists():
        click.echo("Error: Database not initialized. Run 'queuectl init-db' first.", err=True)
        sys.exit(1)

    normalized_key = config_manager.normalize_config_key(key)
    config_manager.set_config(normalized_key, value)

    click.echo(f"[OK] Set {key} = {value}")


# Register command groups with proper names
cli.add_command(worker_group, name='worker')


if __name__ == '__main__':
    cli()

