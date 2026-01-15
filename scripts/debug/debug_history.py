import asyncio
import os
from dotenv import load_dotenv
from backend.services.topstep_client import topstep_client

async def test_history():
    load_dotenv()
    # Re-init client to load env vars
    topstep_client.username = os.getenv("TOPSTEP_USERNAME")
    topstep_client.password = os.getenv("TOPSTEP_PASSWORD")
    topstep_client.api_key = os.getenv("TOPSTEP_APIKEY")
    
    print("Logging in...")
    if not await topstep_client.login():
        print("Login failed.")
        return

    print("Fetching Accounts...")
    accounts = await topstep_client.get_accounts()
    if not accounts:
        print("No accounts found.")
        return
        
    print(f"Found {len(accounts)} Accounts.")

    for acc in accounts:
        account_id = acc['id']
        print(f"\n=== Checking Account: {account_id} ({acc.get('name')}) ===")
        
        # Test 1 Day
        print("--- Last 1 Day ---")
        orders_1 = await topstep_client.get_orders(account_id, days=1)
        trades_1 = await topstep_client.get_historical_trades(account_id, days=1)
        print(f"Orders: {len(orders_1)}, Trades: {len(trades_1)}")

        # Test 7 Days
        print("--- Last 7 Days ---")
        orders_7 = await topstep_client.get_orders(account_id, days=7)
        trades_7 = await topstep_client.get_historical_trades(account_id, days=7)
        print(f"Orders: {len(orders_7)}, Trades: {len(trades_7)}")
        
        # Test 30 Days
        print("--- Last 30 Days ---")
        orders_30 = await topstep_client.get_orders(account_id, days=30)
        trades_30 = await topstep_client.get_historical_trades(account_id, days=30)
        print(f"Orders: {len(orders_30)}, Trades: {len(trades_30)}")

        if len(trades_30) > len(trades_1):
            print("SUCCESS: 30 Days returned more data.")
        else:
            print("WARNING: 30 Days returned same data. (Maybe no history exists?)")
        
        if trades_1:
             print("\nLast 5 Trades (1 Day Fetch):")
             for t in trades_1[:5]:
                 print(f" - {t}")



if __name__ == "__main__":
    asyncio.run(test_history())
