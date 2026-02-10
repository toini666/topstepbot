"""
Unit tests for RiskEngine - Position sizing and validation logic.

Tests the core risk management calculations without needing
database or API connections.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestPositionSizing:
    """Tests for position size calculations."""
    
    def test_calculate_position_size_basic(self):
        """Test basic position size calculation."""
        from backend.services.risk_engine import RiskEngine
        
        db = MagicMock()
        engine = RiskEngine(db)
        
        # Given: Entry 4500, SL 4495, Risk $200, Tick 0.25, TickValue $1.25 (MNQ)
        # Distance: 5 points = 20 ticks @ $1.25 = $25 risk/contract
        # Expected: $200 / $25 = 8 contracts
        qty = engine.calculate_position_size(
            entry_price=4500.0,
            sl_price=4495.0,
            risk_amount=200.0,
            tick_size=0.25,
            tick_value=1.25
        )
        
        assert qty == 8
    
    def test_calculate_position_size_fractional(self):
        """Test position size rounds down."""
        from backend.services.risk_engine import RiskEngine
        
        db = MagicMock()
        engine = RiskEngine(db)
        
        # Given: Risk $100, tight stop that yields 2.5 contracts
        # Distance: 10 points = 40 ticks @ $1.25 = $50 risk/contract
        # Expected: $100 / $50 = 2 contracts (floor)
        qty = engine.calculate_position_size(
            entry_price=4500.0,
            sl_price=4490.0,
            risk_amount=100.0,
            tick_size=0.25,
            tick_value=1.25
        )
        
        assert qty == 2
    
    def test_calculate_position_size_zero_distance(self):
        """Test zero stop distance returns 0."""
        from backend.services.risk_engine import RiskEngine
        
        db = MagicMock()
        engine = RiskEngine(db)
        
        qty = engine.calculate_position_size(
            entry_price=4500.0,
            sl_price=4500.0,  # Same as entry
            risk_amount=200.0,
            tick_size=0.25,
            tick_value=1.25
        )
        
        assert qty == 0
    
    def test_calculate_position_size_zero_tick_size(self):
        """Test zero tick size returns 0."""
        from backend.services.risk_engine import RiskEngine
        
        db = MagicMock()
        engine = RiskEngine(db)
        
        qty = engine.calculate_position_size(
            entry_price=4500.0,
            sl_price=4495.0,
            risk_amount=200.0,
            tick_size=0.0,
            tick_value=1.25
        )
        
        assert qty == 0
    
    def test_calculate_position_size_wide_stop(self):
        """Test wide stop that exceeds risk returns 0."""
        from backend.services.risk_engine import RiskEngine
        
        db = MagicMock()
        engine = RiskEngine(db)
        
        # Given: Risk $50, stop 50 points away
        # Distance: 50 points = 200 ticks @ $1.25 = $250 risk/contract
        # Expected: $50 / $250 = 0.2 = 0 contracts
        qty = engine.calculate_position_size(
            entry_price=4500.0,
            sl_price=4450.0,
            risk_amount=50.0,
            tick_size=0.25,
            tick_value=1.25
        )
        
        assert qty == 0


class TestUnrealizedPnL:
    """Tests for unrealized PnL calculations."""
    
    def test_unrealized_pnl_long_profit(self):
        """Test unrealized PnL for profitable long."""
        from backend.services.risk_engine import calculate_unrealized_pnl
        
        # Long MNQ: entered 4500, now at 4510
        # +10 points = 40 ticks * $0.50 * 2 contracts = $40
        pnl = calculate_unrealized_pnl(
            entry_price=4500.0,
            current_price=4510.0,
            quantity=2,
            is_long=True,
            tick_size=0.25,
            tick_value=0.50
        )
        
        assert pnl == 40.0
    
    def test_unrealized_pnl_long_loss(self):
        """Test unrealized PnL for losing long."""
        from backend.services.risk_engine import calculate_unrealized_pnl
        
        # Long MNQ: entered 4500, now at 4490
        # -10 points = -40 ticks * $0.50 * 2 contracts = -$40
        pnl = calculate_unrealized_pnl(
            entry_price=4500.0,
            current_price=4490.0,
            quantity=2,
            is_long=True,
            tick_size=0.25,
            tick_value=0.50
        )
        
        assert pnl == -40.0
    
    def test_unrealized_pnl_short_profit(self):
        """Test unrealized PnL for profitable short."""
        from backend.services.risk_engine import calculate_unrealized_pnl
        
        # Short MNQ: entered 4500, now at 4490
        # +10 points down = 40 ticks * $0.50 * 2 contracts = $40
        pnl = calculate_unrealized_pnl(
            entry_price=4500.0,
            current_price=4490.0,
            quantity=2,
            is_long=False,
            tick_size=0.25,
            tick_value=0.50
        )
        
        assert pnl == 40.0
    
    def test_unrealized_pnl_short_loss(self):
        """Test unrealized PnL for losing short."""
        from backend.services.risk_engine import calculate_unrealized_pnl
        
        # Short MNQ: entered 4500, now at 4510
        # -10 points = -40 ticks * $0.50 * 2 contracts = -$40
        pnl = calculate_unrealized_pnl(
            entry_price=4500.0,
            current_price=4510.0,
            quantity=2,
            is_long=False,
            tick_size=0.25,
            tick_value=0.50
        )
        
        assert pnl == -40.0
    
    def test_unrealized_pnl_zero_tick_size(self):
        """Test zero tick size returns 0."""
        from backend.services.risk_engine import calculate_unrealized_pnl
        
        pnl = calculate_unrealized_pnl(
            entry_price=4500.0,
            current_price=4510.0,
            quantity=2,
            is_long=True,
            tick_size=0.0,
            tick_value=0.50
        )
        
        assert pnl == 0.0


class TestMarketHoursCheck:
    """Tests for market hours validation."""
    
    @patch('backend.services.risk_engine.datetime')
    def test_market_closed_before_open(self, mock_datetime):
        """Test market closed before open time."""
        from backend.services.risk_engine import RiskEngine
        from backend.services.timezone_service import get_user_tz
        from datetime import datetime, time

        # Mock 23:00 in user timezone (after 22:00 close)
        mock_now = datetime(2025, 2, 4, 23, 0, 0, tzinfo=get_user_tz())
        mock_datetime.now.return_value = mock_now
        
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        
        engine = RiskEngine(db)
        
        # Mock settings query
        with patch.object(engine, 'get_global_settings') as mock_settings:
            mock_settings.return_value = {
                "market_open_time": "00:00",
                "market_close_time": "22:00",
                "trading_days": ["MON", "TUE", "WED", "THU", "FRI"]
            }
            
            allowed, reason = engine.check_market_hours()
            
            assert not allowed
            assert "22:00" in reason or "closed" in reason.lower()
