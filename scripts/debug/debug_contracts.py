
import asyncio
import os
from dotenv import load_dotenv
from backend.services.topstep_client import topstep_client

# Load Env for credentials
load_dotenv()

async def main():
    print("Logging in...")
    # Ensure credentials are in env or client handles it
    if not os.getenv("TOPSTEP_USERNAME") or not os.getenv("TOPSTEP_APIKEY"):
        print("Error: TOPSTEP_USERNAME or TOPSTEP_APIKEY not set in .env")
        return

    print("Login successful.")
    
    # Re-inject credentials since client instantiated before load_dotenv
    topstep_client.username = os.getenv("TOPSTEP_USERNAME")
    topstep_client.api_key = os.getenv("TOPSTEP_APIKEY")
    
    login_success = await topstep_client.login()
    
    # Try to fetch a specific market or list (depending on what methods exist)
    # The user wants "infos qu'on a récupérées de l'API ... contrats disponibles"
    # Looking at client code, we have: search_tradable_objects(symbol_prefix="MNQ")
    # Let's try to search for common indices to see the structure
    
    tickers_to_check = ["MNQ", "NQ", "MES", "ES", "MCL", "CL", "GC", "MGC"]
    
    print("\n--- Fetching Contract Details ---")
    for t in tickers_to_check:
        print(f"\nSearching for {t}...")
        # Client normally returns the first match or detail. 
        # But we want to see the "mapping" potentially.
        # Let's verify what `get_contract_details` returns.
        details = await topstep_client.get_contract_details(t)
        if details:
            print(f"FOUND {t}:")
            print(details)
        else:
            print(f"NOT FOUND: {t}")

if __name__ == "__main__":
    asyncio.run(main())
