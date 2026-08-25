"""
Unit tests for the asynchronous webhook handoff.

TradingView cancels any webhook that takes longer than 3 seconds, so the
endpoint must acknowledge immediately and execute the alert afterwards.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks

from backend.schemas import TradingViewAlert


def _make_request(ip: str = "127.0.0.1") -> MagicMock:
    """Minimal Request double that passes verify_tradingview_ip."""
    request = MagicMock()
    request.client.host = ip
    request.headers.get.return_value = None
    return request


@pytest.fixture
def signal_alert(sample_tradingview_alert):
    return TradingViewAlert(**sample_tradingview_alert)


@pytest.fixture
def close_alert():
    return TradingViewAlert(
        ticker="ES1!", type="CLOSE", side="BUY", entry=4500.00, timeframe="5m"
    )


class TestWebhookAcknowledgement:
    """The endpoint must answer TradingView before doing any work."""

    async def test_returns_accepted_without_running_handler(self, signal_alert, mock_db_session):
        from backend.routers import webhook

        webhook._signal_cache.clear()
        background_tasks = BackgroundTasks()

        with patch.object(webhook, "handle_signal", new=AsyncMock()) as handler:
            result = await webhook.receive_webhook(
                _make_request(), signal_alert, background_tasks, mock_db_session
            )

        assert result["status"] == "accepted"
        assert result["type"] == "SIGNAL"
        handler.assert_not_awaited()

    async def test_queues_processing_as_background_task(self, signal_alert, mock_db_session):
        from backend.routers import webhook

        webhook._signal_cache.clear()
        background_tasks = BackgroundTasks()

        await webhook.receive_webhook(
            _make_request(), signal_alert, background_tasks, mock_db_session
        )

        assert len(background_tasks.tasks) == 1
        assert background_tasks.tasks[0].func is webhook.process_alert

    async def test_reception_is_logged_before_responding(self, signal_alert, mock_db_session):
        from backend.routers import webhook

        webhook._signal_cache.clear()

        await webhook.receive_webhook(
            _make_request(), signal_alert, BackgroundTasks(), mock_db_session
        )

        assert mock_db_session.add.called
        assert mock_db_session.commit.called

    async def test_duplicate_still_short_circuits(self, signal_alert, mock_db_session):
        from backend.routers import webhook

        webhook._signal_cache.clear()
        background_tasks = BackgroundTasks()

        first = await webhook.receive_webhook(
            _make_request(), signal_alert, background_tasks, mock_db_session
        )
        second = await webhook.receive_webhook(
            _make_request(), signal_alert, background_tasks, mock_db_session
        )

        assert first["status"] == "accepted"
        assert second["status"] == "ignored"
        assert len(background_tasks.tasks) == 1


class TestProcessAlert:
    """process_alert runs after the response and owns its own session."""

    async def test_dispatches_to_close_handler(self, close_alert, mock_db_session):
        from backend.routers import webhook

        with patch.object(webhook, "SessionLocal", return_value=mock_db_session), \
             patch.object(webhook, "handle_close", new=AsyncMock()) as handler:
            await webhook.process_alert(close_alert)

        handler.assert_awaited_once()
        mock_db_session.close.assert_called_once()

    async def test_runs_tasks_deferred_by_handler(self, signal_alert, mock_db_session):
        """handle_signal queues execute_trade; FastAPI will not run it for us."""
        from backend.routers import webhook

        executed = []

        async def fake_handle_signal(alert, db, background_tasks):
            background_tasks.add_task(lambda: executed.append("execute_trade"))
            return {"status": "received"}

        with patch.object(webhook, "SessionLocal", return_value=mock_db_session), \
             patch.object(webhook, "handle_signal", new=fake_handle_signal):
            await webhook.process_alert(signal_alert)

        assert executed == ["execute_trade"]

    async def test_failure_is_logged_and_notified(self, signal_alert, mock_db_session):
        """A background failure is invisible to TradingView, so it must be loud."""
        from backend.routers import webhook

        telegram = AsyncMock()

        with patch.object(webhook, "SessionLocal", return_value=mock_db_session), \
             patch.object(webhook, "handle_signal", new=AsyncMock(side_effect=RuntimeError("boom"))), \
             patch("backend.services.telegram_service.telegram_service", telegram):
            await webhook.process_alert(signal_alert)

        mock_db_session.rollback.assert_called_once()
        logged = mock_db_session.add.call_args[0][0]
        assert logged.level == "ERROR"
        telegram.send_message.assert_awaited_once()
        mock_db_session.close.assert_called_once()
