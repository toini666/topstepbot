import asyncio
import os
from dotenv import load_dotenv

# Load env from .env file if present
load_dotenv()

from backend.services.topstep_client import topstep_client

async def main():
    print("Testing TopStep Client...")
    
    # 1. Login
    if not await topstep_client.login():
        print("Login Failed")
        return

    # 2. Get Quote for MNQ
    # We need to find the specific contract first?
    ticker = "MNQ"
    print(f"Resolving {ticker}...")
    contract_details = await topstep_client.get_contract_details(ticker)
    if not contract_details:
        print("Contract not found.")
        return
    
    print(f"Contract ID: {contract_details.get('id')}")
    print(f"Contract Name: {contract_details.get('name')}")
    
    # Inspect all keys to see if price is there
    # print(contract_details.keys())
    
    if 'lastPrice' in contract_details:
        print(f"Last Price found: {contract_details['lastPrice']}")
    elif 'price' in contract_details:
        print(f"Price found: {contract_details['price']}")
    else:
        print("No explicit price field found. Dumping partial keys:")
        # print(list(contract_details.keys()))

    await topstep_client.logout()

if __name__ == "__main__":
    asyncio.run(main())
