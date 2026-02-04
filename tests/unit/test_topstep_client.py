"""
Tests for TopStep API client functionality.

These tests cover:
- Circuit breaker logic
- Rate limiting
- Retry with exponential backoff
- Response caching
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import httpx

from backend.constants import (
    CIRCUIT_BREAKER_COOLDOWN_SECONDS,
    API_TIMEOUT_SECONDS,
    CACHE_TTL_ACCOUNTS,
    CACHE_TTL_POSITIONS
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def fresh_client():
    """Create a fresh TopStepClient instance for testing."""
    with patch.dict('os.environ', {
        'TOPSTEP_URL': 'https://api.test.topstepx.com',
        'TOPSTEP_USERNAME': 'test_user',
        'TOPSTEP_APIKEY': 'test_api_key'
    }):
        from backend.services.topstep_client import TopStepClient
        client = TopStepClient()
        client.token = "test_token"  # Pre-set token to skip login
        return client


@pytest.fixture
def mock_httpx_response():
    """Factory for creating mock httpx responses."""
    def _create(status_code: int, json_data: dict = None, text: str = None):
        response = MagicMock()
        response.status_code = status_code
        if json_data is not None:
            response.json.return_value = json_data
        else:
            response.json.side_effect = Exception("No JSON")
        response.text = text or str(json_data)
        return response
    return _create


# =============================================================================
# TEST: CIRCUIT BREAKER
# =============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_activates_on_429(fresh_client, mock_httpx_response):
    """Circuit breaker should activate after receiving 429 rate limit error."""
    # Setup mock to return 429
    mock_response = mock_httpx_response(429, {"error": "Rate limit exceeded"})

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Make request that triggers 429
        result = await fresh_client._make_request(
            "POST",
            "https://api.test.topstepx.com/api/test",
            {"test": "data"},
            {"Authorization": "Bearer test_token"}
        )

        # Verify circuit breaker was activated
        assert fresh_client._rate_limit_until is not None
        assert fresh_client._rate_limit_until > datetime.now(timezone.utc)

        # Verify result indicates rate limiting
        data, status_code, success = result
        assert status_code == 429
        assert success is False


@pytest.mark.asyncio
async def test_circuit_breaker_blocks_subsequent_requests(fresh_client, mock_httpx_response):
    """Circuit breaker should block requests while active."""
    # Manually activate circuit breaker
    fresh_client._rate_limit_until = datetime.now(timezone.utc) + timedelta(seconds=60)

    # Attempt request - should be blocked without making HTTP call
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await fresh_client._make_request(
            "POST",
            "https://api.test.topstepx.com/api/test",
            {"test": "data"},
            {"Authorization": "Bearer test_token"}
        )

        # Verify no HTTP call was made
        mock_client_class.assert_not_called()

        # Verify result indicates blocked
        data, status_code, success = result
        assert status_code == 429
        assert success is False


@pytest.mark.asyncio
async def test_circuit_breaker_resets_on_success(fresh_client, mock_httpx_response):
    """Circuit breaker should reset after successful request."""
    # Setup circuit breaker state
    fresh_client._consecutive_errors = 3
    fresh_client._rate_limit_alert_sent = True

    # Setup mock for successful response
    mock_response = mock_httpx_response(200, {"success": True, "data": "test"})

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = await fresh_client._make_request(
            "POST",
            "https://api.test.topstepx.com/api/test",
            {"test": "data"},
            {"Authorization": "Bearer test_token"}
        )

        # Verify circuit breaker was reset
        assert fresh_client._consecutive_errors == 0
        assert fresh_client._rate_limit_alert_sent is False
        assert fresh_client._rate_limit_until is None

        # Verify success
        data, status_code, success = result
        assert success is True


@pytest.mark.asyncio
async def test_circuit_breaker_cooldown_duration(fresh_client, mock_httpx_response):
    """Circuit breaker cooldown should match configured duration."""
    mock_response = mock_httpx_response(429, {"error": "Rate limit"})

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        before = datetime.now(timezone.utc)
        await fresh_client._make_request(
            "POST",
            "https://api.test.topstepx.com/api/test",
            {},
            {}
        )
        after = datetime.now(timezone.utc)

        # Circuit breaker should be set ~60 seconds in future
        expected_earliest = before + timedelta(seconds=CIRCUIT_BREAKER_COOLDOWN_SECONDS - 1)
        expected_latest = after + timedelta(seconds=CIRCUIT_BREAKER_COOLDOWN_SECONDS + 1)

        assert fresh_client._rate_limit_until >= expected_earliest
        assert fresh_client._rate_limit_until <= expected_latest


# =============================================================================
# TEST: CACHING
# =============================================================================

@pytest.mark.asyncio
async def test_cache_returns_valid_data(fresh_client):
    """Cache should return data within TTL."""
    # Set cache with recent timestamp
    fresh_client._set_cache("accounts", [{"id": 1, "name": "Test"}])

    # Retrieve from cache
    data, is_valid = fresh_client._get_cached("accounts")

    assert is_valid is True
    assert data == [{"id": 1, "name": "Test"}]


@pytest.mark.asyncio
async def test_cache_expires_after_ttl(fresh_client):
    """Cache should expire after TTL."""
    # Set cache with old timestamp
    fresh_client._api_cache["accounts"] = (
        [{"id": 1, "name": "Test"}],
        datetime.now(timezone.utc) - timedelta(seconds=CACHE_TTL_ACCOUNTS + 5)
    )

    # Retrieve from cache
    data, is_valid = fresh_client._get_cached("accounts")

    assert is_valid is False


@pytest.mark.asyncio
async def test_cache_per_account(fresh_client):
    """Cache should be per-account for position data."""
    # Set cache for different accounts
    fresh_client._set_cache("positions", [{"id": 1}], account_id=1001)
    fresh_client._set_cache("positions", [{"id": 2}], account_id=1002)

    # Retrieve per account
    data1, valid1 = fresh_client._get_cached("positions", account_id=1001)
    data2, valid2 = fresh_client._get_cached("positions", account_id=1002)

    assert valid1 is True
    assert valid2 is True
    assert data1 == [{"id": 1}]
    assert data2 == [{"id": 2}]


@pytest.mark.asyncio
async def test_clear_cache_specific(fresh_client):
    """Clear cache should remove specific entry."""
    fresh_client._set_cache("accounts", [{"id": 1}])
    fresh_client._set_cache("positions", [{"id": 2}], account_id=1001)

    # Clear only positions for account 1001
    fresh_client.clear_cache("positions", account_id=1001)

    # Accounts cache should still be valid
    data_acc, valid_acc = fresh_client._get_cached("accounts")
    assert valid_acc is True

    # Positions cache for 1001 should be cleared
    data_pos, valid_pos = fresh_client._get_cached("positions", account_id=1001)
    assert valid_pos is False


@pytest.mark.asyncio
async def test_clear_cache_all(fresh_client):
    """Clear cache without args should clear everything."""
    fresh_client._set_cache("accounts", [{"id": 1}])
    fresh_client._set_cache("positions", [{"id": 2}], account_id=1001)

    fresh_client.clear_cache()

    assert len(fresh_client._api_cache) == 0


# =============================================================================
# TEST: RETRY LOGIC
# =============================================================================

@pytest.mark.asyncio
async def test_retry_on_timeout(fresh_client):
    """Should retry on timeout with exponential backoff."""
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.TimeoutException("Timeout")
        # Return success on 3rd attempt
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"success": True}
        return response

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = mock_request
        mock_client_class.return_value = mock_client

        result = await fresh_client._make_request(
            "POST",
            "https://api.test.topstepx.com/api/test",
            {},
            {},
            max_retries=5
        )

        # Should have retried and eventually succeeded
        assert call_count == 3
        data, status_code, success = result
        assert success is True


@pytest.mark.asyncio
async def test_retry_exhausted(fresh_client):
    """Should fail after all retries exhausted."""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value = mock_client

        result = await fresh_client._make_request(
            "POST",
            "https://api.test.topstepx.com/api/test",
            {},
            {},
            max_retries=3
        )

        # Should fail after retries
        data, status_code, success = result
        assert success is False


# =============================================================================
# TEST: ERROR HANDLING
# =============================================================================

@pytest.mark.asyncio
async def test_401_clears_token(fresh_client, mock_httpx_response):
    """401 response should clear the token."""
    fresh_client.token = "valid_token"
    mock_response = mock_httpx_response(401, {"error": "Unauthorized"})

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = await fresh_client._make_request(
            "POST",
            "https://api.test.topstepx.com/api/test",
            {},
            {"Authorization": "Bearer valid_token"}
        )

        # Token should be cleared
        assert fresh_client.token is None

        data, status_code, success = result
        assert status_code == 401
        assert success is False


@pytest.mark.asyncio
async def test_502_waits_and_retries(fresh_client, mock_httpx_response):
    """502 response should wait and retry (maintenance mode)."""
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        response = MagicMock()
        if call_count == 1:
            response.status_code = 502
            response.text = "Bad Gateway"
        else:
            response.status_code = 200
            response.json.return_value = {"success": True}
        return response

    with patch('httpx.AsyncClient') as mock_client_class, \
         patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = mock_request
        mock_client_class.return_value = mock_client

        result = await fresh_client._make_request(
            "POST",
            "https://api.test.topstepx.com/api/test",
            {},
            {},
            max_retries=3
        )

        # Should have waited 60s and retried
        assert call_count == 2
        mock_sleep.assert_called_with(60)

        data, status_code, success = result
        assert success is True


# =============================================================================
# TEST: GET METHODS WITH CACHING
# =============================================================================

@pytest.mark.asyncio
async def test_get_accounts_uses_cache(fresh_client, mock_httpx_response):
    """get_accounts should use cache when available."""
    cached_accounts = [{"id": 1001, "name": "CachedAccount"}]
    fresh_client._set_cache("accounts", cached_accounts)

    with patch('httpx.AsyncClient') as mock_client_class:
        result = await fresh_client.get_accounts(use_cache=True)

        # Should not make HTTP request
        mock_client_class.assert_not_called()

        assert result == cached_accounts


@pytest.mark.asyncio
async def test_get_accounts_bypasses_cache(fresh_client, mock_httpx_response):
    """get_accounts should bypass cache when use_cache=False."""
    cached_accounts = [{"id": 1001, "name": "CachedAccount"}]
    fresh_client._set_cache("accounts", cached_accounts)

    mock_response = mock_httpx_response(200, {
        "success": True,
        "accounts": [{"id": 2002, "name": "FreshAccount"}]
    })

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = await fresh_client.get_accounts(use_cache=False)

        # Should make HTTP request
        mock_client.post.assert_called_once()

        assert result == [{"id": 2002, "name": "FreshAccount"}]


@pytest.mark.asyncio
async def test_get_positions_caches_result(fresh_client, mock_httpx_response):
    """get_open_positions should cache the result."""
    mock_response = mock_httpx_response(200, {
        "success": True,
        "positions": [{"id": 1, "contractId": "MNQH6"}]
    })

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # First call
        result1 = await fresh_client.get_open_positions(1001)

        # Second call should use cache
        result2 = await fresh_client.get_open_positions(1001)

        # Only one HTTP call should have been made
        assert mock_client.post.call_count == 1

        assert result1 == result2


# =============================================================================
# TEST: CONSECUTIVE ERROR TRACKING
# =============================================================================

@pytest.mark.asyncio
async def test_consecutive_errors_increment(fresh_client, mock_httpx_response):
    """Consecutive errors should increment counter."""
    mock_response = mock_httpx_response(500, {"error": "Server Error"})

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        initial_errors = fresh_client._consecutive_errors

        await fresh_client._make_request("POST", "https://test.com/api", {}, {})

        assert fresh_client._consecutive_errors == initial_errors + 1


@pytest.mark.asyncio
async def test_consecutive_errors_reset_on_success(fresh_client, mock_httpx_response):
    """Consecutive errors should reset on successful request."""
    fresh_client._consecutive_errors = 5
    mock_response = mock_httpx_response(200, {"success": True})

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        await fresh_client._make_request("POST", "https://test.com/api", {}, {})

        assert fresh_client._consecutive_errors == 0
