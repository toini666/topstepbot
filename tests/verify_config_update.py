import httpx
import json

# Configuration
API_URL = "http://localhost:8000/api/dashboard/config"

def test_update_config():
    # Test 1: Toggle Blocked Periods
    print("Test 1: Toggling Blocked Periods Enabled to False")
    payload_1 = {
        "blocked_periods_enabled": False
    }
    Helpers.send_request(payload_1)

    # Test 2: Update Blocked Periods List
    print("\nTest 2: Updating Blocked Periods List")
    payload_2 = {
        "blocked_periods": [
            {"start": "09:00", "end": "10:00"},
            {"start": "14:00", "end": "15:00"}
        ]
    }
    Helpers.send_request(payload_2)

    # Test 3: Verify Persistence
    print("\nTest 3: Verifying Persistence (GET Request)")
    try:
        response = httpx.get(API_URL)
        if response.status_code == 200:
            config = response.json()
            print("Current Config:", json.dumps(config, indent=2))
            
            # Validation
            if config['blocked_periods_enabled'] is False:
                 print("✅ Blocked Periods Enabled is correctly False")
            else:
                 print("❌ Blocked Periods Enabled should be False but is", config['blocked_periods_enabled'])
                 
            if len(config['blocked_periods']) == 2:
                 print("✅ Blocked Periods count is correctly 2")
            else:
                 print("❌ Blocked Periods count mismatch")
        else:
            print(f"❌ GET Failed. Status: {response.status_code}")
    except httpx.ConnectError:
        print("❌ Could not connect.")

class Helpers:
    @staticmethod
    def send_request(payload):
        print(f"Sending payload: {json.dumps(payload, indent=2)}")
        try:
            response = httpx.post(API_URL, json=payload)
            if response.status_code == 200:
                print("✅ Success! Response:", response.json())
            else:
                print(f"❌ Failed. Status Code: {response.status_code}")
                print("Response:", response.text)
        except httpx.ConnectError:
            print("❌ Could not connect to the server.")

if __name__ == "__main__":
    test_update_config()
