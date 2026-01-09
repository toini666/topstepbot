import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_setup_alert():
    print("\n--- Testing SETUP Alert ---")
    payload = {
        "ticker": "NQ1!",
        "type": "SETUP",
        "direction": "LONG",
        "entry": 21450.25,
        "stop": 21415.25,
        "tp": 21485.25
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/webhook", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200 and response.json().get("type") == "SETUP":
            print("✅ SETUP Alert handled correctly")
        else:
            print("❌ SETUP Alert failed")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_signal_alert():
    print("\n--- Testing SIGNAL Alert ---")
    payload = {
        "ticker": "MNQ1!",
        "type": "SIGNAL",
        "direction": "LONG",
        "entry": 21500.00,
        "stop": 21480.00,
        "tp": 21540.00
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/webhook", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Note: It might be rejected if outside trading hours or other risk checks, 
        # but as long as it's processed as SIGNAL (or rejected by logic), it's a pass for the routing logic.
        data = response.json()
        if response.status_code == 200:
            if data.get("type") == "SIGNAL":
                 print("✅ SIGNAL Alert handled correctly (Received/Processed)")
            elif data.get("status") == "rejected":
                 print(f"✅ SIGNAL Alert processed but rejected (Expected depending on logic): {data.get('reason')}")
            else:
                 print("❌ SIGNAL Alert response unexpected")
        else:
            print("❌ SIGNAL Alert failed")

    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_setup_alert()
    test_signal_alert()
