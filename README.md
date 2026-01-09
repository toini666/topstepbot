# TopStepX Auto-Trader

A robust, local automated trading bot designed to execute TradingView alerts on TopStepX with strict risk management.

## 🌟 Features
- **Automated Execution**: Webhook-based order placement.
- **Risk Guardian**: 
    - Daily Loss Limit.
    - Configurable "No-Trade" Time Windows (Brussels Time).
    - **Master Switch** to instantly pause trading.
- **Dashboard**: Real-time monitoring of trades, P&L, and system logs.
- **Secure**: Runs locally, keeping your API keys safe.

## 🚀 Setup & Installation

### Prerequisites
- Python 3.9+
- Node.js & npm

### 1. Configuration
Create a `.env` file in the root directory (copy from `.env.example`):
```bash
cp .env.example .env
```
Fill in your TopStepX credentials:
```env
TOPSTEP_USERNAME=your_username
TOPSTEP_APIKEY=your_api_key
TOPSTEP_URL=https://api.topstepx.com
DATABASE_URL=sqlite:///./trading_bot.db
```

### 2. Install Dependencies
**Backend**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend**
```bash
cd frontend
npm install
```

## 🖥️ Usage

### Start the Application
Use the helper script to start both Backend and Frontend servers:
```bash
./start_dev.sh
```
- **Dashboard**: Open [http://localhost:5173](http://localhost:5173) in your browser.
- **API Docs**: Access Swagger UI at [http://localhost:8000/docs](http://localhost:8000/docs).

### Workflow
1.  **Connect**: On the dashboard, click **"Connect TopStep"**.
2.  **Select Account**: Choose your funded/challenge account from the list.
3.  **Enable Trading**: Ensure the configuration status says **"TRADING ON"**.
4.  **Send Signals**: Point your TradingView alerts to your webhook URL (e.g., via ngrok):
    - URL: `https://your-ngrok-url.io/api/webhook`
    - Payload:
    ```json
    {
      "ticker": "MNQ",
      "action": "BUY",
      "entry_price": 18500,
      "sl_offset": 20,
      "tp_offset": 40
    }
    ```

## 🛡️ Risk Management
- **Blocked Times**: Trading is disabled by default during high volatility windows (e.g. 15:25-15:45 Brussels Time). 
- **Daily Loss**: Trading stops if daily P&L hits the limit (default -$1000).

## 📂 Project Structure
- `backend/`: FastAPI application, database models, and trading logic.
- `frontend/`: React + Vite dashboard application.
- `docs/`: Detailed Product Requirements and Architecture validation.
