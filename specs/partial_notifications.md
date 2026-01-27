# Partial Close Notifications & PnL Tracking

## Executive Summary
Enhance partial close handling by including financial data (Realized PnL) in notifications. 
Currently, partial closes only report contract quantities. This update will fetch exact PnL from Topstep's API for the executed partial close and calculate the remaining unrealized PnL. 
Additionally, a completely new Discord notification type for partial closes will be implemented, controllable via a new global setting.

## Business Requirements
1.  **BR-1**: Display Realized PnL (Net of fees) in Telegram "Partial TP" notifications.
2.  **BR-2**: Display Remaining Unrealized PnL (Latent) in Telegram "Partial TP" notifications.
3.  **BR-3**: Send a specific notification to Discord when a partial close occurs.
4.  **BR-4**: Add a toggle in Discord settings to enable/disable partial close notifications (default: Enabled).

## User Stories
- As a trader, I want to see exactly how much money a partial take-profit secured so I can track my daily performance.
- As a trader, I want to see the floating PnL of the remaining position to know if I'm still safe.
- As a user, I want to receive partial close alerts on Discord to keep my community informed.
- As a user, I want to be able to turn off Discord partial alerts if they become too noisy.

## Technical Architecture

### 1. PnL Retrieval Logic (Backend)
Instead of estimating realized PnL, we will query the Topstep API immediately after the partial close execution.
- **Endpoint**: `/api/trade/search` (Existing client method `get_historical_trades`)
- **Logic**: 
  1. Record partial close execution time.
  2. Wait briefly (1-2s) for trade to settle.
  3. Fetch recent trades for the account.
  4. Filter for the specific trade that just happened (matching Contract + Time + Side).
  5. Extract `pnl` and `fees` from the API response.

### 2. Unrealized PnL Calculation
Since we know the entry price and the current price (execution price of the partial), we can calculate the latent PnL of the *remaining* position manually.
- **Formula**: `(Current Price - Entry Price) * Remaining Qty * Tick Value / Tick Size`
- **Direction**: Invert for SHORT positions.

### 3. Database Schema Changes
**Table**: `discord_notification_settings`
- **New Column**: `notify_partial_close` (Boolean, Default: True)

### 4. Component Changes

#### `backend/routers/webhook.py` (`handle_partial`)
- Implement the "Fetch & Calculate" logic after `topstep_client.partial_close_position`.
- Pass `realized_pnl`, `fees`, and `unrealized_pnl` to notification services.

#### `backend/services/telegram_service.py`
- Update `notify_partial_executed` signature to accept PnL data.
- Update message template to include:
  - "💰 Realized: $XX.XX"
  - "xx Remaining (Latent: $YY.YY)"

#### `backend/services/discord_service.py`
- Update `DiscordNotificationSettings` model (in `database.py`).
- Add `notify_partial_executed` method.
- Send embed with "✂️ Partial Close" title, Green/Red color based on PnL.

## Data Flow
1. **Webhook**: Receives `PARTIAL` signal.
2. **Execution**: Bot calls `partial_close_position`.
3. **Data Fetch**: Bot calls `get_historical_trades` to find the fill.
4. **Calculation**: Bot calculates remaining latent PnL.
5. **Notification**:
   - Telegram: Sends extended message.
   - Discord: Checks `notify_partial_close` setting -> Sends Embed.

## Implementation Checklist
- [ ] **Database**: Add `notify_partial_close` column to `discord_notification_settings` (via alembic or direct check/create).
- [ ] **Topstep Client**: Ensure `get_historical_trades` can be used reliably (already exists).
- [ ] **Webhook Logic**: Modify `handle_partial` to fetch trade details after execution.
- [ ] **Telegram**: Update message format.
- [ ] **Discord**: Implement `notify_partial_executed`.
- [ ] **Discord**: Update `notify_position_closed` (optional, cleanup if needed).

## API Endpoints
No new internal API endpoints. 
External Topstep API calls:
- `GET /api/trade/search` (Wrapped in `get_historical_trades`)

## Risks & Mitigations
- **Risk**: API delay. The trade might not appear in `/trade/search` immediately after execution.
  - **Mitigation**: Implement a retry mechanism or a slightly longer `sleep` (e.g., 2 seconds) before fetching.
- **Risk**: Rate limits.
  - **Mitigation**: We are already making calls sequentially; the extra search call is low overhead.

## Files to Modify
- `backend/database.py` (Schema)
- `backend/routers/webhook.py` (Business Logic)
- `backend/services/telegram_service.py` (Notification Format)
- `backend/services/discord_service.py` (New Notification)
