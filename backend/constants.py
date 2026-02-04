"""
Constants - Centralized configuration values for TopStepBot

This file consolidates all magic numbers and configuration constants
for easier maintenance and understanding of the codebase.
"""

# =============================================================================
# TOPSTEP API RATE LIMITS
# =============================================================================

# Rate limits from TopStep API documentation
RATE_LIMIT_HISTORY_BARS = 50  # POST /api/History/retrieveBars: 50 requests / 30 seconds
RATE_LIMIT_HISTORY_BARS_WINDOW = 30  # seconds

RATE_LIMIT_GENERAL = 200  # All other endpoints: 200 requests / 60 seconds
RATE_LIMIT_GENERAL_WINDOW = 60  # seconds

# Circuit breaker configuration
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 60
CIRCUIT_BREAKER_MAX_CONSECUTIVE_ERRORS = 3

# =============================================================================
# API TIMEOUTS & RETRIES
# =============================================================================

API_TIMEOUT_SECONDS = 15
API_MAX_RETRIES = 5
API_RETRY_BACKOFF_BASE = 1.0  # Base delay for exponential backoff
API_RETRY_BACKOFF_FACTOR = 2  # Multiplier for each retry

# Maintenance retry (502 errors)
API_MAINTENANCE_WAIT_SECONDS = 60

# =============================================================================
# ORDER TYPES (TopStep API Enum)
# =============================================================================

ORDER_TYPE_LIMIT = 1
ORDER_TYPE_MARKET = 2
ORDER_TYPE_STOP_LIMIT = 3
ORDER_TYPE_STOP = 4

# =============================================================================
# ORDER SIDE (TopStep API Enum)
# =============================================================================

ORDER_SIDE_BUY = 0  # Also represents "Long"
ORDER_SIDE_SELL = 1  # Also represents "Short"

# =============================================================================
# ORDER STATUS (TopStep API Enum)
# =============================================================================

ORDER_STATUS_WORKING = 1
ORDER_STATUS_FILLED = 2
ORDER_STATUS_CANCELED = 3
ORDER_STATUS_PENDING = 6
ORDER_STATUS_ACCEPTED = "Accepted"  # String variant

# Working statuses for filtering
ORDER_STATUS_WORKING_LIST = [1, 6, "Working", "Accepted"]

# =============================================================================
# POSITION TYPES (TopStep API Enum)
# =============================================================================

POSITION_TYPE_LONG = 1
POSITION_TYPE_SHORT = 2

# =============================================================================
# CACHE TTL (Time To Live in seconds)
# =============================================================================

CACHE_TTL_ACCOUNTS = 10
CACHE_TTL_POSITIONS = 5
CACHE_TTL_ORDERS = 5
CACHE_TTL_TRADES = 10
CACHE_TTL_PRICE = 5
CACHE_TTL_SETTINGS = 5  # For in-memory settings cache

# =============================================================================
# TIMING CONFIGURATIONS
# =============================================================================

# Delay before fetching PnL after partial close (wait for settlement)
PARTIAL_CLOSE_SETTLEMENT_DELAY = 4.0  # seconds

# Delay before fetching PnL after full close
FULL_CLOSE_SETTLEMENT_DELAY = 1.0  # seconds

# SL/TP order update retry delays
SL_TP_RETRY_INITIAL_DELAY = 0.3  # seconds
SL_TP_RETRY_SUBSEQUENT_DELAY = 0.5  # seconds
SL_TP_MAX_RETRIES = 3

# Rate limit delay between sequential API calls
RATE_LIMIT_DELAY_BETWEEN_CALLS = 0.1  # seconds

# Batch processing configuration
BATCH_SIZE_CANCEL_ORDERS = 10  # Max orders to cancel in parallel batch
BATCH_SIZE_CLOSE_POSITIONS = 5  # Max positions to close in parallel batch

# =============================================================================
# DATE/TIME FORMATS
# =============================================================================

TIMESTAMP_FORMAT_API = '%Y-%m-%dT%H:%M:%SZ'
TIME_FORMAT_DISPLAY = '%H:%M:%S'
DATE_FORMAT_DISPLAY = '%Y-%m-%d'

# =============================================================================
# DEFAULT VALUES
# =============================================================================

DEFAULT_RISK_PER_TRADE = 200.0
DEFAULT_MAX_CONTRACTS = 50
DEFAULT_TICK_SIZE = 0.25
DEFAULT_TICK_VALUE = 0.5
DEFAULT_MICRO_EQUIVALENT = 1

# Market hours defaults (Brussels timezone)
DEFAULT_MARKET_OPEN_TIME = "00:00"
DEFAULT_MARKET_CLOSE_TIME = "22:00"
DEFAULT_AUTO_FLATTEN_TIME = "21:55"

# Trading days defaults
DEFAULT_TRADING_DAYS = ["MON", "TUE", "WED", "THU", "FRI"]

# =============================================================================
# LOGGING & MONITORING
# =============================================================================

LOG_RETENTION_DAYS = 7
LOG_CLEANUP_TIME_UTC = "03:00"  # When to run cleanup

# Database backup time
DB_BACKUP_TIME_UTC = "03:00"

# Heartbeat interval
HEARTBEAT_INTERVAL_SECONDS = 60

# =============================================================================
# TRADE MATCHING TOLERANCES
# =============================================================================

# Time tolerance for matching trades (seconds)
TRADE_MATCH_TIME_TOLERANCE_SECONDS = 5

# Price tolerance for matching trades
TRADE_MATCH_PRICE_TOLERANCE = 0.01

# Duration for considering a trade "recently closed" (seconds)
RECENTLY_CLOSED_THRESHOLD_SECONDS = 120

# Lookback period for PnL aggregation (seconds)
PNL_AGGREGATION_LOOKBACK_SECONDS = 60

# =============================================================================
# PARALLEL PROCESSING LIMITS
# =============================================================================

# Maximum number of parallel API calls to respect rate limits
# General endpoints: 200 req/60s = ~3.3 req/s
# Safe batch size considering we need margin for other operations
MAX_PARALLEL_ACCOUNT_OPERATIONS = 5
MAX_PARALLEL_ORDER_OPERATIONS = 10  # With rate limit delay between batches

# =============================================================================
# TRADINGVIEW IP WHITELIST
# =============================================================================

TRADINGVIEW_IPS = [
    "52.89.214.238",
    "34.212.75.30",
    "54.218.53.128",
    "52.32.178.7"
]

LOCALHOST_IPS = ["127.0.0.1", "localhost", "::1"]
