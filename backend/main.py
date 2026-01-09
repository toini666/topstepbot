from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db, get_db, Setting
from backend.routers import webhook, dashboard, mapping
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.services.risk_engine import RiskEngine
from backend.services.topstep_client import topstep_client
from backend.services.telegram_service import telegram_service
from backend.services.telegram_bot import telegram_bot
from backend.services.maintenance_service import backup_database, clean_logs, check_and_run_startup_backup
from backend.services.persistence_service import save_state, load_state
import asyncio

# Scheduler Setup
scheduler = AsyncIOScheduler()

# Global State for Position Monitoring
# Key: contractId, Value: quantity (snapshot)
_last_open_positions = {}
_last_orphans_ids = set()

async def monitor_closed_positions_job():
    """
    Polls TopStep API for open positions.
    Detects if a previously open position is missing (closed).
    Triggers Telegram Notification for valid closed trades.
    """
    global _last_open_positions
    from backend.database import SessionLocal, Log
    db = SessionLocal()
    
    try:
        # 1. Get Selected Account
        setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
        if not setting:
            return # No account active, nothing to monitor

        account_id = int(setting.value)
        
        # 2. Fetch Current Positions
        # Note: If API fails, we should skip update to avoid false "closures"
        current_positions = await topstep_client.get_open_positions(account_id)
        
        # Convert to Dictionary for easy lookup: { 'MNQH6': 1, 'ESM5': -2 }
        # Should we use contractId or symbol? get_open_positions returns dicts.
        current_map = {}
        for pos in current_positions:
            # pos structure from TopStep: { 'contractId': '...', 'side': 'Buy'/'Sell', 'size': 1, ... }
            cid = str(pos.get('contractId'))
            current_map[cid] = pos

        # DEBUG: Trace Position State
        # if _last_open_positions or current_map:
        #     print(f"DEBUG: Monitor | Last: {list(_last_open_positions.keys())} | Curr: {list(current_map.keys())}")

        # 3. Detect Missing Keys (Closures)
        # Iterate over LAST known snapshot
        if _last_open_positions: # Only check if we had state before
            for prev_cid, prev_pos in _last_open_positions.items():
                if prev_cid not in current_map:
                    # Position CLOSED!
                    print(f"💰 DETECTED CLOSURE FOR {prev_cid}")
                    
                    # 4. Fetch Details of Closed Trade (PnL)
                    # We need to find the trade that just happened.
                    # Fetch last 24h trades and look for matching symbol + high timestamp
                    recent_trades = await topstep_client.get_historical_trades(account_id, days=1)
                    
                    # Filter for this symbol and sort by time desc
                    # Note: API trade symbol might differ slightly from contractId? Usually they match or contain.
                    # 'prev_pos' has 'symbolId' or 'contractId'. 
                    target_symbol = prev_pos.get('symbolId') or prev_cid
                    
                    # Find the EXIT trade (usually Side is opposite to Pos Side, or just latest trade on symbol)
                    # TopStep 'search' returns individual fills or aggregated half-turns? 
                    # Documentation says "Historical Trades" usually means closed trades (round turn) or legs.
                    # If it returns round-turn trades with PnL, that's perfect.
                    # Let's assume the list contains objects with 'pnl'.
                    
                    matching_trade = None
                    if recent_trades:
                        for t in recent_trades:
                            # Check symbol match. strict or fuzzy?
                            # Also check if it looks recent (optional)
                            if str(t.get('symbol')) == str(target_symbol) or str(t.get('contractId')) == str(prev_cid):
                                matching_trade = t
                                break
                    
                    if matching_trade:
                        print(f"   -> Found History Trade: {matching_trade.get('pnl')}")
                        # Notify
                        # Fills (Historical Trades) have 'price' (Exit Price) but not 'entryPrice'
                        exit_px = matching_trade.get('price') or matching_trade.get('fillPrice') or 0
                        entry_px = 0 # Not available in single fill object
                        
                        raw_pnl = matching_trade.get('pnl') or matching_trade.get('profitAndLoss')
                        fees = matching_trade.get('fees')
                        
                        # Handle None values safely
                        # The PnL returned by TopStep (on a Close) usually matches the Dashboard PnL column.
                        # Do not add fees manually unless we are sure it's Net vs Gross mismatch.
                        # User feedback suggests adding fees made it wrong (-159 vs -160).
                        pnl_val = raw_pnl if raw_pnl is not None else 0.0
                        
                        # Map Side (Int -> Str)
                        # API: 1=Buy, 2=Sell (Usually). If 0 or missing, rely on PnL or keep as is?
                        # Let's map explicit values if known.
                        # Map Side (Int -> Str) and Normalize
                        raw_side = matching_trade.get('side')
                        side_str = "UNK"
                        
                        raw_side_upper = str(raw_side).upper().strip()
                        is_buy = raw_side_upper in ["0", "BUY", "LONG"]
                        is_sell = raw_side_upper in ["1", "2", "SELL", "SHORT"]
                        
                        if is_buy: side_str = "SHORT"
                        elif is_sell: side_str = "LONG"
                        else: side_str = str(raw_side)
                        
                        # Calculate Total Fees (Entry + Exit)
                        exit_fees = matching_trade.get('fees') or 0.0
                        total_fees = exit_fees
                        
                        potential_entries = []
                        for t in recent_trades:
                            t_side = str(t.get('side')).upper().strip()
                            t_sym = str(t.get('symbol'))
                            t_cid = str(t.get('contractId'))
                            
                            is_target_entry = False
                            if is_buy: 
                                # Exit=Buy -> Entry=Sell (or Short)
                                if t_side in ["1", "2", "SELL", "SHORT"]: is_target_entry = True
                            elif is_sell:
                                # Exit=Sell -> Entry=Buy (or Long)
                                if t_side in ["0", "BUY", "LONG"]: is_target_entry = True
                                
                            if is_target_entry:
                                # Loose Symbol Match
                                if t_sym == str(target_symbol) or t_cid == str(prev_cid) or prev_cid in t_cid:
                                    # Must be OLDER than the Exit
                                    if t.get('creationTimestamp') < matching_trade.get('creationTimestamp'):
                                        potential_entries.append(t)
                        
                        if potential_entries:
                            # Use the one closest in time (last one before exit)?
                            # List is usually sorted? No guarantee.
                            # Sort potential entries by timestamp, NEWEST first (closest to exit)
                            potential_entries.sort(key=lambda x: x.get('creationTimestamp'), reverse=True)
                            
                            # The most recent opposite trade is likely the entry
                            entry_trade = potential_entries[0] 
                            entry_fees = entry_trade.get('fees') or 0.0
                            
                            # Scaling fees: If exit qty != entry qty, pro-rate?
                            # User wants "Total Fees". 
                            # If we partially close, we should pro-rate the entry fee.
                            entry_qty = entry_trade.get('size') or entry_trade.get('qty') or 1
                            exit_qty = matching_trade.get('size') or matching_trade.get('qty') or 1
                            
                            if float(entry_qty) > 0:
                                ratio = float(exit_qty) / float(entry_qty)
                                if ratio > 1: ratio = 1.0 # Cap at 100%
                                total_fees += (entry_fees * ratio)
                            else:
                                total_fees += entry_fees

                        await telegram_service.notify_position_closed(
                            symbol=matching_trade.get('symbol', prev_cid),
                            side=side_str,
                            entry_price=entry_px,
                            exit_price=exit_px,
                            pnl=pnl_val,
                            fees=total_fees,
                            quantity=matching_trade.get('size', matching_trade.get('qty', 0))
                        )
                    else:
                        print("   -> History Trade NOT Found")
                        await telegram_service.send_message(f"💰 <b>Position Closed: {target_symbol}</b> (PnL data delayed)")

        # 4b. Detect NEW Positions (Opens / Fills)
        # Iterate over CURRENT map
        if _last_open_positions is not None: # Ensure we had a state (not first run)
            for curr_cid, curr_pos in current_map.items():
                if curr_cid not in _last_open_positions:
                    # New Position Detected!
                    print(f"🔵 DETECTED OPEN FOR {curr_cid}")
                    
                    # Fetch Entry Price (Fill)
                    # Use same get_historical_trades logic but look for ENTRY
                    recent_trades = await topstep_client.get_historical_trades(account_id, days=1)
                    target_symbol = curr_pos.get('symbolId') or curr_cid
                    
                    matching_fill = None
                    if recent_trades:
                        for t in recent_trades:
                             # Look for trade with same symbol and recent time
                             # Side should match the position side code?
                             # Position Side: "Buy" or 1? `curr_pos` has `side`.
                             # Trade Side: 1 or 2.
                             # Let's just find the latest fill for this symbol.
                             if str(t.get('symbol')) == str(target_symbol) or str(t.get('contractId')) == str(curr_cid):
                                 matching_fill = t
                                 break
                    
                    if matching_fill:
                         # Get Fill Price
                         fill_price = matching_fill.get('price') or matching_fill.get('fillPrice') or 0
                         
                         fill_side = matching_fill.get('side')
                         # Robust Side Mapping with fallback to Position Snapshot side
                         side_upper = str(fill_side).upper().strip()
                         
                         if side_upper in ["0", "BUY", "LONG"]:
                             side_str = "BUY"
                         elif side_upper in ["1", "2", "SELL", "SHORT"]:
                             side_str = "SELL"
                         else:
                             # Fallback to the Position's side (which detected the Open)
                             # pos['side'] is usually "Buy"/"Sell"
                             pos_side = str(curr_pos.get('side')).upper().strip()
                             if "BUY" in pos_side or "LONG" in pos_side:
                                 side_str = "BUY"
                             elif "SELL" in pos_side or "SHORT" in pos_side:
                                 side_str = "SELL"
                             else:
                                 side_str = "UNK" # Give up

                         await telegram_service.notify_position_opened(
                             symbol=matching_fill.get('symbol', curr_cid),
                             side=side_str,
                             quantity=matching_fill.get('size', 1),
                             price=fill_price,
                             order_id=str(matching_fill.get('orderId', ''))
                         )
        
        # 5. Update State
        _last_open_positions = current_map

        # --- ORPHANED ORDER CHECK ---
        # 6. Fetch Active Orders
        # We need to fetch orders to see if any are working without a position
        recent_orders = await topstep_client.get_orders(account_id, days=1)
        
        # Filter for Working/Accepted
        # Status: 1=Working, 6=Pending? 
        # Or string 'Working', 'Accepted'. TopStepClient might normalize or return raw.
        # Assuming raw from previous debug or similar to webhook logic.
        # Let's handle both int and str to be safe.
        active_orders = []
        for o in recent_orders:
            st = o.get('status')
            # Check for "Working" (1) or "Accepted" ? 
            # Usually we care about Working (1).
            if str(st).upper() in ["WORKING", "ACCEPTED", "1", "6"]:
                active_orders.append(o)
                
        # 7. Identify Orphans
        # An order is orphaned if its contractId/symbol is NOT in _last_open_positions keys
        orphans = []
        for o in active_orders:
            cid = str(o.get('contractId'))
            sym = str(o.get('symbol'))
            
            # Check if we have a position for this contract
            # keys in current_map are contractIds
            has_pos = (cid in current_map)
            
            # If false, check symbol match (sometimes IDs vary slightly?)
            if not has_pos:
                # Fallback check values
                for k, v in current_map.items():
                    if str(v.get('symbol')) == sym:
                        has_pos = True
                        break
            
            if not has_pos:
                orphans.append(o)
                
        # 8. Notify if new Orphans found
        # We need a global state for orphans to avoid spamming every 30s
        global _last_orphans_ids
        current_orphan_ids = set(str(o.get('orderId') or o.get('id')) for o in orphans)
        
        # Logic: Notify if there are any orphans AND the set is different from last time
        # Or active reminders? Let's just notify on NEW orphans or full set if changed.
        if orphans and current_orphan_ids != _last_orphans_ids:
            print(f"⚠️ Orphaned Orders Detected: {current_orphan_ids}")
            await telegram_service.notify_orphaned_orders(orphans)
            
        _last_orphans_ids = current_orphan_ids
        
    except Exception as e:
        # db.add(Log(level="ERROR", message=f"Monitor Job Error: {e}"))
        # db.commit()
        print(f"Monitor Job Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def auto_flatten_job():
    # Create a new session for the job
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        risk_engine = RiskEngine(db)
        await risk_engine.check_auto_flatten()
    except Exception as e:
        print(f"Auto-flatten job error: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    
    # Check & Run Startup Backup (Fail-safe for missed cron jobs)
    check_and_run_startup_backup()
    
    # Load Persistence State
    global _last_open_positions
    state = load_state()
    if "last_open_positions" in state:
        _last_open_positions = state["last_open_positions"]
        print(f"Loaded {len(_last_open_positions)} positions from persistence.")
    
    # Log System Restart
    from backend.database import SessionLocal, Log
    db = SessionLocal()
    try:
        db.add(Log(level="WARNING", message="System Restarted: Connection Reset"))
        db.commit()
    except Exception as e:
        print(f"Startup Log Error: {e}")
    finally:
        db.close()

    # Auto-Connect to TopStep
    try:
        await topstep_client.login()
        # Initialize Position Snapshot to avoid false alerts on startup
        # But wait, if we restart, we lose state. 
        # If we have open positions on startup, we should just record them, not alert "Closed" (obviously).
        # We start with empty dict, and fetch immediately to fill it. 
        # Then next poll checks diff. Correct.
        await telegram_service.notify_startup()
        
    except Exception as e:
        print(f"Auto-login failed: {e}")

    # Add Jobs
    scheduler.add_job(auto_flatten_job, 'interval', minutes=1)
    
    # Monitor for Closures (Every 30s)
    # Monitor for Closures (Every 30s)
    scheduler.add_job(monitor_closed_positions_job, 'interval', seconds=30)
    
    # Maintenance Jobs
    # Backup Database daily at 03:00 UTC
    scheduler.add_job(backup_database, 'cron', hour=3, minute=0)
    
    # Clean Logs daily at 03:15 UTC (keep 7 days)
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

app = FastAPI(title="TopStep Trading Bot", version="0.1.0", lifespan=lifespan)

# CORS Setup (for Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(mapping.router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "online", "service": "TopStep Trading Bot"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
