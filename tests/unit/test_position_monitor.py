"""
Tests for position monitoring job functionality.

These tests cover:
- Closed position detection
- Partial close detection
- Trade record creation and updates
- Orphaned order detection
- Reconciliation logic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

import pytz


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_topstep_client():
    """Create a mocked TopStep client."""
    client = AsyncMock()

    client.get_accounts.return_value = [
        {"id": 1001, "name": "TestAccount1"},
        {"id": 1002, "name": "TestAccount2"}
    ]

    client.get_open_positions.return_value = []
    client.get_orders.return_value = []
    client.get_historical_trades.return_value = []

    return client


@pytest.fixture
def mock_db_session():
    """Create a mocked DB session."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    return session


@pytest.fixture
def mock_telegram():
    """Create a mocked Telegram service."""
    return AsyncMock()


@pytest.fixture
def mock_discord():
    """Create a mocked Discord service."""
    return AsyncMock()


@pytest.fixture
def sample_position():
    """Sample open position data."""
    return {
        "id": 1,
        "contractId": "MNQH6",
        "symbolId": "MNQ",
        "type": 1,  # Long
        "size": 2,
        "averagePrice": 21000.0
    }


@pytest.fixture
def sample_trade():
    """Sample trade record."""
    trade = MagicMock()
    trade.id = 1
    trade.account_id = 1001
    trade.ticker = "MNQ1!"
    trade.action = "BUY"
    trade.entry_price = 21000.0
    trade.quantity = 2
    trade.status = "OPEN"
    trade.strategy = "TestStrategy"
    trade.timeframe = "5m"
    trade.timestamp = datetime.now(timezone.utc) - timedelta(hours=1)
    trade.exit_time = None
    trade.pnl = None
    trade.fees = None
    return trade


# =============================================================================
# TEST: POSITION CLOSURE DETECTION
# =============================================================================

@pytest.mark.asyncio
async def test_detects_full_position_closure(
    mock_topstep_client, mock_db_session, mock_telegram, mock_discord, sample_position, sample_trade
):
    """Should detect when a previously open position is now closed."""
    # Setup: Position was open in last poll
    from backend.jobs.state import update_account_positions, get_last_open_positions

    # Set initial state with position
    update_account_positions(1001, {"MNQH6": sample_position})

    # Now position is gone
    mock_topstep_client.get_open_positions.return_value = []

    # Mock historical trades for PnL
    mock_topstep_client.get_historical_trades.return_value = [
        {
            "contractId": "MNQH6",
            "price": 21020.0,
            "profitAndLoss": 100.0,
            "fees": 4.0,
            "creationTimestamp": datetime.now(timezone.utc).isoformat()
        }
    ]

    # Mock trade lookup
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = sample_trade

    with patch('backend.jobs.position_monitor.topstep_client', mock_topstep_client), \
         patch('backend.jobs.position_monitor.telegram_service', mock_telegram), \
         patch('backend.jobs.position_monitor.discord_service', mock_discord), \
         patch('backend.jobs.position_monitor.SessionLocal', return_value=mock_db_session):

        from backend.jobs.position_monitor import monitor_closed_positions_job

        await monitor_closed_positions_job()

        # Verify trade was updated to CLOSED
        assert sample_trade.status == "CLOSED"

        # Verify notification was sent
        mock_telegram.notify_position_closed.assert_called()


@pytest.mark.asyncio
async def test_detects_partial_position_close(
    mock_topstep_client, mock_db_session, mock_telegram, mock_discord, sample_position, sample_trade
):
    """Should detect when position size decreased (partial close)."""
    from backend.jobs.state import update_account_positions

    # Position was 2 contracts
    update_account_positions(1001, {"MNQH6": sample_position})

    # Now it's 1 contract
    reduced_position = sample_position.copy()
    reduced_position["size"] = 1
    mock_topstep_client.get_open_positions.return_value = [reduced_position]

    # Mock trade lookup
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = sample_trade

    with patch('backend.jobs.position_monitor.topstep_client', mock_topstep_client), \
         patch('backend.jobs.position_monitor.telegram_service', mock_telegram), \
         patch('backend.jobs.position_monitor.discord_service', mock_discord), \
         patch('backend.jobs.position_monitor.SessionLocal', return_value=mock_db_session):

        from backend.jobs.position_monitor import monitor_closed_positions_job

        await monitor_closed_positions_job()

        # Trade should still be OPEN (partial)
        assert sample_trade.status == "OPEN"

        # PnL should be updated
        # Note: Actual update depends on implementation details


@pytest.mark.asyncio
async def test_ignores_stable_position(
    mock_topstep_client, mock_db_session, mock_telegram, sample_position
):
    """Should not trigger notification for unchanged positions."""
    from backend.jobs.state import update_account_positions

    # Same position in both polls
    update_account_positions(1001, {"MNQH6": sample_position})
    mock_topstep_client.get_open_positions.return_value = [sample_position]

    with patch('backend.jobs.position_monitor.topstep_client', mock_topstep_client), \
         patch('backend.jobs.position_monitor.telegram_service', mock_telegram), \
         patch('backend.jobs.position_monitor.SessionLocal', return_value=mock_db_session):

        from backend.jobs.position_monitor import monitor_closed_positions_job

        await monitor_closed_positions_job()

        # No notification should be sent
        mock_telegram.notify_position_closed.assert_not_called()


# =============================================================================
# TEST: NEW POSITION DETECTION
# =============================================================================

@pytest.mark.asyncio
async def test_detects_new_position(
    mock_topstep_client, mock_db_session, mock_telegram, mock_discord, sample_position
):
    """Should detect when a new position is opened."""
    from backend.jobs.state import update_account_positions

    # No positions initially
    update_account_positions(1001, {})

    # New position appeared
    mock_topstep_client.get_open_positions.return_value = [sample_position]

    # Mock fill data
    mock_topstep_client.get_historical_trades.return_value = [
        {
            "contractId": "MNQH6",
            "price": 21000.0,
            "side": 0,  # Buy
            "size": 2,
            "creationTimestamp": datetime.now(timezone.utc).isoformat()
        }
    ]

    with patch('backend.jobs.position_monitor.topstep_client', mock_topstep_client), \
         patch('backend.jobs.position_monitor.telegram_service', mock_telegram), \
         patch('backend.jobs.position_monitor.discord_service', mock_discord), \
         patch('backend.jobs.position_monitor.SessionLocal', return_value=mock_db_session):

        from backend.jobs.position_monitor import monitor_closed_positions_job

        await monitor_closed_positions_job()

        # Notification should be sent for new position
        mock_telegram.notify_position_opened.assert_called()


# =============================================================================
# TEST: ORPHANED ORDERS DETECTION
# =============================================================================

@pytest.mark.asyncio
async def test_detects_orphaned_orders(
    mock_topstep_client, mock_db_session, mock_telegram
):
    """Should detect working orders with no matching position."""
    from backend.jobs.state import update_account_positions, set_last_orphans_ids

    # No positions
    update_account_positions(1001, {})
    set_last_orphans_ids(set())  # Clear previous orphans

    mock_topstep_client.get_open_positions.return_value = []

    # But there's a working order
    mock_topstep_client.get_orders.return_value = [
        {
            "id": 12345,
            "orderId": 12345,
            "contractId": "MNQH6",
            "status": 1,  # Working
            "side": "BUY",
            "price": 20900.0
        }
    ]

    with patch('backend.jobs.position_monitor.topstep_client', mock_topstep_client), \
         patch('backend.jobs.position_monitor.telegram_service', mock_telegram), \
         patch('backend.jobs.position_monitor.SessionLocal', return_value=mock_db_session):

        from backend.jobs.position_monitor import monitor_closed_positions_job

        await monitor_closed_positions_job()

        # Should notify about orphaned orders
        mock_telegram.notify_orphaned_orders.assert_called_once()


@pytest.mark.asyncio
async def test_no_duplicate_orphan_notification(
    mock_topstep_client, mock_db_session, mock_telegram
):
    """Should not send duplicate notification for same orphaned orders."""
    from backend.jobs.state import update_account_positions, set_last_orphans_ids

    update_account_positions(1001, {})

    # Already notified about this order
    set_last_orphans_ids({"12345"})

    mock_topstep_client.get_open_positions.return_value = []
    mock_topstep_client.get_orders.return_value = [
        {
            "id": 12345,
            "orderId": 12345,
            "contractId": "MNQH6",
            "status": 1
        }
    ]

    with patch('backend.jobs.position_monitor.topstep_client', mock_topstep_client), \
         patch('backend.jobs.position_monitor.telegram_service', mock_telegram), \
         patch('backend.jobs.position_monitor.SessionLocal', return_value=mock_db_session):

        from backend.jobs.position_monitor import monitor_closed_positions_job

        await monitor_closed_positions_job()

        # Should NOT notify again
        mock_telegram.notify_orphaned_orders.assert_not_called()


# =============================================================================
# TEST: DATE PARSING
# =============================================================================

def test_parse_topstep_date_standard():
    """Should parse standard ISO format dates."""
    from backend.jobs.position_monitor import parse_topstep_date

    result = parse_topstep_date("2025-02-04T14:30:00Z")

    assert result is not None
    assert result.year == 2025
    assert result.month == 2
    assert result.day == 4
    assert result.tzinfo is not None


def test_parse_topstep_date_with_microseconds():
    """Should handle non-standard microseconds (e.g., 5 digits)."""
    from backend.jobs.position_monitor import parse_topstep_date

    result = parse_topstep_date("2025-02-04T14:30:00.12345+00:00")

    assert result is not None
    assert result.tzinfo is not None


def test_parse_topstep_date_none():
    """Should return None for None input."""
    from backend.jobs.position_monitor import parse_topstep_date

    result = parse_topstep_date(None)

    assert result is None


def test_parse_topstep_date_invalid():
    """Should return None for invalid date strings."""
    from backend.jobs.position_monitor import parse_topstep_date

    result = parse_topstep_date("not-a-date")

    assert result is None


# =============================================================================
# TEST: TIMEZONE HANDLING
# =============================================================================

def test_ensure_aware_with_naive_datetime():
    """Should add UTC timezone to naive datetime."""
    from backend.jobs.position_monitor import ensure_aware

    naive_dt = datetime(2025, 2, 4, 14, 30, 0)
    result = ensure_aware(naive_dt)

    assert result.tzinfo is not None
    assert result.tzinfo == timezone.utc


def test_ensure_aware_with_aware_datetime():
    """Should keep existing timezone on aware datetime."""
    from backend.jobs.position_monitor import ensure_aware

    brussels_tz = pytz.timezone("Europe/Brussels")
    aware_dt = datetime(2025, 2, 4, 14, 30, 0, tzinfo=brussels_tz)
    result = ensure_aware(aware_dt)

    assert result.tzinfo == brussels_tz


def test_ensure_aware_with_none():
    """Should return None for None input."""
    from backend.jobs.position_monitor import ensure_aware

    result = ensure_aware(None)

    assert result is None


# =============================================================================
# TEST: RECONCILIATION LOGIC
# =============================================================================

@pytest.mark.asyncio
async def test_reconciliation_closes_orphan_db_trade(
    mock_topstep_client, mock_db_session, mock_telegram, sample_trade
):
    """Should close DB trades that are no longer open in API."""
    from backend.jobs.state import update_account_positions

    # No positions in API
    update_account_positions(1001, {})
    mock_topstep_client.get_open_positions.return_value = []

    # But trade is OPEN in DB
    sample_trade.status = "OPEN"

    # Mock ticker map
    ticker_map = MagicMock()
    ticker_map.ts_contract_id = "MNQH6"

    def query_side_effect(model):
        mock_q = MagicMock()
        if model.__name__ == "Trade":
            mock_q.filter.return_value.all.return_value = [sample_trade]
        elif model.__name__ == "TickerMap":
            mock_q.filter.return_value.first.return_value = ticker_map
        return mock_q

    mock_db_session.query.side_effect = query_side_effect

    # Mock historical trades showing exit
    mock_topstep_client.get_historical_trades.return_value = [
        {
            "contractId": "MNQH6",
            "price": 21020.0,
            "profitAndLoss": 100.0,
            "fees": 4.0,
            "creationTimestamp": datetime.now(timezone.utc).isoformat()
        }
    ]

    with patch('backend.jobs.position_monitor.topstep_client', mock_topstep_client), \
         patch('backend.jobs.position_monitor.telegram_service', mock_telegram), \
         patch('backend.jobs.position_monitor.SessionLocal', return_value=mock_db_session):

        from backend.jobs.position_monitor import monitor_closed_positions_job

        await monitor_closed_positions_job()

        # Trade should be marked as CLOSED
        assert sample_trade.status == "CLOSED"


# =============================================================================
# TEST: ERROR HANDLING
# =============================================================================

@pytest.mark.asyncio
async def test_continues_on_account_error(
    mock_topstep_client, mock_db_session, mock_telegram
):
    """Should continue processing other accounts if one fails."""
    call_count = 0

    async def positions_with_error(account_id):
        nonlocal call_count
        call_count += 1
        if account_id == 1001:
            raise Exception("API Error for account 1001")
        return []

    mock_topstep_client.get_open_positions.side_effect = positions_with_error

    with patch('backend.jobs.position_monitor.topstep_client', mock_topstep_client), \
         patch('backend.jobs.position_monitor.telegram_service', mock_telegram), \
         patch('backend.jobs.position_monitor.SessionLocal', return_value=mock_db_session):

        from backend.jobs.position_monitor import monitor_closed_positions_job

        # Should not raise
        await monitor_closed_positions_job()

        # Should have attempted both accounts
        assert call_count == 2


@pytest.mark.asyncio
async def test_notifies_on_critical_failure(
    mock_topstep_client, mock_db_session, mock_telegram
):
    """Should notify user if entire job fails."""
    mock_topstep_client.get_accounts.side_effect = Exception("Complete failure")

    with patch('backend.jobs.position_monitor.topstep_client', mock_topstep_client), \
         patch('backend.jobs.position_monitor.telegram_service', mock_telegram), \
         patch('backend.jobs.position_monitor.SessionLocal', return_value=mock_db_session):

        from backend.jobs.position_monitor import monitor_closed_positions_job

        # Should not raise
        await monitor_closed_positions_job()

        # Should have sent critical error notification
        mock_telegram.notify_critical_error.assert_called_once()
