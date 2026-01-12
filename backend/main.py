"""
TopStepBot Main Application - Multi-Account Trading Bot

Key Features:
- Multi-account position monitoring
- Global force flatten (all accounts)
- Trading session awareness
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db, get_db, Setting, AccountSettings, seed_default_sessions
from backend.routers import webhook, dashboard, strategies, export
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.services.risk_engine import RiskEngine
from backend.services.topstep_client import topstep_client
from backend.services.telegram_service import telegram_service
from backend.services.telegram_bot import telegram_bot
from backend.services.maintenance_service import backup_database, clean_logs, check_and_run_startup_backup
from backend.services.persistence_service import save_state, load_state
import asyncio
import json
from datetime import datetime, time
import pytz

# Scheduler Setup
scheduler = AsyncIOScheduler()

# Brussels Timezone
BRUSSELS_TZ = pytz.timezone("Europe/Brussels")

# Global State for Position Monitoring (per-account)
# Key: account_id, Value: { contractId: position_data }
_last_open_positions = {}
_last_orphans_ids = set()


async def monitor_closed_positions_job():
    """
    Polls TopStep API for open positions on ALL accounts.
    Detects if a previously open position is missing (closed).
    Triggers Telegram Notification for valid closed trades.
    """
    global _last_open_positions, _last_orphans_ids
    from backend.database import SessionLocal, Log
    db = SessionLocal()
    
    try:
        # Get all accounts from TopStep
        all_accounts = await topstep_client.get_accounts()
        
        if not all_accounts:
            return
        
        all_orphans = []
        
        for account in all_accounts:
            account_id = account.get('id')
            account_name = account.get('name', str(account_id))
            
            try:
                # Fetch Current Positions for this account
                current_positions = await topstep_client.get_open_positions(account_id)
                
                # Convert to Dictionary: { 'contractId': position_data }
                current_map = {}
                for pos in current_positions:
                    cid = str(pos.get('contractId'))
                    current_map[cid] = pos
                
                # Get last known state for this account
                last_map = _last_open_positions.get(account_id, {})
                
                # Detect Closures
                if last_map:
                    for prev_cid, prev_pos in last_map.items():
                        if prev_cid not in current_map:
                            # Position CLOSED!
                            print(f"💰 DETECTED CLOSURE: {prev_cid} on Account {account_name}")
                            
                            # Fetch Details of Closed Trade (PnL)
                            recent_trades = await topstep_client.get_historical_trades(account_id, days=1)
                            target_symbol = prev_pos.get('symbolId') or prev_cid
                            
                            matching_trade = None
                            if recent_trades:
                                for t in recent_trades:
                                    if str(t.get('symbol')) == str(target_symbol) or str(t.get('contractId')) == str(prev_cid):
                                        matching_trade = t
                                        break
                            
                            if matching_trade:
                                exit_px = matching_trade.get('price') or matching_trade.get('fillPrice') or 0
                                raw_pnl = matching_trade.get('pnl') or matching_trade.get('profitAndLoss')
                                pnl_val = raw_pnl if raw_pnl is not None else 0.0
                                
                                # Map Side
                                raw_side = matching_trade.get('side')
                                raw_side_upper = str(raw_side).upper().strip()
                                
                                if raw_side_upper in ["0", "BUY", "LONG"]:
                                    side_str = "SHORT"  # Exit buy = was short
                                elif raw_side_upper in ["1", "2", "SELL", "SHORT"]:
                                    side_str = "LONG"  # Exit sell = was long
                                else:
                                    side_str = str(raw_side)
                                
                                # Calculate Total Fees
                                exit_fees = matching_trade.get('fees') or 0.0
                                total_fees = exit_fees
                                
                                # Find entry trade for fee calculation
                                is_buy = raw_side_upper in ["0", "BUY", "LONG"]
                                for t in recent_trades:
                                    t_side = str(t.get('side')).upper().strip()
                                    t_sym = str(t.get('symbol'))
                                    t_cid = str(t.get('contractId'))
                                    
                                    is_target_entry = False
                                    if is_buy and t_side in ["1", "2", "SELL", "SHORT"]:
                                        is_target_entry = True
                                    elif not is_buy and t_side in ["0", "BUY", "LONG"]:
                                        is_target_entry = True
                                    
                                    if is_target_entry and (t_sym == str(target_symbol) or t_cid == str(prev_cid)):
                                        if t.get('creationTimestamp') < matching_trade.get('creationTimestamp'):
                                            entry_fees = t.get('fees') or 0.0
                                            total_fees += entry_fees
                                            break
                                
                                # UPDATE TRADE RECORD IN DATABASE
                                from backend.database import Trade
                                ticker_variants = [prev_cid, target_symbol]
                                # Find matching open trade and update it
                                open_trade = db.query(Trade).filter(
                                    Trade.account_id == account_id,
                                    Trade.ticker.in_(ticker_variants),
                                    Trade.status == "OPEN"
                                ).order_by(Trade.timestamp.desc()).first()
                                
                                if open_trade:
                                    open_trade.status = "CLOSED"
                                    open_trade.exit_price = exit_px
                                    open_trade.pnl = pnl_val
                                    open_trade.fees = total_fees
                                    open_trade.exit_time = datetime.now(pytz.UTC)
                                    db.commit()
                                    print(f"✅ Trade #{open_trade.id} marked as CLOSED (PnL: ${pnl_val:.2f})")
                                
                                await telegram_service.notify_position_closed(
                                    symbol=f"{matching_trade.get('symbol', prev_cid)} ({account_name})",
                                    side=side_str,
                                    entry_price=0,
                                    exit_price=exit_px,
                                    pnl=pnl_val,
                                    fees=total_fees,
                                    quantity=matching_trade.get('size', 0),
                                    daily_pnl=sum((t.get('profitAndLoss') or 0) - (t.get('fees') or 0) for t in recent_trades)
                                )
                            else:
                                # No matching trade from API, still try to update our DB
                                from backend.database import Trade
                                open_trade = db.query(Trade).filter(
                                    Trade.account_id == account_id,
                                    Trade.ticker == prev_cid,
                                    Trade.status == "OPEN"
                                ).order_by(Trade.timestamp.desc()).first()
                                
                                if open_trade:
                                    open_trade.status = "CLOSED"
                                    open_trade.exit_time = datetime.now(pytz.UTC)
                                    db.commit()
                                    print(f"✅ Trade #{open_trade.id} marked as CLOSED (no API match)")
                                
                                await telegram_service.send_message(
                                    f"💰 <b>Position Closed: {target_symbol}</b> ({account_name})"
                                )
                
                # Detect New Positions (Opens)
                if last_map is not None:
                    for curr_cid, curr_pos in current_map.items():
                        if curr_cid not in last_map:
                            print(f"🔵 DETECTED OPEN: {curr_cid} on Account {account_name}")
                            
                            recent_trades = await topstep_client.get_historical_trades(account_id, days=1)
                            matching_fill = None
                            
                            if recent_trades:
                                for t in recent_trades:
                                    if str(t.get('contractId')) == str(curr_cid):
                                        matching_fill = t
                                        break
                            
                            if matching_fill:
                                fill_price = matching_fill.get('price') or 0
                                fill_side = str(matching_fill.get('side')).upper().strip()
                                
                                if fill_side in ["0", "BUY", "LONG"]:
                                    side_str = "BUY"
                                elif fill_side in ["1", "2", "SELL", "SHORT"]:
                                    side_str = "SELL"
                                else:
                                    side_str = "UNK"
                                
                                await telegram_service.notify_position_opened(
                                    symbol=f"{matching_fill.get('symbol', curr_cid)} ({account_name})",
                                    side=side_str,
                                    quantity=matching_fill.get('size', 1),
                                    price=fill_price,
                                    order_id=str(matching_fill.get('orderId', ''))
                                )
                
                # Update state for this account
                _last_open_positions[account_id] = current_map
                
                # Check for orphaned orders on this account
                recent_orders = await topstep_client.get_orders(account_id, days=1)
                for o in recent_orders:
                    st = o.get('status')
                    if str(st).upper() in ["WORKING", "ACCEPTED", "1", "6"]:
                        cid = str(o.get('contractId'))
                        if cid not in current_map:
                            o['_account_name'] = account_name
                            all_orphans.append(o)
            
            except Exception as e:
                print(f"Monitor error for account {account_id}: {e}")
                continue
        
        # Notify orphans (globally)
        current_orphan_ids = set(str(o.get('orderId') or o.get('id')) for o in all_orphans)
        
        if all_orphans and current_orphan_ids != _last_orphans_ids:
            print(f"⚠️ Orphaned Orders Detected: {current_orphan_ids}")
            await telegram_service.notify_orphaned_orders(all_orphans)
        
        _last_orphans_ids = current_orphan_ids
        
    except Exception as e:
        print(f"Monitor Job Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def auto_flatten_job():
    """
    Global force flatten at scheduled time.
    Affects ALL accounts regardless of trading_enabled setting.
    """
    from backend.database import SessionLocal, Log
    db = SessionLocal()
    
    try:
        risk_engine = RiskEngine(db)
        settings = risk_engine.get_global_settings()
        
        if not settings.get("auto_flatten_enabled", False):
            return
        
        flatten_time = settings.get("auto_flatten_time", "21:55")
        now_bru = datetime.now(BRUSSELS_TZ)
        
        try:
            flatten_h, flatten_m = map(int, flatten_time.split(':'))
            target = time(flatten_h, flatten_m)
            
            # Check if within 1 minute window (since job runs every minute)
            current_time = now_bru.time()
            if current_time.hour == target.hour and current_time.minute == target.minute:
                print("⏰ Auto-Flatten Triggered!")
                
                # Get all accounts and flatten each
                all_accounts = await topstep_client.get_accounts()
                
                for account in all_accounts:
                    account_id = account.get('id')
                    account_name = account.get('name', str(account_id))
                    
                    try:
                        # Cancel all orders
                        orders = await topstep_client.get_orders(account_id)
                        for order in orders:
                            if order.get('status') in [1, 6]:
                                await topstep_client.cancel_order(account_id, order.get('id'))
                        
                        # Close all positions
                        positions = await topstep_client.get_open_positions(account_id)
                        for pos in positions:
                            await topstep_client.close_position(account_id, pos.get('contractId'))
                        
                        db.add(Log(level="WARNING", message=f"Auto-Flatten: Account {account_name} flattened"))
                        
                    except Exception as e:
                        db.add(Log(level="ERROR", message=f"Auto-Flatten failed for {account_name}: {e}"))
                
                db.commit()
                await telegram_service.send_message("⏰ <b>Auto-Flatten Complete</b> - All accounts flattened")
        
        except ValueError:
            print(f"Invalid auto_flatten_time format: {flatten_time}")
    
    except Exception as e:
        print(f"Auto-flatten job error: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    
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
    global _last_open_positions
    state = load_state()
    if "last_open_positions" in state:
        _last_open_positions = state["last_open_positions"]
        print(f"Loaded position state for {len(_last_open_positions)} accounts from persistence.")
    
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
                _last_open_positions[account_id] = current_map
                
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
    scheduler.add_job(auto_flatten_job, 'interval', minutes=1)
    scheduler.add_job(monitor_closed_positions_job, 'interval', seconds=30)
    
    # Maintenance Jobs
    scheduler.add_job(backup_database, 'cron', hour=3, minute=0)
    scheduler.add_job(clean_logs, 'cron', hour=3, minute=15, kwargs={'days': 7})

    scheduler.start()
    print("Scheduler started.")

    # Start Telegram Polling (Background)
    polling_task = asyncio.create_task(telegram_bot.start_polling())
    
    yield
    
    # Shutdown
    telegram_bot.stop_polling()
    
    # Save Persistence State
    save_state({
        "last_open_positions": _last_open_positions
    })
    
    await telegram_service.notify_shutdown()
    scheduler.shutdown()
    
    try:
        await polling_task
    except asyncio.CancelledError:
        pass


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


@app.get("/")
def read_root():
    return {"status": "online", "service": "TopStep Trading Bot", "version": "2.0.0"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
