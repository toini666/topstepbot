from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, UniqueConstraint, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./topstepbot.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class TradeStatus(str):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


# =============================================================================
# GLOBAL SETTINGS
# =============================================================================

class Setting(Base):
    """Global key-value settings store."""
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String)  # Stored as JSON string or raw value


class TradingSession(Base):
    """Global trading session definitions (Asia, UK, US)."""
    __tablename__ = "trading_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # E.g., "ASIA", "UK", "US"
    display_name = Column(String)  # E.g., "Asian Session"
    start_time = Column(String)  # HH:MM format (Brussels TZ)
    end_time = Column(String)  # HH:MM format (Brussels TZ)
    is_active = Column(Boolean, default=True)  # Can disable a session
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


class TickerMap(Base):
    """Global ticker mapping table (TV ticker -> TopStep contract)."""
    __tablename__ = "ticker_maps"

    id = Column(Integer, primary_key=True, index=True)
    tv_ticker = Column(String, unique=True, index=True)
    ts_contract_id = Column(String)
    ts_ticker = Column(String)  # Human readable name mapping (e.g. MNQH6)
    tick_size = Column(Float)
    tick_value = Column(Float)
    micro_equivalent = Column(Integer, default=1)  # 1 for micro, 10 for mini contracts


# =============================================================================
# STRATEGY TEMPLATES (Global definitions)
# =============================================================================

class Strategy(Base):
    """Global strategy template - can be configured per-account."""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # Display Name
    tv_id = Column(String, unique=True, index=True)  # ID sent in Webhook 'strat'
    
    # Default values (can be overridden per-account in AccountStrategyConfig)
    default_risk_factor = Column(Float, default=1.0)  # Default multiplier
    default_allowed_sessions = Column(String, default="ASIA,UK,US")  # Comma-separated
    default_partial_tp_percent = Column(Float, default=50.0)  # % to reduce on partial
    default_move_sl_to_entry = Column(Boolean, default=True)  # Move SL to BE after partial
    default_allow_outside_sessions = Column(Boolean, default=False)  # Allow trading outside sessions
    
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    # Relationship to account configs
    account_configs = relationship("AccountStrategyConfig", back_populates="strategy", cascade="all, delete-orphan")


# =============================================================================
# ACCOUNT SETTINGS (Per-account configuration)
# =============================================================================

class AccountSettings(Base):
    """Per-account trading settings."""
    __tablename__ = "account_settings"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, unique=True, index=True)  # TopStep account ID
    account_name = Column(String, nullable=True)  # Cached account name for display
    trading_enabled = Column(Boolean, default=True)  # Master switch per account
    risk_per_trade = Column(Float, default=200.0)  # Account-specific risk amount ($)
    max_contracts = Column(Integer, default=50)  # Max micro-equivalent contracts allowed
    
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    # Relationship to strategy configs
    strategy_configs = relationship("AccountStrategyConfig", back_populates="account", cascade="all, delete-orphan")


class AccountStrategyConfig(Base):
    """Per-account strategy configuration with session restrictions."""
    __tablename__ = "account_strategy_configs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('account_settings.account_id'), index=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), index=True)
    
    enabled = Column(Boolean, default=True)  # Strategy enabled on this account
    risk_factor = Column(Float, default=1.0)  # Override factor for this account
    allowed_sessions = Column(String, default="ASIA,UK,US")  # Comma-separated session names
    partial_tp_percent = Column(Float, default=50.0)  # % to reduce on partial TP
    move_sl_to_entry = Column(Boolean, default=True)  # Move SL to BE after partial
    allow_outside_sessions = Column(Boolean, default=False)  # Allow trading outside sessions
    
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    # Relationships
    account = relationship("AccountSettings", back_populates="strategy_configs")
    strategy = relationship("Strategy", back_populates="account_configs")
    
    # Constraints: unique combo of account + strategy
    __table_args__ = (
        UniqueConstraint('account_id', 'strategy_id', name='uq_account_strategy'),
    )


# =============================================================================
# DISCORD NOTIFICATION SETTINGS
# =============================================================================

class DiscordNotificationSettings(Base):
    """Per-account Discord notification settings."""
    __tablename__ = "discord_notification_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, unique=True, index=True)
    
    # Global Discord settings
    enabled = Column(Boolean, default=False)
    webhook_url = Column(String, nullable=True)
    
    # Notification toggles
    notify_position_open = Column(Boolean, default=True)
    notify_position_close = Column(Boolean, default=True)
    notify_daily_summary = Column(Boolean, default=False)
    
    # Daily summary time (HH:MM format)
    daily_summary_time = Column(String, default="21:00")
    
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))


# =============================================================================
# TRADE TRACKING
# =============================================================================

class Trade(Base):
    """Local trade records for tracking positions opened by the bot."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, index=True)  # Which TopStep account
    ticker = Column(String, index=True)
    action = Column(String)  # BUY / SELL
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)  # NEW: Exit price for analytics
    sl = Column(Float)
    tp = Column(Float)
    quantity = Column(Integer)
    status = Column(String, default="PENDING")
    pnl = Column(Float, nullable=True)
    fees = Column(Float, nullable=True)  # NEW: Trading fees
    
    # Timeframe & Session tracking
    timeframe = Column(String, nullable=True)  # E.g., "M5", "H1", "D1"
    session = Column(String, nullable=True)  # NEW: Session at trade time (ASIA, UK, US)
    
    # Timestamps
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    exit_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # NEW: Trade duration for stats
    
    # Order tracking
    topstep_order_id = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)
    strategy = Column(String, default="default", nullable=True, index=True)


# =============================================================================
# LOGGING
# =============================================================================

class Log(Base):
    """System logs stored in database."""
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String)  # INFO, ERROR, WARNING
    message = Column(Text)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def seed_default_sessions(db_session):
    """Seed default trading sessions if they don't exist."""
    default_sessions = [
        {"name": "ASIA", "display_name": "Asian Session", "start_time": "00:00", "end_time": "08:59"},
        {"name": "UK", "display_name": "UK Session", "start_time": "09:00", "end_time": "15:29"},
        {"name": "US", "display_name": "US Session", "start_time": "15:30", "end_time": "21:59"},
    ]
    
    for session_data in default_sessions:
        existing = db_session.query(TradingSession).filter(TradingSession.name == session_data["name"]).first()
        if not existing:
            db_session.add(TradingSession(**session_data))
    
    db_session.commit()


def get_db():
    """Dependency for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
