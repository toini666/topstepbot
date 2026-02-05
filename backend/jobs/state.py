"""
Global State Management for Scheduled Jobs

Provides thread-safe accessors and mutators for global state
used by various scheduled jobs.
"""

from typing import Dict, Set, Any, Optional
from datetime import datetime

# Global State for Position Monitoring (per-account)
# Key: account_id, Value: { contractId: position_data }
_last_open_positions: Dict[int, Dict[str, Any]] = {}
_last_orphans_ids: Set[str] = set()

# Health Check State
_api_health: Dict[str, Any] = {
    "consecutive_failures": 0,
    "last_check_time": None,
    "last_response_time": None,
    "is_healthy": True,
    "notified_down": False
}

# Heartbeat State
_heartbeat_state: Dict[str, Any] = {
    "start_time": None,
    "last_sent": None,
    "consecutive_failures": 0
}

# Track handled blocks to prevent duplicate actions (reset daily by calendar job)
_handled_position_action_blocks: Set[str] = set()


# ============================================================================
# Position State Accessors
# ============================================================================

import asyncio
_state_lock = asyncio.Lock()

# Global State for Position Monitoring (per-account)
# Key: account_id, Value: { contractId: position_data }
_last_open_positions: Dict[int, Dict[str, Any]] = {}

async def update_account_positions(account_id: int, positions_map: Dict[str, Any]) -> None:
    """Update positions for a specific account (Thread-Safe)."""
    async with _state_lock:
        _last_open_positions[account_id] = positions_map.copy()

async def get_last_open_positions_safely() -> Dict[int, Dict[str, Any]]:
    """Get a safe copy of the open positions state."""
    async with _state_lock:
        # Deep copy might be too slow, shallow copy of dict is usually enough if values aren't mutated in place
        # But here we return the whole dict of dicts.
        import copy
        return copy.deepcopy(_last_open_positions)
        
def get_last_open_positions() -> Dict[int, Dict[str, Any]]:
    """
    Get the current state of open positions (Direct access).
    WARNING: Use get_last_open_positions_safely() for async contexts where possible.
    This is kept for synchronous compatibility but is not thread-safe.
    """
    return _last_open_positions

def get_last_orphans_ids() -> Set[str]:
    """Get the set of known orphan order IDs."""
    return _last_orphans_ids


def set_last_orphans_ids(orphan_ids: Set[str]) -> None:
    """Set the orphan order IDs."""
    global _last_orphans_ids
    _last_orphans_ids = orphan_ids


# ============================================================================
# API Health State Accessors
# ============================================================================

def get_api_health() -> Dict[str, Any]:
    """Get the current API health state."""
    return _api_health


def update_api_health(**kwargs) -> None:
    """Update specific fields in API health state."""
    for key, value in kwargs.items():
        if key in _api_health:
            _api_health[key] = value


# ============================================================================
# Heartbeat State Accessors
# ============================================================================

def get_heartbeat_state() -> Dict[str, Any]:
    """Get the current heartbeat state."""
    return _heartbeat_state


def update_heartbeat_state(**kwargs) -> None:
    """Update specific fields in heartbeat state."""
    for key, value in kwargs.items():
        if key in _heartbeat_state:
            _heartbeat_state[key] = value


def init_heartbeat_start_time(start_time: datetime) -> None:
    """Initialize heartbeat start time (called at app startup)."""
    _heartbeat_state["start_time"] = start_time


# ============================================================================
# Position Action Blocks State Accessors
# ============================================================================

def get_handled_position_action_blocks() -> Set[str]:
    """Get the set of handled position action blocks."""
    return _handled_position_action_blocks


def add_handled_position_action_block(block_id: str) -> None:
    """Add a block ID to the handled set."""
    _handled_position_action_blocks.add(block_id)


def clear_handled_position_action_blocks() -> None:
    """Clear all handled position action blocks (called daily)."""
    _handled_position_action_blocks.clear()
