"""
TopStepBot Scheduled Jobs Module

This module contains all the scheduled jobs that run periodically
to monitor positions, handle auto-flatten, etc.
"""

from backend.jobs.state import (
    get_last_open_positions,
    set_last_open_positions,
    get_last_orphans_ids,
    set_last_orphans_ids,
    get_api_health,
    update_api_health,
    get_heartbeat_state,
    update_heartbeat_state,
    get_handled_position_action_blocks,
    add_handled_position_action_block,
    clear_handled_position_action_blocks,
)

from backend.jobs.position_monitor import monitor_closed_positions_job
from backend.jobs.auto_flatten import auto_flatten_job, execute_flatten_all
from backend.jobs.position_actions import position_action_job, execute_breakeven_all
from backend.jobs.health_checks import (
    api_health_check_job,
    heartbeat_job,
    format_uptime,
    send_shutdown_webhook
)
from backend.jobs.price_refresh import price_refresh_job
from backend.jobs.discord_summary import discord_daily_summary_job

__all__ = [
    # State management
    'get_last_open_positions',
    'set_last_open_positions',
    'get_last_orphans_ids',
    'set_last_orphans_ids',
    'get_api_health',
    'update_api_health',
    'get_heartbeat_state',
    'update_heartbeat_state',
    'get_handled_position_action_blocks',
    'add_handled_position_action_block',
    'clear_handled_position_action_blocks',
    
    # Jobs
    'monitor_closed_positions_job',
    'auto_flatten_job',
    'execute_flatten_all',
    'position_action_job',
    'execute_breakeven_all',
    'api_health_check_job',
    'heartbeat_job',
    'format_uptime',
    'send_shutdown_webhook',
    'price_refresh_job',
    'discord_daily_summary_job',
]
