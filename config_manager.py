"""
Configuration manager for QueueCTL
"""
from typing import Optional, Dict
import db


def get_config(key: str) -> Optional[str]:
    """Get a configuration value by key"""
    result = db.fetch_one("SELECT value FROM config WHERE key = ?", (key,))
    if result:
        return result['value']
    return None


def get_all_configs() -> Dict[str, str]:
    """Get all configuration values"""
    results = db.execute_query("SELECT key, value FROM config ORDER BY key")
    return {row['key']: row['value'] for row in results}


def set_config(key: str, value: str) -> bool:
    """Set a configuration value"""
    # Try to update first
    rowcount = db.execute_update(
        "UPDATE config SET value = ? WHERE key = ?",
        (value, key)
    )
    
    # If no rows updated, insert new config
    if rowcount == 0:
        db.execute_update(
            "INSERT INTO config (key, value) VALUES (?, ?)",
            (key, value)
        )
    
    return True


def get_config_int(key: str, default: int = 0) -> int:
    """Get a configuration value as integer"""
    value = get_config(key)
    if value is None:
        return default
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_max_retries() -> int:
    """Get max_retries configuration"""
    return get_config_int('max_retries', 3)


def get_backoff_base() -> int:
    """Get backoff_base configuration"""
    return get_config_int('backoff_base', 2)


def get_poll_interval() -> int:
    """Get poll_interval configuration"""
    return get_config_int('poll_interval', 1)


def normalize_config_key(key: str) -> str:
    """
    Normalize config key from CLI format to DB format
    e.g., 'max-retries' -> 'max_retries'
    """
    return key.replace('-', '_')


def denormalize_config_key(key: str) -> str:
    """
    Denormalize config key from DB format to CLI format
    e.g., 'max_retries' -> 'max-retries'
    """
    return key.replace('_', '-')

