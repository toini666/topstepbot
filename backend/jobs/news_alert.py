"""
News Alert Job
Runs every minute to check for upcoming high-impact news.
Sends Discord notification 5 minutes before the event.
"""

from datetime import datetime, timedelta
import pytz
import logging
import json
from backend.services.calendar_service import calendar_service
from backend.services.discord_service import discord_service
from backend.database import SessionLocal, Setting, Log

logger = logging.getLogger("topstepbot")
BRUSSELS_TZ = pytz.timezone("Europe/Brussels")

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

        now_bru = datetime.now(BRUSSELS_TZ)
        today_str = now_bru.strftime("%m-%d-%Y")
        
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
            
            target_impacts = json.loads(impacts_setting.value) if impacts_setting and impacts_setting.value else ["High", "Medium"]
            target_countries = json.loads(countries_setting.value) if countries_setting and countries_setting.value else ["USD"]
            webhook_url = webhook_setting.value if webhook_setting else None
            
        finally:
            db.close()

        if not webhook_url:
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
                event_dt = now_bru.replace(hour=h, minute=m, second=0, microsecond=0)
                
                # Check logic: Event is in 5 minutes
                # Means: event_dt - now is approx 5 minutes
                # We run every minute, so we check if 4m30s < diff < 5m30s ? 
                # Or just match the minute: event_dt.minute == (now + 5min).minute
                # Let's match strictly on minutes to avoid double alerting if job drifts slightly
                
                target_check_time = now_bru + timedelta(minutes=5)
                
                if event_dt.hour == target_check_time.hour and event_dt.minute == target_check_time.minute:
                    alert_events.append(event)
                    
            except Exception as e:
                print(f"Time parse error in news alert: {e}")
                continue
        
        if alert_events:
            await send_pre_news_alert(webhook_url, alert_events)

    except Exception as e:
        print(f"News alert job failed: {e}")

async def send_pre_news_alert(webhook_url: str, events: list):
    """Send the 5-minute warning to Discord."""
    
    fields = []
    for ev in events:
        impact_emoji = "🔴" if ev.get("impact") == "High" else "🟠"
        fields.append({
            "name": f"{impact_emoji} {ev.get('time')} - {ev.get('country')} {ev.get('title')}",
            "value": "Starting in 5 minutes",
            "inline": False
        })

    embed = {
        "title": "⚠️ Upcoming High-Impact News",
        "description": "Trading volatility expected in **5 minutes**.",
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
