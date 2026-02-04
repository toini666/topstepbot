"""
Settings Cache - In-memory cache for frequently accessed settings.

This module provides a thread-safe, TTL-based cache for global settings
and account settings to reduce database queries during frequent operations
like position monitoring and signal processing.
"""

import json
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps

from backend.constants import CACHE_TTL_SETTINGS


class SettingsCache:
    """
    Thread-safe in-memory cache for database settings.

    Features:
    - TTL-based expiration
    - Per-account caching for account-specific settings
    - Manual invalidation support
    - Thread-safe access
    """

    def __init__(self, ttl_seconds: int = CACHE_TTL_SETTINGS):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._lock = threading.RLock()
        self._ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache if it exists and is not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                return None

            value, expiry = self._cache[key]

            if datetime.now(timezone.utc) > expiry:
                # Expired - remove and return None
                del self._cache[key]
                return None

            return value

    def set(self, key: str, value: Any, ttl_seconds: int = None):
        """
        Set a value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Override default TTL
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        expiry = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        with self._lock:
            self._cache[key] = (value, expiry)

    def delete(self, key: str):
        """Remove a specific key from cache."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()

    def invalidate_pattern(self, pattern: str):
        """
        Invalidate all keys matching a pattern.

        Args:
            pattern: Key prefix to match (e.g., "account_settings_")
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(pattern)]
            for key in keys_to_delete:
                del self._cache[key]


# Global cache instance
_settings_cache = SettingsCache()


def get_cached_global_settings(db_session) -> Dict[str, Any]:
    """
    Get global settings with caching.

    First checks cache, then falls back to database if cache miss.
    """
    cache_key = "global_settings"
    cached = _settings_cache.get(cache_key)

    if cached is not None:
        return cached

    # Cache miss - fetch from database
    from backend.database import Setting

    settings = {}

    # Fetch all settings at once
    all_settings = db_session.query(Setting).all()
    settings_dict = {s.key: s.value for s in all_settings}

    # Parse settings with defaults
    settings["blocked_periods_enabled"] = settings_dict.get("blocked_periods_enabled", "true").lower() == "true"

    bp_json = settings_dict.get("blocked_periods", "[]")
    try:
        settings["blocked_periods"] = json.loads(bp_json)
    except Exception:
        settings["blocked_periods"] = []

    settings["auto_flatten_enabled"] = settings_dict.get("auto_flatten_enabled", "false").lower() == "true"
    settings["auto_flatten_time"] = settings_dict.get("auto_flatten_time", "21:55")
    settings["market_open_time"] = settings_dict.get("market_open_time", "00:00")
    settings["market_close_time"] = settings_dict.get("market_close_time", "22:00")
    settings["weekend_markets_open"] = settings_dict.get("weekend_markets_open", "false").lower() == "true"

    td_json = settings_dict.get("trading_days", '["MON","TUE","WED","THU","FRI"]')
    try:
        settings["trading_days"] = json.loads(td_json)
    except Exception:
        settings["trading_days"] = ["MON", "TUE", "WED", "THU", "FRI"]

    settings["enforce_single_position_per_asset"] = settings_dict.get("enforce_single_position_per_asset", "true").lower() == "true"
    settings["block_cross_account_opposite"] = settings_dict.get("block_cross_account_opposite", "true").lower() == "true"
    settings["news_block_enabled"] = settings_dict.get("news_block_enabled", "false").lower() == "true"
    settings["news_block_before_minutes"] = int(settings_dict.get("news_block_before_minutes", "5"))
    settings["news_block_after_minutes"] = int(settings_dict.get("news_block_after_minutes", "5"))
    settings["blocked_hours_position_action"] = settings_dict.get("blocked_hours_position_action", "NOTHING")
    settings["position_action_buffer_minutes"] = int(settings_dict.get("position_action_buffer_minutes", "1"))

    # Cache the result
    _settings_cache.set(cache_key, settings)

    return settings


def get_cached_account_settings(db_session, account_id: int) -> Optional[Dict[str, Any]]:
    """
    Get account settings with caching.

    Args:
        db_session: SQLAlchemy session
        account_id: Account ID to fetch settings for

    Returns:
        Account settings dict or None if not found
    """
    cache_key = f"account_settings_{account_id}"
    cached = _settings_cache.get(cache_key)

    if cached is not None:
        return cached

    # Cache miss - fetch from database
    from backend.database import AccountSettings

    account = db_session.query(AccountSettings).filter(
        AccountSettings.account_id == account_id
    ).first()

    if not account:
        return None

    settings = {
        "id": account.id,
        "account_id": account.account_id,
        "account_name": account.account_name,
        "trading_enabled": account.trading_enabled,
        "risk_per_trade": account.risk_per_trade,
        "max_contracts": account.max_contracts
    }

    _settings_cache.set(cache_key, settings)

    return settings


def get_cached_all_account_settings(db_session) -> Dict[int, Dict[str, Any]]:
    """
    Get all account settings with caching.

    Fetches all accounts at once to avoid N+1 queries.

    Returns:
        Dict mapping account_id to settings dict
    """
    cache_key = "all_account_settings"
    cached = _settings_cache.get(cache_key)

    if cached is not None:
        return cached

    # Cache miss - fetch all from database
    from backend.database import AccountSettings

    all_accounts = db_session.query(AccountSettings).all()

    result = {}
    for account in all_accounts:
        result[account.account_id] = {
            "id": account.id,
            "account_id": account.account_id,
            "account_name": account.account_name,
            "trading_enabled": account.trading_enabled,
            "risk_per_trade": account.risk_per_trade,
            "max_contracts": account.max_contracts
        }

    _settings_cache.set(cache_key, result)

    return result


def get_cached_strategy_configs(db_session, account_id: int) -> Dict[str, Dict[str, Any]]:
    """
    Get all strategy configs for an account with caching.

    Returns:
        Dict mapping strategy tv_id to config dict
    """
    cache_key = f"strategy_configs_{account_id}"
    cached = _settings_cache.get(cache_key)

    if cached is not None:
        return cached

    # Cache miss - fetch from database
    from backend.database import AccountStrategyConfig, Strategy

    configs = db_session.query(AccountStrategyConfig).filter(
        AccountStrategyConfig.account_id == account_id
    ).all()

    # Get strategy templates for tv_id mapping
    strategy_ids = [c.strategy_id for c in configs]
    strategies = db_session.query(Strategy).filter(Strategy.id.in_(strategy_ids)).all()
    strategy_map = {s.id: s.tv_id for s in strategies}

    result = {}
    for config in configs:
        tv_id = strategy_map.get(config.strategy_id)
        if tv_id:
            result[tv_id] = {
                "enabled": config.enabled,
                "risk_factor": config.risk_factor,
                "allowed_sessions": config.allowed_sessions,
                "partial_tp_percent": config.partial_tp_percent,
                "move_sl_to_entry": config.move_sl_to_entry,
                "allow_outside_sessions": config.allow_outside_sessions
            }

    _settings_cache.set(cache_key, result)

    return result


def invalidate_global_settings():
    """Invalidate global settings cache."""
    _settings_cache.delete("global_settings")


def invalidate_account_settings(account_id: int = None):
    """
    Invalidate account settings cache.

    Args:
        account_id: Specific account to invalidate, or None for all
    """
    if account_id:
        _settings_cache.delete(f"account_settings_{account_id}")
        _settings_cache.delete(f"strategy_configs_{account_id}")
    else:
        _settings_cache.invalidate_pattern("account_settings_")
        _settings_cache.invalidate_pattern("strategy_configs_")
        _settings_cache.delete("all_account_settings")


def invalidate_all():
    """Invalidate all cached settings."""
    _settings_cache.clear()


# Decorator for cached database access
def cached_db_call(key_func):
    """
    Decorator to cache database call results.

    Args:
        key_func: Function that returns cache key from function args
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = key_func(*args, **kwargs)
            cached = _settings_cache.get(cache_key)

            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            _settings_cache.set(cache_key, result)
            return result

        return wrapper
    return decorator
