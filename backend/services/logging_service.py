"""
Structured Logging Service

Provides consistent, structured logging across the application with:
- Component-based logging
- Trade context tracking
- Performance timing
- Both file and database logging
"""

import logging
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from functools import wraps
import time
import asyncio


# =============================================================================
# LOGGER SETUP
# =============================================================================

def setup_logger(name: str = "topstepbot", level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger with consistent formatting.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Console handler with structured format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


# Global logger instance
logger = setup_logger()


# =============================================================================
# STRUCTURED LOGGING HELPERS
# =============================================================================

class TradeContext:
    """Context manager for trade-related logging."""

    def __init__(
        self,
        ticker: str,
        action: str,
        account_id: int = None,
        strategy: str = None
    ):
        self.ticker = ticker
        self.action = action
        self.account_id = account_id
        self.strategy = strategy
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        logger.info(self._format_message("Starting trade execution"))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type:
            logger.error(self._format_message(f"Trade failed after {duration:.2f}s: {exc_val}"))
        else:
            logger.info(self._format_message(f"Trade completed in {duration:.2f}s"))

    def _format_message(self, message: str) -> str:
        parts = [f"[{self.ticker}]"]
        if self.action:
            parts.append(f"[{self.action}]")
        if self.account_id:
            parts.append(f"[Acct:{self.account_id}]")
        if self.strategy:
            parts.append(f"[{self.strategy}]")
        parts.append(message)
        return " ".join(parts)


def log_trade_event(
    event: str,
    ticker: str,
    account_id: int = None,
    account_name: str = None,
    strategy: str = None,
    extra: Dict[str, Any] = None,
    level: str = "INFO"
):
    """
    Log a trade-related event with structured context.

    Args:
        event: Event description
        ticker: Trading instrument
        account_id: Account ID
        account_name: Account display name
        strategy: Strategy name
        extra: Additional context data
        level: Log level
    """
    parts = [f"[{ticker}]"]
    if account_name:
        parts.append(f"[{account_name}]")
    elif account_id:
        parts.append(f"[Acct:{account_id}]")
    if strategy:
        parts.append(f"[{strategy}]")
    parts.append(event)

    if extra:
        extras = ", ".join(f"{k}={v}" for k, v in extra.items())
        parts.append(f"({extras})")

    message = " ".join(parts)

    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message)


def log_api_call(
    method: str,
    endpoint: str,
    account_id: int = None,
    status_code: int = None,
    duration_ms: float = None,
    cached: bool = False
):
    """
    Log an API call with performance data.

    Args:
        method: HTTP method
        endpoint: API endpoint
        account_id: Account ID if applicable
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        cached: Whether result was from cache
    """
    parts = [f"API {method} {endpoint}"]

    if account_id:
        parts.append(f"[Acct:{account_id}]")

    if cached:
        parts.append("[CACHED]")
    elif status_code:
        parts.append(f"[{status_code}]")

    if duration_ms:
        parts.append(f"({duration_ms:.0f}ms)")

    logger.debug(" ".join(parts))


def log_job_execution(job_name: str, duration_seconds: float, success: bool, error: str = None):
    """
    Log a scheduled job execution.

    Args:
        job_name: Name of the job
        duration_seconds: Execution duration
        success: Whether job succeeded
        error: Error message if failed
    """
    if success:
        logger.info(f"[JOB] {job_name} completed in {duration_seconds:.2f}s")
    else:
        logger.error(f"[JOB] {job_name} failed after {duration_seconds:.2f}s: {error}")


def log_risk_check(
    check_name: str,
    passed: bool,
    reason: str = None,
    account_id: int = None,
    ticker: str = None
):
    """
    Log a risk check result.

    Args:
        check_name: Name of the risk check
        passed: Whether check passed
        reason: Reason for result
        account_id: Account ID
        ticker: Ticker being checked
    """
    status = "PASS" if passed else "FAIL"
    parts = [f"[RISK] {check_name}: {status}"]

    if ticker:
        parts.append(f"[{ticker}]")
    if account_id:
        parts.append(f"[Acct:{account_id}]")
    if reason:
        parts.append(f"- {reason}")

    log_func = logger.debug if passed else logger.warning
    log_func(" ".join(parts))


# =============================================================================
# DECORATORS
# =============================================================================

def log_execution_time(func):
    """Decorator to log function execution time."""
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            logger.debug(f"[PERF] {func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(f"[PERF] {func.__name__} failed after {duration:.3f}s: {e}")
            raise

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            logger.debug(f"[PERF] {func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(f"[PERF] {func.__name__} failed after {duration:.3f}s: {e}")
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def log_exceptions(component: str = None):
    """
    Decorator to log exceptions with component context.

    Args:
        component: Component name for context
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                comp = component or func.__name__
                logger.error(f"[{comp}] Exception: {e}", exc_info=True)
                raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                comp = component or func.__name__
                logger.error(f"[{comp}] Exception: {e}", exc_info=True)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# =============================================================================
# DATABASE LOGGING (async-safe)
# =============================================================================

async def log_to_database(level: str, message: str, details: str = None):
    """
    Log to database asynchronously.

    Args:
        level: Log level (INFO, WARNING, ERROR)
        message: Log message
        details: Additional details
    """
    from backend.services.async_db import async_add_log
    await async_add_log(level, message, details)


def log_to_database_sync(level: str, message: str, details: str = None):
    """
    Log to database synchronously (for non-async contexts).

    Args:
        level: Log level
        message: Log message
        details: Additional details
    """
    from backend.database import SessionLocal, Log

    db = SessionLocal()
    try:
        db.add(Log(level=level, message=message, details=details))
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log to database: {e}")
    finally:
        db.close()
