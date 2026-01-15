"""
Reconciliation Service - Trade synchronization with TopStep API

Provides functions to:
- Preview proposed changes (dry-run)
- Apply reconciliation changes to database
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.database import Trade, TickerMap, Log
from backend.services.topstep_client import topstep_client


def _parse_topstep_date(date_str: str) -> Optional[datetime]:
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
                    dt = datetime.fromisoformat(clean)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
            except Exception:
                pass
        return None


async def preview_reconciliation(account_id: int, db: Session) -> Dict[str, Any]:
    """
    Analyze trades and return proposed changes WITHOUT applying them.
    
    Returns:
        Dictionary with proposed_changes list and summary
    """
    proposed_changes = []
    
    # 1. Fetch current positions from TopStep
    current_positions = await topstep_client.get_open_positions(account_id)
    current_position_ids = set(str(pos.get('contractId')) for pos in current_positions)
    
    # 2. Fetch historical trades from TopStep (last 7 days for broader coverage)
    api_trades = await topstep_client.get_historical_trades(account_id, days=7)
    
    # 3. Get all OPEN trades from our database for this account
    db_open_trades = db.query(Trade).filter(
        Trade.account_id == account_id,
        Trade.status == "OPEN"
    ).all()
    
    # 4. Check each DB trade against TopStep data
    for trade in db_open_trades:
        # Find expected contract ID
        expected_cid = None
        ticker_map = db.query(TickerMap).filter(TickerMap.tv_ticker == trade.ticker).first()
        
        if ticker_map:
            expected_cid = ticker_map.ts_contract_id
        else:
            # Fallback: try to match by ticker root
            clean_ticker = trade.ticker.replace("1!", "").replace("2!", "").upper()
            for cid in current_position_ids:
                if clean_ticker in cid.upper():
                    expected_cid = cid
                    break
        
        if not expected_cid:
            # Cannot verify - skip
            continue
        
        # Check if trade is still physically open in TopStep
        if expected_cid not in current_position_ids:
            # Trade should be CLOSED - find exit data from API history
            exit_fill = None
            trade_entry_time = trade.timestamp
            
            for t in api_trades:
                t_cid = str(t.get('contractId') or '')
                if t_cid == expected_cid:
                    t_time = _parse_topstep_date(
                        t.get('creationTimestamp') or t.get('timestamp') or t.get('time')
                    )
                    if trade_entry_time and t_time:
                        if trade_entry_time.tzinfo is None:
                            trade_entry_time = trade_entry_time.replace(tzinfo=timezone.utc)
                        if t_time.tzinfo is None:
                            t_time = t_time.replace(tzinfo=timezone.utc)
                        
                        if t_time > trade_entry_time:
                            exit_fill = t
                            break
                    elif not trade_entry_time:
                        exit_fill = t
                        break
            
            if exit_fill:
                exit_px = exit_fill.get('price') or exit_fill.get('fillPrice') or 0
                new_pnl = exit_fill.get('pnl') or exit_fill.get('profitAndLoss') or 0
                new_fees = exit_fill.get('fees') or 0
                
                proposed_changes.append({
                    "trade_id": trade.id,
                    "ticker": trade.ticker,
                    "type": "close",
                    "description": f"Close trade #{trade.id} ({trade.ticker})",
                    "old_status": "OPEN",
                    "new_status": "CLOSED",
                    "old_pnl": trade.pnl or 0,
                    "new_pnl": new_pnl,
                    "new_exit_price": exit_px,
                    "new_fees": new_fees
                })
    
    # 5. Check for PnL discrepancies on recently closed trades
    today = datetime.now(timezone.utc).date()
    db_closed_trades = db.query(Trade).filter(
        Trade.account_id == account_id,
        Trade.status == "CLOSED",
        Trade.exit_time >= datetime.now(timezone.utc) - timedelta(days=1)
    ).all()
    
    for trade in db_closed_trades:
        # Try to find matching API trade
        ticker_map = db.query(TickerMap).filter(TickerMap.tv_ticker == trade.ticker).first()
        expected_cid = ticker_map.ts_contract_id if ticker_map else None
        
        if not expected_cid:
            continue
        
        for api_trade in api_trades:
            if str(api_trade.get('contractId')) == expected_cid:
                api_pnl = api_trade.get('pnl') or api_trade.get('profitAndLoss') or 0
                api_fees = api_trade.get('fees') or 0
                
                # Check if there's a significant PnL difference
                if trade.pnl is not None and abs((trade.pnl or 0) - api_pnl) > 0.01:
                    proposed_changes.append({
                        "trade_id": trade.id,
                        "ticker": trade.ticker,
                        "type": "pnl_update",
                        "description": f"Update PnL for trade #{trade.id} ({trade.ticker})",
                        "old_pnl": trade.pnl or 0,
                        "new_pnl": api_pnl,
                        "old_fees": trade.fees or 0,
                        "new_fees": api_fees
                    })
                break
    
    # Build summary
    summary = {
        "trades_to_close": sum(1 for c in proposed_changes if c["type"] == "close"),
        "pnl_updates": sum(1 for c in proposed_changes if c["type"] == "pnl_update"),
        "total_pnl_change": sum(c.get("new_pnl", 0) - c.get("old_pnl", 0) for c in proposed_changes)
    }
    
    return {
        "success": True,
        "proposed_changes": proposed_changes,
        "summary": summary
    }


async def apply_reconciliation(account_id: int, changes: List[Dict], db: Session) -> Dict[str, Any]:
    """
    Apply the proposed reconciliation changes to the database.
    
    Args:
        account_id: The account ID
        changes: List of proposed changes (from preview)
        db: Database session
        
    Returns:
        Dictionary with applied changes count
    """
    applied = {"closed": 0, "pnl_updated": 0}
    
    for change in changes:
        trade_id = change.get("trade_id")
        change_type = change.get("type")
        
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            continue
        
        if change_type == "close":
            trade.status = "CLOSED"
            trade.exit_price = change.get("new_exit_price", 0)
            trade.exit_time = datetime.now(timezone.utc)
            trade.pnl = change.get("new_pnl", 0)
            trade.fees = change.get("new_fees", 0)
            applied["closed"] += 1
            
            db.add(Log(
                level="INFO",
                message=f"MANUAL RECONCILIATION: Trade #{trade_id} marked as CLOSED (PnL: ${change.get('new_pnl', 0):.2f})"
            ))
        
        elif change_type == "pnl_update":
            old_pnl = trade.pnl
            trade.pnl = change.get("new_pnl", 0)
            trade.fees = change.get("new_fees", trade.fees)
            applied["pnl_updated"] += 1
            
            db.add(Log(
                level="INFO",
                message=f"MANUAL RECONCILIATION: Trade #{trade_id} PnL updated: ${old_pnl:.2f} -> ${change.get('new_pnl', 0):.2f}"
            ))
    
    db.commit()
    
    return {
        "success": True,
        "applied": applied,
        "message": f"Applied {applied['closed']} closures and {applied['pnl_updated']} PnL updates"
    }
