"""
Health Checks Jobs

API health monitoring and external heartbeat integrations.
"""

import asyncio
import os
from datetime import datetime
from typing import Tuple, Optional

import aiohttp

from backend.database import SessionLocal, Log, Setting
from backend.services.topstep_client import topstep_client
from backend.services.telegram_service import telegram_service
from backend.services.timezone_service import now_user_tz
from backend.jobs.state import (
    get_api_health,
    update_api_health,
    get_heartbeat_state,
    update_heartbeat_state
)
FAILURE_THRESHOLD = 3  # Notify after 3 consecutive failures


async def api_health_check_job() -> None:
    """
    Periodically checks TopStep API health using /api/Status/ping.
    Sends Telegram notification after 3 consecutive failures.
    Logs recovery when API comes back online.
    """
    api_health = get_api_health()
    
    is_healthy, response_time, error = await topstep_client.ping()
    
    update_api_health(
        last_check_time=now_user_tz().isoformat(),
        last_response_time=response_time
    )
    
    if is_healthy:
        # API is healthy
        if not api_health["is_healthy"]:
            # Was down, now recovered
            db = SessionLocal()
            try:
                db.add(Log(level="INFO", message=f"TopStep API recovered - Response time: {response_time:.0f}ms"))
                db.commit()
                await telegram_service.send_message(
                    f"✅ <b>TopStep API Recovered</b>\n\n"
                    f"• Response time: {response_time:.0f}ms\n"
                    f"• Previous failures: {api_health['consecutive_failures']}"
                )
            finally:
                db.close()
        
        update_api_health(
            consecutive_failures=0,
            is_healthy=True,
            notified_down=False
        )
    else:
        # API is down
        new_failures = api_health["consecutive_failures"] + 1
        update_api_health(
            consecutive_failures=new_failures,
            is_healthy=False
        )
        
        db = SessionLocal()
        try:
            db.add(Log(level="ERROR", message=f"TopStep API ping failed: {error} (#{new_failures})"))
            db.commit()
            
            # Send notification only after threshold and only once
            if new_failures >= FAILURE_THRESHOLD and not api_health["notified_down"]:
                await telegram_service.send_message(
                    f"🚨 <b>TopStep API DOWN</b>\n\n"
                    f"• Error: {error}\n"
                    f"• Consecutive failures: {new_failures}\n"
                    f"• Trading may be affected!"
                )
                update_api_health(notified_down=True)
        finally:
            db.close()


async def heartbeat_job() -> None:
    """
    Sends a heartbeat ping to external monitoring system (N8N).
    Includes metadata about bot status for richer monitoring.
    """
    heartbeat_state = get_heartbeat_state()
    api_health = get_api_health()
    
    webhook_url = os.getenv("HEARTBEAT_WEBHOOK_URL")
    if not webhook_url:
        return  # Heartbeat not configured
    
    db = SessionLocal()
    try:
        now = now_user_tz()
        
        # Detect sleep: if last heartbeat was > 2 minutes ago, reset start_time
        if heartbeat_state["last_sent"]:
            time_since_last = (now - heartbeat_state["last_sent"]).total_seconds()
            if time_since_last > 120:  # More than 2 minutes = likely sleep/wake
                print(f"💤 Sleep detected ({int(time_since_last)}s gap). Resetting uptime.")
                update_heartbeat_state(start_time=now)
        
        # Calculate uptime
        uptime_seconds = 0
        if heartbeat_state["start_time"]:
            uptime_seconds = (now - heartbeat_state["start_time"]).total_seconds()
        
        # Get global trading status
        trading_enabled = True
        setting = db.query(Setting).filter(Setting.key == "trading_enabled").first()
        if setting:
            trading_enabled = setting.value == "true"
        
        # Get active accounts count
        try:
            all_accounts = await topstep_client.get_accounts()
            active_accounts = len(all_accounts) if all_accounts else 0
        except Exception:
            active_accounts = 0
        
        # Get API health status
        api_healthy = api_health.get("is_healthy", True)
        
        # Build payload with both timestamp formats for flexibility
        payload = {
            "bot_name": "TopStepBot",
            "timestamp": now.isoformat(),
            "timestamp_unix": int(now.timestamp()),
            "uptime_seconds": int(uptime_seconds),
            "uptime_formatted": format_uptime(uptime_seconds),
            "trading_enabled": trading_enabled,
            "active_accounts": active_accounts,
            "api_healthy": api_healthy,
            "version": "2.0.0"
        }
        
        # Build headers (with optional auth)
        headers = {"Content-Type": "application/json"}
        auth_token = os.getenv("HEARTBEAT_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = auth_token
        
        # Send heartbeat
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload, headers=headers, timeout=10) as response:
                if response.status in [200, 201, 202, 204]:
                    update_heartbeat_state(
                        last_sent=now_user_tz(),
                        consecutive_failures=0
                    )
                else:
                    update_heartbeat_state(
                        consecutive_failures=heartbeat_state["consecutive_failures"] + 1
                    )
                    print(f"⚠️ Heartbeat failed: HTTP {response.status}")
    
    except asyncio.TimeoutError:
        update_heartbeat_state(
            consecutive_failures=heartbeat_state["consecutive_failures"] + 1
        )
        print("⚠️ Heartbeat timeout")
    except Exception as e:
        update_heartbeat_state(
            consecutive_failures=heartbeat_state["consecutive_failures"] + 1
        )
        print(f"⚠️ Heartbeat error: {e}")
    finally:
        db.close()


def format_uptime(seconds: float) -> str:
    """Format uptime in a human-readable way."""
    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


async def send_shutdown_webhook() -> None:
    """
    Sends a shutdown notification to external monitoring system (N8N).
    This indicates a graceful shutdown (not a crash), so N8N can differentiate.
    """
    heartbeat_state = get_heartbeat_state()
    
    webhook_url = os.getenv("HEARTBEAT_WEBHOOK_URL")
    if not webhook_url:
        return
    
    try:
        now = now_user_tz()
        
        # Calculate final uptime
        uptime_seconds = 0
        if heartbeat_state["start_time"]:
            uptime_seconds = (now - heartbeat_state["start_time"]).total_seconds()
        
        # Build payload
        payload = {
            "bot_name": "TopStepBot",
            "timestamp": now.isoformat(),
            "timestamp_unix": int(now.timestamp()),
            "event": "shutdown",
            "reason": "graceful",
            "uptime_seconds": int(uptime_seconds),
            "uptime_formatted": format_uptime(uptime_seconds),
            "version": "2.0.0"
        }
        
        # Build headers
        headers = {"Content-Type": "application/json"}
        auth_token = os.getenv("HEARTBEAT_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = auth_token
        
        # Send shutdown notification
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload, headers=headers, timeout=5) as response:
                if response.status in [200, 201, 202, 204]:
                    print("✅ Shutdown notification sent to monitoring")
                else:
                    print(f"⚠️ Shutdown notification failed: HTTP {response.status}")
    
    except Exception as e:
        print(f"⚠️ Shutdown notification error: {e}")
