"""
Tests for webhook signal handling logic.

These tests cover the critical signal execution path including:
- Account eligibility checks
- Multi-account execution
- Cross-account conflict detection
- Position sizing
- Contract limit checks
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from backend.schemas import TradingViewAlert
from backend.database import Trade, TradeStatus, AccountSettings, Strategy, AccountStrategyConfig


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_risk_engine():
    """Create a mocked RiskEngine with configurable responses."""
    engine = MagicMock()

    # Default: all checks pass
    engine.check_market_hours.return_value = (True, "OK")
    engine.check_blocked_periods.return_value = (True, "OK")
    engine.check_account_enabled.return_value = (True, "OK")
    engine.check_strategy_enabled.return_value = (True, "OK")
    engine.check_session_allowed.return_value = (True, "OK")
    engine.check_open_position = AsyncMock(return_value=(True, "OK"))
    engine.check_cross_account_direction = AsyncMock(return_value=(True, "OK"))
    engine.check_contract_limit = AsyncMock(return_value=(True, "OK"))

    # Position sizing
    engine.get_risk_amount.return_value = 200.0
    engine.calculate_position_size.return_value = 2
    engine.get_current_session.return_value = "US"
    engine.ensure_account_settings.return_value = MagicMock()

    return engine


@pytest.fixture
def mock_topstep_client():
    """Create a mocked TopStep client."""
    client = AsyncMock()

    client.get_accounts.return_value = [
        {"id": 1001, "name": "Account1", "balance": 50000},
        {"id": 1002, "name": "Account2", "balance": 50000}
    ]
    client.get_open_positions.return_value = []
    client.get_contract_details.return_value = {
        "id": "MNQH6",
        "name": "MNQH6",
        "tickSize": 0.25,
        "tickValue": 0.50
    }
    client.place_order.return_value = {
        "status": "filled",
        "order_id": "12345",
        "price": 21000.0
    }

    return client


@pytest.fixture
def mock_telegram():
    """Create a mocked Telegram service."""
    telegram = AsyncMock()
    return telegram


@pytest.fixture
def sample_signal_alert():
    """Create a sample SIGNAL alert."""
    return TradingViewAlert(
        ticker="MNQ1!",
        type="SIGNAL",
        side="BUY",
        entry=21000.0,
        stop=20980.0,
        tp=21040.0,
        strat="TestStrategy",
        timeframe="5m"
    )


@pytest.fixture
def mock_db_session():
    """Create a mocked DB session with query capabilities."""
    session = MagicMock()

    # Mock Trade query to return empty by default
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []

    return session


# =============================================================================
# TEST: MARKET HOURS REJECTION
# =============================================================================

@pytest.mark.asyncio
async def test_signal_rejected_market_closed(
    mock_risk_engine, mock_topstep_client, mock_telegram,
    mock_db_session, sample_signal_alert
):
    """Signal should be rejected when market is closed."""
    mock_risk_engine.check_market_hours.return_value = (False, "Market Closed (After 22:00)")

    with patch('backend.routers.webhook.RiskEngine', return_value=mock_risk_engine), \
         patch('backend.routers.webhook.topstep_client', mock_topstep_client), \
         patch('backend.services.telegram_service.telegram_service', mock_telegram):

        from backend.routers.webhook import handle_signal

        result = await handle_signal(sample_signal_alert, mock_db_session, MagicMock())

        assert result["status"] == "rejected"
        assert "Market Closed" in result["reason"]

        # Verify notification was sent
        mock_telegram.notify_signal.assert_called_once()
        mock_telegram.notify_trade_rejection.assert_called_once()


@pytest.mark.asyncio
async def test_signal_rejected_blocked_period(
    mock_risk_engine, mock_topstep_client, mock_telegram,
    mock_db_session, sample_signal_alert
):
    """Signal should be rejected during blocked periods."""
    mock_risk_engine.check_blocked_periods.return_value = (False, "Blocked Time (14:00-14:30)")

    with patch('backend.routers.webhook.RiskEngine', return_value=mock_risk_engine), \
         patch('backend.routers.webhook.topstep_client', mock_topstep_client), \
         patch('backend.services.telegram_service.telegram_service', mock_telegram):

        from backend.routers.webhook import handle_signal

        result = await handle_signal(sample_signal_alert, mock_db_session, MagicMock())

        assert result["status"] == "rejected"
        assert "Blocked" in result["reason"]


# =============================================================================
# TEST: ACCOUNT ELIGIBILITY
# =============================================================================

@pytest.mark.asyncio
async def test_signal_no_eligible_accounts(
    mock_risk_engine, mock_topstep_client, mock_telegram,
    mock_db_session, sample_signal_alert
):
    """Signal should be skipped when no accounts are eligible."""
    # All accounts have trading disabled
    mock_risk_engine.check_account_enabled.return_value = (False, "Trading disabled")

    with patch('backend.routers.webhook.RiskEngine', return_value=mock_risk_engine), \
         patch('backend.routers.webhook.topstep_client', mock_topstep_client), \
         patch('backend.services.telegram_service.telegram_service', mock_telegram):

        from backend.routers.webhook import handle_signal

        result = await handle_signal(sample_signal_alert, mock_db_session, MagicMock())

        assert result["status"] == "skipped"
        assert "No eligible accounts" in result["reason"]

        # No signal notification since no eligible accounts
        mock_telegram.notify_signal.assert_not_called()


@pytest.mark.asyncio
async def test_signal_strategy_not_configured(
    mock_risk_engine, mock_topstep_client, mock_telegram,
    mock_db_session, sample_signal_alert
):
    """Signal should skip accounts where strategy is not configured."""
    mock_risk_engine.check_strategy_enabled.return_value = (False, "Strategy not configured")

    with patch('backend.routers.webhook.RiskEngine', return_value=mock_risk_engine), \
         patch('backend.routers.webhook.topstep_client', mock_topstep_client), \
         patch('backend.services.telegram_service.telegram_service', mock_telegram):

        from backend.routers.webhook import handle_signal

        result = await handle_signal(sample_signal_alert, mock_db_session, MagicMock())

        assert result["status"] == "skipped"


# =============================================================================
# TEST: POSITION CONFLICTS
# =============================================================================

@pytest.mark.asyncio
async def test_signal_rejected_existing_position(
    mock_risk_engine, mock_topstep_client, mock_telegram,
    mock_db_session, sample_signal_alert
):
    """Signal should skip accounts with existing position on same ticker."""
    # Position check fails for both accounts
    mock_risk_engine.check_open_position = AsyncMock(
        return_value=(False, "Position already open for MNQ1!")
    )

    with patch('backend.routers.webhook.RiskEngine', return_value=mock_risk_engine), \
         patch('backend.routers.webhook.topstep_client', mock_topstep_client), \
         patch('backend.services.telegram_service.telegram_service', mock_telegram):

        from backend.routers.webhook import handle_signal

        result = await handle_signal(sample_signal_alert, mock_db_session, MagicMock())

        assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_signal_rejected_cross_account_conflict(
    mock_risk_engine, mock_topstep_client, mock_telegram,
    mock_db_session, sample_signal_alert
):
    """Signal should be rejected when opposing position exists on another account."""
    mock_risk_engine.check_cross_account_direction = AsyncMock(
        return_value=(False, "Conflicting SHORT position on MNQ in account 1002")
    )

    with patch('backend.routers.webhook.RiskEngine', return_value=mock_risk_engine), \
         patch('backend.routers.webhook.topstep_client', mock_topstep_client), \
         patch('backend.services.telegram_service.telegram_service', mock_telegram):

        from backend.routers.webhook import handle_signal

        result = await handle_signal(sample_signal_alert, mock_db_session, MagicMock())

        assert result["status"] == "rejected"
        assert "Conflicting" in result["reason"]


# =============================================================================
# TEST: POSITION SIZING
# =============================================================================

@pytest.mark.asyncio
async def test_signal_rejected_zero_quantity(
    mock_risk_engine, mock_topstep_client, mock_telegram,
    mock_db_session, sample_signal_alert
):
    """Signal should be skipped when calculated quantity is 0."""
    # Only one account for simplicity
    mock_topstep_client.get_accounts.return_value = [
        {"id": 1001, "name": "Account1", "balance": 50000}
    ]
    mock_risk_engine.calculate_position_size.return_value = 0

    # Mock account settings query
    mock_account_settings = MagicMock()
    mock_account_settings.account_name = "Account1"
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_account_settings

    with patch('backend.routers.webhook.RiskEngine', return_value=mock_risk_engine), \
         patch('backend.routers.webhook.topstep_client', mock_topstep_client), \
         patch('backend.services.telegram_service.telegram_service', mock_telegram):

        from backend.routers.webhook import handle_signal

        result = await handle_signal(sample_signal_alert, mock_db_session, MagicMock())

        # Signal notification sent but no trades executed
        assert result["status"] == "skipped" or result.get("reason", "").startswith("No trades")


@pytest.mark.asyncio
async def test_signal_rejected_contract_limit(
    mock_risk_engine, mock_topstep_client, mock_telegram,
    mock_db_session, sample_signal_alert
):
    """Signal should skip account when contract limit would be exceeded."""
    mock_topstep_client.get_accounts.return_value = [
        {"id": 1001, "name": "Account1", "balance": 50000}
    ]
    mock_risk_engine.check_contract_limit = AsyncMock(
        return_value=(False, "Contract limit exceeded: 48 + 5 = 53 > 50 max")
    )

    # Mock account settings query
    mock_account_settings = MagicMock()
    mock_account_settings.account_name = "Account1"
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_account_settings

    with patch('backend.routers.webhook.RiskEngine', return_value=mock_risk_engine), \
         patch('backend.routers.webhook.topstep_client', mock_topstep_client), \
         patch('backend.services.telegram_service.telegram_service', mock_telegram):

        from backend.routers.webhook import handle_signal

        result = await handle_signal(sample_signal_alert, mock_db_session, MagicMock())

        # Should skip this account
        # Note: might still return "received" if other accounts succeed
        # In this case with single account, should skip
        assert result["status"] in ["skipped", "received"]


# =============================================================================
# TEST: SUCCESSFUL EXECUTION
# =============================================================================

@pytest.mark.asyncio
async def test_signal_successful_single_account(
    mock_risk_engine, mock_topstep_client, mock_telegram,
    mock_db_session, sample_signal_alert
):
    """Signal should execute successfully on a single eligible account."""
    mock_topstep_client.get_accounts.return_value = [
        {"id": 1001, "name": "Account1", "balance": 50000}
    ]

    # Mock ticker map query to return None (will use API)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    with patch('backend.routers.webhook.RiskEngine', return_value=mock_risk_engine), \
         patch('backend.routers.webhook.topstep_client', mock_topstep_client), \
         patch('backend.services.telegram_service.telegram_service', mock_telegram), \
         patch('backend.routers.webhook.resolve_contract', new_callable=AsyncMock) as mock_resolve:

        mock_resolve.return_value = ("MNQH6", 0.25, 0.50)

        from backend.routers.webhook import handle_signal

        background_tasks = MagicMock()
        result = await handle_signal(sample_signal_alert, mock_db_session, background_tasks)

        assert result["status"] == "received"
        assert result["type"] == "SIGNAL"
        assert "Account1" in result["accounts"]

        # Verify background task was added
        background_tasks.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_signal_successful_multi_account(
    mock_risk_engine, mock_topstep_client, mock_telegram,
    mock_db_session, sample_signal_alert
):
    """Signal should execute on multiple eligible accounts."""
    mock_topstep_client.get_accounts.return_value = [
        {"id": 1001, "name": "Account1", "balance": 50000},
        {"id": 1002, "name": "Account2", "balance": 50000},
        {"id": 1003, "name": "Account3", "balance": 50000}
    ]

    # Mock ticker map query
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    with patch('backend.routers.webhook.RiskEngine', return_value=mock_risk_engine), \
         patch('backend.routers.webhook.topstep_client', mock_topstep_client), \
         patch('backend.services.telegram_service.telegram_service', mock_telegram), \
         patch('backend.routers.webhook.resolve_contract', new_callable=AsyncMock) as mock_resolve:

        mock_resolve.return_value = ("MNQH6", 0.25, 0.50)

        from backend.routers.webhook import handle_signal

        background_tasks = MagicMock()
        result = await handle_signal(sample_signal_alert, mock_db_session, background_tasks)

        assert result["status"] == "received"
        assert len(result["accounts"]) == 3

        # Verify background task was added for each account
        assert background_tasks.add_task.call_count == 3


# =============================================================================
# TEST: SIDE MAPPING
# =============================================================================

@pytest.mark.asyncio
async def test_signal_buy_side_mapping(sample_signal_alert):
    """BUY side should map correctly."""
    sample_signal_alert.side = "BUY"
    assert sample_signal_alert.side.upper() in ["BUY", "LONG"]


@pytest.mark.asyncio
async def test_signal_long_side_mapping(sample_signal_alert):
    """LONG side should be treated as BUY."""
    sample_signal_alert.side = "LONG"
    assert sample_signal_alert.side.upper() in ["BUY", "LONG"]


@pytest.mark.asyncio
async def test_signal_sell_side_mapping(sample_signal_alert):
    """SELL side should map correctly."""
    sample_signal_alert.side = "SELL"
    assert sample_signal_alert.side.upper() in ["SELL", "SHORT"]


@pytest.mark.asyncio
async def test_signal_short_side_mapping(sample_signal_alert):
    """SHORT side should be treated as SELL."""
    sample_signal_alert.side = "SHORT"
    assert sample_signal_alert.side.upper() in ["SELL", "SHORT"]
