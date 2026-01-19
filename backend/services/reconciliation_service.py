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
            except:
                pass
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
    
    # 6. Check for orphan trades (entry time matches an exit fill time)
    for trade in orphan_db_trades:
        trade_entry = _ensure_tz(trade.timestamp)
        
        is_orphan = False
        for fill in api_fills:
            if fill.get('profitAndLoss') is None:
                continue
            exit_ts = _parse_ts(fill.get('creationTimestamp'))
            if exit_ts and abs((trade_entry - exit_ts).total_seconds()) < 5:
                is_orphan = True
                break
        
        if is_orphan:
            proposed_changes.append({
                "trade_id": trade.id,
                "ticker": trade.ticker,
                "type": "delete",
                "description": f"Delete orphan #{trade.id}",
                "old_pnl": trade.pnl or 0,
                "new_pnl": 0
            })
    
    # 7. Calculate verification totals
    api_total_pnl = sum(rt['pnl'] for rt in api_round_turns)
    api_total_fees = sum(rt['fees'] for rt in api_round_turns)
    
    db_total_pnl = sum(t.pnl or 0 for t in db_trades)
    db_total_fees = sum(t.fees or 0 for t in db_trades)
    
    summary = {
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
    applied = {"closed": 0, "pnl_updated": 0, "deleted": 0}
    
    for change in changes:
        trade_id = change.get("trade_id")
        change_type = change.get("type")
        
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
        "message": f"Updates: {applied['pnl_updated']}, Deletions: {applied['deleted']}"
    }
