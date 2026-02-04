"""
Market Hub Client - Native WebSocket for real-time price data.

Uses native websockets library with SignalR protocol handshake.
No external SignalR library dependency - full control and modern websockets support.
"""

import asyncio
import json
import logging
from typing import Set, Optional, Callable
from datetime import datetime
from urllib.parse import urlencode

logger = logging.getLogger("topstepbot")


class MarketHubClient:
    """
    Native WebSocket client for TopStepX Market Hub.
    Implements SignalR Core protocol manually for full control.
    
    Usage:
        client = MarketHubClient()
        client.on_quote(handle_quote)
        await client.connect(access_token)
        await client.subscribe_contract("CON.F.US.EP.H26")
        ...
        await client.disconnect()
    """
    
    # SignalR protocol constants
    HANDSHAKE_REQUEST = {"protocol": "json", "version": 1}
    RECORD_SEPARATOR = "\x1e"  # SignalR message delimiter
    
    HUB_URL = "wss://rtc.topstepx.com/hubs/market"
    
    def __init__(self):
        self._websocket = None
        self._subscribed_contracts: Set[str] = set()
        self._is_connected = False
        self._on_quote_callback: Optional[Callable] = None
        self._access_token: Optional[str] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay_base = 2
        self._ping_task: Optional[asyncio.Task] = None
    
    @property
    def is_connected(self) -> bool:
        return self._is_connected
    
    @property
    def subscribed_contracts(self) -> Set[str]:
        return self._subscribed_contracts.copy()
    
    def on_quote(self, callback: Callable[[str, dict], None]):
        """Register callback for quote events."""
        self._on_quote_callback = callback
    
    async def connect(self, access_token: str) -> bool:
        """Establish WebSocket connection to Market Hub."""
        if self._is_connected:
            logger.debug("MarketHubClient already connected")
            return True
        
        self._access_token = access_token
        
        try:
            import websockets
            
            # Build WebSocket URL with token
            params = urlencode({"access_token": access_token})
            url = f"{self.HUB_URL}?{params}"
            
            # Connect with modern websockets API
            self._websocket = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5
            )
            
            # Send SignalR handshake
            handshake = json.dumps(self.HANDSHAKE_REQUEST) + self.RECORD_SEPARATOR
            await self._websocket.send(handshake)
            
            # Wait for handshake response
            response = await asyncio.wait_for(self._websocket.recv(), timeout=10)
            if self.RECORD_SEPARATOR in response:
                response_data = json.loads(response.rstrip(self.RECORD_SEPARATOR))
                if "error" in response_data:
                    logger.error(f"SignalR handshake failed: {response_data['error']}")
                    await self._websocket.close()
                    return False
            
            self._is_connected = True
            self._reconnect_attempts = 0
            
            # Start message receiver
            self._receive_task = asyncio.create_task(self._receive_messages())
            
            logger.info("MarketHubClient connected (native WebSocket)")
            return True
            
        except Exception as e:
            logger.error(f"MarketHubClient connection failed: {e}")
            self._is_connected = False
            return False
    
    async def disconnect(self):
        """Close WebSocket connection."""
        self._is_connected = False
        
        # Cancel receiver task
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
        
        self._websocket = None
        self._subscribed_contracts.clear()
        logger.info("MarketHubClient disconnected")
    
    async def subscribe_contract(self, contract_id: str) -> bool:
        """Subscribe to quotes for a contract."""
        if not self._is_connected or not self._websocket:
            logger.warning(f"Cannot subscribe to {contract_id}: not connected")
            return False
        
        if contract_id in self._subscribed_contracts:
            return True
        
        try:
            # SignalR invocation message
            message = {
                "type": 1,  # Invocation
                "target": "SubscribeContractQuotes",
                "arguments": [contract_id]
            }
            await self._websocket.send(json.dumps(message) + self.RECORD_SEPARATOR)
            self._subscribed_contracts.add(contract_id)
            logger.info(f"Subscribed to quotes for {contract_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {contract_id}: {e}")
            return False
    
    async def unsubscribe_contract(self, contract_id: str) -> bool:
        """Unsubscribe from a contract's quotes."""
        if not self._is_connected or not self._websocket:
            return False
        
        if contract_id not in self._subscribed_contracts:
            return True
        
        try:
            message = {
                "type": 1,
                "target": "UnsubscribeContractQuotes", 
                "arguments": [contract_id]
            }
            await self._websocket.send(json.dumps(message) + self.RECORD_SEPARATOR)
            self._subscribed_contracts.discard(contract_id)
            logger.info(f"Unsubscribed from {contract_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {contract_id}: {e}")
            return False
    
    async def _receive_messages(self):
        """Background task to receive and process messages."""
        try:
            async for raw_message in self._websocket:
                # SignalR messages are delimited by record separator
                for msg_str in raw_message.split(self.RECORD_SEPARATOR):
                    if not msg_str.strip():
                        continue
                    
                    try:
                        msg = json.loads(msg_str)
                        await self._handle_message(msg)
                    except json.JSONDecodeError:
                        continue
                        
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"WebSocket receive error: {e}")
            self._is_connected = False
            self._schedule_reconnect()
    
    async def _handle_message(self, msg: dict):
        """Process incoming SignalR message."""
        msg_type = msg.get("type")
        
        if msg_type == 1:  # Invocation
            target = msg.get("target", "")
            arguments = msg.get("arguments", [])
            
            if target == "GatewayQuote" and len(arguments) >= 2:
                contract_id = arguments[0]
                quote_data = arguments[1] if isinstance(arguments[1], dict) else {}
                
                if self._on_quote_callback:
                    try:
                        self._on_quote_callback(contract_id, quote_data)
                    except Exception as e:
                        logger.error(f"Quote callback error: {e}")
        
        elif msg_type == 6:  # Ping
            # Respond with pong
            pong = {"type": 6}
            if self._websocket:
                await self._websocket.send(json.dumps(pong) + self.RECORD_SEPARATOR)
    
    def _schedule_reconnect(self):
        """Schedule reconnection attempt."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self._reconnect_attempts += 1
        delay = min(self._reconnect_delay_base ** self._reconnect_attempts, 60)
        
        logger.info(f"Scheduling reconnect in {delay}s (attempt {self._reconnect_attempts})")
        asyncio.create_task(self._reconnect_after_delay(delay))
    
    async def _reconnect_after_delay(self, delay: float):
        """Attempt reconnection after delay."""
        await asyncio.sleep(delay)
        
        if self._access_token and not self._is_connected:
            contracts_to_resub = self._subscribed_contracts.copy()
            self._subscribed_contracts.clear()
            
            success = await self.connect(self._access_token)
            if success:
                for contract_id in contracts_to_resub:
                    await self.subscribe_contract(contract_id)


# Global singleton
market_hub_client = MarketHubClient()
