# AutoTrader Setup Guide 🤖💰

**For Non-Technical Users - Complete Mac Setup Guide**

This trading bot automatically reads emails from TradingView and places trades in your Interactive Brokers account 24/7.

---

## 📋 What You Need Before Starting

✅ **Mac computer** (macOS 10.14 or newer)  
✅ **Interactive Brokers account** with Paper Trading enabled  
✅ **Gmail account** that receives TradingView alerts  
✅ **Admin password** for your Mac  

---

## 🚀 Quick Start (Copy & Paste Each Step)

### Step 1: Download the Project

1. **Open Terminal** (Press `Cmd + Space`, type "Terminal", press Enter)

2. **Navigate to your Desktop:**
```bash
cd ~/Desktop
```

3. **Download the project:**
```bash
git clone https://github.com/Edge-Capital-Partners/edge-capital-partners.git
cd edge-capital-partners
```

### Step 2: Run the Setup Script

**Copy and paste this single command:**
```bash
chmod +x manage_trader.sh && ./manage_trader.sh setup
```

This will:
- Install Python dependencies
- Check your system
- Guide you through configuration
- Set up the trading bot

**⚠️ Important: Follow the prompts and provide the information when asked**

---

## 🔧 Configuration Files You Need to Complete

### A) Email Configuration (.env file)

The setup script will help you create this, but here's what you need:

**Gmail Settings:**
- Email: `your-email@gmail.com`
- App Password: (Google App Password - NOT your regular password)

**How to get Gmail App Password:**
1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Security → App passwords
3. Generate password for "Mail"
4. Use that 16-character password

### B) IBKR Settings

You'll need:
- IBKR Account Number
- TWS API Port (usually 7497 for live, 4001 for paper)

### C) Trading Configuration

Create file: `config/trade_config_version_B.csv`
```csv
ibkr_account,ticker,price,quantity
YOUR_ACCOUNT_NUMBER,BTCUSD,50000,1
YOUR_ACCOUNT_NUMBER,AAPL,150,10
```

---

## 🖥️ Interactive Brokers TWS Setup

### Download & Install TWS

1. **Download TWS:** [Interactive Brokers Download](https://www.interactivebrokers.com/en/trading/tws.php)
2. **Install TWS** following the installer prompts
3. **Login to TWS** with your IBKR credentials

### Configure TWS API (CRITICAL STEP)

**Step 1: Enable API**
1. In TWS, go to **File → Global Configuration**
2. Click **API → Settings**
3. ✅ Check "Enable ActiveX and Socket Clients"
4. ✅ Check "Download open orders on connection"
5. Set **Socket Port** to `7497` (or `4001` for paper trading)

**Step 2: Add Trusted IP**
1. Still in API Settings
2. **Trusted IPs** section
3. Click **Add** 
4. Enter: `127.0.0.1`
5. Click **OK**

**Step 3: Save Settings**
1. Click **Apply**
2. Click **OK**
3. **Restart TWS**

---

## 🔄 Daily Operations

### Check Bot Status
```bash
./manage_trader.sh status
```

### Start the Trading Bot
```bash
./manage_trader.sh start
```

### Stop the Trading Bot
```bash
./manage_trader.sh stop
```

### View Recent Logs
```bash
./manage_trader.sh logs
```

### Update Bot (when Seyed pushes changes)
```bash
./manage_trader.sh update
```

---

## 📊 What to Expect

### Normal Operation
- Bot runs silently in background 24/7
- Checks email every few seconds
- Places trades automatically when TradingView signals arrive
- Logs all activity to `log/` folder

### Email Format Expected
**Subject:** `Alert: Top Overall 15M BTCUSD nSkew v3 3%SL 5%TP`
**Body:** Contains trade details like "BUY Signal Activated order buy @ 50000..."

### Trade Types
- **Long positions only** (no shorting)
- **Bracket orders** with automatic stop-loss and take-profit
- **Paper trading recommended** for testing

---

## ⚠️ Troubleshooting

### "Bot won't start"
1. Check TWS is running: `./manage_trader.sh check-tws`
2. Verify API settings in TWS
3. Check logs: `./manage_trader.sh logs`

### "No trades happening"
1. Check email is being received
2. Verify sender email in `.env` matches TradingView sender
3. Check trade config CSV has correct account number

### "Permission denied"
```bash
chmod +x manage_trader.sh
```

### "Python not found"
Install Python from [python.org](https://www.python.org/downloads/)

### TWS Connection Issues
1. Restart TWS
2. Check API port number matches `.env` file
3. Verify trusted IP (127.0.0.1) is added

---

## 🔒 Safety Features

- **No Short Selling**: Bot only places long positions
- **Position Validation**: Checks existing positions before selling
- **Paper Trading**: Test with virtual money first
- **Detailed Logging**: All trades logged for review
- **Manual Override**: You can stop the bot anytime

---

## 📞 Getting Help

### Quick Self-Help
```bash
./manage_trader.sh doctor    # Diagnoses common issues
./manage_trader.sh logs      # Shows recent activity
```

### Contact Seyed
- Include the output of: `./manage_trader.sh status`
- Include recent logs: `./manage_trader.sh logs`
- Describe what you were trying to do

---

## 🔄 Monthly Updates

When Seyed pushes updates:

```bash
./manage_trader.sh update
```

This will:
1. Stop the current bot
2. Download latest changes  
3. Update dependencies
4. Restart the bot
5. Confirm everything is working

---

## ⚡ Emergency Stops

**Stop Everything Immediately:**
```bash
./manage_trader.sh emergency-stop
```

**Stop Just the Bot:**
```bash
./manage_trader.sh stop
```

**Check What's Running:**
```bash
./manage_trader.sh status
```

---

*Last Updated: November 2025*  
*Questions? Contact Seyed with the output of `./manage_trader.sh doctor`*