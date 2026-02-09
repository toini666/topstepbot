"""
Setup Router - First-run configuration wizard API.

Provides endpoints for the frontend setup wizard to check configuration
status and save credentials (stored in the SQLite settings table).
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.database import SessionLocal, Setting
from backend.services.config_service import (
    is_app_configured,
    is_telegram_configured,
    is_heartbeat_configured,
    get_config_value,
)
from backend.services.topstep_client import topstep_client
from backend.services.telegram_service import telegram_service
from backend.services.telegram_bot import telegram_bot

router = APIRouter()

SETUP_KEYS = [
    "TOPSTEP_USERNAME",
    "TOPSTEP_APIKEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ID",
    "HEARTBEAT_WEBHOOK_URL",
    "HEARTBEAT_INTERVAL_SECONDS",
    "HEARTBEAT_AUTH_TOKEN",
]


class SetupConfig(BaseModel):
    TOPSTEP_USERNAME: Optional[str] = None
    TOPSTEP_APIKEY: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ID: Optional[str] = None
    HEARTBEAT_WEBHOOK_URL: Optional[str] = None
    HEARTBEAT_INTERVAL_SECONDS: Optional[str] = None
    HEARTBEAT_AUTH_TOKEN: Optional[str] = None


@router.get("/setup/status")
def get_setup_status():
    """Returns configuration status without exposing credential values."""
    return {
        "configured": is_app_configured(),
        "details": {
            "topstep": is_app_configured(),
            "telegram": is_telegram_configured(),
            "heartbeat": is_heartbeat_configured(),
        },
    }


@router.post("/setup/save")
async def save_setup(config: SetupConfig):
    """
    Save configuration to the SQLite settings table and reload credentials.
    Only non-empty values are saved. Attempts a TopStep login to validate.
    """
    db = SessionLocal()
    saved_keys = []
    try:
        config_dict = config.model_dump(exclude_none=True)
        for key, value in config_dict.items():
            if key not in SETUP_KEYS:
                continue
            value = value.strip() if value else ""
            if not value:
                continue

            existing = db.query(Setting).filter(Setting.key == key).first()
            if existing:
                existing.value = value
            else:
                db.add(Setting(key=key, value=value))
            saved_keys.append(key)

        db.commit()
    finally:
        db.close()

    # Reload credentials in running services
    topstep_client.reload_credentials()
    telegram_service.reload_credentials()
    telegram_bot.reload_credentials()

    # Attempt TopStep login to validate credentials
    connected = False
    error_message = None
    if topstep_client.username and topstep_client.api_key:
        try:
            await topstep_client.login()
            connected = True
        except Exception as e:
            error_message = str(e)

    # Send startup notification if Telegram is now configured
    if connected and telegram_service.bot_token and telegram_service.chat_id:
        try:
            await telegram_service.notify_startup()
        except Exception:
            pass

    return {
        "success": True,
        "saved_keys": saved_keys,
        "connected": connected,
        "error": error_message,
    }
