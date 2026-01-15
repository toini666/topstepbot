
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Trade, Log

# Setup DB connection
DATABASE_URL = "sqlite:///./topstepbot.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("=== DEBUGGING GHOST TRADES ===")

# 1. Recent Trades (Look for duplicates)
print("\n--- Recent Trades (Last 10) ---")
trades = db.query(Trade).order_by(Trade.id.desc()).limit(10).all()
for t in trades:
    print(f"Trade #{t.id}: {t.ticker} | Action: {t.action} | Status: {t.status} | Strat: {t.strategy} | Time: {t.timestamp}")

# 2. Logs (Look for Monitor actions)
print("\n--- Monitor Open/Create Logs ---")
# Look for "DETECTED OPEN" or "Created Trade" or "Webhook"
logs = db.query(Log).order_by(Log.id.desc()).limit(100).all()
relevant_logs = []
for l in logs:
    if any(k in l.message for k in ["DETECTED OPEN", "Created Trade", "Webhook", "MANUAL", "RECONCILIATION"]):
        relevant_logs.append(l)

# Reverse to show chronological
for l in reversed(relevant_logs):
    print(f"[{l.timestamp.strftime('%H:%M:%S')}] {l.message}")

db.close()
