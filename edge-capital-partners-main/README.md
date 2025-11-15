# AutoTrader - Automated Email-to-IBKR Trading Bot 🤖💰

**Professional automated trading system that executes IBKR trades based on TradingView email signals with comprehensive safety measures.**

---

## 📋 Overview

This trading bot:
- **Monitors Gmail 24/7** for TradingView email signals
- **Automatically places trades** in Interactive Brokers (IBKR) accounts
- **Implements bracket orders** with dynamic stop-loss and take-profit
- **Prevents short selling** through multiple safety layers
- **Tracks all trades** with persistent logging and position management
- **Operates in demo mode** when credentials are incomplete (perfect for testing)

---

## 🚀 Quick Start Guide

### Step 1: Download and Setup

```bash
# Clone the repository
git clone https://github.com/Edge-Capital-Partners/edge-capital-partners.git
cd edge-capital-partners-main

# Run the one-command setup
chmod +x manage_trader.sh
./manage_trader.sh setup
```

### Step 2: Configure Your Credentials

The setup script will guide you through configuring:

**A) Edit `.env` file:**
```bash
nano .env
```

**B) Edit trade configuration:**
```bash
nano config/trade_config_version_B.csv
```

### Step 3: Start Trading

```bash
# Start the bot
./manage_trader.sh start

# Check status
./manage_trader.sh status

# View logs
./manage_trader.sh logs
```

---

## 🔧 Configuration Files

### A) Environment Configuration (`.env`)

**The setup script creates this file from `sample.env`. Edit it with your credentials:**

```env
# Email Settings (Gmail with App Password)
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=your-16-character-app-password
SENDER_EMAIL=noreply@tradingview.com

# IBKR Settings
IB_API_HOST=127.0.0.1
IB_API_PORT=7497
IBKR_ACCOUNT=your-account-number

# Telegram Notifications (Optional)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_ECP_CHANNEL_CHAT_ID=your-chat-id
```

### 🔑 How to Get Each Credential

#### **Gmail App Password (EMAIL_PASS)**

**⚠️ CRITICAL: Do NOT use your regular Gmail password!**

1. **Go to [Google Account Settings](https://myaccount.google.com/)**
2. **Security** → **2-Step Verification** (must be enabled first)
3. **Search for**: "App passwords" or go to [App Passwords](https://myaccount.google.com/apppasswords)
4. **Select app**: "Mail" 
5. **Select device**: "Other" → Type "AutoTrader"
6. **Click Generate** → Copy the 16-character password (like `abcd efgh ijkl mnop`)
7. **Use this password** in `EMAIL_PASS` (remove spaces: `abcdefghijklmnop`)

**Example:**
```env
EMAIL_USER=john.smith@gmail.com
EMAIL_PASS=abcdefghijklmnop
```

#### **IBKR Account Details**

**Paper Trading Account (Recommended for Testing):**
1. **Login to IBKR Client Portal**
2. **Account Management** → **Trade Permissions** 
3. **Enable Paper Trading** if not already active
4. **Your paper account** will be in format: `DU123456`
5. **Use paper account** number for `IBKR_ACCOUNT`

**Live Trading Account:**
1. **Account number** format: `U123456` 
2. **⚠️ WARNING**: This trades real money!
3. **Test thoroughly** with paper trading first

**API Port Settings:**
- **TWS (Trader Workstation)**: `7497`
- **IB Gateway**: `4001` 
- **Paper Trading**: Usually `7497`

**Example:**
```env
IB_API_HOST=127.0.0.1
IB_API_PORT=7497
IBKR_ACCOUNT=DU123456
```

#### **TradingView Sender Email (SENDER_EMAIL)**

**This is the email address that TradingView sends alerts from:**

**Common TradingView senders:**
- `noreply@tradingview.com` (most common)
- `alerts-noreply@tradingview.com`
- Custom webhook senders (if using webhooks)

**To find your sender:**
1. **Check existing TradingView emails** in your Gmail
2. **Look at "From" field** 
3. **Copy exact email address**

**Example:**
```env
SENDER_EMAIL=noreply@tradingview.com
```

#### **Telegram Bot (Optional but Recommended)**

**Step 1: Create Telegram Bot**
1. **Open Telegram** and search for `@BotFather`
2. **Send**: `/newbot`
3. **Choose bot name**: "My Trading Bot"
4. **Choose username**: "my_trading_bot_12345"
5. **Copy the token**: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

**Step 2: Get Chat ID**
1. **Add your bot** to a channel/group or message it directly
2. **Send a test message** to the bot
3. **Visit**: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. **Look for**: `"chat":{"id":-123456789}` in the response
5. **Copy the chat ID** (including the minus sign if present)

**Example:**
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_ECP_CHANNEL_CHAT_ID=-123456789
```

### 📝 Complete Example `.env` File

```env
# Email Settings
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USER=john.smith@gmail.com
EMAIL_PASS=abcdefghijklmnop
SENDER_EMAIL=noreply@tradingview.com

# IBKR Settings  
IB_API_HOST=127.0.0.1
IB_API_PORT=7497
IBKR_ACCOUNT=DU123456

# Telegram Notifications
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_ECP_CHANNEL_CHAT_ID=-123456789
```

### B) Trading Configuration (`config/trade_config_version_B.csv`)

```csv
ibkr_account,ticker,price,quantity
DU123456,BTCUSD,50000,1
DU123456,AAPL,150,10
DU123456,GOOGL,2800,5
```

---

## 📧 Email Signal Format

### Expected Email Structure

**Subject Format:**
```
Alert: Top Overall 15M BTCUSD nSkew v3 3%SL 5%TP
```
- Extracts: `SL = 3%`, `TP = 5%`

**Body Format:**
```
ECP nSkew SL TP v3 (, 14, 70, -30, 5, 1): BUY Signal Activated order buy @ 100242 for 12.264199 filled on BTCUSD at 2025-11-07T12:00:00Z. New strategy position is 12.264199
```

**Key Elements Extracted:**
- **Action**: `buy` or `sell`
- **Price**: `100242`
- **Quantity**: `12.264199`
- **Ticker**: `BTCUSD`
- **Timestamp**: `2025-11-07T12:00:00Z`
- **SL/TP from body**: `5%` and `1%` (positions 4 and 5 in the parameters)

### SL/TP Priority Logic

1. **Body parameters take priority** (more trade-specific)
2. **Subject parameters as fallback** (general strategy parameters)
3. **First extracted values are sent to IBKR immediately**

---

## 🛡️ Safety Features & Trading Logic

### 🔒 Anti-Shorting Protection (Multi-Layer)

#### **Layer 1: IBKR Position Validation**
```python
# Checks actual IBKR position before any sell
if position <= 0:
    BLOCK_SELL("No long position exists")
```

#### **Layer 2: Bot Trade Tracking**
```python
# Only sells what the bot previously bought
if requested_quantity > bot_open_quantity:
    BLOCK_SELL("Bot doesn't own enough shares")
```

#### **Layer 3: Quantity Validation**
```python
# Never sells more than owned
validated_quantity = min(requested, ibkr_position, bot_owned)
```

### 📊 Position Management

#### **Bot Trade Tracking System**
- **Persistent logging** of all bot trades in `bot_trades.json`
- **Order ID tracking** for precise trade matching
- **FIFO selling** - oldest buys are closed first
- **Position reconciliation** on startup

#### **Trade State Management**
```json
{
  "order_id": "12345",
  "ticker": "BTCUSD",
  "action": "BUY", 
  "quantity": 1,
  "price": 50000,
  "status": "filled",
  "is_closed": false,
  "sl_pct": 3,
  "tp_pct": 5
}
```

### ⚖️ Trading Rules

#### **Long-Only Strategy**
- ✅ **BUY signals**: Always allowed (with fund checking)
- ⚠️ **SELL signals**: Only if bot has open long position
- ❌ **SHORT positions**: Never allowed under any circumstance

#### **Bracket Order Implementation (Version B)**
```python
# Automatic SL/TP orders with every buy
bracket_order = ib.bracketOrder(
    'BUY', 
    quantity, 
    entry_price,
    take_profit_price,  # entry_price * (1 + tp_pct/100)
    stop_loss_price     # entry_price * (1 - sl_pct/100)
)
```

---

## 🖥️ Operating Modes

### 🔄 Demo Mode (Automatic)

**Activates when:**
- IBKR credentials missing or invalid
- Connection to TWS/Gateway fails
- Account number is placeholder value

**In Demo Mode:**
- ✅ **Full email processing** and parsing
- ✅ **Safety validation** testing
- ✅ **Trade logging** with mock order IDs
- ✅ **All notifications** and alerts
- ❌ **No real trades** placed

**Perfect for:**
- Testing email signal parsing
- Validating safety mechanisms
- Training users
- Development and debugging

### 💰 Live Mode

**Requirements:**
- Valid IBKR credentials in `.env`
- TWS or IB Gateway running with API enabled
- Proper position and fund availability

**Features:**
- 🔴 **Real money trading**
- 📊 **Live position tracking**
- 🚨 **Real-time safety validation**
- 💬 **Telegram trade notifications**

---

## 📱 Daily Operations

### Essential Commands

```bash
# Check bot status
./manage_trader.sh status

# View recent activity
./manage_trader.sh logs

# Start/stop trading
./manage_trader.sh start
./manage_trader.sh stop

# Emergency shutdown
./manage_trader.sh emergency

# Health diagnostics
./manage_trader.sh health

# Update bot (monthly)
./manage_trader.sh update
```

### Monitoring & Alerts

#### **Log Files**
- **`log/application.log`** - General bot activity
- **`log/trade.log`** - Trade execution details
- **`log/position_safety.log`** - Safety validation audit trail

#### **Trade Tracking File**
- **`bot_trades.json`** - Complete bot trade history
- **Auto-backup** system with recovery
- **Thread-safe** atomic file operations

---

## 🔧 Interactive Brokers Setup

### Download & Install TWS

1. **Go to**: [Interactive Brokers Download Page](https://www.interactivebrokers.com/en/trading/tws.php)
2. **Download**: Latest TWS version for your operating system
3. **Install**: Follow the installer prompts
4. **Create Account**: If you don't have one yet
   - **Paper Trading**: Recommended for testing
   - **Live Trading**: Only after thorough testing

### Critical TWS API Configuration

**⚠️ IMPORTANT: These settings MUST be configured or the bot won't work!**

#### **Step 1: Enable API Access**
1. **Open TWS** and login with your credentials
2. **File** → **Global Configuration** (or press Ctrl+Alt+U)
3. **API** → **Settings** (left sidebar)
4. **✅ Check**: "Enable ActiveX and Socket Clients"
5. **✅ Check**: "Download open orders on connection"
6. **✅ Check**: "Allow connections from localhost only" (for security)

#### **Step 2: Set Socket Port**
1. **Still in API Settings**
2. **Socket port**: 
   - **Paper Trading**: `7497` (most common)
   - **Live Trading**: `7497` 
   - **IB Gateway**: `4001`
3. **Master Client ID**: Leave as `0`
4. **✅ Check**: "Create API message log file"

#### **Step 3: Configure Trusted IPs** 
1. **Still in API Settings** 
2. **Trusted IPs** section (bottom)
3. **Click**: "+" or "Add" button
4. **Enter**: `127.0.0.1` (localhost)
5. **Click**: "OK"

#### **Step 4: Apply Settings**
1. **Click**: "Apply" button
2. **Click**: "OK" to close configuration
3. **⚠️ CRITICAL**: **Restart TWS completely**
4. **Login again** and verify settings saved

### Advanced TWS Configuration

#### **Memory Allocation (Important)**
1. **Configure** → **Settings** → **Lock and Exit**
2. **Memory Allocation**: Set to `4096 MB` minimum
3. **Why**: Prevents crashes during bulk data operations
4. **Apply** and restart TWS

#### **Auto-Login (Optional)**
1. **Configure** → **Settings** → **Lock and Exit**
2. **✅ Check**: "Bypass Password"
3. **⚠️ Security**: Only use on secure computers

#### **Market Data Subscriptions**
1. **Account Management** → **Market Data Subscriptions**
2. **Ensure you have permissions** for:
   - **US Securities** (for AAPL, GOOGL, etc.)
   - **Cryptocurrency** (for BTCUSD if trading crypto)
3. **Some data is free** for paper trading

### Verification Steps

#### **Test API Connection**
1. **Start TWS** with API enabled
2. **Run this test** in terminal:
```bash
# Test if TWS API port is open
nc -zv localhost 7497
# Should show: Connection to localhost port 7497 [tcp/*] succeeded!
```

#### **Check TWS API Status**
1. **In TWS**: Look for **green "API"** indicator in status bar
2. **If red**: API is disabled or misconfigured
3. **Click the API indicator** to see connection details

### Common TWS Issues & Fixes

#### **"API connection failed"**
1. **Check TWS is running** and logged in
2. **Verify API is enabled** (green API indicator)
3. **Check port number** matches `.env` file
4. **Restart TWS** after any API settings changes

#### **"Trusted IP" errors**
1. **Ensure `127.0.0.1` is in trusted IPs**
2. **Try adding**: `::1` (IPv6 localhost) as well
3. **Restart TWS** after changes

#### **TWS crashes with bot**
1. **Increase memory allocation** to 4096 MB
2. **Update to latest TWS version**
3. **Close unnecessary TWS windows/charts**

### Paper vs Live Trading Setup

#### **Paper Trading (Recommended First)**
- **Account Format**: DU123456
- **Port**: Usually 7497
- **Benefits**: 
  - ✅ Risk-free testing
  - ✅ Same functionality as live
  - ✅ Real market data
  - ✅ Practice with actual bot

#### **Live Trading (After Paper Testing)**
- **Account Format**: U123456  
- **Port**: Usually 7497
- **⚠️ Requirements**:
  - Successful paper trading tests
  - Understanding of all safety features
  - Adequate account funding
  - Risk management plan

### Quick Setup Checklist

```
□ TWS installed and can login
□ API enabled (File → Global Configuration → API)
□ Socket port set (7497 for most users)
□ Trusted IP added (127.0.0.1)
□ "Download open orders" checked
□ Settings applied and TWS restarted
□ Green "API" indicator visible in TWS
□ Port connectivity test passes
□ Account number matches .env file
```

**✅ When all checkboxes are complete, TWS is ready for the bot!**

---

## ⚠️ Risk Management

### Built-in Safety Measures

#### **Position Limits**
- **Maximum position size** defined in trade config
- **Quantity validation** before every order
- **Balance checking** before buy orders

#### **Order Validation**
- **Market hours detection** (switches to limit orders outside hours)
- **Price reasonableness** checks
- **Duplicate order prevention**

#### **Emergency Procedures**
```bash
# Immediate stop (kills all processes)
./manage_trader.sh emergency

# Graceful stop
./manage_trader.sh stop

# Check what's running
./manage_trader.sh status
```

### Error Handling

#### **Connection Failures**
- **Automatic reconnection** to email server
- **IBKR connection recovery** with retry logic
- **Fallback to demo mode** if IBKR unavailable

#### **Email Parsing Errors**
- **Detailed logging** of failed parses
- **Telegram alerts** for critical issues
- **Continue processing** other emails

#### **File Corruption Protection**
- **Automatic backups** of trade logs
- **Atomic file operations**
- **Recovery procedures** for corrupted data

---

## 📊 Performance & Monitoring

### Real-Time Metrics

#### **Trade Statistics**
```bash
# View trade summary
./manage_trader.sh logs | grep "Bot trade logged"

# Check position status
./manage_trader.sh health
```

#### **Safety Statistics**
- **Blocked sells**: Count of prevented short positions
- **Position mismatches**: Bot vs IBKR reconciliation issues
- **Validation failures**: Safety system effectiveness

### Telegram Integration

#### **Notifications Sent:**
- ✅ **Successful trades**: "Order placed: BUY BTCUSD x1 @ $50,000"
- 🚨 **Blocked trades**: "SELL ORDER BLOCKED: No bot position"
- ⚠️ **System errors**: "Email parsing failed"
- 🔄 **Status updates**: "Bot started/stopped"

---

## 🔄 Maintenance & Updates

### Monthly Update Process

```bash
# Automated update (stops bot, pulls changes, restarts)
./manage_trader.sh update
```

**Update Process:**
1. **Gracefully stops** current bot
2. **Downloads latest** code changes
3. **Updates dependencies**
4. **Preserves configuration** and trade logs
5. **Restarts bot** automatically
6. **Validates functionality**

### Backup Procedures

#### **Automatic Backups**
- **Trade logs**: `.backup` files created automatically
- **Configuration**: Preserved during updates
- **Log rotation**: Prevents disk space issues

#### **Manual Backup**
```bash
# Backup trade history
cp bot_trades.json bot_trades_backup_$(date +%Y%m%d).json

# Backup configuration
cp .env env_backup_$(date +%Y%m%d).env
```

---

## 🐛 Troubleshooting

### Common Issues

#### **"No trades happening"**
1. **Check email credentials**: Gmail app password correct?
2. **Verify sender email**: Matches TradingView sender exactly?
3. **Check TWS connection**: API enabled and running?
4. **Review logs**: `./manage_trader.sh logs`

#### **"Sell orders blocked"**
- ✅ **This is normal** - safety system working correctly
- **Check**: Do you have open long positions from bot?
- **Review**: `log/position_safety.log` for details

#### **"Demo mode won't disable"**
1. **Verify IBKR credentials** in `.env` file
2. **Check TWS is running** with API enabled
3. **Test connection**: `./manage_trader.sh check-tws`

### Advanced Diagnostics

#### **Health Check**
```bash
./manage_trader.sh health
```
**Checks:**
- Python environment
- File permissions
- IBKR connection
- Email configuration
- Trade log integrity

#### **Manual Testing**
```bash
# Test email parsing (place test email in inbox)
./manage_trader.sh logs | tail -20

# Verify position tracking
cat bot_trades.json | python3 -m json.tool
```

---

## 🔒 Security Best Practices

### Email Security
- ✅ **Use Gmail app passwords** (never regular password)
- ✅ **Enable 2FA** on Gmail account
- ✅ **Dedicated email** for trading signals only

### IBKR Security
- ✅ **Paper trading first** for all testing
- ✅ **API IP restrictions** to localhost only
- ✅ **Regular password changes**
- ✅ **Monitor account** for unexpected activity

### System Security
- ✅ **Regular updates** with `./manage_trader.sh update`
- ✅ **Log file monitoring**
- ✅ **Backup verification**

---

## 📞 Support & Contact

### Self-Service Diagnostics
```bash
# Complete system check
./manage_trader.sh health

# Recent activity
./manage_trader.sh logs

# Error investigation
cat log/position_safety.log | tail -20
```

### When Contacting Support

**Include:**
1. **Output of**: `./manage_trader.sh health`
2. **Recent logs**: Last 50 lines of main log
3. **Description**: What you were trying to accomplish
4. **Error messages**: Exact text of any error messages

### Emergency Contact

**Immediate Issues:**
- Bot placing unexpected trades
- Safety systems not working
- System compromised

**Action:**
1. **Stop immediately**: `./manage_trader.sh emergency`
2. **Secure account**: Change IBKR passwords
3. **Contact support**: With full diagnostic output

---

## 📈 Advanced Features

### Version A vs Version B

#### **Version A (Simple Orders)**
- **Market/Limit orders** only
- **No automatic SL/TP**
- **Basic position tracking**
- **Suitable for**: Manual SL/TP management

#### **Version B (Bracket Orders) - Recommended**
- **Automatic SL/TP** from email parameters
- **Advanced position tracking**
- **Comprehensive safety features**
- **Suitable for**: Fully automated trading

### Custom Modifications

#### **Adding New Tickers**
1. **Edit**: `config/trade_config_version_B.csv`
2. **Add row**: `account,NEW_TICKER,price,quantity`
3. **Restart bot**: `./manage_trader.sh restart`

#### **Adjusting Position Sizes**
- **Modify quantity** in trade config
- **Changes apply** to new trades only
- **Existing positions** unchanged

---

## 📚 Technical Details

### Email Parsing Engine
- **Dual extraction**: Subject and body SL/TP parsing
- **Robust regex**: Handles format variations
- **Priority logic**: Body parameters override subject
- **Error recovery**: Continues processing on parse failures

### Position Management System
- **Persistent storage**: JSON-based trade tracking
- **ACID compliance**: Atomic file operations
- **State reconciliation**: Startup sync with IBKR
- **Audit trail**: Complete trade history

### Safety Architecture
- **Multi-layer validation**: Three independent safety checks
- **Fail-safe design**: Blocks unsafe trades by default
- **Comprehensive logging**: Full audit trail
- **Real-time alerts**: Immediate notification of issues

---

*Last Updated: November 2025*  
*Version: 2.0 - Enhanced Safety & Demo Mode*  

**⚠️ Trading involves substantial risk of loss. Past performance is not indicative of future results. Use paper trading for testing. Never risk more than you can afford to lose.**