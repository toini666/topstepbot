
import requests
import json
import time

API_URL = "http://localhost:8000"
WEBHOOK_URL = "http://localhost:8000/api/webhook"

def run_test():
    print("--- Starting Verification: Factor Logic ---")
    
    # 1. Create Strategy with Factor 2.0 (Double Risk)
    print("\n1. Creating 'FactorStrat' (Factor: 2.5)...")
    strat_payload = {
        "name": "FactorStrat",
        "tv_id": "factor_strat_v1",
        "risk_factor": 2.5
    }
    
    # Check if exists first (clean run?)
    try:
        requests.delete(f"{API_URL}/api/strategies/1") # Try delete existing ID 1
    except:
        pass

    try:
        res = requests.post(f"{API_URL}/api/strategies/", json=strat_payload)
        print(f"   Response: {res.json()}")
    except Exception as e:
        print(f"   Error: {e}")

    # 2. Mock Webhook
    # Global Risk is likely $200. Factor 2.5 = $500 Risk.
    # At $2/pt and 10pt stop ($20 risk/contract), Quantity should be 500/20 = 25 contracts.
    
    print("\n2. Sending Webhook for 'factor_strat_v1'...")
    webhook_payload = {
        "type": "SIGNAL",
        "ticker": "MNQ",
        "direction": "BUY",
        "entry": 10000,
        "stop": 9990,
        "tp": 10020,
        "strat": "factor_strat_v1"
    }
    
    try:
        res = requests.post(WEBHOOK_URL, json=webhook_payload)
        print(f"   -> Webhook: {res.json()}")
        trade_id = res.json().get('trade_id')
        
        # 3. Check Trade Quantity
        time.sleep(1)
        if trade_id:
             # We can't fetch single trade by ID deeply easily without auth sometimes, but let's try dashboard trades
             trades = requests.get(f"{API_URL}/dashboard/trades").json()
             # Find the trade
             my_trade = next((t for t in trades if t['id'] == trade_id), None)
             if my_trade:
                 print(f"   ✅ Found Trade. Qty: {my_trade['quantity']}")
                 print(f"   (Expected Qty Calculation: Risk $500 / $20 per con = 25)")
             else:
                 print("   ❌ Trade not found in dashboard.")
        
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    run_test()
