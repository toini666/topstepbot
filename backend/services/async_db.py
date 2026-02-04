"""
Async Database Utilities

Provides wrappers to run synchronous database operations
in an executor to avoid blocking the async event loop.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps, partial
from typing import TypeVar, Callable, Any

from backend.database import SessionLocal

# Thread pool for database operations
_db_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="db_worker")

T = TypeVar('T')


async def run_in_executor(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a synchronous function in the database thread pool.

    This prevents blocking the async event loop when performing
    database operations.

    Args:
        func: Synchronous function to run
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        The function's return value
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _db_executor,
        partial(func, *args, **kwargs)
    )


def async_db_session(func):
    """
    Decorator that provides a database session to async functions.

    Creates a session in a thread pool worker, executes the function,
    and properly closes the session.

    Usage:
        @async_db_session
        def my_db_operation(db):
            return db.query(Model).all()

        # Call as async
        result = await my_db_operation()
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        def run_with_session():
            db = SessionLocal()
            try:
                return func(db, *args, **kwargs)
            finally:
                db.close()

        return await run_in_executor(run_with_session)

    return wrapper


class AsyncDBContext:
    """
    Async context manager for database sessions.

    Usage:
        async with AsyncDBContext() as db:
            result = db.query(Model).all()
    """

    def __init__(self):
        self._db = None
        self._loop = None

    async def __aenter__(self):
        self._loop = asyncio.get_event_loop()
        self._db = await self._loop.run_in_executor(_db_executor, SessionLocal)
        return self._db

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._db:
            await self._loop.run_in_executor(_db_executor, self._db.close)


async def execute_db_query(query_func: Callable, *args, **kwargs) -> Any:
    """
    Execute a database query function asynchronously.

    Automatically handles session creation and cleanup.

    Args:
        query_func: Function that takes (session, *args, **kwargs) and returns result
        *args: Additional arguments
        **kwargs: Additional keyword arguments

    Returns:
        Query result
    """
    def run_query():
        db = SessionLocal()
        try:
            return query_func(db, *args, **kwargs)
        finally:
            db.close()

    return await run_in_executor(run_query)


# Common async database operations

async def async_get_by_id(model_class, id_value: int) -> Any:
    """Get a model instance by ID asynchronously."""
    def query(db):
        return db.query(model_class).filter(model_class.id == id_value).first()

    return await execute_db_query(query)


async def async_get_all(model_class, filters: dict = None, limit: int = None) -> list:
    """Get all instances of a model asynchronously with optional filters."""
    def query(db):
        q = db.query(model_class)
        if filters:
            for key, value in filters.items():
                q = q.filter(getattr(model_class, key) == value)
        if limit:
            q = q.limit(limit)
        return q.all()

    return await execute_db_query(query)


async def async_add(model_instance) -> Any:
    """Add a model instance asynchronously."""
    def add_and_commit(db):
        db.add(model_instance)
        db.commit()
        db.refresh(model_instance)
        return model_instance

    return await execute_db_query(add_and_commit)


async def async_update(model_class, id_value: int, updates: dict) -> bool:
    """Update a model instance asynchronously."""
    def update_query(db):
        instance = db.query(model_class).filter(model_class.id == id_value).first()
        if not instance:
            return False
        for key, value in updates.items():
            setattr(instance, key, value)
        db.commit()
        return True

    return await execute_db_query(update_query)


async def async_delete(model_class, id_value: int) -> bool:
    """Delete a model instance asynchronously."""
    def delete_query(db):
        instance = db.query(model_class).filter(model_class.id == id_value).first()
        if not instance:
            return False
        db.delete(instance)
        db.commit()
        return True

    return await execute_db_query(delete_query)


async def async_add_log(level: str, message: str, details: str = None):
    """Add a log entry asynchronously."""
    from backend.database import Log

    def add_log(db):
        log = Log(level=level, message=message, details=details)
        db.add(log)
        db.commit()

    await execute_db_query(add_log)
