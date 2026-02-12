"""
Reconciliation Service - Trade synchronization with TopStep API

The goal: Sum(DB PnL - Fees) = Sum(API PnL - Fees)

TopStep API returns "half-turns" (fills):
- Entry fills: side=0 (buy) or side=1 (sell for shorts), NO profitAndLoss field
- Exit fills: opposite side, HAS profitAndLoss field

Reconciliation is limited to TODAY's trades only.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.database import Trade, TickerMap, Log
from backend.services.topstep_client import topstep_client


def _parse_ts(date_str: str) -> Optional[datetime]:
    """Parse TopStep API date format to datetime."""
    if not date_str:
        return None
    clean = str(date_str).replace('Z', '+00:00')
    try:
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        if "." in clean:
            try:
                left, right = clean.split(".", 1)
                if "+" in right:
                    micro, tz = right.split("+", 1)
                    micro = (micro + "000000")[:6]
                    clean = f"{left}.{micro}+{tz}"
                    return datetime.fromisoformat(clean).replace(tzinfo=timezone.utc)
            except Exception as e:
                import logging
                logging.getLogger("topstepbot").warning(f"Failed to parse timestamp '{date_str}': {e}")
        return None


def _ensure_tz(dt: Optional[datetime]) -> Optional[datetime]:
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _get_today_start() -> datetime:
    """Get start of today (midnight local time) in UTC."""
    now_local = datetime.now().astimezone()
    midnight_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight_local.astimezone(timezone.utc)


def _build_round_turns(api_fills: List[Dict]) -> List[Dict]:
    """
    Convert half-turns (fills) into round-turns (complete trades).
    """
    entries = []
    exits = []
    
    for fill in api_fills:
        ts = _parse_ts(fill.get('creationTimestamp'))
        if not ts:
            continue
            
        pnl = fill.get('profitAndLoss')
        
        fill_data = {
            'contract_id': str(fill.get('contractId') or ''),
            'timestamp': ts,
            'price': fill.get('price', 0),
            'size': fill.get('size', 0),
            'fees': fill.get('fees', 0),
            'side': fill.get('side'),
            'pnl': pnl
        }
        
        if pnl is None:
            entries.append(fill_data)
        else:
            exits.append(fill_data)
    
    entries.sort(key=lambda x: x['timestamp'])
    exits.sort(key=lambda x: x['timestamp'])
    
    round_turns = []
    
    for entry in entries:
        # Find next entry on same contract
        next_entry_time = None
        for other_entry in entries:
            if other_entry is entry:
                continue
            if other_entry['contract_id'] != entry['contract_id']:
                continue
            if other_entry['timestamp'] > entry['timestamp']:
                next_entry_time = other_entry['timestamp']
                break
        
        # Collect matching exits
        total_pnl = 0
        total_fees = entry['fees']
        last_exit_time = None
        last_exit_price = None
        
        for exit in exits:
            if exit['contract_id'] != entry['contract_id']:
                continue
            if exit['timestamp'] <= entry['timestamp']:
                continue
            if next_entry_time and exit['timestamp'] >= next_entry_time:
                continue
            
            total_pnl += exit['pnl'] or 0
            total_fees += exit['fees'] or 0
            
            if last_exit_time is None or exit['timestamp'] > last_exit_time:
                last_exit_time = exit['timestamp']
                last_exit_price = exit['price']
        
        round_turns.append({
            'contract_id': entry['contract_id'],
            'entry_time': entry['timestamp'],
            'entry_price': entry['price'],
            'exit_time': last_exit_time,
            'exit_price': last_exit_price,
            'size': entry['size'],
            'side': entry['side'],
            'pnl': total_pnl,
            'fees': total_fees
        })
    
    return round_turns


async def preview_reconciliation(account_id: int, db: Session) -> Dict[str, Any]:
    """
    Analyze TODAY's trades and return proposed changes.
    """
    proposed_changes = []
    today_start = _get_today_start()
    
    # 1. Fetch fills from TopStep (today only)
    api_fills = await topstep_client.get_historical_trades(account_id, days=1)
    
    # 2. Build round-turns from fills
    api_round_turns = _build_round_turns(api_fills)
    
    # 3. Get DB trades (today only)
    db_trades = db.query(Trade).filter(
        Trade.account_id == account_id,
        Trade.timestamp >= today_start
    ).order_by(Trade.timestamp.asc()).all()
    
    # 4. Build ticker -> contract_id mapping
    ticker_to_cid = {}
    for trade in db_trades:
        if trade.ticker not in ticker_to_cid:
            tm = db.query(TickerMap).filter(TickerMap.tv_ticker == trade.ticker).first()
            if tm:
                ticker_to_cid[trade.ticker] = tm.ts_contract_id
            else:
                clean = trade.ticker.replace("1!", "").replace("2!", "").upper()
                for fill in api_fills:
                    cid = str(fill.get('contractId') or '')
                    if clean in cid.upper():
                        ticker_to_cid[trade.ticker] = cid
                        break
    
    # 5. Match DB trades to API round-turns
    matched_api_rts = set()
    matched_db_trades = set()
    orphan_db_trades = []
    
    for trade in db_trades:
        cid = ticker_to_cid.get(trade.ticker)
        if not cid:
            continue
        
        trade_entry = _ensure_tz(trade.timestamp)
        if not trade_entry:
            continue
        
        # Find matching API round-turn by entry time
        best_match = None
        best_diff = float('inf')
        
        for i, rt in enumerate(api_round_turns):
            if i in matched_api_rts:
                continue
            if rt['contract_id'] != cid:
                continue
            
            diff = abs((rt['entry_time'] - trade_entry).total_seconds())
            if diff < 5 and diff < best_diff:
                best_match = (i, rt)
                best_diff = diff
        
        if best_match:
            i, rt = best_match
            matched_api_rts.add(i)
            matched_db_trades.add(trade.id)
            
            db_pnl = trade.pnl or 0
            db_fees = trade.fees or 0
            db_exit = _ensure_tz(trade.exit_time)
            db_exit_price = trade.exit_price or 0
            
            needs_update = False
            changes = []
            
            if abs(db_pnl - rt['pnl']) > 0.01:
                needs_update = True
                changes.append(f"PnL ${db_pnl:.2f}→${rt['pnl']:.2f}")
            
            if abs(db_fees - rt['fees']) > 0.01:
                needs_update = True
                changes.append(f"Fees ${db_fees:.2f}→${rt['fees']:.2f}")
            
            if rt['exit_time'] and not db_exit:
                needs_update = True
                changes.append(f"Closing Trade at {rt['exit_time'].strftime('%H:%M:%S')}")

            elif rt['exit_time'] and db_exit:
                if abs((db_exit - rt['exit_time']).total_seconds()) > 10:
                    needs_update = True
                    changes.append(f"ExitTime→{rt['exit_time'].strftime('%H:%M:%S')}")
            
            if rt['exit_price'] and abs(db_exit_price - rt['exit_price']) > 0.01:
                needs_update = True
                changes.append(f"ExitPrice→{rt['exit_price']}")
            
            if needs_update:
                # determine type: if it was open (no db_exit) and now has exit, it's a close
                p_type = "close" if (not db_exit and rt['exit_time']) else "pnl_update"
                
                # Skip false positives: if it's a pnl_update but nothing meaningful changed
                if p_type == "pnl_update":
                    pnl_same = abs(db_pnl - rt['pnl']) <= 0.01
                    fees_same = abs(db_fees - rt['fees']) <= 0.01
                    exit_price_same = abs(db_exit_price - (rt['exit_price'] or 0)) <= 0.01
                    if pnl_same and fees_same and exit_price_same:
                        continue  # No meaningful change, skip
                
                proposed_changes.append({
                    "trade_id": trade.id,
                    "ticker": trade.ticker,
                    "type": p_type,
                    "description": f"#{trade.id}: " + ", ".join(changes),
                    "old_pnl": db_pnl,
                    "new_pnl": rt['pnl'],
                    "old_fees": db_fees,
                    "new_fees": rt['fees'],
                    "new_exit_time": rt['exit_time'],  # datetime object
                    "new_exit_price": rt['exit_price']
                })
        else:
            orphan_db_trades.append(trade)
    
    # 6. Check for orphan trades (Delete if duplicate or invalid)
    # Group matched trades for duplicate detection
    matched_trade_sigs = []
    for trade_id in matched_db_trades:
        # potential optimization: cache these earlier
        t = db.query(Trade).filter(Trade.id == trade_id).first() 
        if t:
             # Signature: Ticker + Side + Price + Time (approx)
             ts = _ensure_tz(t.timestamp)
             matched_trade_sigs.append({
                 "ticker": t.ticker,
                 "side": t.action,
                 "price": t.entry_price,
                 "time": ts,
                 "id": t.id
             })

    for trade in orphan_db_trades:
        trade_entry = _ensure_tz(trade.timestamp)
        trade_sig = {
            "ticker": trade.ticker,
            "side": trade.action,
            "price": trade.entry_price,
            "time": trade_entry
        }
        
        is_duplicate = False
        duplicate_of_id = None
        
        # Check against matched trades
        for sig in matched_trade_sigs:
            if (sig["ticker"] == trade_sig["ticker"] and 
                sig["side"] == trade_sig["side"] and 
                abs(sig["price"] - trade_sig["price"]) < 0.0001):
                
                # Check time closeness (e.g. within 60s)
                if abs((sig["time"] - trade_sig["time"]).total_seconds()) < 60:
                    is_duplicate = True
                    duplicate_of_id = sig["id"]
                    break
        
        if is_duplicate:
            proposed_changes.append({
                "trade_id": trade.id,
                "ticker": trade.ticker,
                "type": "delete",
                "description": f"Delete duplicate of #{duplicate_of_id}",
                "old_pnl": trade.pnl or 0,
                "new_pnl": 0
            })
            continue

        # Existing "Orphan but Entry Matches Exit Timestamp" Logic (Legacy?)
        # Keeping it as a fallback but refining it
        is_legacy_orphan = False
        for fill in api_fills:
            if fill.get('profitAndLoss') is None:
                continue
            exit_ts = _parse_ts(fill.get('creationTimestamp'))
            if exit_ts and trade_entry and abs((trade_entry - exit_ts).total_seconds()) < 5:
                is_legacy_orphan = True
                break
        
        if is_legacy_orphan:
            proposed_changes.append({
                "trade_id": trade.id,
                "ticker": trade.ticker,
                "type": "delete",
                "description": f"Delete invalid orphan #{trade.id}",
                "old_pnl": trade.pnl or 0,
                "new_pnl": 0
            })
            continue
            
        # If it's CLOSED but not matched to any API round turn, it might be a ghost trade
        if trade.status == "CLOSED":
             proposed_changes.append({
                "trade_id": trade.id,
                "ticker": trade.ticker,
                "type": "delete",
                "description": f"Delete unmatched CLOSED trade #{trade.id}",
                "old_pnl": trade.pnl or 0,
                "new_pnl": 0
            })
    
    # 6.5 CHECK FOR UNMATCHED API TRADES (Missing in DB)
    for i, rt in enumerate(api_round_turns):
        if i not in matched_api_rts:
            # This is a round-turn in API that has no corresponding DB trade
            # We should import it
            
            # Determine ticker (might need TickerMap reverse lookup or use contract_id)
            # Try to resolve friendly ticker
            ticker = rt['contract_id']
            tm = db.query(TickerMap).filter(TickerMap.ts_contract_id == rt['contract_id']).first()
            if tm:
                ticker = tm.tv_ticker
            
            # Determine Action
            action = "BUY" if rt.get('size', 0) > 0 else "SELL" # Simple heuristic, or infer from side?
            # Actually side is on the fill. 
            # rt doesn't explicitly store side, let's look at the fills again if needed
            # But wait, round turn implies entry and exit.
            # Entry side: 
            # If entry side was Buy (0), then Action is BUY.
            # Let's check the build_round_turns
            
            # For now, let's assume standard Long=Buy
            # We need to pass side through _build_round_turns if we want it here
            # But let's check `rt` keys.
            
            changes = [f"Import missing trade {ticker}"]
            
            proposed_changes.append({
                "type": "create",
                "ticker": ticker,
                "description": f"Import missing trade {ticker} (PnL: ${rt['pnl']:.2f})",
                "contract_id": rt['contract_id'],
                "entry_time": rt['entry_time'],
                "entry_price": rt['entry_price'],
                "exit_time": rt['exit_time'],
                "exit_price": rt['exit_price'],
                "size": rt['size'],
                "side": rt['side'],
                "new_pnl": rt['pnl'],
                "old_pnl": 0,
                "fees": rt['fees'],
                # We need side. API side 0=Buy, 1=Sell.
                # Let's defaults to BUY and user can fix if wrong, or better:
                # We can infer from PnL logic but that's complex.
                # Let's add 'side' to _build_round_turns
            })

    # 7. Calculate verification totals
    api_total_pnl = sum(rt['pnl'] for rt in api_round_turns)
    api_total_fees = sum(rt['fees'] for rt in api_round_turns)
    
    db_total_pnl = sum(t.pnl or 0 for t in db_trades)
    db_total_fees = sum(t.fees or 0 for t in db_trades)
    
    summary = {
        "trades_to_create": sum(1 for c in proposed_changes if c["type"] == "create"),   
        "trades_to_close": sum(1 for c in proposed_changes if c["type"] == "close"),
        "trades_to_delete": sum(1 for c in proposed_changes if c["type"] == "delete"),
        "pnl_updates": sum(1 for c in proposed_changes if c["type"] == "pnl_update"),
        "api_total_pnl": api_total_pnl,
        "api_total_fees": api_total_fees,
        "api_net": api_total_pnl - api_total_fees,
        "db_total_pnl": db_total_pnl,
        "db_total_fees": db_total_fees,
        "db_net": db_total_pnl - db_total_fees,
        "total_pnl_change": (api_total_pnl - api_total_fees) - (db_total_pnl - db_total_fees)
    }
    
    return {
        "success": True,
        "proposed_changes": proposed_changes,
        "summary": summary
    }


async def apply_reconciliation(account_id: int, changes: List[Dict], db: Session) -> Dict[str, Any]:
    """Apply the proposed reconciliation changes to the database."""
    applied = {"created": 0, "closed": 0, "pnl_updated": 0, "deleted": 0}
    
    for change in changes:
        trade_id = change.get("trade_id")
        change_type = change.get("type")
        
        if change_type == "create":
            # Create new trade - side mapping handled below
            
            # Ok, let's implement the create logic assuming the dict has the data
            side_str = "BUY"
            # It seems 'side' in build_round_turns comes from entry['side']
            # TopStep API: Side often 0=Buy, 1=Sell? Or Strings?
            # Trade log showed: 'side': 1. Let's assume 1 is SELL/SHORT.
            # 0 is BUY/LONG.
            
            # Actually, let's check Trade log again:
            # {'id': ..., 'side': 1, 'profitAndLoss': -58.5 ...}
            # This was a CLOSE trade.
            # Entry would be opposite.
            # If close is 1 (Sell), Entry was 0 (Buy).
            # If close is 0 (Buy), Entry was 1 (Sell).
            
            # Wait, api_round_turns uses entry['side'].
            # If entry side is 0 -> BUY.
            # If entry side is 1 -> SELL.
            
            # Let's refine build_round_turns to get the side from ENTRY fill.
             
            rt_side = change.get("side") # Need to pass this
            action = "BUY"
            if str(rt_side) in ["1", "SELL", "Short"]:
                action = "SELL"
            
            # Parse timestamps
            entry_time = change.get("entry_time")
            if isinstance(entry_time, str):
                entry_time = _parse_ts(entry_time)

            exit_time = change.get("exit_time")
            if isinstance(exit_time, str):
                exit_time = _parse_ts(exit_time)

            new_trade = Trade(
                account_id=account_id,
                ticker=change.get("ticker"),
                action=action,
                entry_price=change.get("entry_price"),
                exit_price=change.get("exit_price"),
                quantity=change.get("size"),
                status="CLOSED",
                pnl=change.get("new_pnl"),
                fees=change.get("fees"),
                timestamp=entry_time,
                exit_time=exit_time,
                strategy="IMPORTED",  # Mark as imported
                timeframe="-"
            )
            db.add(new_trade)
            applied["created"] += 1
            db.add(Log(level="INFO", message=f"RECONCILIATION: Created missing trade {new_trade.ticker}"))
            continue

        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            continue
        
        if change_type == "close":
            trade.status = "CLOSED"
            new_exit_time = change.get("new_exit_time")
            if new_exit_time:
                # Ensure it's a datetime object
                if isinstance(new_exit_time, str):
                    new_exit_time = _parse_ts(new_exit_time)
                trade.exit_time = new_exit_time
            if change.get("new_exit_price"):
                trade.exit_price = change["new_exit_price"]
            trade.pnl = change.get("new_pnl", 0)
            trade.fees = change.get("new_fees", trade.fees or 0)
            applied["closed"] += 1
            db.add(Log(level="INFO", message=f"RECONCILIATION: #{trade_id} CLOSED"))
        
        elif change_type == "pnl_update":
            old_pnl = trade.pnl or 0
            trade.pnl = change.get("new_pnl", 0)
            trade.fees = change.get("new_fees", trade.fees)
            
            new_exit_time = change.get("new_exit_time")
            if new_exit_time:
                # Ensure it's a datetime object
                if isinstance(new_exit_time, str):
                    new_exit_time = _parse_ts(new_exit_time)
                trade.exit_time = new_exit_time
            
            if change.get("new_exit_price"):
                trade.exit_price = change["new_exit_price"]
            
            applied["pnl_updated"] += 1
            db.add(Log(level="INFO", message=f"RECONCILIATION: #{trade_id} updated"))
        
        elif change_type == "delete":
            db.delete(trade)
            applied["deleted"] += 1
            db.add(Log(level="WARNING", message=f"RECONCILIATION: #{trade_id} DELETED"))
    
    db.commit()
    
    return {
        "success": True,
        "applied": applied,
        "message": f"Created: {applied['created']}, Updates: {applied['pnl_updated']}, Deletions: {applied['deleted']}"
    }
