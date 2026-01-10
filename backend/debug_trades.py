from backend.database import SessionLocal, Trade
import json

def inspect_trades():
    db = SessionLocal()
    try:
        # Filter trades around the problematic times (2026-01-09 15:00 - 16:00 UTC approx?)
        # User time might be local (CET?), so 15:00 is 14:00 UTC?
        # Let's just list all trades from that day to be sure.
        trades = db.query(Trade).order_by(Trade.timestamp.desc()).all()
        print(f"--- Trades Analysis ---")
        for t in trades:
            # Simple filtered print
            if "2026-01-09" in str(t.timestamp):
                print(f"ID: {t.id} | Date: {t.timestamp} | Qty: {t.quantity} | Ticker: {t.ticker} | Strat: {t.strategy} | TS_Order_ID: {t.topstep_order_id}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_trades()
