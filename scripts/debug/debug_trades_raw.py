
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.topstep_client import TopStepClient

load_dotenv()

async def main():
    client = TopStepClient()
    await client.login()
    # Get accounts to find a valid account ID if needed, or just use generic fetch if possible
    accounts = await client.get_accounts()
    
    if isinstance(accounts, dict):
        accounts = accounts.get('accounts', [])

    # accounts is a list
    for acc in accounts:
        account_id = acc['id']
        print(f"\nFetching trades for Account {account_id} ({acc.get('name')})...")
        trades = await client.get_historical_trades(account_id, days=7)
        if not trades:
            print("  No trades found.")
            continue
            
        trade_list = trades if isinstance(trades, list) else trades.get('trades', [])
        for t in trade_list:
            # Print relevant fields to debug Side and PnL
            details = f"ID: {t.get('orderId')} | Time: {t.get('creationTimestamp')} | Side: {t.get('side')} | Price: {t.get('price')} | PnL: {t.get('profitAndLoss')} | Fees: {t.get('fees')}"
            print(details)

if __name__ == "__main__":
    asyncio.run(main())
