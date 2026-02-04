"""
Pytest Fixtures and Configuration

Provides shared fixtures for database mocking, client mocking,
and other test utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture
def mock_db_session():
    """Provides a mocked SQLAlchemy session for unit tests."""
    session = MagicMock()
    session.query = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_setting_factory():
    """Factory to create mock Setting objects."""
    def _create(key: str, value: str):
        setting = MagicMock()
        setting.key = key
        setting.value = value
        return setting
    return _create


# =============================================================================
# API CLIENT FIXTURES
# =============================================================================

@pytest.fixture
def mock_topstep_client():
    """Provides a mocked TopStep API client."""
    client = AsyncMock()
    client.get_accounts = AsyncMock(return_value=[
        {"id": 123, "name": "Test Account", "balance": 50000, "simulated": True}
    ])
    client.get_open_positions = AsyncMock(return_value=[])
    client.get_orders = AsyncMock(return_value=[])
    client.get_historical_trades = AsyncMock(return_value=[])
    return client


# =============================================================================
# TIME FIXTURES
# =============================================================================

@pytest.fixture
def fixed_now():
    """Provides a fixed datetime for testing."""
    return datetime(2025, 2, 4, 14, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_datetime(fixed_now):
    """Mocks datetime.now() to return fixed_now."""
    with patch('datetime.datetime') as mock_dt:
        mock_dt.now.return_value = fixed_now
        mock_dt.fromisoformat = datetime.fromisoformat
        yield mock_dt


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_tradingview_alert():
    """Sample TradingView alert payload."""
    return {
        "ticker": "ES1!",
        "type": "SIGNAL",
        "side": "BUY",
        "entry": 4500.25,
        "stop": 4495.00,
        "tp": 4510.00,
        "strat": "RobReversal",
        "timeframe": "5m"
    }


@pytest.fixture
def sample_position():
    """Sample open position data."""
    return {
        "id": 1,
        "contractId": "CON123",
        "symbolId": "ES",
        "type": 1,  # Long
        "size": 2,
        "averagePrice": 4500.25,
        "unrealizedPnl": 150.00
    }


@pytest.fixture
def sample_trade():
    """Sample trade data from internal database."""
    trade = MagicMock()
    trade.id = 1
    trade.account_id = 123
    trade.ticker = "ES1!"
    trade.action = "BUY"
    trade.entry_price = 4500.25
    trade.quantity = 2
    trade.status = "OPEN"
    trade.strategy = "RobReversal"
    trade.timeframe = "5m"
    trade.timestamp = datetime(2025, 2, 4, 14, 0, 0, tzinfo=timezone.utc)
    return trade
