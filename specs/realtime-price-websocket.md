# Real-Time Price WebSocket (SignalR Market Hub)

Replace polling-based price fetching with SignalR WebSocket for real-time unrealized PnL updates.

## Business Requirements

| ID | Requirement |
|----|-------------|
| BR-1 | Use SignalR Market Hub WebSocket for real-time price updates |
| BR-2 | Connect to WebSocket only when open positions exist |
| BR-3 | Disconnect WebSocket when all positions are closed |
| BR-4 | Subscribe to `GatewayQuote` for each open contract |
| BR-5 | Keep existing polling mechanism as fallback (10s interval) |
| BR-6 | Fallback activates automatically if WebSocket disconnects |

---

## Technical Architecture

### New Service: MarketHubClient

```python
# backend/services/market_hub_client.py

from aiosignalrcore.hub_connection_builder import HubConnectionBuilder
import asyncio
from typing import Set, Optional, Callable

class MarketHubClient:
    """
    SignalR WebSocket client for real-time market data.
    Connects to TopStepX Market Hub for GatewayQuote events.
    """
    
    def __init__(self):
        self.hub_url = "https://rtc.topstepx.com/hubs/market"
        self._connection = None
        self._subscribed_contracts: Set[str] = set()
        self._is_connected = False
        self._on_quote_callback: Optional[Callable] = None
        self._reconnect_task = None
    
    async def connect(self, access_token: str):
        """Establish WebSocket connection to Market Hub."""
        ...
    
    async def disconnect(self):
        """Close WebSocket connection."""
        ...
    
    async def subscribe_contract(self, contract_id: str):
        """Subscribe to GatewayQuote for a specific contract."""
        ...
    
    async def unsubscribe_contract(self, contract_id: str):
        """Unsubscribe from a contract's quotes."""
        ...
    
    def on_quote(self, callback: Callable):
        """Register callback for GatewayQuote events."""
        ...
    
    @property
    def is_connected(self) -> bool:
        return self._is_connected
```

---

### Modified PriceCache

Add source tracking and WebSocket integration:

```python
class PriceCache:
    def __init__(self):
        self._cache: Dict[str, dict] = {}
        self._cache_ttl = 10  # For polling fallback
        self._websocket_active = False  # Track if WS is primary source
    
    def set_price_from_websocket(self, contract_id: str, price: float):
        """Update price from WebSocket (no TTL, always fresh)."""
        self._cache[contract_id] = {
            "price": price,
            "timestamp": datetime.now(),
            "source": "websocket"
        }
    
    def set_websocket_active(self, active: bool):
        """Track WebSocket status for fallback decision."""
        self._websocket_active = active
    
    @property
    def should_use_polling_fallback(self) -> bool:
        """True if WebSocket is disconnected and fallback needed."""
        return not self._websocket_active
```

---

## Data Flow

### Normal Operation (WebSocket Active)
```
Position Opened
       │
       ▼
┌──────────────────────────────┐
│  MarketHubClient.connect()   │
│  if not already connected    │
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  SubscribeContractQuotes     │
│  (for new contract)          │
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  GatewayQuote event          │───────────┐
│  {symbol, lastPrice, ...}    │           │
└──────────────────────────────┘           │
       │                                   │ Every tick
       ▼                                   │
┌──────────────────────────────┐           │
│  price_cache.set_price_      │◄──────────┘
│  from_websocket()            │
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Dashboard/Telegram reads    │
│  real-time unrealized PnL    │
└──────────────────────────────┘
```

### Fallback Operation (WebSocket Down)
```
WebSocket Disconnected
       │
       ▼
┌──────────────────────────────┐
│  price_cache.set_websocket_  │
│  active(False)               │
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  price_refresh_job (10s)     │
│  uses retrieveBars API       │
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Automatic reconnect         │
│  attempts in background      │
└──────────────────────────────┘
```

### Lifecycle Management
```
┌─────────────────────────────────────────────────────────────┐
│              Position Monitor Job (every 10s)                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │  Count total open positions  │
            │  across all accounts         │
            └──────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
    positions > 0                   positions = 0
           │                               │
           ▼                               ▼
   ┌───────────────────┐          ┌───────────────────┐
   │ WS not connected? │          │ WS connected?     │
   │ → Connect + Sub   │          │ → Disconnect      │
   └───────────────────┘          └───────────────────┘
```

---

## Implementation Checklist

### Phase 1: MarketHubClient Service
- [ ] Install `aiosignalrcore` package
- [ ] Create `backend/services/market_hub_client.py`
- [ ] Implement `connect()` with token from `topstep_client`
- [ ] Implement `disconnect()`
- [ ] Implement `subscribe_contract()` / `unsubscribe_contract()`
- [ ] Implement `GatewayQuote` event handler
- [ ] Add automatic reconnection logic

### Phase 2: PriceCache Integration
- [ ] Add `set_price_from_websocket()` method
- [ ] Add `_websocket_active` flag
- [ ] Add `should_use_polling_fallback` property
- [ ] Modify `price_refresh_job` to check fallback flag

### Phase 3: Lifecycle Management
- [ ] Add WebSocket connection logic to position monitor
- [ ] Connect when first position opens
- [ ] Subscribe to new contracts dynamically
- [ ] Disconnect when last position closes
- [ ] Handle reconnection on WebSocket errors

### Phase 4: Testing
- [ ] Test connection/disconnection lifecycle
- [ ] Verify GatewayQuote updates PriceCache
- [ ] Test fallback to polling when WS fails
- [ ] Verify reconnection after network issues

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| WebSocket connection failures | Automatic reconnect with exponential backoff |
| Token expiration during WS session | Re-authenticate and reconnect |
| Symbol format mismatch | Verify `GatewayQuote.symbol` matches `position.contractId` |
| Rate limits on subscribe/unsubscribe | Batch operations, debounce rapid changes |
| Memory leak from stale subscriptions | Track subscribed contracts, cleanup on disconnect |

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/services/market_hub_client.py` | **NEW** - SignalR WebSocket client |
| `backend/services/price_cache.py` | Add WebSocket source tracking |
| `backend/main.py` | Add WS lifecycle to position monitor |
| `requirements.txt` | Add `aiosignalrcore` |
