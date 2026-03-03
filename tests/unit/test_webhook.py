"""
Unit tests for Webhook Alert Parsing

Tests the TradingViewAlert schema validation and parsing logic.
"""

import pytest
from pydantic import ValidationError


class TestTradingViewAlertSchema:
    """Tests for TradingView alert validation."""
    
    def test_valid_signal_alert(self):
        """Test parsing a valid SIGNAL alert."""
        from backend.schemas import TradingViewAlert
        
        alert = TradingViewAlert(
            ticker="MNQ1!",
            type="SIGNAL",
            side="BUY",
            entry=17500.25,
            stop=17495.00,
            tp=17510.00,
            strat="RobReversal",
            timeframe="5m"
        )
        
        assert alert.ticker == "MNQ1!"
        assert alert.type == "SIGNAL"
        assert alert.side == "BUY"
        assert alert.entry == 17500.25
        assert alert.stop == 17495.00
        assert alert.tp == 17510.00
        assert alert.strat == "RobReversal"
        assert alert.timeframe == "5m"
    
    def test_valid_close_alert(self):
        """Test parsing a valid CLOSE alert."""
        from backend.schemas import TradingViewAlert
        
        alert = TradingViewAlert(
            ticker="ES1!",
            type="CLOSE",
            side="BUY",  # Side from which to close
            entry=4500.00,
            strat="UTBot",
            timeframe="15m"
        )
        
        assert alert.type == "CLOSE"
        assert alert.ticker == "ES1!"
    
    def test_valid_partial_alert(self):
        """Test parsing a valid PARTIAL alert."""
        from backend.schemas import TradingViewAlert
        
        alert = TradingViewAlert(
            ticker="NQ1!",
            type="PARTIAL",
            side="SELL",
            entry=17800.00,
            stop=17810.00,  # New SL after partial
            tp=17780.00,    # New TP after partial
            strat="DeltaDiv",
            timeframe="7m"
        )
        
        assert alert.type == "PARTIAL"
    
    def test_valid_setup_alert(self):
        """Test parsing a valid SETUP alert (informational)."""
        from backend.schemas import TradingViewAlert
        
        alert = TradingViewAlert(
            ticker="CL1!",
            type="SETUP",
            side="BUY",
            entry=75.50,
            stop=74.50,
            tp=77.00,
            strat="OilSetup",
            timeframe="1h"
        )
        
        assert alert.type == "SETUP"
    
    def test_alert_missing_ticker_fails(self):
        """Test that missing ticker raises validation error."""
        from backend.schemas import TradingViewAlert
        
        with pytest.raises(ValidationError):
            TradingViewAlert(
                type="SIGNAL",
                side="BUY",
                entry=4500.00
            )
    
    def test_alert_missing_type_fails(self):
        """Test that missing type raises validation error."""
        from backend.schemas import TradingViewAlert
        
        with pytest.raises(ValidationError):
            TradingViewAlert(
                ticker="ES1!",
                side="BUY",
                entry=4500.00
            )
    
    def test_alert_side_variations(self):
        """Test that BUY/SELL and LONG/SHORT are all valid."""
        from backend.schemas import TradingViewAlert
        
        # BUY
        alert_buy = TradingViewAlert(
            ticker="ES1!", type="SIGNAL", side="BUY", entry=4500.00, timeframe="5m"
        )
        assert alert_buy.side.upper() in ["BUY", "LONG"]
        
        # SELL
        alert_sell = TradingViewAlert(
            ticker="ES1!", type="SIGNAL", side="SELL", entry=4500.00, timeframe="5m"
        )
        assert alert_sell.side.upper() in ["SELL", "SHORT"]
    
    def test_alert_optional_fields(self):
        """Test that optional fields can be omitted (except timeframe which is required)."""
        from backend.schemas import TradingViewAlert
        
        # Minimal valid alert (no stop, tp, strat but timeframe is required)
        alert = TradingViewAlert(
            ticker="ES1!",
            type="SIGNAL",
            side="BUY",
            entry=4500.00,
            timeframe="5m"
        )
        
        assert alert.stop is None or alert.stop == 0
        assert alert.tp is None or alert.tp == 0
        # strat defaults to "default" when not provided
        assert alert.strat == "default" or alert.strat is None

    def test_valid_movebe_alert(self):
        """Test parsing a valid MOVEBE alert (no stop/tp required)."""
        from backend.schemas import TradingViewAlert
        
        alert = TradingViewAlert(
            ticker="MNQ1!",
            type="MOVEBE",
            side="BUY",
            entry=20000.00,
            strat="rob_rev",
            timeframe="M5"
        )
        
        assert alert.type == "MOVEBE"
        assert alert.ticker == "MNQ1!"
        assert alert.stop is None
        assert alert.tp is None
        assert alert.strat == "rob_rev"
        assert alert.timeframe == "M5"


class TestAlertTypeRouting:
    """Tests for alert type routing logic."""
    
    def test_signal_type_normalized(self):
        """Test that signal type is case-insensitive."""
        from backend.schemas import TradingViewAlert
        
        alert_lower = TradingViewAlert(
            ticker="ES1!", type="signal", side="BUY", entry=4500.00, timeframe="5m"
        )
        alert_upper = TradingViewAlert(
            ticker="ES1!", type="SIGNAL", side="BUY", entry=4500.00, timeframe="5m"
        )
        
        assert alert_lower.type.upper() == "SIGNAL"
        assert alert_upper.type.upper() == "SIGNAL"
    
    def test_close_type_case_variations(self):
        """Test CLOSE type case handling."""
        from backend.schemas import TradingViewAlert
        
        for type_val in ["CLOSE", "close", "Close"]:
            alert = TradingViewAlert(
                ticker="ES1!", type=type_val, side="BUY", entry=4500.00, timeframe="5m"
            )
            assert alert.type.upper() == "CLOSE"

    def test_movebe_type_case_variations(self):
        """Test MOVEBE type case handling."""
        from backend.schemas import TradingViewAlert
        
        for type_val in ["MOVEBE", "movebe", "MoveBE"]:
            alert = TradingViewAlert(
                ticker="MNQ1!", type=type_val, side="BUY", entry=20000.00, timeframe="M5"
            )
            assert alert.type.upper() == "MOVEBE"


class TestIPVerification:
    """Tests for TradingView IP verification."""
    
    def test_tradingview_ips_defined(self):
        """Test that TradingView IPs are properly defined."""
        from backend.routers.webhook import TRADINGVIEW_IPS
        
        # TradingView has 4 official IPs
        assert len(TRADINGVIEW_IPS) == 4
        assert "52.89.214.238" in TRADINGVIEW_IPS
        assert "34.212.75.30" in TRADINGVIEW_IPS
        assert "54.218.53.128" in TRADINGVIEW_IPS
        assert "52.32.178.7" in TRADINGVIEW_IPS
    
    def test_localhost_ips_allowed(self):
        """Test that localhost IPs are defined for testing."""
        from backend.routers.webhook import LOCALHOST_IPS
        
        assert "127.0.0.1" in LOCALHOST_IPS
        assert "localhost" in LOCALHOST_IPS
        assert "::1" in LOCALHOST_IPS

