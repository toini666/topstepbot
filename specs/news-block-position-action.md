# Feature Specification: News-Based Trading Block & Position Action on Blocked Hours

> **Status**: 📋 Ready for Implementation  
> **Created**: 2026-01-17  
> **Priority**: High (Advanced Risk Management)

---

## 1. Executive Summary

This specification defines two interconnected features for enhanced risk management:

1. **Dynamic News-Based Trading Block**: Automatically block trading around major economic events detected by the daily calendar fetch
2. **Position Action on Blocked Hours**: Define what happens to open positions when entering any blocked trading period (manual or dynamic)

---

## 2. Business Requirements

### 2.1 Dynamic News Block

| Requirement | Description |
|-------------|-------------|
| **BR-1** | System shall provide a global toggle `news_block_enabled` to enable/disable automatic trading blocks around major economic events |
| **BR-2** | System shall allow configuration of `news_block_before_minutes` (default: 5) - minutes to block BEFORE the event |
| **BR-3** | System shall allow configuration of `news_block_after_minutes` (default: 5) - minutes to block AFTER the event |
| **BR-4** | Dynamic blocks shall be calculated from events already marked as "major" by existing calendar filter settings (`calendar_major_countries` + `calendar_major_impacts`) |
| **BR-5** | Dynamic blocks are ephemeral - they exist only in memory for the current day, NOT persisted to database |
| **BR-6** | Dynamic blocks shall be recalculated daily when the calendar job runs (07:00) |

### 2.2 Position Action on Blocked Hours

> ⚠️ **Note**: These are **GLOBAL settings** that apply to **ALL accounts**. There are no per-account overrides for this feature.

| Requirement | Description |
|-------------|-------------|
| **BR-7** | System shall provide a global setting `blocked_hours_position_action` with 3 options: `NOTHING`, `BREAKEVEN`, `FLATTEN` |
| **BR-8** | `NOTHING`: Keep positions open, only block new entries |
| **BR-9** | `BREAKEVEN`: Move Stop Loss to entry price for all open positions (ALL accounts) |
| **BR-10** | `FLATTEN`: Close all open positions and cancel all pending orders (ALL accounts) |
| **BR-11** | Action shall be executed `position_action_buffer_minutes` (default: 1) before entering the blocked period |
| **BR-12** | This action applies to BOTH manually configured blocked periods AND dynamic news blocks |
| **BR-13** | For `BREAKEVEN`: If position is already in loss, still move SL to entry price (position auto-closes) |

### 2.3 Frontend Display

| Requirement | Description |
|-------------|-------------|
| **BR-14** | Display dynamic news blocks in frontend, in a separate section below manual blocks |
| **BR-15** | Dynamic news blocks shall have a visual indicator showing they are "Today only" |
| **BR-16** | Display news block event name, time range, and impact level |
| **BR-17** | Dynamic blocks section is read-only (not editable, calculated automatically) |

### 2.4 Notifications

| Requirement | Description |
|-------------|-------------|
| **BR-18** | Send Telegram notification when news blocks are calculated for the day |
| **BR-19** | Send Telegram notification when position action is executed (BREAKEVEN/FLATTEN) |
| **BR-20** | Log all actions to System Logs (visible in Logs tab) |
| **BR-21** | No Discord notifications for these features |

---

## 3. User Stories

### US-1: Enable News Block
> As a trader, I want to automatically block trading around major economic events so that I avoid volatile market conditions.

**Acceptance Criteria:**
- Toggle in Global Settings to enable/disable
- Configurable before/after buffer in minutes
- Visual indication when a news block is active

### US-2: Configure Position Action
> As a trader, I want to define what happens to my open positions when entering a blocked period so that I can protect my capital.

**Acceptance Criteria:**
- Dropdown in Global Settings with 3 options
- Configurable buffer time before block starts
- Applies to all types of blocked periods

### US-3: Receive Notifications
> As a trader, I want to be notified when automatic actions are taken so that I stay informed.

**Acceptance Criteria:**
- Telegram message listing today's news blocks (in daily briefing)
- Telegram message when positions are modified/closed
- Actions logged in System Logs

---

## 4. Technical Architecture

### 4.1 New Global Settings

Add to `Setting` table (key-value store):

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `news_block_enabled` | boolean | `false` | Enable dynamic news blocks |
| `news_block_before_minutes` | int | `5` | Minutes to block before event |
| `news_block_after_minutes` | int | `5` | Minutes to block after event |
| `blocked_hours_position_action` | enum | `NOTHING` | Action: `NOTHING`, `BREAKEVEN`, `FLATTEN` |
| `position_action_buffer_minutes` | int | `1` | Minutes before block to execute action |

### 4.2 Schema Changes

#### `schemas.py` - Update `GlobalSettingsResponse` and `GlobalSettingsUpdate`

```python
class GlobalSettingsResponse(BaseModel):
    # Existing fields...
    
    # NEW: News Block Settings
    news_block_enabled: bool = False
    news_block_before_minutes: int = 5
    news_block_after_minutes: int = 5
    
    # NEW: Position Action Settings
    blocked_hours_position_action: str = "NOTHING"  # NOTHING, BREAKEVEN, FLATTEN
    position_action_buffer_minutes: int = 1
```

### 4.3 Dynamic News Blocks Storage

#### In-Memory Cache (NOT persisted)

```python
# calendar_service.py
class CalendarService:
    def __init__(self):
        self._cache = None
        self._last_fetch = None
        self._today_news_blocks: List[Dict] = []  # NEW: [{start: "14:25", end: "14:35", event: "CPI"}]
```

#### Block Structure
```python
{
    "start": "14:25",       # HH:MM Brussels time
    "end": "14:35",         # HH:MM Brussels time  
    "event": "CPI m/m",     # Event name for display
    "country": "USD",       # Country code
    "impact": "High"        # Impact level
}
```

### 4.4 Component Changes

#### 4.4.1 `calendar_service.py`

**New Method: `calculate_news_blocks()`**

```python
async def calculate_news_blocks(self) -> List[Dict]:
    """
    Calculate dynamic trading blocks based on today's major events.
    Called after fetching calendar in check_calendar_job().
    
    Returns list of time blocks for today's major events.
    """
    # 1. Get settings from DB
    # 2. Filter today's events by major_countries + major_impacts
    # 3. For each major event with a time:
    #    - Calculate start = event_time - news_block_before_minutes
    #    - Calculate end = event_time + news_block_after_minutes
    # 4. Store in self._today_news_blocks
    # 5. Return blocks for notification
```

**Update: `check_calendar_job()`**

```python
async def check_calendar_job(self):
    events = await self.fetch_calendar()
    
    # Existing Discord summary...
    
    # NEW: Calculate news blocks if enabled
    if news_block_enabled:
        blocks = await self.calculate_news_blocks()
        if blocks:
            await self.notify_news_blocks(blocks)  # Telegram + Logs
    
    # Clear yesterday's blocks (fresh start)
    self._today_news_blocks = blocks if news_block_enabled else []
```

**New Method: `get_today_news_blocks()`**

```python
def get_today_news_blocks(self) -> List[Dict]:
    """Return cached news blocks for today (for risk_engine to check)."""
    return self._today_news_blocks or []
```

#### 4.4.2 `risk_engine.py`

**Update: `check_blocked_periods()`**

```python
def check_blocked_periods(self) -> Tuple[bool, str]:
    """
    Check if current time is in a blocked period.
    Now checks BOTH manual blocks AND dynamic news blocks.
    """
    # Existing manual block check...
    
    # NEW: Also check dynamic news blocks
    from backend.services.calendar_service import calendar_service
    news_blocks = calendar_service.get_today_news_blocks()
    
    for block in news_blocks:
        # Same time comparison logic...
        if in_block:
            return False, f"News Block ({block['event']} - {block['start']}-{block['end']})"
    
    return True, "OK"
```

**New Method: `get_upcoming_block()`**

```python
def get_upcoming_block(self, buffer_minutes: int) -> Optional[Dict]:
    """
    Check if we're within buffer_minutes of entering a blocked period.
    Returns the block info if action needed, None otherwise.
    
    Used by position_action_job to trigger BREAKEVEN/FLATTEN.
    """
    # 1. Get all blocks (manual + dynamic)
    # 2. Check if current_time + buffer_minutes falls within any block start
    # 3. Return first matching block or None
```

#### 4.4.3 `main.py`

**New Scheduled Job: `position_action_job()`**

```python
async def position_action_job():
    """
    Check if approaching a blocked period and execute position action.
    Runs every 30 seconds to catch buffer window precisely.
    """
    # 1. Get settings: blocked_hours_position_action, position_action_buffer_minutes
    # 2. If action == "NOTHING", return early
    # 3. Call risk_engine.get_upcoming_block(buffer_minutes)
    # 4. If block found AND not already handled:
    #    - Track "handled" blocks to avoid duplicate actions
    #    - Execute action (BREAKEVEN or FLATTEN)
    #    - Send Telegram notification
    #    - Log to System Logs
```

**Action Implementations:**

```python
async def execute_breakeven_all(accounts: List, reason: str):
    """Move all position SLs to entry price."""
    for account in accounts:
        positions = await topstep_client.get_open_positions(account['id'])
        for pos in positions:
            # Find the SL order for this position
            orders = await topstep_client.get_orders(account['id'])
            sl_order = find_sl_order(orders, pos)
            
            if sl_order:
                # Modify SL to entry price
                entry_price = pos.get('averagePrice')
                await topstep_client.modify_order(
                    account['id'],
                    sl_order['id'],
                    stop_price=entry_price
                )
    
    # Notify
    await telegram_service.send_message(f"🛡️ Breakeven: All positions moved to entry ({reason})")

async def execute_flatten_all(accounts: List, reason: str):
    """Close all positions and cancel all orders."""
    # Reuse existing flatten_all logic
    # Notify with reason
```

**Scheduler Addition:**

```python
# In lifespan startup
scheduler.add_job(position_action_job, 'interval', seconds=30)
```

### 4.5 Frontend Changes

#### `ConfigModal.tsx`

Add new section "News Block Settings" with:

```tsx
// Toggle: Enable News Block
<Toggle 
    label="Block trading around major news events"
    value={newsBlockEnabled}
    onChange={...}
/>

// Number inputs (shown when enabled):
<NumberInput label="Minutes before event" value={newsBlockBefore} min={0} max={30} />
<NumberInput label="Minutes after event" value={newsBlockAfter} min={0} max={30} />

// Separator

// Dropdown: Position Action on Blocked Hours
<Select 
    label="Action when entering blocked hours"
    options={[
        { value: "NOTHING", label: "Do nothing (block new entries only)" },
        { value: "BREAKEVEN", label: "Move Stop Loss to entry price" },
        { value: "FLATTEN", label: "Close all positions" }
    ]}
    value={blockedHoursPositionAction}
/>

// Number input: Buffer
<NumberInput 
    label="Execute action X minutes before blocked period" 
    value={positionActionBuffer} 
    min={0} max={10} 
/>
```

#### `types.ts`

```typescript
interface GlobalConfig {
    // Existing...
    
    // News Block
    news_block_enabled: boolean;
    news_block_before_minutes: number;
    news_block_after_minutes: number;
    
    // Position Action
    blocked_hours_position_action: 'NOTHING' | 'BREAKEVEN' | 'FLATTEN';
    position_action_buffer_minutes: number;
}

// New interface for dynamic news blocks
interface NewsBlock {
    start: string;      // HH:MM
    end: string;        // HH:MM
    event: string;      // Event name
    country: string;    // USD, EUR, etc.
    impact: string;     // High, Medium, Low
}
```

#### Dynamic News Blocks Display (ConfigModal.tsx)

Add a read-only section below the manual blocked periods:

```tsx
{/* Dynamic News Blocks Section (Read-only) */}
{newsBlockEnabled && todayNewsBlocks.length > 0 && (
    <div className="mt-4 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
        <div className="flex items-center gap-2 mb-3">
            <Calendar className="w-4 h-4 text-amber-500" />
            <span className="font-medium text-amber-500">Today's News Blocks</span>
            <span className="px-2 py-0.5 text-xs bg-amber-500/20 text-amber-400 rounded-full">
                Today only
            </span>
        </div>
        <div className="space-y-2">
            {todayNewsBlocks.map((block, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                        {block.impact === 'High' && <span className="text-red-500">🔴</span>}
                        {block.impact === 'Medium' && <span className="text-orange-500">🟠</span>}
                        <span>{block.country}</span>
                        <span className="text-zinc-400">{block.event}</span>
                    </div>
                    <span className="font-mono text-zinc-300">
                        {block.start} - {block.end}
                    </span>
                </div>
            ))}
        </div>
        <p className="text-xs text-zinc-500 mt-2">
            These blocks are calculated automatically from today's major economic events.
        </p>
    </div>
)}
```

---

## 5. Data Flow Diagrams

### 5.1 Daily News Block Calculation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         07:00 - Calendar Job                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Fetch Calendar XML (7 days)  │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Filter Today's Major Events  │
                    │  (calendar_major_countries +  │
                    │   calendar_major_impacts)     │
                    └───────────────────────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              │                                           │
              ▼                                           ▼
┌──────────────────────────┐                ┌─────────────────────────────┐
│  news_block_enabled?     │───── No ──────▶│  Clear _today_news_blocks   │
└──────────────────────────┘                └─────────────────────────────┘
              │ Yes
              ▼
┌──────────────────────────────────────────┐
│  For each major event with time:         │
│  - start = time - before_minutes         │
│  - end = time + after_minutes            │
│  - Store in _today_news_blocks           │
└──────────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────┐
│  Send Telegram: "📅 News blocks today:"  │
│  - 14:25-14:35: CPI m/m (USD) 🔴         │
│  - 16:00-16:10: FOMC Minutes (USD) 🔴    │
└──────────────────────────────────────────┘
```

### 5.2 Position Action Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Every 30s - Position Action Job                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  blocked_hours_position_action│
                    │       == "NOTHING" ?          │
                    └───────────────────────────────┘
                              │           │
                           Yes│           │No
                              ▼           ▼
                          [Return]    ┌───────────────────────────────┐
                                      │  Get all blocks:              │
                                      │  - Manual blocked_periods     │
                                      │  - Dynamic news blocks        │
                                      └───────────────────────────────┘
                                                    │
                                                    ▼
                                      ┌───────────────────────────────┐
                                      │  Current time + buffer_mins   │
                                      │  falls in block start window? │
                                      └───────────────────────────────┘
                                              │           │
                                           No │           │Yes
                                              ▼           ▼
                                          [Return]    ┌───────────────────────────────┐
                                                      │  Already handled this block?  │
                                                      └───────────────────────────────┘
                                                              │           │
                                                           Yes│           │No
                                                              ▼           ▼
                                                          [Return]    ┌───────────────────────────────┐
                                                                      │  action == "BREAKEVEN" ?      │
                                                                      └───────────────────────────────┘
                                                                              │           │
                                                                           Yes│           │No
                                                                              ▼           ▼
                                                      ┌───────────────────────────────┐   ▼
                                                      │  For all accounts:            │  ┌───────────────────┐
                                                      │  - Find SL orders             │  │  FLATTEN:         │
                                                      │  - Modify SL → entry price    │  │  Close positions  │
                                                      └───────────────────────────────┘  │  Cancel orders    │
                                                                      │                  └───────────────────┘
                                                                      ▼                            │
                                                      ┌───────────────────────────────────────────────────┐
                                                      │  Mark block as handled                             │
                                                      │  Send Telegram notification                        │
                                                      │  Log to System Logs                                │
                                                      └───────────────────────────────────────────────────┘
```

---

## 6. Implementation Checklist

### Phase 1: Backend - Settings & Storage
- [ ] Add new settings to `schemas.py` (`GlobalSettingsResponse`, `GlobalSettingsUpdate`)
- [ ] Update `risk_engine.py` → `get_global_settings()` to load new settings
- [ ] Update `dashboard.py` → `update_global_config()` to save new settings
- [ ] Add `_today_news_blocks` cache to `calendar_service.py`

### Phase 2: Backend - News Block Calculation
- [ ] Implement `CalendarService.calculate_news_blocks()`
- [ ] Implement `CalendarService.get_today_news_blocks()`
- [ ] Update `CalendarService.check_calendar_job()` to calculate blocks
- [ ] Implement `CalendarService.notify_news_blocks()` for Telegram

### Phase 3: Backend - Block Period Check
- [ ] Update `RiskEngine.check_blocked_periods()` to include news blocks
- [ ] Implement `RiskEngine.get_all_blocked_periods()` helper
- [ ] Implement `RiskEngine.get_upcoming_block()` for action trigger

### Phase 4: Backend - Position Action Job
- [ ] Implement `position_action_job()` in `main.py`
- [ ] Implement `execute_breakeven_all()` helper
- [ ] Reuse `execute_flatten_all()` (already exists most logic)
- [ ] Add job to scheduler (every 30s)
- [ ] Implement "handled blocks" tracking to prevent duplicate actions

### Phase 5: Backend - Notifications
- [ ] Add Telegram notification for daily news blocks summary
- [ ] Add Telegram notification for BREAKEVEN execution
- [ ] Add Telegram notification for FLATTEN execution
- [ ] Add System Logs for all actions

### Phase 6: Frontend - Settings UI
- [ ] Add "News Block Settings" section to `ConfigModal.tsx`
- [ ] Add "Position Action on Blocked Hours" section
- [ ] Add `position_action_buffer_minutes` input field
- [ ] Update `types.ts` with new config fields
- [ ] Wire up API calls to save/load settings

### Phase 7: Frontend - Dynamic News Blocks Display
- [ ] Add new API call to fetch `/dashboard/news-blocks`
- [ ] Display "Today's News Blocks" section in ConfigModal
- [ ] Add "Today only" badge indicator
- [ ] Show event name, time range, and impact level
- [ ] Make section read-only (no edit controls)

### Phase 8: Testing & Validation
- [ ] Test news block calculation with mock calendar data
- [ ] Test BREAKEVEN action modifies SL correctly
- [ ] Test FLATTEN action closes all positions
- [ ] Test buffer timing (action fires X min before block)
- [ ] Test that handled blocks don't trigger duplicate actions
- [ ] Verify Telegram notifications format

---

## 7. API Endpoints

### Existing (No Changes)
- `GET /dashboard/config` - Already returns all global settings
- `POST /dashboard/config` - Already updates global settings

### New Endpoint

#### `GET /dashboard/news-blocks`

Returns today's calculated news blocks for frontend display.

**Response:**
```json
{
    "enabled": true,
    "blocks": [
        {
            "start": "14:25",
            "end": "14:35",
            "event": "CPI m/m",
            "country": "USD",
            "impact": "High"
        }
    ]
}
```

**Implementation:**
```python
@router.get("/dashboard/news-blocks")
async def get_news_blocks():
    from backend.services.calendar_service import calendar_service
    from backend.services.risk_engine import RiskEngine
    
    db = SessionLocal()
    try:
        risk_engine = RiskEngine(db)
        settings = risk_engine.get_global_settings()
        
        return {
            "enabled": settings.get("news_block_enabled", False),
            "blocks": calendar_service.get_today_news_blocks()
        }
    finally:
        db.close()
```

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| News blocks cleared on restart | Recalculate in startup if calendar cache exists |
| Multiple actions for same block | Track "handled" blocks in memory with block hash |
| BREAKEVEN fails (no SL order) | Log warning, continue with other positions |
| API rate limits on mass modify | Add small delay between order modifications |
| Timezone issues | All times in Brussels TZ, same as existing |

---

## 9. Future Enhancements (Out of Scope)

- Per-account override of position action
- Per-strategy override of news block sensitivity
- Visual calendar in UI showing blocked times
- Historical log of auto-actions taken

---

## 10. Files to Modify

| File | Changes |
|------|---------|
| `backend/schemas.py` | Add new settings fields |
| `backend/services/risk_engine.py` | Update `check_blocked_periods()`, add `get_upcoming_block()` |
| `backend/services/calendar_service.py` | Add news block calculation, storage, notification |
| `backend/routers/dashboard.py` | Handle new settings in config endpoints |
| `backend/main.py` | Add `position_action_job()`, helpers, scheduler |
| `frontend/src/components/ConfigModal.tsx` | Add new settings UI sections |
| `frontend/src/types.ts` | Add new config interface fields |

> **Note**: Documentation updates are handled separately via the `/update-documentation` workflow.
