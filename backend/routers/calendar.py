
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from backend.database import get_db, Setting
from backend.services.calendar_service import calendar_service
import json

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
    responses={404: {"description": "Not found"}},
)

class CalendarSettings(BaseModel):
    discord_url: Optional[str] = None
    enabled: bool = False
    major_countries: List[str] = ["USD"]
    major_impacts: List[str] = ["High", "Medium"]
    news_alert_enabled: bool = False
    news_alert_minutes: int = 5

@router.get("/")
async def get_calendar():
    """Get the current economic calendar."""
    # If cache is empty, try to fetch
    if not calendar_service.get_cached_calendar():
        await calendar_service.fetch_calendar()
    
    return calendar_service.get_cached_calendar()

@router.get("/refresh")
async def refresh_calendar():
    """Force refresh of the calendar data."""
    # Reset last fetch to allow immediate refresh override
    calendar_service._last_fetch = None 
    events = await calendar_service.fetch_calendar()
    
    # CRITICAL: Recalculate news blocks immediately after refresh so settings/risk engine are aware
    await calendar_service.recalculate_news_blocks()
    
    return events

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Get calendar settings."""
    url_setting = db.query(Setting).filter(Setting.key == "calendar_discord_url").first()
    
    # We don't have a separate enabled flag in Setting yet, maybe just imply enabled if URL is present?
    # Or strict flag? Let's use a separate key.
    today_setting = db.query(Setting).filter(Setting.key == "calendar_discord_enabled").first()
    
    impacts_setting = db.query(Setting).filter(Setting.key == "calendar_major_impacts").first()
    countries_setting = db.query(Setting).filter(Setting.key == "calendar_major_countries").first()
    
    alert_enabled_setting = db.query(Setting).filter(Setting.key == "calendar_news_alert_enabled").first()
    alert_minutes_setting = db.query(Setting).filter(Setting.key == "calendar_news_alert_minutes").first()
    
    return {
        "discord_url": url_setting.value if url_setting else "",
        "enabled": (today_setting.value == "true") if today_setting else False,
        "major_countries": json.loads(countries_setting.value) if countries_setting and countries_setting.value else ["USD"],
        "major_impacts": json.loads(impacts_setting.value) if impacts_setting and impacts_setting.value else ["High", "Medium"],
        "news_alert_enabled": (alert_enabled_setting.value == "true") if alert_enabled_setting else False,
        "news_alert_minutes": int(alert_minutes_setting.value) if alert_minutes_setting else 5
    }

@router.post("/settings")
async def update_settings(settings: CalendarSettings, db: Session = Depends(get_db)):
    """Update calendar settings and recalculate news blocks."""
    # URL
    url_setting = db.query(Setting).filter(Setting.key == "calendar_discord_url").first()
    if not url_setting:
        url_setting = Setting(key="calendar_discord_url", value=settings.discord_url or "")
        db.add(url_setting)
    else:
        url_setting.value = settings.discord_url or ""
    
    # Enabled
    today_setting = db.query(Setting).filter(Setting.key == "calendar_discord_enabled").first()
    val_str = "true" if settings.enabled else "false"
    if not today_setting:
        today_setting = Setting(key="calendar_discord_enabled", value=val_str)
        db.add(today_setting)
    else:
        today_setting.value = val_str
        
    # Major Countries
    countries_setting = db.query(Setting).filter(Setting.key == "calendar_major_countries").first()
    countries_json = json.dumps(settings.major_countries)
    if not countries_setting:
        countries_setting = Setting(key="calendar_major_countries", value=countries_json)
        db.add(countries_setting)
    else:
        countries_setting.value = countries_json
        
    # Major Impacts
    impacts_setting = db.query(Setting).filter(Setting.key == "calendar_major_impacts").first()
    impacts_json = json.dumps(settings.major_impacts)
    if not impacts_setting:
        impacts_setting = Setting(key="calendar_major_impacts", value=impacts_json)
        db.add(impacts_setting)
    else:
        impacts_setting.value = impacts_json

    # News Alert Enabled
    alert_enabled_setting = db.query(Setting).filter(Setting.key == "calendar_news_alert_enabled").first()
    val_str = "true" if settings.news_alert_enabled else "false"
    if not alert_enabled_setting:
        alert_enabled_setting = Setting(key="calendar_news_alert_enabled", value=val_str)
        db.add(alert_enabled_setting)
    else:
        alert_enabled_setting.value = val_str

    # News Alert Minutes
    alert_minutes_setting = db.query(Setting).filter(Setting.key == "calendar_news_alert_minutes").first()
    if not alert_minutes_setting:
        alert_minutes_setting = Setting(key="calendar_news_alert_minutes", value=str(settings.news_alert_minutes))
        db.add(alert_minutes_setting)
    else:
        alert_minutes_setting.value = str(settings.news_alert_minutes)
        
    db.commit()
    
    # Recalculate news blocks with new settings
    await calendar_service.recalculate_news_blocks()
    
    return {"status": "success"}


@router.post("/recalculate-blocks")
async def recalculate_blocks():
    """Force recalculation of news blocks based on current settings."""
    blocks = await calendar_service.recalculate_news_blocks()
    return {"status": "success", "blocks_count": len(blocks), "blocks": blocks}


@router.post("/test-notification")
async def test_notification():
    """Trigger a test notification to Discord for today's events."""
    await calendar_service.check_calendar_job()
    return {"status": "triggered"}
