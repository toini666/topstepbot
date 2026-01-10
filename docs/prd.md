# Product Requirements Document (PRD) - TopStepX Trading Bot

## 1. Overview
The **TopStepX Trading Bot** is an automated trading interface designed to bridge **TradingView** alerts with the **TopStepX** trading platform. It acts as a middleware that executes trades based on external signals while enforcing strict, locally managed risk management rules.

The primary goal is to **automate execution** while preserving **account safety** through rigid, pre-defined constraints that override any incoming signal if necessary.

## 2. Core Business Features

### 2.1 Automated Order Execution
- **Signal Source**: Receives JSON payloads via HTTP Webhooks.
    - **SETUP**: Logged for analysis only (No Trade).
    - **SIGNAL**: Triggers risk checks and trade execution.
- **Protocol**: Translates generic signals into TopStepX API orders.
- **Instrument Support**: Compatible with Futures contracts (e.g., MNQ, MES).
- **Dynamic Sizing**: Automatically calculates position size based on Risk Amount ($) and Stop Loss distance.
- **Contract Cache**: Optimizes performance by caching contract IDs to reduce API calls.
- **Multi-Strategy Support**:
    - Accepts `strat` parameter in webhook payload.
    - Labels trades in Dashboard and Telegram with strategy name.
    - Allows performance tracking per strategy (future scope).

### 2.2 Risk Management Engine (The "Guardian")
Before any trade is sent to TopStep, it must pass the internal Risk Engine checks:
- **Single Position Limit**: **Prevents** opening a new trade if a position is already open for the same ticker (No Stacking).
- **Time filters**: Blocks trading during specific high-volatility windows.
    - *Configurable*: Users can Add/Remove blocks via UI.
    - *Toggleable*: Global "Enable/Disable" switch for time filters.
- **Daily Loss Limit**: *Removed* (Managed manually or via TopStep settings).
- **Master Switch**: A global "Kill Switch" to instantly pause all new trading.

### 2.3 Dashboard & Monitoring
A real-time React-based dashboard provides visibility and control:
- **Live Status**: Visual indication of connection status.
- **Trade Feed**: Displays history of recent trades with "Today" (since local midnight) and "7 Days" (rolling) filters. Includes **Strategy Column** to identify source of trade.
- **Daily PnL**: Real-time calculation of realized Profit & Loss.
- **System Logs**: Detailed logs timestamped in local time.
- **Account Selection**: Custom styled dropdown to select active trading account.
- **Configuration View**: **Editable** panel to configure Risk Amount ($) and Blocked Time Periods.

### 2.4 Manual Controls
- **Connect/Disconnect**: Manual initiation and termination of the API session.
- **Select Account**: Dropdown to choose which specific TopStep account to use for execution.
- **Toggle Trading**: Button to globally Enable/Pause the trading bot.
- **Close Position**: "X" button on each open position to manually close a specific contract. **Automatically cancels** any working orders (SL/TP) associated with that contract to prevent orphaned orders.
- **Flatten & Cancel All**: A "Panic" button to immediately close all positions and cancel all pending orders for the account (Protected by Confirmation Modal).
- **Mock Trading Interface**: A built-in testing tool to simulate TradingView webhooks with custom payloads (Entry, SL, TP) directly from the UI, verifying the entire execution pipeline without waiting for real market signals.

### 2.5 Telegram Remote Control (2-Way)
The bot includes a robust Telegram interface for remote management:
- **Architecture**: Long Polling (Secure, no open ports needed).
- **Security**: ID verification (Whitelist).
- **Commands**:
    - `/status`: System "Health Check" (Connection, Balance, Net PnL, Open Positions).
    - `/flatten`: **Remote Panic Button** (Closes all positions, cancels all orders).
    - `/cancel_orders`: Orphan cleanup.
    - `/switch <id>`: Changes active trading account remotely.
    - `/on` / `/off`: Toggles Master Switch.
    - `/login` / `/logout`: Manages TopStep API connection state manually.

## 3. User Flow
1.  **Initialization**: User starts the application via `start_dev.sh`.
2.  **Connection**: User clicks "Connect TopStep" in the dashboard. The system authenticates with API Keys.
3.  **Account Selection**: User selects the active trading account from the dropdown.
4.  **Signal Reception**: A webhook sends a signal (e.g., `{"ticker": "MNQ", "action": "BUY", "entry_price": 18000}`).
5.  **Validation**:
    *   Is Master Switch ON?
    *   Is Time within allowed hours?
    *   Is Daily Loss Limit respected?
6.  **execution**: If VALID, the bot calculates size and sends the order to TopStepX.
7.  **Feedback**: The dashboard updates immediately with the new trade status or rejection reason.

## 4. Technical Constraints
- **Local Execution**: The system runs locally to keep API keys secure/private.
- **Polling Architecture**: Frontend updates via polling (2s interval) rather than websockets for simplicity and robustness.
