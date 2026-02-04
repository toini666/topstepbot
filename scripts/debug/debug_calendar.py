
import asyncio
import httpx
import xmltodict
from datetime import datetime, timedelta

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"

async def fetch_and_debug():
    print(f"Fetching from {CALENDAR_URL}...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(CALENDAR_URL)
        print(f"Status: {response.status_code}")
        
    data = xmltodict.parse(response.content)
    events_raw = data.get("weeklyevents", {}).get("event", [])
    if not isinstance(events_raw, list):
        events_raw = [events_raw] if events_raw else []
        
    print(f"Found {len(events_raw)} total events.")
    
    today_str = datetime.now().strftime("%m-%d-%Y")
    print(f"Looking for date: {today_str}")
    
    usd_events = []
    
    for ev in events_raw:
        if ev.get("country") == "USD" and ev.get("impact") == "High":
            # Print details
            print("\n--- Found High Impact USD Event ---")
            print(f"Title: {ev.get('title')}")
            print(f"Date: {ev.get('date')}")
            print(f"Time (Raw): {ev.get('time')}")
            
            # Simulate parsing logic
            raw_time = ev.get("time", "")
            final_time = raw_time
            try:
                if "am" in raw_time.lower() or "pm" in raw_time.lower():
                    dt = datetime.strptime(raw_time, "%I:%M%p")
                    # Original logic added 1 hour
                    dt_plus_1 = dt + timedelta(hours=1)
                    print(f"Parsed: {dt.strftime('%H:%M')} -> Plus 1h: {dt_plus_1.strftime('%H:%M')}")
                    final_time = dt_plus_1.strftime("%H:%M")
            except Exception as e:
                print(f"Parsing error: {e}")
            
            if ev.get("date") == today_str:
                print(">>> MATCHES TODAY <<<")
            else:
                print(f"Date mismatch: {ev.get('date')} != {today_str}")

if __name__ == "__main__":
    asyncio.run(fetch_and_debug())
