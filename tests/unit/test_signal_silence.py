"""
Unit tests for the signal silence detector.

This monitor is the only thing that catches a broken TradingView -> bot delivery
path: the tunnel answers every probe while TradingView cannot reach it, so a
reachability check sees nothing wrong. A false "recovered" from this monitor is
therefore worse than no monitor at all - it tells the operator the outage is over.

On 26/08/2026 it did exactly that: it announced "signals are arriving again" after
15h of total silence, because it anchored on heartbeat_state["start_time"], which
heartbeat_job resets whenever a heartbeat gap looks like a sleep/wake.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _log_at(timestamp):
    """A Log row double carrying only what the detector reads."""
    row = MagicMock()
    row.timestamp = timestamp
    return row


def _db_returning(last_webhook_at):
    """Session double: no silence_hours setting, one Webhook log row."""
    db = MagicMock()
    setting_query = MagicMock()
    setting_query.filter.return_value.first.return_value = None
    log_query = MagicMock()
    log_query.filter.return_value.order_by.return_value.first.return_value = (
        _log_at(last_webhook_at) if last_webhook_at else None
    )

    def query(model):
        return setting_query if model.__name__ == "Setting" else log_query

    db.query.side_effect = query
    return db


@pytest.fixture
def silent_for_15h():
    """Now, and a last alert 15h earlier - well past the 12h default threshold."""
    now = datetime(2026, 8, 26, 11, 8, 52)
    return now, now - timedelta(hours=15)


class TestSignalSilenceAnchor:
    """The anchor must not move unless an alert actually arrives."""

    async def test_heartbeat_reset_does_not_fake_a_recovery(self, silent_for_15h):
        """
        The regression: heartbeat_job resets its own start_time on a sleep/wake gap.
        The detector must ignore that entirely and keep reporting the silence.
        """
        from backend.jobs import health_checks, state

        now, last_webhook = silent_for_15h
        state.update_signal_silence_state(
            notified=True, monitor_started_at=last_webhook - timedelta(hours=2)
        )
        # heartbeat_job just decided the machine woke up and reset its clock to now
        state.update_heartbeat_state(start_time=now)

        db = _db_returning(last_webhook)
        telegram = AsyncMock()

        with patch.object(health_checks, "SessionLocal", return_value=db), \
             patch.object(health_checks, "now_utc", return_value=now), \
             patch.object(health_checks, "telegram_service", telegram), \
             patch("backend.services.risk_engine.RiskEngine") as risk_engine:
            risk_engine.return_value.check_market_hours.return_value = (True, "open")
            await health_checks.signal_silence_check_job()

        telegram.send_message.assert_not_awaited()
        assert state.get_signal_silence_state()["notified"] is True

    async def test_recovery_still_fires_when_an_alert_arrives(self, silent_for_15h):
        """The fix must not mute a genuine recovery."""
        from backend.jobs import health_checks, state

        now, _ = silent_for_15h
        state.update_signal_silence_state(
            notified=True, monitor_started_at=now - timedelta(hours=20)
        )
        state.update_heartbeat_state(start_time=now - timedelta(hours=20))

        db = _db_returning(now - timedelta(minutes=3))
        telegram = AsyncMock()

        with patch.object(health_checks, "SessionLocal", return_value=db), \
             patch.object(health_checks, "now_utc", return_value=now), \
             patch.object(health_checks, "telegram_service", telegram), \
             patch("backend.services.risk_engine.RiskEngine") as risk_engine:
            risk_engine.return_value.check_market_hours.return_value = (True, "open")
            await health_checks.signal_silence_check_job()

        telegram.send_message.assert_awaited_once()
        assert "arriving again" in telegram.send_message.await_args.args[0]
        assert state.get_signal_silence_state()["notified"] is False

    async def test_silence_is_reported_when_threshold_is_crossed(self, silent_for_15h):
        """The warning itself must still fire on a real outage."""
        from backend.jobs import health_checks, state

        now, last_webhook = silent_for_15h
        state.update_signal_silence_state(
            notified=False, monitor_started_at=last_webhook - timedelta(hours=2)
        )

        db = _db_returning(last_webhook)
        telegram = AsyncMock()

        with patch.object(health_checks, "SessionLocal", return_value=db), \
             patch.object(health_checks, "now_utc", return_value=now), \
             patch.object(health_checks, "telegram_service", telegram), \
             patch("backend.services.risk_engine.RiskEngine") as risk_engine:
            risk_engine.return_value.check_market_hours.return_value = (True, "open")
            await health_checks.signal_silence_check_job()

        telegram.send_message.assert_awaited_once()
        assert "No signal received" in telegram.send_message.await_args.args[0]
        assert state.get_signal_silence_state()["notified"] is True

    async def test_raising_the_threshold_does_not_fake_a_recovery(self, silent_for_15h):
        """
        The second door onto the same lie: the operator raises signal_silence_hours
        from the dashboard, the computed silence drops under it, and nothing arrived.
        """
        from backend.jobs import health_checks, state

        now, last_webhook = silent_for_15h
        state.update_signal_silence_state(
            notified=True,
            webhook_at_warning=last_webhook,  # what we saw when we warned
            monitor_started_at=last_webhook - timedelta(hours=2),
        )

        db = _db_returning(last_webhook)  # unchanged: still no new alert
        telegram = AsyncMock()

        with patch.object(health_checks, "SessionLocal", return_value=db), \
             patch.object(health_checks, "now_utc", return_value=now), \
             patch.object(health_checks, "telegram_service", telegram), \
             patch.object(health_checks, "DEFAULT_SIGNAL_SILENCE_HOURS", 18), \
             patch("backend.services.risk_engine.RiskEngine") as risk_engine:
            risk_engine.return_value.check_market_hours.return_value = (True, "open")
            await health_checks.signal_silence_check_job()

        telegram.send_message.assert_not_awaited()
        # the episode flag still clears, so a later crossing can warn again
        assert state.get_signal_silence_state()["notified"] is False

    async def test_recovery_needs_an_alert_newer_than_the_warning(self, silent_for_15h):
        """A newer alert than the one seen at warning time is what proves reception."""
        from backend.jobs import health_checks, state

        now, last_webhook = silent_for_15h
        state.update_signal_silence_state(
            notified=True,
            webhook_at_warning=last_webhook,
            monitor_started_at=last_webhook - timedelta(hours=2),
        )

        db = _db_returning(now - timedelta(minutes=2))  # a genuinely newer alert
        telegram = AsyncMock()

        with patch.object(health_checks, "SessionLocal", return_value=db), \
             patch.object(health_checks, "now_utc", return_value=now), \
             patch.object(health_checks, "telegram_service", telegram), \
             patch("backend.services.risk_engine.RiskEngine") as risk_engine:
            risk_engine.return_value.check_market_hours.return_value = (True, "open")
            await health_checks.signal_silence_check_job()

        telegram.send_message.assert_awaited_once()
        assert "arriving again" in telegram.send_message.await_args.args[0]

    async def test_warning_records_the_alert_it_saw(self, silent_for_15h):
        """Without this bookkeeping the recovery check has nothing to compare against."""
        from backend.jobs import health_checks, state

        now, last_webhook = silent_for_15h
        state.update_signal_silence_state(
            notified=False, webhook_at_warning=None,
            monitor_started_at=last_webhook - timedelta(hours=2),
        )

        db = _db_returning(last_webhook)

        with patch.object(health_checks, "SessionLocal", return_value=db), \
             patch.object(health_checks, "now_utc", return_value=now), \
             patch.object(health_checks, "telegram_service", AsyncMock()), \
             patch("backend.services.risk_engine.RiskEngine") as risk_engine:
            risk_engine.return_value.check_market_hours.return_value = (True, "open")
            await health_checks.signal_silence_check_job()

        assert state.get_signal_silence_state()["webhook_at_warning"] == last_webhook

    async def test_a_fresh_restart_is_never_reported_as_silence(self):
        """Anchoring on process start is the behaviour we keep - just on our own field."""
        from backend.jobs import health_checks, state

        now = datetime(2026, 8, 26, 11, 8, 52)
        state.update_signal_silence_state(
            notified=False, monitor_started_at=now - timedelta(minutes=5)
        )

        db = _db_returning(now - timedelta(hours=30))  # last alert is ancient
        telegram = AsyncMock()

        with patch.object(health_checks, "SessionLocal", return_value=db), \
             patch.object(health_checks, "now_utc", return_value=now), \
             patch.object(health_checks, "telegram_service", telegram), \
             patch("backend.services.risk_engine.RiskEngine") as risk_engine:
            risk_engine.return_value.check_market_hours.return_value = (True, "open")
            await health_checks.signal_silence_check_job()

        telegram.send_message.assert_not_awaited()
