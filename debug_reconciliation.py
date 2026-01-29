
import asyncio
import os
from datetime import datetime, timedelta
from backend.services.topstep_client import topstep_client

# Account ID provided by user
TARGET_ACCOUNT_ID = 16630119

async def fetch_trades():
    print(f"Login to TopStep...")
    await topstep_client.login()
    
    print(f"Fetching trades for account {TARGET_ACCOUNT_ID}...")
    
    # Try fetching last 24 hours first
    trades = await topstep_client.get_historical_trades(TARGET_ACCOUNT_ID, days=1)
    
    print(f"--- Found {len(trades)} trades (Last 24h) ---")
    for t in trades:
        print(t)
        
    print("\n--- Daily PnL Check ---")
    total_pnl = sum(t.get('profitAndLoss', 0) or 0 for t in trades)
    print(f"Calculated Daily PnL: {total_pnl}")

if __name__ == "__main__":
    try:
        asyncio.run(fetch_trades())
    except Exception as e:
        print(f"Error: {e}")
