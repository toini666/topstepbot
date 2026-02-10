"""
News Alert Job
Runs every minute to check for upcoming high-impact news.
Sends Discord notification 5 minutes before the event.
"""

from datetime import datetime, timedelta
import logging
import json
from backend.services.calendar_service import calendar_service
from backend.services.discord_service import discord_service
from backend.services.timezone_service import now_user_tz
from backend.database import SessionLocal, Setting, Log

logger = logging.getLogger("topstepbot")

async def news_alert_job():
    """
    Checks if there are any high-impact news events starting in exactly 5 minutes.
    Sends a Discord alert if found.
    """
    try:
        # Get today's events (cached)
        # We use cached calendar because it's updated at 7 AM or manually
        events = calendar_service.get_cached_calendar()
        if not events:
            # Try to fetch if cache is empty (e.g. restart)
            events = await calendar_service.fetch_calendar()
            if not events:
                return

        now_local = now_user_tz()
        today_str = now_local.strftime("%m-%d-%Y")
        
        # Filter for today
        todays_events = [e for e in events if e.get("date") == today_str]
        if not todays_events:
            return

        # Get settings for filtering (same as daily summary)
        db = SessionLocal()
        try:
            # Check if news blocking is enabled effectively (or just use the same filters)
            # We want to alert for the same events that we block or summarize
            impacts_setting = db.query(Setting).filter(Setting.key == "calendar_major_impacts").first()
            countries_setting = db.query(Setting).filter(Setting.key == "calendar_major_countries").first()
            webhook_setting = db.query(Setting).filter(Setting.key == "calendar_discord_url").first()
            
            # New Settings
            alert_enabled = db.query(Setting).filter(Setting.key == "calendar_news_alert_enabled").first()
            alert_minutes = db.query(Setting).filter(Setting.key == "calendar_news_alert_minutes").first()
            
            # Defaults
            target_impacts = json.loads(impacts_setting.value) if impacts_setting and impacts_setting.value else ["High", "Medium"]
            target_countries = json.loads(countries_setting.value) if countries_setting and countries_setting.value else ["USD"]
            webhook_url = webhook_setting.value if webhook_setting else None
            
            is_enabled = alert_enabled.value.lower() == "true" if alert_enabled and alert_enabled.value else False
            minutes_before = int(alert_minutes.value) if alert_minutes and alert_minutes.value else 5
            
        finally:
            db.close()

        if not webhook_url or not is_enabled:
            return

        alert_events = []
        
        for event in todays_events:
            # Filter
            if event.get("impact") not in target_impacts:
                continue
            if event.get("country") not in target_countries:
                continue
                
            event_time_str = event.get("time") # "HH:MM" 24h format
            if not event_time_str or ":" not in event_time_str:
                continue
            
            try:
                # Parse event time
                h, m = map(int, event_time_str.split(":"))
                event_dt = now_local.replace(hour=h, minute=m, second=0, microsecond=0)
                
                # Check logic: Event is in X minutes
                target_check_time = now_local + timedelta(minutes=minutes_before)
                
                if event_dt.hour == target_check_time.hour and event_dt.minute == target_check_time.minute:
                    alert_events.append(event)
                    
            except Exception as e:
                print(f"Time parse error in news alert: {e}")
                continue
        
        if alert_events:
            await send_pre_news_alert(webhook_url, alert_events, minutes_before)


    except Exception as e:
        print(f"News alert job failed: {e}")

async def send_pre_news_alert(webhook_url: str, events: list, minutes_before: int):
    """Send the pre-news warning to Discord."""
    
    fields = []
    for ev in events:
        impact_emoji = "🔴" if ev.get("impact") == "High" else "🟠"
        fields.append({
            "name": f"{impact_emoji} {ev.get('time')} - {ev.get('country')} {ev.get('title')}",
            "value": f"Starting in {minutes_before} minutes",
            "inline": False
        })
    
    embed = {
        "title": "⚠️ Upcoming High-Impact News",
        "description": f"Trading volatility expected in **{minutes_before} minutes**.",
        "color": 0xFF0000, # Red
        "fields": fields,
        "footer": {"text": "TopStep Bot News Alert"}
    }
    
    try:
        await discord_service.send_message(webhook_url, embeds=[embed])
        # Log it
        db = SessionLocal()
        db.add(Log(level="INFO", message=f"Sent pre-news alert for {len(events)} events"))
        db.commit()
        db.close()
    except Exception as e:
        print(f"Failed to send pre-news alert: {e}")
