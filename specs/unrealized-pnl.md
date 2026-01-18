# Feature Specification: Unrealized PnL Display

> **Status**: 📋 Ready for Implementation  
> **Created**: 2026-01-17  
> **Priority**: Medium (Data & Analytics)

---

## 1. Executive Summary

Add unrealized (floating) PnL display for open positions in both the dashboard and Telegram commands. Uses TopStep's `/api/History/retrieveBars` endpoint to fetch near real-time prices with 5-second refresh intervals.

---

## 2. Business Requirements

### 2.1 Dashboard Display

| Requirement | Description |
|-------------|-------------|
| **BR-1** | Add new "PnL" column to the Open Positions table in the dashboard |
| **BR-2** | Display unrealized PnL per position using current market price |
| **BR-3** | PnL color: green for positive, red for negative (same as closed trades) |
| **BR-4** | Format: `$XX.XX` (no + sign for positive, same style as trade history) |
| **BR-5** | Refresh rate: ~5 seconds (synchronized with existing position polling) |

### 2.2 Telegram Commands

| Requirement | Description |
|-------------|-------------|
| **BR-6** | Add unrealized PnL to `/status` command for each open position |
| **BR-7** | Add unrealized PnL per account in `/status_all` command |
| **BR-8** | Include total unrealized PnL in the totals line of `/status_all` |

### 2.3 Technical

| Requirement | Description |
|-------------|-------------|
| **BR-9** | Use `/api/History/retrieveBars` with `unit: 1` (Second) to get current prices |
| **BR-10** | Contract ID for API calls MUST be the TopStep `ts_contract_id` from TickerMap table (NOT the TradingView ticker) |
| **BR-11** | Implement price caching to batch API calls (one call per unique contract) |
| **BR-12** | Price refresh interval: 5 seconds |
| **BR-13** | Calculate PnL using formula: `(currentPrice - entryPrice) × qty × tickValue / tickSize` |
| **BR-14** | For SHORT positions: `(entryPrice - currentPrice) × qty × tickValue / tickSize` |

---

## 3. User Stories

### US-1: View Unrealized PnL in Dashboard
> As a trader, I want to see the current unrealized PnL for each open position so that I can monitor my exposure in real-time.

**Acceptance Criteria:**
- New "PnL" column visible in Open Positions table
- Values update every ~5 seconds
- Green/red coloring based on profit/loss

### US-2: Check Unrealized PnL via Telegram
> As a trader, I want to see unrealized PnL in Telegram status commands so that I can monitor positions from mobile.

**Acceptance Criteria:**
- `/status` shows PnL per position
- `/status_all` shows PnL per account and total

---

## 4. Technical Architecture

### 4.1 New TopStep Client Method

Add to `topstep_client.py`:

```python
async def get_current_price(self, contract_id: str) -> Optional[float]:
    """
    Get the current/latest price for a contract using retrieveBars API.
    Uses 1-second bars, fetching the last few seconds to get the most recent close price.
    
    Returns the close price of the most recent bar, or None if unavailable.
    """
    await self._ensure_token()
    
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(seconds=10)  # Look back 10 seconds
    
    payload = {
        "contractId": contract_id,
        "live": True,
        "startTime": start_time.isoformat(),
        "endTime": now.isoformat(),
        "unit": 1,  # 1 = Second
        "unitNumber": 1,  # 1-second bars
        "limit": 5,  # Get last 5 bars
        "includePartialBar": True
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{self.base_url}/api/History/retrieveBars",
            headers={"Authorization": f"Bearer {self.token}"},
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            bars = data.get("bars", [])
            if bars:
                # Return close price of most recent bar
                return bars[-1].get("close")
    
    return None
```

### 4.2 Price Cache Service

New file: `backend/services/price_cache.py`

```python
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio

class PriceCache:
    """
    In-memory cache for current prices.
    Batches API calls to reduce load.
    """
    def __init__(self):
        self._cache: Dict[str, dict] = {}  # {contract_id: {price, timestamp}}
        self._cache_ttl = 5  # seconds
    
    def get_price(self, contract_id: str) -> Optional[float]:
        """Get cached price if still valid."""
        if contract_id in self._cache:
            entry = self._cache[contract_id]
            age = (datetime.now() - entry["timestamp"]).total_seconds()
            if age < self._cache_ttl:
                return entry["price"]
        return None
    
    def set_price(self, contract_id: str, price: float):
        """Store price in cache."""
        self._cache[contract_id] = {
            "price": price,
            "timestamp": datetime.now()
        }
    
    async def refresh_prices(self, contract_ids: list, topstep_client):
        """Batch refresh prices for all given contracts."""
        for contract_id in contract_ids:
            price = await topstep_client.get_current_price(contract_id)
            if price is not None:
                self.set_price(contract_id, price)
            await asyncio.sleep(0.1)  # Small delay to avoid rate limits

price_cache = PriceCache()
```

### 4.3 Unrealized PnL Calculation

Add utility function in `risk_engine.py` or new helper:

```python
def calculate_unrealized_pnl(
    entry_price: float,
    current_price: float,
    quantity: int,
    is_long: bool,
    tick_size: float,
    tick_value: float
) -> float:
    """
    Calculate unrealized PnL for a position.
    
    Formula: ((current - entry) / tick_size) × tick_value × quantity
    For SHORT: negate the price difference
    """
    if is_long:
        price_diff = current_price - entry_price
    else:
        price_diff = entry_price - current_price
    
    ticks = price_diff / tick_size
    pnl = ticks * tick_value * quantity
    
    return round(pnl, 2)
```

### 4.4 Dashboard API Enhancement

Modify `GET /dashboard/positions/{account_id}` in `dashboard.py`:

```python
@router.get("/dashboard/positions/{account_id}")
async def get_positions(account_id: int):
    """Get open positions with unrealized PnL."""
    positions = await topstep_client.get_open_positions(account_id)
    
    # Enrich with unrealized PnL
    enriched_positions = []
    
    for pos in positions:
        contract_id = pos.get("contractId")
        entry_price = pos.get("averagePrice", 0)
        quantity = pos.get("size", 0)
        is_long = pos.get("type") == 1
        
        # Get current price from cache
        current_price = price_cache.get_price(contract_id)
        
        unrealized_pnl = None
        if current_price and entry_price:
            # Get tick info from TickerMap or contract details
            tick_info = get_tick_info(contract_id)
            if tick_info:
                unrealized_pnl = calculate_unrealized_pnl(
                    entry_price=entry_price,
                    current_price=current_price,
                    quantity=quantity,
                    is_long=is_long,
                    tick_size=tick_info["tick_size"],
                    tick_value=tick_info["tick_value"]
                )
        
        enriched_positions.append({
            **pos,
            "currentPrice": current_price,
            "unrealizedPnl": unrealized_pnl
        })
    
    return enriched_positions
```

### 4.5 Scheduled Price Refresh Job

Add to `main.py`:

```python
async def price_refresh_job():
    """
    Refresh current prices for all active contracts.
    Runs every 5 seconds.
    """
    from backend.services.price_cache import price_cache
    
    try:
        # Get all open positions across all accounts
        accounts = await topstep_client.get_accounts()
        active_contracts = set()
        
        for account in accounts:
            positions = await topstep_client.get_open_positions(account["id"])
            for pos in positions:
                active_contracts.add(pos.get("contractId"))
        
        if active_contracts:
            await price_cache.refresh_prices(list(active_contracts), topstep_client)
    
    except Exception as e:
        print(f"Price refresh error: {e}")

# In lifespan startup:
scheduler.add_job(price_refresh_job, 'interval', seconds=5)
```

### 4.6 Frontend Changes

#### Update Position Type (`types.ts`)

```typescript
interface Position {
    id: number;
    accountId: number;
    contractId: string;
    creationTimestamp: string;
    type: number;  // 1=Long, 2=Short
    size: number;
    averagePrice: number;
    // NEW
    currentPrice?: number;
    unrealizedPnl?: number;
}
```

#### Update Positions Table (`App.tsx`)

```tsx
{/* Open Positions Table - Add PnL column */}
<thead>
    <tr>
        <th>Contract</th>
        <th>Strategy</th>
        <th>Side</th>
        <th>Qty</th>
        <th>Entry</th>
        <th>Current</th>  {/* NEW */}
        <th>PnL</th>       {/* NEW */}
        <th>Action</th>
    </tr>
</thead>
<tbody>
    {positions.map((pos) => (
        <tr key={pos.id}>
            {/* ... existing columns ... */}
            <td className="text-right font-mono">
                {pos.currentPrice?.toFixed(2) ?? '-'}
            </td>
            <td className={`text-right font-mono font-bold ${
                (pos.unrealizedPnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
                {pos.unrealizedPnl !== null && pos.unrealizedPnl !== undefined 
                    ? `$${pos.unrealizedPnl.toFixed(2)}` 
                    : '-'}
            </td>
            {/* ... action column ... */}
        </tr>
    ))}
</tbody>
```

### 4.7 Telegram Updates

#### Update `cmd_status()` in `telegram_bot.py`

```python
async def cmd_status(self):
    # ... existing code ...
    
    if positions:
        msg += "📈 <b>Open Positions:</b>\n"
        for p in positions:
            contract = p.get('contractId')
            side_icon = "🟢 LONG" if p.get('type') == 1 else "🔴 SHORT"
            qty = p.get('size', 0)
            entry = p.get('averagePrice', 0)
            
            # NEW: Get unrealized PnL
            current_price = price_cache.get_price(contract)
            unrealized_pnl = calculate_unrealized_pnl_for_position(p, current_price)
            pnl_str = f"${unrealized_pnl:,.2f}" if unrealized_pnl is not None else "-"
            pnl_emoji = "🟢" if (unrealized_pnl or 0) >= 0 else "🔴"
            
            msg += f"• {contract}: {side_icon} x{qty} @ {entry}"
            msg += f" | {pnl_emoji} {pnl_str}\n"
```

#### Update `cmd_status_all()` in `telegram_bot.py`

```python
async def cmd_status_all(self):
    # ... existing code ...
    
    total_unrealized_pnl = 0.0
    
    for acc in accounts_list:
        # ... existing code ...
        
        # NEW: Calculate unrealized PnL for this account
        account_unrealized_pnl = 0.0
        for p in positions:
            current_price = price_cache.get_price(p.get('contractId'))
            pnl = calculate_unrealized_pnl_for_position(p, current_price)
            if pnl is not None:
                account_unrealized_pnl += pnl
        
        total_unrealized_pnl += account_unrealized_pnl
        
        # Include in per-account line
        unrealized_str = f"${account_unrealized_pnl:,.2f}" if positions else ""
        msg += f"{trading_status} <b>{acc_name}</b>\n"
        msg += f"   💰 ${balance:,.2f} | PnL: ${daily_pnl:,.2f} | {pos_str}"
        if unrealized_str:
            msg += f" | 📊 {unrealized_str}"
        msg += "\n"
    
    # NEW: Include total unrealized in totals
    unrealized_emoji = "🟢" if total_unrealized_pnl >= 0 else "🔴"
    msg += f"\n<b>TOTAL:</b> {pnl_emoji} ${total_pnl:,.2f} Realized | "
    msg += f"{unrealized_emoji} ${total_unrealized_pnl:,.2f} Unrealized | {total_positions} pos"
```

---

## 5. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Every 5s - Price Refresh Job                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Get all open positions       │
                    │  across all accounts          │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Extract unique contract IDs  │
                    │  (e.g., MNQZ5, ESH6)          │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  For each contract:           │
                    │  Call /api/History/retrieveBars│
                    │  (unit=1, last 5 seconds)     │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Store prices in PriceCache   │
                    │  {contract_id: price, ts}     │
                    └───────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    Frontend Polling (every 3s)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  GET /dashboard/positions/{id}│
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Backend enriches positions   │
                    │  with currentPrice + PnL      │
                    │  from PriceCache              │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Frontend displays PnL column │
                    │  with green/red coloring      │
                    └───────────────────────────────┘
```

---

## 6. Implementation Checklist

### Phase 1: Backend - Price Fetching
- [ ] Add `get_current_price()` method to `topstep_client.py`
- [ ] Create `backend/services/price_cache.py` with `PriceCache` class
- [ ] Add `price_refresh_job()` to `main.py`
- [ ] Schedule job to run every 5 seconds

### Phase 2: Backend - PnL Calculation
- [ ] Add `calculate_unrealized_pnl()` utility function
- [ ] Add helper to get tick info from TickerMap
- [ ] Modify `GET /dashboard/positions/{id}` to include PnL

### Phase 3: Backend - Telegram Integration
- [ ] Import `price_cache` in `telegram_bot.py`
- [ ] Update `cmd_status()` to show per-position PnL
- [ ] Update `cmd_status_all()` to show per-account and total unrealized PnL

### Phase 4: Frontend - Display
- [ ] Update `Position` interface in `types.ts`
- [ ] Add "Current" and "PnL" columns to Open Positions table
- [ ] Apply green/red styling based on PnL value

### Phase 5: Testing & Validation
- [ ] Test price fetching with retrieveBars API
- [ ] Verify PnL calculation for LONG positions
- [ ] Verify PnL calculation for SHORT positions
- [ ] Test Telegram `/status` output format
- [ ] Test Telegram `/status_all` output format
- [ ] Verify frontend updates every ~5 seconds

---

## 7. API Endpoints

### Modified Endpoint

#### `GET /dashboard/positions/{account_id}`

**Response (Updated):**
```json
[
    {
        "id": 123,
        "accountId": 456,
        "contractId": "MNQZ5",
        "type": 1,
        "size": 2,
        "averagePrice": 20150.50,
        "creationTimestamp": "2026-01-17T15:30:00Z",
        "currentPrice": 20175.25,
        "unrealizedPnl": 49.50
    }
]
```

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| API rate limits on retrieveBars | Batch calls per unique contract, add small delay between calls |
| Price not available for a contract | Display "-" in UI, skip in calculations |
| Tick info not in TickerMap | Fall back to contract details API or display "-" |
| Price cache stale | TTL of 5 seconds ensures freshness |
| Market closed = no bars | Handle empty bars array gracefully |

---

## 9. Files to Modify

| File | Changes |
|------|---------|
| `backend/services/topstep_client.py` | Add `get_current_price()` method |
| `backend/services/price_cache.py` | **NEW** - Price caching service |
| `backend/main.py` | Add `price_refresh_job()` and scheduler |
| `backend/routers/dashboard.py` | Enrich positions with PnL |
| `backend/services/telegram_bot.py` | Update `/status` and `/status_all` |
| `frontend/src/types.ts` | Add `currentPrice`, `unrealizedPnl` to Position |
| `frontend/src/App.tsx` | Add columns to Open Positions table |

> **Note**: Documentation updates are handled separately via the `/update-documentation` workflow.
