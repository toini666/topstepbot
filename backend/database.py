from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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

class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    action = Column(String)  # BUY / SELL
    entry_price = Column(Float)
    sl = Column(Float)
    tp = Column(Float)
    quantity = Column(Integer)
    status = Column(String, default="PENDING")
    pnl = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    exit_time = Column(DateTime, nullable=True)
    topstep_order_id = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)

class TickerMap(Base):
    __tablename__ = "ticker_maps"

    id = Column(Integer, primary_key=True, index=True)
    tv_ticker = Column(String, unique=True, index=True)
    ts_contract_id = Column(String)
    ts_ticker = Column(String) # Human readable name mapping (e.g. MNQH6)
    tick_size = Column(Float)
    tick_value = Column(Float)

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String)  # INFO, ERROR, WARNING
    message = Column(Text)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String) # Stored as JSON string or raw value

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
