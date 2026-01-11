"""
Export Router - Trade Statistics & Data Export

Provides endpoints for:
- Exporting trades with filters (date, strategy, timeframe, ticker, account)
- CSV and JSON formats
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime, timedelta
import csv
import io
import json

from backend.database import get_db, Trade, Strategy

router = APIRouter()


# =============================================================================
# EXPORT TRADES
# =============================================================================

@router.get("/export/trades")
def export_trades(
    format: str = Query("json", description="Export format: json or csv"),
    status: Optional[str] = Query(None, description="Filter by status: OPEN, CLOSED, REJECTED"),
    strategy: Optional[str] = Query(None, description="Filter by strategy TV ID"),
    timeframe: Optional[str] = Query(None, description="Filter by timeframe: M5, H1, D1, etc."),
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol (partial match)"),
    account_id: Optional[int] = Query(None, description="Filter by account ID"),
    session: Optional[str] = Query(None, description="Filter by session: ASIA, UK, US"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(1000, description="Max records to export"),
    db: Session = Depends(get_db)
):
    """
    Export trades with comprehensive filters.
    Supports JSON and CSV formats.
    """
    # Build query
    query = db.query(Trade)
    
    # Apply filters
    filters = []
    
    if status:
        filters.append(Trade.status == status.upper())
    
    if strategy:
        filters.append(Trade.strategy == strategy)
    
    if timeframe:
        filters.append(Trade.timeframe == timeframe.upper())
    
    if ticker:
        filters.append(Trade.ticker.ilike(f"%{ticker}%"))
    
    if account_id:
        filters.append(Trade.account_id == account_id)
    
    if session:
        filters.append(Trade.session == session.upper())
    
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            filters.append(Trade.timestamp >= from_dt)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
            filters.append(Trade.timestamp < to_dt)
        except ValueError:
            pass
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Order by most recent first
    query = query.order_by(Trade.timestamp.desc()).limit(limit)
    
    trades = query.all()
    
    # Get strategy name lookup
    strategies = db.query(Strategy).all()
    strategy_names = {s.tv_id: s.name for s in strategies}
    
    # Build export data
    export_data = []
    for t in trades:
        record = {
            "id": t.id,
            "account_id": t.account_id,
            "ticker": t.ticker,
            "strategy_id": t.strategy,
            "strategy_name": strategy_names.get(t.strategy, t.strategy),
            "timeframe": t.timeframe,
            "session": t.session,
            "action": t.action,
            "quantity": t.quantity,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "sl": t.sl,
            "tp": t.tp,
            "pnl": t.pnl,
            "fees": t.fees,
            "status": t.status,
            "rejection_reason": t.rejection_reason,
            "entry_time": t.timestamp.isoformat() if t.timestamp else None,
            "exit_time": t.exit_time.isoformat() if t.exit_time else None,
            "duration_seconds": t.duration_seconds,
            "topstep_order_id": t.topstep_order_id
        }
        export_data.append(record)
    
    # Return based on format
    if format.lower() == "csv":
        return _export_csv(export_data)
    else:
        return {
            "total": len(export_data),
            "filters": {
                "status": status,
                "strategy": strategy,
                "timeframe": timeframe,
                "ticker": ticker,
                "account_id": account_id,
                "session": session,
                "from_date": from_date,
                "to_date": to_date
            },
            "trades": export_data
        }


def _export_csv(data: List[dict]) -> StreamingResponse:
    """Generate CSV file response."""
    if not data:
        return StreamingResponse(
            iter(["No data"]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=trades_export.csv"}
        )
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    output.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trades_export_{timestamp}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# =============================================================================
# TRADE STATISTICS
# =============================================================================

@router.get("/export/stats")
def get_trade_stats(
    strategy: Optional[str] = Query(None, description="Filter by strategy TV ID"),
    timeframe: Optional[str] = Query(None, description="Filter by timeframe"),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    account_id: Optional[int] = Query(None, description="Filter by account"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated statistics for trades.
    """
    # Build query for CLOSED trades only
    query = db.query(Trade).filter(Trade.status == "CLOSED")
    
    filters = []
    
    if strategy:
        filters.append(Trade.strategy == strategy)
    
    if timeframe:
        filters.append(Trade.timeframe == timeframe.upper())
    
    if ticker:
        filters.append(Trade.ticker.ilike(f"%{ticker}%"))
    
    if account_id:
        filters.append(Trade.account_id == account_id)
    
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            filters.append(Trade.timestamp >= from_dt)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
            filters.append(Trade.timestamp < to_dt)
        except ValueError:
            pass
    
    if filters:
        query = query.filter(and_(*filters))
    
    trades = query.all()
    
    if not trades:
        return {
            "total_trades": 0,
            "message": "No matching trades found"
        }
    
    # Calculate stats
    total_trades = len(trades)
    winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
    losing_trades = [t for t in trades if t.pnl and t.pnl < 0]
    
    total_pnl = sum(t.pnl or 0 for t in trades)
    total_fees = sum(t.fees or 0 for t in trades)
    net_pnl = total_pnl - total_fees
    
    avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    # Calculate average duration
    durations = [t.duration_seconds for t in trades if t.duration_seconds]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # Win rate
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
    
    # Profit factor
    gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
    gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
    
    return {
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "total_fees": round(total_fees, 2),
        "net_pnl": round(net_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "∞",
        "avg_duration_minutes": round(avg_duration / 60, 1) if avg_duration else None,
        "filters_applied": {
            "strategy": strategy,
            "timeframe": timeframe,
            "ticker": ticker,
            "account_id": account_id,
            "from_date": from_date,
            "to_date": to_date
        }
    }
