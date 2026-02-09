"""
Config Service - Centralized configuration resolution.

Priority: Environment variable > SQLite settings table > None

This allows Docker users to configure the app either via env vars
(docker-compose.yml) or via the web-based setup wizard (which saves to DB).
"""

import os
from typing import Optional


def get_config_value(key: str) -> Optional[str]:
    """
    Get a configuration value with priority:
    1. Environment variable (set via .env, docker-compose, or shell)
    2. SQLite settings table (set via setup wizard)
    3. None
    """
    # Priority 1: Environment variable
    env_val = os.getenv(key)
    if env_val:
        return env_val

    # Priority 2: Database settings table
    try:
        from backend.database import SessionLocal, Setting
        db = SessionLocal()
        try:
            setting = db.query(Setting).filter(Setting.key == key).first()
            if setting and setting.value:
                return setting.value
        finally:
            db.close()
    except Exception:
        pass

    return None


def is_app_configured() -> bool:
    """Check if the minimum required credentials are configured (TopStep)."""
    username = get_config_value("TOPSTEP_USERNAME")
    api_key = get_config_value("TOPSTEP_APIKEY")
    return bool(username and api_key)


def is_telegram_configured() -> bool:
    """Check if Telegram credentials are configured."""
    bot_token = get_config_value("TELEGRAM_BOT_TOKEN")
    chat_id = get_config_value("TELEGRAM_ID")
    return bool(bot_token and chat_id)


def is_heartbeat_configured() -> bool:
    """Check if heartbeat monitoring is configured."""
    webhook_url = get_config_value("HEARTBEAT_WEBHOOK_URL")
    return bool(webhook_url)
