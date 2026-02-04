
import httpx
import xmltodict
import logging
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional
from backend.database import SessionLocal, Log, Setting
from backend.services.discord_service import discord_service

logger = logging.getLogger("topstepbot")

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
import json

class CalendarService:
    def __init__(self):
        self._cache = None
        self._last_fetch = None
        self._today_news_blocks: List[Dict] = []  # Dynamic news blocks for today

    async def fetch_calendar(self) -> List[Dict]:
        """
        Fetches the economic calendar from the remote XML source,
        parses it, and returns a list of events.
        """
        # Throttling: Prevent fetching more than once per minute
        if self._last_fetch and (datetime.now() - self._last_fetch).total_seconds() < 60:
            return self._cache or []

        try:
            # Update fetch time immediately to prevent race conditions/parallel calls
            self._last_fetch = datetime.now()
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(CALENDAR_URL)
                response.raise_for_status()
                
            data = xmltodict.parse(response.content)
            
            # Root is usually "weeklyevents" and contains list of "event"
            events_raw = data.get("weeklyevents", {}).get("event", [])
            if not isinstance(events_raw, list):
                events_raw = [events_raw] if events_raw else []
                
            formatted_events = []
            for ev in events_raw:
                # Parse and adjust time (Add 1 hour for Brussels, convert to 24h)
                raw_time = ev.get("time", "")
                final_time = raw_time
                try:
                    if raw_time and ":" in raw_time:
                        # Parse e.g. "8:30am" or "2:00pm"
                        # Sometimes format is "Day 1" or similar for all day events, handle that
                        if "am" in raw_time.lower() or "pm" in raw_time.lower():
                            dt = datetime.strptime(raw_time, "%I:%M%p")
                            # Add 1 hour
                            dt = dt + timedelta(hours=1)
                            final_time = dt.strftime("%H:%M")
                        else:
                            # Try 24h just in case or leave as is
                            pass
                except Exception:
                    pass

                formatted_events.append({
                    "title": ev.get("title"),
                    "country": ev.get("country"),
                    "date": ev.get("date"), # Format: MM-DD-YYYY
                    "time": final_time, # Adjusted 24h format
                    "impact": ev.get("impact"), # Low, Medium, High
                    "forecast": ev.get("forecast"),
                    "previous": ev.get("previous")
                })
            
            # Sort by date and time
            # Note: parsing these custom time formats for sorting might be heavy, 
            # but usually the XML is already sorted by time.
            
            self._cache = formatted_events
            self._last_fetch = datetime.now()
            
            return formatted_events

        except Exception as e:
            self._log_error(f"Failed to fetch calendar: {e}")
            return []

    def get_cached_calendar(self) -> List[Dict]:
        return self._cache or []

    def get_today_news_blocks(self) -> List[Dict]:
        """Return cached news blocks for today (for risk_engine to check)."""
        return self._today_news_blocks or []

    async def recalculate_news_blocks(self) -> List[Dict]:
        """
        Recalculate news blocks based on cached calendar and current settings.
        Call this after changing calendar settings to sync the blocks.
        
        Returns:
            Updated list of news blocks
        """
        if not self._cache:
            # Try to fetch if cache is empty
            await self.fetch_calendar()
        
        if not self._cache:
            logger.warning("Cannot recalculate news blocks: no calendar data")
            return []
        
        # Get today's events from cache
        today_str = datetime.now().strftime("%m-%d-%Y")
        todays_events = [e for e in self._cache if e.get("date") == today_str]
        
        # Recalculate blocks
        blocks = await self.calculate_news_blocks(todays_events)
        logger.info(f"Recalculated news blocks: {len(blocks)} blocks for today")
        
        return blocks


    async def calculate_news_blocks(self, todays_events: List[Dict]) -> List[Dict]:
        """
        Calculate dynamic trading blocks based on today's major events.
        Called after fetching calendar in check_calendar_job().
        
        Returns list of time blocks for today's major events.
        """
        db = SessionLocal()
        try:
            # Get settings
            news_enabled = db.query(Setting).filter(Setting.key == "news_block_enabled").first()
            if not news_enabled or news_enabled.value.lower() != "true":
                self._today_news_blocks = []
                return []
            
            before_setting = db.query(Setting).filter(Setting.key == "news_block_before_minutes").first()
            after_setting = db.query(Setting).filter(Setting.key == "news_block_after_minutes").first()
            
            before_minutes = int(before_setting.value) if before_setting else 5
            after_minutes = int(after_setting.value) if after_setting else 5
            
            # Get filtering settings (same as used for Discord summary)
            impacts_setting = db.query(Setting).filter(Setting.key == "calendar_major_impacts").first()
            countries_setting = db.query(Setting).filter(Setting.key == "calendar_major_countries").first()
            
            target_impacts = json.loads(impacts_setting.value) if impacts_setting and impacts_setting.value else ["High", "Medium"]
            target_countries = json.loads(countries_setting.value) if countries_setting and countries_setting.value else ["USD"]
            
            blocks = []
            for event in todays_events:
                # Check if event matches major criteria
                if event.get("impact") not in target_impacts:
                    continue
                if event.get("country") not in target_countries:
                    continue
                
                event_time = event.get("time")
                if not event_time or ":" not in event_time:
                    continue
                
                try:
                    # Parse event time
                    hour, minute = map(int, event_time.split(":"))
                    event_dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # Calculate block start and end
                    block_start = event_dt - timedelta(minutes=before_minutes)
                    block_end = event_dt + timedelta(minutes=after_minutes)
                    
                    blocks.append({
                        "start": block_start.strftime("%H:%M"),
                        "end": block_end.strftime("%H:%M"),
                        "event": event.get("title"),
                        "country": event.get("country"),
                        "impact": event.get("impact")
                    })
                except Exception as e:
                    print(f"Error parsing event time: {e}")
                    continue
            
            self._today_news_blocks = blocks
            return blocks
            
        except Exception as e:
            self._log_error(f"Failed to calculate news blocks: {e}")
            return []
        finally:
            db.close()

    async def notify_news_blocks(self, blocks: List[Dict]):
        """Send Telegram notification with today's news blocks."""
        if not blocks:
            return
        
        try:
            from backend.services.telegram_bot import telegram_service
            
            # Build message
            lines = ["📅 <b>Today's News Trading Blocks</b>\n"]
            lines.append("<i>Trading will be blocked around these events:</i>\n")
            
            impact_emoji = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}
            
            for block in blocks:
                emoji = impact_emoji.get(block.get("impact"), "⚪")
                lines.append(
                    f"{emoji} <code>{block['start']}-{block['end']}</code> "
                    f"{block['country']} {block['event']}"
                )
            
            message = "\n".join(lines)
            await telegram_service.send_message(message)
            self._log_info(f"News blocks notification sent: {len(blocks)} blocks")
            
        except Exception as e:
            self._log_error(f"Failed to send news blocks notification: {e}")

    async def check_calendar_job(self):
        """
        Scheduled job to run at 7 AM.
        Fetches calendar and sends Discord notification for today's major events.
        Also calculates news blocks if enabled.
        """
        print("📅 Running Daily Calendar Job...")
        events = await self.fetch_calendar()
        
        # Filter for today
        # XML Date Format: MM-DD-YYYY (e.g., 01-16-2025)
        today_str = datetime.now().strftime("%m-%d-%Y")
        
        todays_events = [e for e in events if e.get("date") == today_str]
        
        if todays_events:
            await self.send_discord_summary(todays_events)
        
        # Calculate and notify news blocks
        blocks = await self.calculate_news_blocks(todays_events)
        if blocks:
            await self.notify_news_blocks(blocks)

    async def send_discord_summary(self, events: List[Dict]):
        """Send a summary of today's major events to Discord."""
        # Check if enabled
        db = SessionLocal()
        try:
            setting = db.query(Setting).filter(Setting.key == "calendar_discord_url").first()
            if not setting or not setting.value:
                return # No webhook configured
            
            webhook_url = setting.value
            
            # Retrieve filtering settings
            impacts_setting = db.query(Setting).filter(Setting.key == "calendar_major_impacts").first()
            countries_setting = db.query(Setting).filter(Setting.key == "calendar_major_countries").first()
            
            target_impacts = json.loads(impacts_setting.value) if impacts_setting and impacts_setting.value else ["High", "Medium"]
            target_countries = json.loads(countries_setting.value) if countries_setting and countries_setting.value else ["USD"]
            
            # Filter events
            major_events = []
            for e in events:
                if e.get("impact") in target_impacts and e.get("country") in target_countries:
                    major_events.append(e)
            
            if not major_events:
                return

            embed_fields = []
            for ev in major_events:
                impact_dict = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}
                impact_emoji = impact_dict.get(ev.get("impact"), "⚪")
                
                embed_fields.append({
                    "name": f"{impact_emoji} {ev.get('time')} - {ev.get('country')} {ev.get('title')}",
                    "value": f"Forecast: {ev.get('forecast') or '-'} | Prev: {ev.get('previous') or '-'}",
                    "inline": False
                })

            embed = {
                "title": f"📅 Economic Calendar - {datetime.now().strftime('%d %B %Y')}",
                "description": "Major events scheduled for today:",
                "color": 0x3b82f6, # Blue
                "fields": embed_fields,
                "footer": {"text": "TopStep Bot Calendar"}
            }
            
            await discord_service.send_message(webhook_url, embeds=[embed])
            self._log_info("Sent daily calendar summary to Discord")
            
        except Exception as e:
            self._log_error(f"Failed to send Discord calendar summary: {e}")
        finally:
            db.close()

    def _log_error(self, message: str):
        try:
            db = SessionLocal()
            db.add(Log(level="ERROR", message=message))
            db.commit()
            db.close()
        except Exception as e:
            print(f"Failed to log error to database: {e}")

    def _log_info(self, message: str):
        try:
            db = SessionLocal()
            db.add(Log(level="INFO", message=message))
            db.commit()
            db.close()
        except Exception as e:
            print(f"Failed to log info to database: {e}")

calendar_service = CalendarService()
