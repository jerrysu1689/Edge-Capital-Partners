# import argparse
# from datetime import datetime, time
# import os
# import logging
# import logging.config
# import threading
# import time as time_lib
# from typing import Optional
# from dotenv import load_dotenv
# import certifi
# from ib_insync import *
# import telebot
# import base64
# import hmac
# import hashlib
# import requests
# import ccxt
# import asyncio
# import pytz

# load_dotenv()

# main_logger = logging.getLogger('trade')

# IB_API_HOST = os.getenv("IB_API_HOST")
# IB_API_PORT = os.getenv("IB_API_PORT")
# IBKR_ACCOUNT = os.getenv("IBKR_ACCOUNT")
# KUCOIN_API_BASE_URL = os.getenv("KUCOIN_API_BASE_URL")
# KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY")
# KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET")
# KUCOIN_API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# TELEGRAM_ECP_CHANNEL_CHAT_ID = os.getenv("TELEGRAM_ECP_CHANNEL_CHAT_ID")
# telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


# ib = None
# trades = []
# EDT_timezone = pytz.timezone('America/Toronto')

# # Setup IB connection
# def setup_ib_connection():
#     global ib
#     client_id = 0
#     ib = IB()
#     while not ib.isConnected():
#         try:
#             ib.connect(IB_API_HOST, IB_API_PORT, clientId=client_id)
#             main_logger.info(f"Connected to IBKR client id: {client_id}")
#         except asyncio.exceptions.TimeoutError as e:
#             client_id += 1
#     return ib


# def on_trade_status(trade):
#     """Callback function for trade status updates."""
#     global trades
#     main_logger.debug(f"{trade.contract.symbol} order status: {trade.orderStatus.status}")
#     if trade.isDone():
#         main_logger.info(f"{trade.contract.symbol} trade is done.")
#         trades.remove(trade)


# # Setup KuCoin connection
# # exchange = ccxt.kucoin({
# #     'apiKey': KUCOIN_API_KEY,
# #     'secret': KUCOIN_API_SECRET,
# #     'password': KUCOIN_API_PASSPHRASE,
# #     'enableRateLimit': True,  # recommend enabling rate limit in ccxt
# #     'timeout': 60000,
# #     'certfile': certifi.where()
# # })


# def fetch_open_positions(account: str) -> dict:
#     open_positions = {}
#     for position in ib.positions(account=account):
#         open_positions[position.contract.symbol] = position
#     return open_positions


# def fetch_open_orders() -> dict:
#     open_orders = {}
#     for trade in ib.openTrades():
#         main_logger.info(f"Open trade: {trade}")
#         open_orders.setdefault(trade.contract.symbol, [])
#         open_orders[trade.contract.symbol].append(trade)
#     return open_orders


# def fetch_kucoin_positions(method: str, endpoint: str):
#     now = int(time_lib.time() * 1000)
#     str_to_sign = str(now) + method + endpoint
#     signature = base64.b64encode(hmac.new(KUCOIN_API_SECRET.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())

#     passphrase = base64.b64encode(hmac.new(KUCOIN_API_SECRET.encode('utf-8'), KUCOIN_API_PASSPHRASE.encode('utf-8'), hashlib.sha256).digest())
#     headers = {
#         "KC-API-SIGN": signature,
#         "KC-API-TIMESTAMP": str(now),
#         "KC-API-KEY": KUCOIN_API_KEY,
#         "KC-API-PASSPHRASE": passphrase,
#         "KC-API-KEY-VERSION": "2"
#     }
#     response = requests.request(method, KUCOIN_API_BASE_URL + endpoint, headers=headers)
#     print(response.status_code)
#     return response.json()


# def place_order(ticker: str, action: str, quantity: int, price: float, notification_datetime: datetime, sl_pct: Optional[float], tp_pct: Optional[float], args: argparse.Namespace):
#     global ib
#     contract = Stock(ticker, exchange="SMART", currency="USD")
    
#     def place_and_track_order(order: Order):
#         trade = ib.placeOrder(contract, order)
#         trade.statusEvent += on_trade_status
#         trades.append(trade)
#         return trade
    
#     open_stock_positions = fetch_open_positions(IBKR_ACCOUNT)
#     open_stock_orders = fetch_open_orders()
#     order = None
#     bracket_order = False
#     preferred_order_type = "MIDPRICE"
#     limit_price = None
#     price = round(price, 2)
#     notification_time_EDT = notification_datetime.astimezone(EDT_timezone).time()
#     if notification_time_EDT < time(9, 30, tzinfo=EDT_timezone) or notification_time_EDT > time(15, 59, tzinfo=EDT_timezone):
#         main_logger.info(f"Order type set to LMT as notification datetime is outside of trading hours: {notification_datetime}")
#         preferred_order_type = "LMT"
#         limit_price = price
    
#     if action == "SELL":
#         if ticker in open_stock_orders:
#             main_logger.warning(f"Sell order for {ticker} already placed.")
#             return
#         elif ticker in open_stock_positions:
#             quantity = open_stock_positions[ticker].position
#         else:
#             main_logger.warning(f"Sell order for {ticker} not placed as no open position found.")
#             return

#     if args.version == "A" or action == "SELL" or (not sl_pct and not tp_pct):
#         # TODO: add check balance b4 placing order
#         order = Order(
#             action=action,
#             lmtPrice=limit_price,
#             totalQuantity=quantity, 
#             orderType=preferred_order_type,
#             tif="GTC",
#             account=IBKR_ACCOUNT
#         )
#     elif args.version == "B" and action == "BUY":
#         bracket_order = ib.bracketOrder('BUY',1, price, round(price*(1+tp_pct/100), 2), round(price*(1-sl_pct/100), 2), account=IBKR_ACCOUNT)

#     if args.version == "B" and action == "SELL":
#         for open_bracket_order in open_stock_orders.get(ticker, []):
#             open_bracket_order.cancel()

#     trade_log_message = None
#     if order:
#         if not ib.isConnected():
#             ib = setup_ib_connection()
#         place_and_track_order(order)
#         trade_log_message = f"Order (id: {order.orderId}) placed: {action} {ticker} x{quantity}. Order type: {preferred_order_type} triggered at ${price}"  
#     elif bracket_order:
#         if not ib.isConnected():
#             ib = setup_ib_connection()
#         for o in bracket_order:
#             o.tif = "GTC"
#             if o.action == 'BUY':
#                 o.ordetType = preferred_order_type
#                 o.limitPrice = None
#             main_logger.info(f"Placing bracket order: {o}")
#             place_and_track_order(o)
#         trade_log_message = f"Bracket Order (id: {bracket_order[0].orderId}) placed: {action} {ticker} x{quantity}. " \
#                             f"Order type: {preferred_order_type} triggered at ${price}. "\
#                             f"TP: ${bracket_order[1].lmtPrice}, SL: ${bracket_order[2].auxPrice}"

#     if trade_log_message:
#         main_logger.info(trade_log_message)
#         if notification_datetime.date() == datetime.today().date():
#             telegram_bot.send_message(TELEGRAM_ECP_CHANNEL_CHAT_ID, trade_log_message)


# def place_ibkr_order(ticker: str, action: str, quantity: int, price: float, notification_datetime: datetime, sl_pct: Optional[float], tp_pct: Optional[float], args: argparse.Namespace):
#     if action.lower() == "buy":
#         place_order(ticker, "BUY", quantity, price, notification_datetime, sl_pct, tp_pct, args)
#     elif action.lower() == "sell":
#         place_order(ticker, "SELL", quantity, price, notification_datetime, sl_pct, tp_pct, args)


# def place_crypto_order(ticker: str, action: str, quantity: int, price: float, notification_datetime: datetime):
#     global exchange
#     order = None
#     open_crypto_positions = {}
#     if action.lower() == "buy":
#         # TODO: add check balance b4 placing order
#         order = exchange.create_order(
#             symbol=ticker,
#             type='limit',
#             side='buy',
#             amount=quantity,
#             price=price
#         )
#     elif action.lower() == "sell":
#         if ticker in open_crypto_positions:
#             order = exchange.create_order(
#                 symbol=ticker,
#                 type='limit',
#                 side='sell',
#                 amount=quantity,
#                 price=price
#             )
#         else:
#             main_logger.warning(f"Sell order for {ticker} not placed as no open position found.")
#     if order:
#         trade_log_message = f"Order placed: {action} {ticker} x{quantity} triggered at ${price}"
#         main_logger.info(trade_log_message)
#         if notification_datetime.date() == datetime.today().date():
#             telegram_bot.send_message(TELEGRAM_ECP_CHANNEL_CHAT_ID, trade_log_message)


import argparse
from datetime import datetime, time
import os
import logging
import logging.config
import threading
import time as time_lib
from typing import Optional, Dict, List, Tuple
import json
import fcntl
import shutil
from dotenv import load_dotenv
import certifi
from ib_insync import *
import telebot
import base64
import hmac
import hashlib
import requests
import ccxt
import asyncio
import pytz

load_dotenv()

main_logger = logging.getLogger('trade')

# Configuration with validation
IB_API_HOST = os.getenv("IB_API_HOST", "127.0.0.1")
IB_API_PORT = os.getenv("IB_API_PORT", "7497")
IBKR_ACCOUNT = os.getenv("IBKR_ACCOUNT", "DEMO_ACCOUNT")
KUCOIN_API_BASE_URL = os.getenv("KUCOIN_API_BASE_URL")
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY")
KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET")
KUCOIN_API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ECP_CHANNEL_CHAT_ID = os.getenv("TELEGRAM_ECP_CHANNEL_CHAT_ID")

# Demo mode detection
DEMO_MODE = (
    not IBKR_ACCOUNT or 
    IBKR_ACCOUNT in ["", "YOUR_ACCOUNT_NUMBER", "DEMO_ACCOUNT"] or
    not IB_API_PORT or 
    IB_API_PORT in ["", "YOUR_PORT"]
)

if DEMO_MODE:
    main_logger.warning("🔄 DEMO MODE ACTIVATED - No actual trades will be placed")
    telegram_bot = None
else:
    try:
        telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
    except:
        telegram_bot = None

ib = None
trades = []
EDT_timezone = pytz.timezone('America/Toronto')

# Bot trade tracking
BOT_TRADES_FILE = "bot_trades.json"
trade_log_lock = threading.Lock()

# Mock data for demo mode
MOCK_POSITIONS = {
    "BTCUSD": {"position": 2, "avgCost": 50000},
    "AAPL": {"position": 10, "avgCost": 150},
    "GOOGL": {"position": 5, "avgCost": 2800}
}

class MockPosition:
    def __init__(self, symbol, position, avg_cost):
        self.symbol = symbol
        self.position = position
        self.avgCost = avg_cost

class MockContract:
    def __init__(self, symbol):
        self.symbol = symbol

class MockOrder:
    def __init__(self, action, quantity, order_type="MKT"):
        self.action = action
        self.totalQuantity = quantity
        self.orderType = order_type
        self.orderId = f"MOCK_{int(time_lib.time())}"

class MockTrade:
    def __init__(self, contract, order):
        self.contract = contract
        self.order = order
        self.orderStatus = type('obj', (object,), {'status': 'Submitted'})()
        self.statusEvent = type('obj', (object,), {'__iadd__': lambda self, x: None})()
    
    def isDone(self):
        return True

# Bot Trade Log Management Functions (same as before but with error handling)

def load_bot_trades() -> Dict:
    """Load bot trades from JSON file with error handling"""
    try:
        if os.path.exists(BOT_TRADES_FILE):
            with open(BOT_TRADES_FILE, 'r') as f:
                data = json.load(f)
                # Validate structure
                if 'trades' not in data:
                    data['trades'] = []
                if 'summary' not in data:
                    data['summary'] = {}
                return data
        else:
            # Create new structure
            return {
                'trades': [],
                'summary': {}
            }
    except (json.JSONDecodeError, FileNotFoundError) as e:
        main_logger.error(f"Error loading bot trades file: {e}")
        # Try to load from backup
        backup_file = f"{BOT_TRADES_FILE}.backup"
        if os.path.exists(backup_file):
            main_logger.info("Loading from backup file...")
            try:
                with open(backup_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Return empty structure if all fails
        main_logger.warning("Creating new bot trades log")
        return {'trades': [], 'summary': {}}

def save_bot_trades(trades_data: Dict) -> bool:
    """Save bot trades to JSON file with atomic write and backup"""
    try:
        with trade_log_lock:
            # Create backup first
            if os.path.exists(BOT_TRADES_FILE):
                shutil.copy2(BOT_TRADES_FILE, f"{BOT_TRADES_FILE}.backup")
            
            # Atomic write using temporary file
            temp_file = f"{BOT_TRADES_FILE}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(trades_data, f, indent=2, default=str)
            
            # Move temp file to actual file
            shutil.move(temp_file, BOT_TRADES_FILE)
            main_logger.debug("Bot trades saved successfully")
            return True
            
    except Exception as e:
        main_logger.error(f"Error saving bot trades: {e}")
        return False

def add_bot_trade(order_id: str, ticker: str, action: str, quantity: int, price: float, 
                 sl_pct: Optional[float], tp_pct: Optional[float], email_source: str) -> None:
    """Add new trade to bot log"""
    try:
        trades_data = load_bot_trades()
        
        new_trade = {
            "order_id": str(order_id),
            "ticker": ticker,
            "action": action.upper(),
            "quantity": quantity,
            "price": price,
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "email_source": email_source[:100],  # Limit length
            "status": "pending",
            "sl_pct": sl_pct,
            "tp_pct": tp_pct,
            "is_closed": False,
            "demo_mode": DEMO_MODE
        }
        
        if action.upper() == "SELL":
            # For sells, try to link to oldest open buy
            buy_order = get_oldest_open_buy(ticker)
            if buy_order:
                new_trade["closes_order_id"] = buy_order["order_id"]
        
        trades_data['trades'].append(new_trade)
        
        # Update summary
        if ticker not in trades_data['summary']:
            trades_data['summary'][ticker] = {"open_quantity": 0, "total_buys": 0, "total_sells": 0}
        
        if action.upper() == "BUY":
            trades_data['summary'][ticker]["total_buys"] += quantity
            trades_data['summary'][ticker]["open_quantity"] += quantity
        else:  # SELL
            trades_data['summary'][ticker]["total_sells"] += quantity
            trades_data['summary'][ticker]["open_quantity"] -= quantity
        
        save_bot_trades(trades_data)
        
        mode_indicator = "🔄 [DEMO]" if DEMO_MODE else "💰 [LIVE]"
        main_logger.info(f"{mode_indicator} Bot trade logged: {action} {ticker} x{quantity} @ ${price} (Order: {order_id})")
        
    except Exception as e:
        main_logger.error(f"Error adding bot trade: {e}")

def update_trade_status(order_id: str, status: str) -> None:
    """Update trade status when order completes"""
    try:
        trades_data = load_bot_trades()
        
        for trade in trades_data['trades']:
            if trade['order_id'] == str(order_id):
                trade['status'] = status
                trade['completed_timestamp'] = datetime.now(pytz.UTC).isoformat()
                main_logger.info(f"Updated trade status: Order {order_id} -> {status}")
                break
        
        save_bot_trades(trades_data)
        
    except Exception as e:
        main_logger.error(f"Error updating trade status: {e}")

def close_bot_trade(sell_order_id: str, buy_order_id: str) -> None:
    """Mark a buy trade as closed by linking sell order"""
    try:
        trades_data = load_bot_trades()
        
        for trade in trades_data['trades']:
            if trade['order_id'] == buy_order_id and trade['action'] == 'BUY':
                trade['is_closed'] = True
                trade['closed_by_order_id'] = sell_order_id
                trade['closed_timestamp'] = datetime.now(pytz.UTC).isoformat()
                main_logger.info(f"Closed buy trade {buy_order_id} with sell order {sell_order_id}")
                break
        
        save_bot_trades(trades_data)
        
    except Exception as e:
        main_logger.error(f"Error closing bot trade: {e}")

def get_bot_open_quantity(ticker: str) -> int:
    """Return quantity bot can sell for this ticker"""
    try:
        trades_data = load_bot_trades()
        
        if ticker in trades_data.get('summary', {}):
            open_qty = trades_data['summary'][ticker].get('open_quantity', 0)
            main_logger.debug(f"Bot open quantity for {ticker}: {open_qty}")
            return max(0, open_qty)  # Never return negative
        
        return 0
        
    except Exception as e:
        main_logger.error(f"Error getting bot open quantity: {e}")
        return 0

def get_oldest_open_buy(ticker: str) -> Optional[Dict]:
    """Get oldest unfilled buy order for FIFO selling"""
    try:
        trades_data = load_bot_trades()
        
        open_buys = [
            trade for trade in trades_data['trades']
            if (trade['ticker'] == ticker and 
                trade['action'] == 'BUY' and 
                not trade.get('is_closed', False) and
                trade.get('status') in ['filled', 'pending'])
        ]
        
        if open_buys:
            # Sort by timestamp, return oldest
            open_buys.sort(key=lambda x: x['timestamp'])
            return open_buys[0]
        
        return None
        
    except Exception as e:
        main_logger.error(f"Error getting oldest open buy: {e}")
        return None

def validate_bot_sell(ticker: str, requested_quantity: int) -> Tuple[bool, int, str]:
    """
    Two-level validation for sell safety - works in both demo and live mode
    """
    try:
        # Level 1: Position Safety Check (IBKR or Mock)
        open_positions = fetch_open_positions(IBKR_ACCOUNT)
        
        if ticker not in open_positions:
            return False, 0, f"SAFETY BLOCK: No position found for {ticker}"
        
        if DEMO_MODE:
            position_qty = open_positions[ticker].position
        else:
            position_qty = open_positions[ticker].position
        
        if position_qty <= 0:
            return False, 0, f"SAFETY BLOCK: Position for {ticker} is {position_qty} (not long)"
        
        # Level 2: Bot Trade Precision Check
        bot_open_qty = get_bot_open_quantity(ticker)
        if bot_open_qty <= 0:
            return False, 0, f"BOT PRECISION BLOCK: No bot open position for {ticker}"
        
        if requested_quantity > bot_open_qty:
            return False, 0, f"BOT PRECISION BLOCK: Requested {requested_quantity} > bot's open {bot_open_qty} for {ticker}"
        
        # Additional safety: Don't sell more than actual position
        if requested_quantity > position_qty:
            validated_qty = min(requested_quantity, position_qty, bot_open_qty)
            return True, validated_qty, f"QUANTITY ADJUSTED: Selling {validated_qty} instead of {requested_quantity}"
        
        # All checks passed
        return True, requested_quantity, f"SELL VALIDATED: Can safely sell {requested_quantity} shares of {ticker}"
        
    except Exception as e:
        error_msg = f"VALIDATION ERROR: {str(e)}"
        main_logger.error(error_msg)
        return False, 0, error_msg

def log_position_safety(ticker: str, action: str, quantity: int, price: float, validation_result: str = None) -> None:
    """Enhanced logging for position tracking and safety audits"""
    try:
        open_positions = fetch_open_positions(IBKR_ACCOUNT)
        current_position = open_positions.get(ticker, None)
        
        if current_position:
            current_qty = current_position.position
            avg_cost = getattr(current_position, 'avgCost', 'N/A')
        else:
            current_qty = 0
            avg_cost = 'N/A'
        
        bot_open_qty = get_bot_open_quantity(ticker)
        
        mode_indicator = "🔄 [DEMO MODE]" if DEMO_MODE else "💰 [LIVE MODE]"
        
        safety_log = f"""
=== POSITION SAFETY LOG ===
{mode_indicator}
Timestamp: {datetime.now()}
Ticker: {ticker}
Action: {action}
Requested Quantity: {quantity}
Trade Price: ${price}
Current Position: {current_qty}
Average Cost: {avg_cost}
Bot Open Quantity: {bot_open_qty}
Validation Result: {validation_result or 'N/A'}
========================
"""
        main_logger.info(safety_log)
        
        # Also log to dedicated safety file
        os.makedirs('log', exist_ok=True)
        with open('log/position_safety.log', 'a') as f:
            f.write(f"{datetime.now()} - {safety_log}\n")
        
    except Exception as e:
        main_logger.error(f"Error in position safety logging: {e}")

def reconcile_bot_trades_with_ibkr() -> None:
    """Reconcile bot trade log with actual positions - works in demo mode"""
    try:
        main_logger.info("Starting bot trade reconciliation...")
        
        trades_data = load_bot_trades()
        open_positions = fetch_open_positions(IBKR_ACCOUNT)
        
        for ticker, summary in trades_data.get('summary', {}).items():
            bot_qty = summary.get('open_quantity', 0)
            
            if ticker in open_positions:
                actual_qty = open_positions[ticker].position
            else:
                actual_qty = 0
            
            if bot_qty != actual_qty and not DEMO_MODE:
                main_logger.warning(f"Position mismatch for {ticker}: Bot={bot_qty}, Actual={actual_qty}")
        
        mode_indicator = "🔄 [DEMO MODE]" if DEMO_MODE else "💰 [LIVE MODE]"
        main_logger.info(f"{mode_indicator} Bot trade reconciliation completed")
        
    except Exception as e:
        main_logger.error(f"Error in trade reconciliation: {e}")

# Setup IB connection with demo mode support
def setup_ib_connection():
    global ib
    
    if DEMO_MODE:
        main_logger.info("🔄 DEMO MODE: Simulating IBKR connection")
        ib = type('MockIB', (), {
            'isConnected': lambda: True,
            'connect': lambda *args: None,
            'sleep': lambda x: time_lib.sleep(x)
        })()
        reconcile_bot_trades_with_ibkr()
        return ib
    
    # Real IBKR connection
    client_id = 0
    ib = IB()
    while not ib.isConnected():
        try:
            ib.connect(IB_API_HOST, int(IB_API_PORT), clientId=client_id)
            main_logger.info(f"💰 Connected to IBKR client id: {client_id}")
            reconcile_bot_trades_with_ibkr()
            
        except asyncio.exceptions.TimeoutError as e:
            client_id += 1
        except Exception as e:
            main_logger.error(f"IBKR connection failed: {e}")
            # Switch to demo mode if connection fails
            main_logger.warning("🔄 Switching to DEMO MODE due to connection failure")
            global DEMO_MODE
            DEMO_MODE = True
            return setup_ib_connection()
    
    return ib

def on_trade_status(trade):
    """Enhanced callback function for trade status updates with bot tracking"""
    global trades
    
    if DEMO_MODE:
        main_logger.info(f"🔄 [DEMO] Trade status update: {trade.contract.symbol}")
        return
    
    main_logger.debug(f"{trade.contract.symbol} order status: {trade.orderStatus.status}")
    
    if trade.isDone():
        main_logger.info(f"{trade.contract.symbol} trade is done.")
        
        # Update bot trade log
        update_trade_status(trade.order.orderId, "filled")
        
        # If it's a sell, link it to the buy it closes
        if trade.order.action == "SELL":
            buy_order = get_oldest_open_buy(trade.contract.symbol)
            if buy_order:
                close_bot_trade(str(trade.order.orderId), buy_order['order_id'])
        
        trades.remove(trade)

def fetch_open_positions(account: str) -> dict:
    """Fetch all open positions - supports both demo and live mode"""
    open_positions = {}
    
    try:
        if DEMO_MODE:
            # Return mock positions for demo
            for ticker, data in MOCK_POSITIONS.items():
                open_positions[ticker] = MockPosition(ticker, data["position"], data["avgCost"])
            main_logger.debug(f"🔄 [DEMO] Mock positions: {list(open_positions.keys())}")
        else:
            # Real IBKR positions
            for position in ib.positions(account=account):
                if position.position != 0:  # Only include actual positions
                    open_positions[position.contract.symbol] = position
                    main_logger.debug(f"Open position: {position.contract.symbol} = {position.position} shares")
        
    except Exception as e:
        main_logger.error(f"Error fetching positions: {e}")
        if not DEMO_MODE:
            main_logger.warning("🔄 Using demo positions due to error")
            return fetch_open_positions(account)  # Recursive call in demo mode
    
    return open_positions

def fetch_open_orders() -> dict:
    """Fetch all open orders - supports demo mode"""
    open_orders = {}
    
    if DEMO_MODE:
        main_logger.debug("🔄 [DEMO] No open orders in demo mode")
        return open_orders
    
    try:
        for trade in ib.openTrades():
            main_logger.info(f"Open trade: {trade}")
            open_orders.setdefault(trade.contract.symbol, [])
            open_orders[trade.contract.symbol].append(trade)
    except Exception as e:
        main_logger.error(f"Error fetching open orders: {e}")
    
    return open_orders

def place_order(ticker: str, action: str, quantity: int, price: float, notification_datetime: datetime, 
               sl_pct: Optional[float], tp_pct: Optional[float], args: argparse.Namespace, email_source: str = ""):
    """Enhanced place_order with demo mode support and sell safety"""
    global ib
    
    mode_indicator = "🔄 [DEMO]" if DEMO_MODE else "💰 [LIVE]"
    main_logger.info(f"{mode_indicator} Processing order: {action} {ticker} x{quantity} @ ${price}")
    
    # Enhanced sell safety validation
    if action == "SELL":
        is_safe, validated_quantity, safety_reason = validate_bot_sell(ticker, quantity)
        
        # Log the validation attempt
        log_position_safety(ticker, action, quantity, price, safety_reason)
        
        if not is_safe:
            # Send alert about blocked sell
            alert_message = f"🚨 SELL ORDER BLOCKED: {safety_reason}"
            main_logger.error(alert_message)
            try:
                if telegram_bot:
                    telegram_bot.send_message(TELEGRAM_ECP_CHANNEL_CHAT_ID, alert_message)
            except:
                pass  # Don't fail on telegram errors
            return
        
        # Use validated quantity
        quantity = validated_quantity
        main_logger.info(f"Sell validation passed: {safety_reason}")
    
    # Log position tracking for all actions
    if action == "BUY":
        log_position_safety(ticker, action, quantity, price, "Buy order initiated")
    
    if DEMO_MODE:
        # Demo mode order simulation
        mock_order_id = f"DEMO_{int(time_lib.time())}_{ticker}_{action}"
        
        # Simulate order placement
        main_logger.info(f"🔄 [DEMO] Simulated order placed: ID {mock_order_id}")
        
        # Add to bot trade log (demo orders)
        add_bot_trade(
            order_id=mock_order_id,
            ticker=ticker,
            action=action,
            quantity=quantity,
            price=price,
            sl_pct=sl_pct,
            tp_pct=tp_pct,
            email_source=email_source
        )
        
        # Simulate immediate fill in demo mode
        update_trade_status(mock_order_id, "filled")
        
        trade_log_message = f"🔄 [DEMO] Order completed: {action} {ticker} x{quantity} @ ${price} (ID: {mock_order_id})"
        main_logger.info(trade_log_message)
        
        return
    
    # Real IBKR order placement (original logic)
    contract = Stock(ticker, exchange="SMART", currency="USD")
    
    def place_and_track_order(order: Order):
        trade = ib.placeOrder(contract, order)
        trade.statusEvent += on_trade_status
        trades.append(trade)
        return trade
    
    open_stock_positions = fetch_open_positions(IBKR_ACCOUNT)
    open_stock_orders = fetch_open_orders()
    order = None
    bracket_order = False
    preferred_order_type = "MIDPRICE"
    limit_price = None
    price = round(price, 2)
    notification_time_EDT = notification_datetime.astimezone(EDT_timezone).time()
    
    if notification_time_EDT < time(9, 30, tzinfo=EDT_timezone) or notification_time_EDT > time(15, 59, tzinfo=EDT_timezone):
        main_logger.info(f"Order type set to LMT as notification datetime is outside of trading hours: {notification_datetime}")
        preferred_order_type = "LMT"
        limit_price = price
    
    # Sell logic - already validated above
    if action == "SELL":
        if ticker in open_stock_orders:
            main_logger.warning(f"Sell order for {ticker} already placed.")
            return
    
    # Order creation logic
    if args.version == "A" or action == "SELL" or (not sl_pct and not tp_pct):
        order = Order(
            action=action,
            lmtPrice=limit_price,
            totalQuantity=quantity, 
            orderType=preferred_order_type,
            tif="GTC",
            account=IBKR_ACCOUNT
        )
    elif args.version == "B" and action == "BUY":
        # Fixed bracket order - use actual quantity, not hard-coded 1
        bracket_order = ib.bracketOrder('BUY', quantity, price, 
                                      round(price*(1+tp_pct/100), 2), 
                                      round(price*(1-sl_pct/100), 2), 
                                      account=IBKR_ACCOUNT)

    if args.version == "B" and action == "SELL":
        # Cancel existing bracket orders for this ticker
        for open_bracket_order in open_stock_orders.get(ticker, []):
            open_bracket_order.cancel()

    trade_log_message = None
    placed_order_id = None
    
    # Place orders and get order ID
    if order:
        if not ib.isConnected():
            ib = setup_ib_connection()
        
        trade_obj = place_and_track_order(order)
        placed_order_id = order.orderId
        trade_log_message = f"💰 [LIVE] Order (id: {order.orderId}) placed: {action} {ticker} x{quantity}. Order type: {preferred_order_type} triggered at ${price}"
        
    elif bracket_order:
        if not ib.isConnected():
            ib = setup_ib_connection()
        
        for o in bracket_order:
            o.tif = "GTC"
            if o.action == 'BUY':
                o.orderType = preferred_order_type
                o.lmtPrice = limit_price
            main_logger.info(f"Placing bracket order: {o}")
            place_and_track_order(o)
        
        placed_order_id = bracket_order[0].orderId
        trade_log_message = f"💰 [LIVE] Bracket Order (id: {bracket_order[0].orderId}) placed: {action} {ticker} x{quantity}. " \
                            f"Order type: {preferred_order_type} triggered at ${price}. "\
                            f"TP: ${bracket_order[1].lmtPrice}, SL: ${bracket_order[2].auxPrice}"

    # Log trade to bot tracking system
    if placed_order_id and trade_log_message:
        main_logger.info(trade_log_message)
        
        # Add to bot trade log
        add_bot_trade(
            order_id=placed_order_id,
            ticker=ticker,
            action=action,
            quantity=quantity,
            price=price,
            sl_pct=sl_pct,
            tp_pct=tp_pct,
            email_source=email_source
        )
        
        # Send telegram notification
        if notification_datetime.date() == datetime.today().date():
            try:
                if telegram_bot:
                    telegram_bot.send_message(TELEGRAM_ECP_CHANNEL_CHAT_ID, trade_log_message)
            except:
                pass  # Don't fail on telegram errors

def place_ibkr_order(ticker: str, action: str, quantity: int, price: float, notification_datetime: datetime, 
                    sl_pct: Optional[float], tp_pct: Optional[float], args: argparse.Namespace, email_source: str = ""):
    """Wrapper for place_order with email source tracking"""
    if action.lower() == "buy":
        place_order(ticker, "BUY", quantity, price, notification_datetime, sl_pct, tp_pct, args, email_source)
    elif action.lower() == "sell":
        place_order(ticker, "SELL", quantity, price, notification_datetime, sl_pct, tp_pct, args, email_source)

def place_crypto_order(ticker: str, action: str, quantity: int, price: float, notification_datetime: datetime):
    """Crypto order placement (unchanged)"""
    if DEMO_MODE:
        main_logger.info(f"🔄 [DEMO] Crypto order: {action} {ticker} x{quantity} @ ${price}")
        return
    
    global exchange
    order = None
    open_crypto_positions = {}
    if action.lower() == "buy":
        # TODO: add check balance b4 placing order
        order = exchange.create_order(
            symbol=ticker,
            type='limit',
            side='buy',
            amount=quantity,
            price=price
        )
    elif action.lower() == "sell":
        if ticker in open_crypto_positions:
            order = exchange.create_order(
                symbol=ticker,
                type='limit',
                side='sell',
                amount=quantity,
                price=price
            )
        else:
            main_logger.warning(f"Sell order for {ticker} not placed as no open position found.")
    if order:
        trade_log_message = f"Order placed: {action} {ticker} x{quantity} triggered at ${price}"
        main_logger.info(trade_log_message)
        if notification_datetime.date() == datetime.today().date():
            try:
                if telegram_bot:
                    telegram_bot.send_message(TELEGRAM_ECP_CHANNEL_CHAT_ID, trade_log_message)
            except:
                pass