import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000/api"

async def test_fetch_contracts():
    async with httpx.AsyncClient() as client:
        print(f"Fetching contracts from {BASE_URL}/mappings/available-contracts ...")
        try:
            res = await client.get(f"{BASE_URL}/mappings/available-contracts", timeout=20)
            print(f"Status Code: {res.status_code}")
            if res.status_code == 200:
                data = res.json()
                print(f"Success! Got {len(data)} contracts.")
                if len(data) > 0:
                    print("First contract sample:", data[0])
            else:
                print("Error Response:", res.text)
        except Exception as e:
            print(f"Request Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_fetch_contracts())
