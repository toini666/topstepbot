"""
TopStepBot Main Application - Multi-Account Trading Bot

Key Features:
- Multi-account position monitoring
- Global force flatten (all accounts)
- Trading session awareness
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db, get_db, Setting, AccountSettings, seed_default_sessions, TickerMap
from backend.routers import webhook, dashboard, strategies, export, calendar
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.services.topstep_client import topstep_client
from backend.services.telegram_service import telegram_service
from backend.services.telegram_bot import telegram_bot
from backend.services.maintenance_service import backup_database, clean_logs, check_and_run_startup_backup
from backend.services.persistence_service import save_state, load_state, save_ngrok_url, get_last_ngrok_url
from backend.services.calendar_service import calendar_service
from backend.services.contract_validator import contract_validator

# Import all jobs from the jobs module
from backend.jobs import (
    get_last_open_positions,
    set_last_open_positions,
    update_heartbeat_state,
    monitor_closed_positions_job,
    auto_flatten_job,
    position_action_job,
    api_health_check_job,
    heartbeat_job,
    send_shutdown_webhook,
    price_refresh_job,
    discord_daily_summary_job,
)
from backend.jobs.state import update_account_positions, init_heartbeat_start_time

import asyncio
import os
from datetime import datetime, timedelta
import pytz

# Scheduler Setup
scheduler = AsyncIOScheduler()

# Brussels Timezone
BRUSSELS_TZ = pytz.timezone("Europe/Brussels")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    
    # Initialize Persistent HTTP Client
    await topstep_client.startup()
    
    # Seed default trading sessions
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        seed_default_sessions(db)
    except Exception as e:
        print(f"Session seeding error: {e}")
    finally:
        db.close()
    
    # Check & Run Startup Backup
    check_and_run_startup_backup()
    
    # Load Persistence State
    _last_open_positions = get_last_open_positions()
    state = load_state()
    if "last_open_positions" in state:
        set_last_open_positions(state["last_open_positions"])
        print(f"Loaded position state for {len(state['last_open_positions'])} accounts from persistence.")
    
    # Log System Restart
    db = SessionLocal()
    try:
        from backend.database import Log
        db.add(Log(level="WARNING", message="System Restarted: Connection Reset"))
        db.commit()
    except Exception as e:
        print(f"Startup Log Error: {e}")
    finally:
        db.close()

    # Auto-Connect to TopStep
    try:
        await topstep_client.login()
        
        # Pre-load existing positions to avoid false "Position Opened" notifications
        all_accounts = await topstep_client.get_accounts()
        open_positions_summary = []
        
        for account in all_accounts:
            account_id = account.get('id')
            account_name = account.get('name', str(account_id))
            
            try:
                positions = await topstep_client.get_open_positions(account_id)
                current_map = {}
                
                for pos in positions:
                    cid = str(pos.get('contractId'))
                    current_map[cid] = pos
                    
                    # Collect for summary
                    p_type = pos.get('type')
                    side = "LONG" if str(p_type) == '1' else "SHORT"
                    qty = pos.get('size', 1)
                    open_positions_summary.append({
                        'account': account_name,
                        'contract': cid,
                        'side': side,
                        'qty': qty
                    })
                
                # Store in state to prevent monitor from treating as new
                await update_account_positions(account_id, current_map)
                
            except Exception as e:
                print(f"Error pre-loading positions for {account_name}: {e}")
        
        # Send startup notification with positions summary
        if open_positions_summary:
            summary_msg = "🤖 <b>TopStep Bot Online</b>\n\n📈 <b>Open Positions:</b>\n"
            for p in open_positions_summary:
                side_emoji = "🟢" if p['side'] == "LONG" else "🔴"
                summary_msg += f"• {side_emoji} {p['contract']} x{p['qty']} ({p['account']})\n"
            await telegram_service.send_message(summary_msg)
        else:
            await telegram_service.notify_startup()
        
    except Exception as e:
        print(f"Auto-login failed: {e}")

    # Add Scheduled Jobs
    # Add max_instances=1 and coalesce=True to prevent job overlap and execution pile-up
    scheduler.add_job(auto_flatten_job, 'interval', minutes=1, max_instances=1, coalesce=True)
    # Position monitoring: 10s interval
    scheduler.add_job(monitor_closed_positions_job, 'interval', seconds=10, id='monitor_positions', max_instances=1, coalesce=True)
    # Price refresh: 10s interval, starts 5s after monitor job to stagger API calls
    price_refresh_start = datetime.now() + timedelta(seconds=5)
    scheduler.add_job(price_refresh_job, 'interval', seconds=10, id='price_refresh', next_run_time=price_refresh_start, max_instances=1, coalesce=True)
    
    # Maintenance Jobs
    scheduler.add_job(backup_database, 'cron', hour=3, minute=0, max_instances=1, coalesce=True)
    scheduler.add_job(clean_logs, 'cron', hour=3, minute=15, kwargs={'days': 7}, max_instances=1, coalesce=True)
    
    # API Health Check (every 60 seconds)
    scheduler.add_job(api_health_check_job, 'interval', seconds=60, max_instances=1, coalesce=True)
    
    # Discord Daily Summary (every minute, checks configured times per account)
    scheduler.add_job(discord_daily_summary_job, 'interval', minutes=1, max_instances=1, coalesce=True)
    
    # Position Action Job (every 30 seconds - checks for upcoming blocked periods)
    scheduler.add_job(position_action_job, 'interval', seconds=30, max_instances=1, coalesce=True)

    # Heartbeat Job (configurable interval, default 60s)
    heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "60"))
    if os.getenv("HEARTBEAT_WEBHOOK_URL"):
        scheduler.add_job(heartbeat_job, 'interval', seconds=heartbeat_interval, max_instances=1, coalesce=True)
        print(f"Heartbeat configured: every {heartbeat_interval}s -> {os.getenv('HEARTBEAT_WEBHOOK_URL')}")

    # Initialize heartbeat start time
    init_heartbeat_start_time(datetime.now(BRUSSELS_TZ))

    # Calendar Job (7:00 AM Brussels)
    scheduler.add_job(calendar_service.check_calendar_job, 'cron', hour=7, minute=0, timezone=BRUSSELS_TZ, max_instances=1, coalesce=True)

    # Daily Contract Validation (Daily at 23:00 Brussels)
    scheduler.add_job(contract_validator.validate_active_mappings, 'cron', hour=23, minute=0, timezone=BRUSSELS_TZ, id='contract_validation', max_instances=1, coalesce=True)

    scheduler.start()
    print("Scheduler started.")

    # Start Telegram Polling (Background)
    polling_task = asyncio.create_task(telegram_bot.start_polling())
    
    yield
    
    # Shutdown
    print("\n🛑 Graceful shutdown initiated...")
    
    # Stop scheduler FIRST to prevent jobs from running during shutdown
    scheduler.shutdown(wait=False)
    print("   ✓ Scheduler stopped")
    
    # Stop Telegram polling
    telegram_bot.stop_polling()
    print("   ✓ Telegram polling stopped")
    
    # Close Persistent HTTP Client
    await topstep_client.shutdown()
    
    # Send shutdown notification to monitoring
    await send_shutdown_webhook()
    print("   ✓ Shutdown notification sent")
    
    # Save Persistence State
    save_state({
        "last_open_positions": get_last_open_positions()
    })
    print("   ✓ State persisted")
    
    # Notify Telegram users
    await telegram_service.notify_shutdown()
    print("   ✓ Telegram notification sent")
    
    # Wait for polling task to finish
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    
    print("✅ Shutdown complete")


app = FastAPI(title="TopStep Trading Bot", version="2.0.0", lifespan=lifespan)

# CORS Setup (for Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include Routers
app.include_router(webhook.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(strategies.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")


@app.get("/")
def read_root():
    return {"status": "online", "service": "TopStep Trading Bot", "version": "2.0.0"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/ngrok-url")
async def set_ngrok_url(payload: dict):
    """
    Receives the current Ngrok URL from start_bot.sh.
    Detects if URL has changed and notifies user via:
    - Terminal (print)
    - System Logs (DB)
    - Telegram
    """
    from backend.database import SessionLocal, Log
    
    new_url = payload.get("url", "").strip()
    if not new_url:
        return {"status": "error", "message": "No URL provided"}
    
    # Get last known URL
    last_url = get_last_ngrok_url()
    
    # Check for change
    if last_url and last_url != new_url:
        # URL has changed - notify on all channels
        print(f"⚠️  NGROK URL CHANGED!")
        print(f"   Old: {last_url}")
        print(f"   New: {new_url}")
        print(f"   👉 Update your TradingView webhooks to: {new_url}/api/webhook")
        
        # Log to database
        db = SessionLocal()
        try:
            db.add(Log(
                level="WARNING",
                message=f"Ngrok URL changed: {last_url} -> {new_url}"
            ))
            db.commit()
        finally:
            db.close()
        
        # Send Telegram notification
        await telegram_service.notify_ngrok_url_changed(last_url, new_url)
        
        # Save new URL
        save_ngrok_url(new_url)
        
        return {"status": "changed", "old_url": last_url, "new_url": new_url}
    
    elif not last_url:
        # First run - just save
        print(f"📝 Ngrok URL saved: {new_url}")
        save_ngrok_url(new_url)
        return {"status": "saved", "url": new_url}
    
    else:
        # URL unchanged
        return {"status": "unchanged", "url": new_url}
