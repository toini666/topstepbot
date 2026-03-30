"""
Price Refresh Job

Refresh current prices for all active contracts.
Primary: WebSocket (real-time) via MarketHubClient
Fallback: Polling every 10 seconds if WebSocket disconnects
"""

from typing import Set

from backend.services.topstep_client import topstep_client
from backend.services.price_cache import price_cache
from backend.services.market_hub_client import market_hub_client
from backend.jobs.state import get_last_open_positions_safely
from backend.services.config_service import get_config_value


async def price_refresh_job() -> None:
    """
    Refresh current prices for all active contracts.
    
    Primary: WebSocket (real-time) via MarketHubClient
    Fallback: Polling every 10 seconds if WebSocket disconnects
    
    Lifecycle:
    - Connect WebSocket when positions exist
    - Subscribe to new contracts dynamically  
    - Disconnect when all positions closed
    """
    try:
        # Get accounts (cached) to determine sim/live mode
        accounts = await topstep_client.get_accounts()
        active_contracts: Set[str] = set()
        is_simulated = True  # Default to simulated

        for account in accounts:
            if not account.get("simulated", True):
                is_simulated = False

        # Use last known positions state to avoid extra API calls
        last_positions = await get_last_open_positions_safely()
        for account_positions in last_positions.values():
            for contract_id in account_positions.keys():
                if contract_id:
                    active_contracts.add(contract_id)
        
        # ===== WebSocket Lifecycle Management =====

        websocket_disabled = get_config_value("websocket_disabled") == "true"

        if websocket_disabled and market_hub_client.is_connected:
            await market_hub_client.disconnect()
            price_cache.set_websocket_active(False)

        if active_contracts:
            # Positions exist - try to use WebSocket (unless manually disabled)
            if not websocket_disabled and not market_hub_client.is_connected:
                # Get token and connect
                token = getattr(topstep_client, 'token', None)
                if token:
                    success = await market_hub_client.connect(token)
                    if success:
                        # Set up quote callback to update PriceCache
                        def on_quote(contract_id: str, data: dict) -> None:
                            price = data.get("lastPrice") or data.get("last")
                            if price:
                                price_cache.set_price_from_websocket(contract_id, float(price))
                        
                        market_hub_client.on_quote(on_quote)
                        price_cache.set_websocket_active(True)
                    else:
                        price_cache.set_websocket_active(False)
                else:
                    price_cache.set_websocket_active(False)
            
            # Subscribe to new contracts if connected (and not disabled)
            if not websocket_disabled and market_hub_client.is_connected:
                current_subs = market_hub_client.subscribed_contracts
                for contract_id in active_contracts:
                    if contract_id not in current_subs:
                        await market_hub_client.subscribe_contract(contract_id)
                
                # Unsubscribe from contracts no longer needed
                for contract_id in current_subs - active_contracts:
                    await market_hub_client.unsubscribe_contract(contract_id)
            
            # Fallback: Use polling if WebSocket is not active or disabled
            if websocket_disabled or price_cache.should_use_polling_fallback:
                await price_cache.refresh_prices(
                    list(active_contracts), 
                    topstep_client, 
                    is_simulated=is_simulated
                )
        else:
            # No positions - disconnect WebSocket to save resources
            if market_hub_client.is_connected:
                await market_hub_client.disconnect()
                price_cache.set_websocket_active(False)
    
    except Exception as e:
        print(f"Price refresh error: {e}")
        price_cache.set_websocket_active(False)
