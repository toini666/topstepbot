"""
Timezone Service - Centralized timezone management.

Provides a single source of truth for the user's configured timezone.
All backend code should import get_user_tz() and now_user_tz() from here
instead of creating their own pytz timezone objects.

Resolution priority: ENV var > SQLite setting > Default (Europe/Brussels)
"""

from zoneinfo import ZoneInfo, available_timezones
from datetime import datetime, timezone, timedelta
from typing import Optional
import os

# Default timezone for backward compatibility
DEFAULT_TIMEZONE = "Europe/Brussels"

# Eastern Time zone (ForexFactory calendar source timezone)
ET_TIMEZONE = ZoneInfo("America/New_York")

# Module-level cache to avoid repeated DB lookups
_cached_tz: Optional[ZoneInfo] = None
_cached_tz_name: Optional[str] = None


def _resolve_tz_name() -> str:
    """
    Resolve timezone name with priority:
    1. USER_TIMEZONE env var
    2. SQLite settings table (key: "USER_TIMEZONE")
    3. Default: Europe/Brussels
    """
    # Priority 1: Environment variable
    env_tz = os.getenv("USER_TIMEZONE")
    if env_tz and env_tz in available_timezones():
        return env_tz

    # Priority 2: Database setting
    try:
        from backend.services.config_service import get_config_value
        db_tz = get_config_value("USER_TIMEZONE")
        if db_tz and db_tz in available_timezones():
            return db_tz
    except Exception:
        pass

    return DEFAULT_TIMEZONE


def get_user_tz() -> ZoneInfo:
    """Get the user's configured timezone as a ZoneInfo object."""
    global _cached_tz, _cached_tz_name
    tz_name = _resolve_tz_name()
    if _cached_tz is None or _cached_tz_name != tz_name:
        _cached_tz = ZoneInfo(tz_name)
        _cached_tz_name = tz_name
    return _cached_tz


def get_user_tz_name() -> str:
    """Get the user's configured timezone name string (e.g. 'Europe/Brussels')."""
    return _resolve_tz_name()


def now_user_tz() -> datetime:
    """Get current datetime in the user's configured timezone."""
    return datetime.now(get_user_tz())


def now_utc() -> datetime:
    """Get current datetime in UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


def reload_timezone():
    """Force re-read of timezone from config. Call after settings change."""
    global _cached_tz, _cached_tz_name
    _cached_tz = None
    _cached_tz_name = None


def is_valid_timezone(tz_name: str) -> bool:
    """Check if a timezone name is valid."""
    return tz_name in available_timezones()


def get_et_offset_hours() -> float:
    """
    Calculate the offset in hours from ET (America/New_York) to user's timezone.
    """
    now = datetime.now(timezone.utc)
    et_offset = now.astimezone(ET_TIMEZONE).utcoffset().total_seconds()
    user_offset = now.astimezone(get_user_tz()).utcoffset().total_seconds()
    return (user_offset - et_offset) / 3600


def get_utc_offset_hours() -> float:
    """
    Calculate the offset in hours from UTC to user's timezone.
    Used by calendar_service to convert ForexFactory XML times (which are in UTC).
    """
    now = datetime.now(timezone.utc)
    user_offset = now.astimezone(get_user_tz()).utcoffset().total_seconds()
    return user_offset / 3600
