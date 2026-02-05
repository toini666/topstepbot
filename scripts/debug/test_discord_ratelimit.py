import asyncio
import httpx
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.discord_service import discord_service

async def test_retry_logic():
    print("🧪 Starting Discord Rate Limit Test...")
    
    # Mock URL
    url = "https://discord.com/api/webhooks/TEST"
    
    # Simulate: 1st call -> 429 error, 2nd call -> 200 OK
    mock_response_429 = MagicMock()
    mock_response_429.status_code = 429
    mock_response_429.headers = {"Retry-After": "1.5"}
    
    mock_response_success = MagicMock()
    mock_response_success.status_code = 204
    
    mock_client = AsyncMock()
    # Chain responses: first calls return 429, last one success
    mock_client.post.side_effect = [mock_response_429, mock_response_success]
    
    # Patch httpx.AsyncClient to return our mock
    with patch("httpx.AsyncClient", return_value=mock_client):
        # We need __aenter__ and __aexit__ for the context manager
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        start_time = asyncio.get_running_loop().time()
        
        success = await discord_service.send_message(url, "Test Message")
        
        end_time = asyncio.get_running_loop().time()
        duration = end_time - start_time
        
        print("\n📝 Results:")
        print(f"Success: {success}")
        print(f"Call Count: {mock_client.post.call_count}")
        print(f"Duration: {duration:.2f}s (Should be > 1.5s)")
        
        if success and mock_client.post.call_count == 2 and duration >= 1.5:
            print("✅ TEST PASSED: Retry logic worked correctly!")
        else:
            print("❌ TEST FAILED: Logic did not retry correctly.")

if __name__ == "__main__":
    asyncio.run(test_retry_logic())
