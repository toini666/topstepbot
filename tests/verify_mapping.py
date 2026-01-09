import httpx
import asyncio
import os
from dotenv import load_dotenv

# Load Env
load_dotenv()

BASE_URL = "http://localhost:8000/api"

async def test_mapping_flow():
    async with httpx.AsyncClient() as client:
        print("--- 1. Testing Create Mapping ---")
        # Define a mapping: "TEST_TICKER" -> "CON.F.US.MNQ.H26" (using a real ID for safety in mock)
        mapping_data = {
            "tv_ticker": "TEST_TICKER",
            "ts_contract_id": "CON.F.US.MNQ.H26",
            "ts_ticker": "MNQH6",
            "tick_size": 0.25,
            "tick_value": 0.5
        }
        
        # Create
        res = await client.post(f"{BASE_URL}/mappings", json=mapping_data)
        if res.status_code == 200:
            print("Mapping Created:", res.json())
        else:
            print("Failed to create mapping:", res.text)
            return

        print("\n--- 2. Verify Mapping List ---")
        res = await client.get(f"{BASE_URL}/mappings")
        mappings = res.json()
        found = next((m for m in mappings if m["tv_ticker"] == "TEST_TICKER"), None)
        if found:
            print("Mapping confirmed in DB:", found)
        else:
            print("Mapping NOT found in list!")
            return

        print("\n--- 3. Simulate Webhook (Using Mapped Ticker) ---")
        # Send a webhook with "TEST_TICKER"
        # We expect it to NOT look up via API (which would fail for TEST_TICKER), but use our mapping.
        payload = {
            "ticker": "TEST_TICKER",
            "action": "buy",
            "entry_price": 10000,
            "sl": 9950,
            "tp": 10100,
            "quantity": 1 # Will be overwritten by risk engine but required by schema? No, qty calc is internal actually? 
            # Wait, webhook logic calculates qty. The payload depends on schema.
        }
        # Actually Webhook Schema is:
        # ticker, type, direction, entry, stop, tp
        webhook_payload = {
            "ticker": "TEST_TICKER",
            "type": "setup",
            "direction": "long",
            "entry": 10000.0,
            "stop": 9990.0, # 10 pts risk
            "tp": 10020.0
        }
        
        # Note: This might trigger a real trade if we are not careful.
        # But `TEST_TICKER` won't match a real symbol for placement unless we mocked place_order too.
        # However, TopStepClient `place_order` checks `find_contract`.
        # If we didn't map it properly there, it might fail at placement stage.
        # BUT the goal is to verify the *Contract Retrieval* part in webhook.
        # The logs will show "Using Mapped Contract" if we uncommented that log, or we can check if it processed without "Contract Not Found".
        
        res = await client.post(f"{BASE_URL}/webhook", json=webhook_payload)
        print("Webhook Response:", res.json())
        
        # Clean up
        print("\n--- 4. clean up ---")
        if found:
            await client.delete(f"{BASE_URL}/mappings/{found['id']}")
            print("Mapping deleted.")

if __name__ == "__main__":
    asyncio.run(test_mapping_flow())
