# TopStepX Auto-Trader 🤖

A robust, automated trading bot designed to execute TradingView alerts on TopStepX with professional-grade risk management and monitoring.

## 🌟 Features

### ⚡ Execution & Automation
- **Webhook Integration**: Executes trades instantly from TradingView alerts.
- **Auto-Flatten**: Automatically closes all positions at a specific time (e.g., 20:55 UTC) to avoid holding overnight.
- **Fail-Safe Startup**: Checks for missed backups on startup and performs them if necessary, ensuring your data is always safe even if your PC was off.
- **Durable Persistence**: System state (open positions, tracking) is saved to disk, so you never lose track of a trade even if the bot restarts.
- **Orphaned Order Detection**: Automatically detects and warns about orders that don't have a matching position.
- **Telegram Control**: Monitor and control the bot remotely:
  - `/switch`: Change active trading account instantly.
  - `/flatten`: Close all positions and cancel orders.
  - Real-time notifications for Fills, P&L, and Errors.
  - Etc.

### 🛡️ Risk Guardian
- **Global Master Switch**: Instantly pause all trading with one click from the dashboard.
- **Time filters**: Prevents trading during high-volatility windows (News, Open/Close).
- **Position Sizing**: Calculates quantity based on risk settings.

### 📊 Dashboard & Monitoring
- **Real-Time Dashboard**: View open positions, P&L, contract mapping, and account stats live.
- **Ticker Mapping**: Map TradingView tickers (e.g., `MNQ`) to TopStep contracts (e.g., `MNQH6`) easily via UI.
- **System Logs**: Live logs of all actions, errors, and trade executions with 7-day auto-cleaning.
- **Toast Notifications**: Instant visual feedback for all actions.

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.9+
- Node.js & npm
- Git
- Ngrok (for Webhook URL)

### 1. Clone the Repository
```bash
git clone https://github.com/toini666/topstepbot.git
cd topstepbot
```

### 2. Configure Environment
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Edit `.env` and fill in your credentials:
```env
# TopStep / Tradovate Credentials
TOPSTEP_USERNAME=your_username
TOPSTEP_APIKEY=your_api_key

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ID=your_chat_id

# Database
DATABASE_URL=sqlite:///./topstepbot.db

# Optional: Ngrok Auth for persistent sessions
NGROK_AUTHTOKEN=your_ngrok_auth_token
```

### 3. Install Dependencies
**Backend**
```bash
cd backend
pip install -r requirements.txt
# Run migrations to setup database
alembic upgrade head
```

**Frontend**
```bash
cd ../frontend
npm install
```

---

## 🖥️ Usage

### Start the Application
Return to the root directory and use the main startup script:
```bash
./start_bot.sh
```
This script handles everything:
- Starts the Backend API.
- Starts the Frontend Dashboard.
- Checks/Starts Ngrok.
- Prevents your PC from sleeping (MacOS).

- **Dashboard**: [http://localhost:5173](http://localhost:5173)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 🌍 Ngrok & Webhook Setup

To receive alerts from TradingView, your local bot needs a public URL. This is handled by **Ngrok**.

1. **Install Ngrok**: If not already installed, download it from [ngrok.com](https://ngrok.com).
2. **Auth Token**: Run `ngrok config add-authtoken <your_token>` (get it from your Ngrok dashboard).
3. **Automatic Start**: Where you run `./start_bot.sh`, it will automatically look for Ngrok and create a tunnel. 
4. **Copy URL**: The script will print your Webhook URL in the terminal (e.g., `https://a1b2c3d4.ngrok-free.app/api/webhook`).

**Use this URL in your TradingView Alert settings.**

---

## 📡 TradingView Alert Configuration

Configure your TradingView alerts to send a JSON payload to your Webhook URL.

**Webhook URL**: `https://your-ngrok-url.app/api/webhook`

**Message (JSON Payload)**:
```json
{
  "ticker": "MNQ1!",
  "type": "SIGNAL",
  "direction": "SELL",
  "entry": 25955,
  "stop": 25980,
  "tp": 25920
}
```
*Note: You can use TradingView placeholders like `{{close}}`, `{{plot("SL")}}`, etc. to make this dynamic.*

---

## 🛠️ Maintenance & Backup

The bot handles maintenance automatically:
- **Daily Backups**: Saved to `./backups` every day at 03:00 UTC.
- **Startup Checks**: Checks if a backup exists for today on startup; if not, creates one.
- **Log Cleaning**: Logs older than 7 days are auto-deleted.

To manually restore, replace `topstepbot.db` with a file from `backups/`.

---

## ⚠️ Security Note
This application runs locally. **Your credentials and database never leave your machine.**
The `.gitignore` file ensures standard sensitive files (`.env`, `*.db`, `backups/`) are ignored by Git.
