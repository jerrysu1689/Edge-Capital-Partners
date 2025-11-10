import argparse
from datetime import datetime, time
import os
import logging
import logging.config
import threading
import time as time_lib
from typing import Optional
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

IB_API_HOST = os.getenv("IB_API_HOST")
IB_API_PORT = os.getenv("IB_API_PORT")
IBKR_ACCOUNT = os.getenv("IBKR_ACCOUNT")
KUCOIN_API_BASE_URL = os.getenv("KUCOIN_API_BASE_URL")
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY")
KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET")
KUCOIN_API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ECP_CHANNEL_CHAT_ID = os.getenv("TELEGRAM_ECP_CHANNEL_CHAT_ID")
telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


ib = None
trades = []
EDT_timezone = pytz.timezone('America/Toronto')

# Setup IB connection
def setup_ib_connection():
    global ib
    client_id = 0
    ib = IB()
    while not ib.isConnected():
        try:
            ib.connect(IB_API_HOST, IB_API_PORT, clientId=client_id)
            main_logger.info(f"Connected to IBKR client id: {client_id}")
        except asyncio.exceptions.TimeoutError as e:
            client_id += 1
    return ib


def on_trade_status(trade):
    """Callback function for trade status updates."""
    global trades
    main_logger.debug(f"{trade.contract.symbol} order status: {trade.orderStatus.status}")
    if trade.isDone():
        main_logger.info(f"{trade.contract.symbol} trade is done.")
        trades.remove(trade)


# Setup KuCoin connection
# exchange = ccxt.kucoin({
#     'apiKey': KUCOIN_API_KEY,
#     'secret': KUCOIN_API_SECRET,
#     'password': KUCOIN_API_PASSPHRASE,
#     'enableRateLimit': True,  # recommend enabling rate limit in ccxt
#     'timeout': 60000,
#     'certfile': certifi.where()
# })


def fetch_open_positions(account: str) -> dict:
    open_positions = {}
    for position in ib.positions(account=account):
        open_positions[position.contract.symbol] = position
    return open_positions


def fetch_open_orders() -> dict:
    open_orders = {}
    for trade in ib.openTrades():
        main_logger.info(f"Open trade: {trade}")
        open_orders.setdefault(trade.contract.symbol, [])
        open_orders[trade.contract.symbol].append(trade)
    return open_orders


def fetch_kucoin_positions(method: str, endpoint: str):
    now = int(time_lib.time() * 1000)
    str_to_sign = str(now) + method + endpoint
    signature = base64.b64encode(hmac.new(KUCOIN_API_SECRET.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())

    passphrase = base64.b64encode(hmac.new(KUCOIN_API_SECRET.encode('utf-8'), KUCOIN_API_PASSPHRASE.encode('utf-8'), hashlib.sha256).digest())
    headers = {
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": str(now),
        "KC-API-KEY": KUCOIN_API_KEY,
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-KEY-VERSION": "2"
    }
    response = requests.request(method, KUCOIN_API_BASE_URL + endpoint, headers=headers)
    print(response.status_code)
    return response.json()


def place_order(ticker: str, action: str, quantity: int, price: float, notification_datetime: datetime, sl_pct: Optional[float], tp_pct: Optional[float], args: argparse.Namespace):
    global ib
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
    
    if action == "SELL":
        if ticker in open_stock_orders:
            main_logger.warning(f"Sell order for {ticker} already placed.")
            return
        elif ticker in open_stock_positions:
            quantity = open_stock_positions[ticker].position
        else:
            main_logger.warning(f"Sell order for {ticker} not placed as no open position found.")
            return

    if args.version == "A" or action == "SELL" or (not sl_pct and not tp_pct):
        # TODO: add check balance b4 placing order
        order = Order(
            action=action,
            lmtPrice=limit_price,
            totalQuantity=quantity, 
            orderType=preferred_order_type,
            tif="GTC",
            account=IBKR_ACCOUNT
        )
    elif args.version == "B" and action == "BUY":
        bracket_order = ib.bracketOrder('BUY',1, price, round(price*(1+tp_pct/100), 2), round(price*(1-sl_pct/100), 2), account=IBKR_ACCOUNT)

    if args.version == "B" and action == "SELL":
        for open_bracket_order in open_stock_orders.get(ticker, []):
            open_bracket_order.cancel()

    trade_log_message = None
    if order:
        if not ib.isConnected():
            ib = setup_ib_connection()
        place_and_track_order(order)
        trade_log_message = f"Order (id: {order.orderId}) placed: {action} {ticker} x{quantity}. Order type: {preferred_order_type} triggered at ${price}"  
    elif bracket_order:
        if not ib.isConnected():
            ib = setup_ib_connection()
        for o in bracket_order:
            o.tif = "GTC"
            if o.action == 'BUY':
                o.ordetType = preferred_order_type
                o.limitPrice = None
            main_logger.info(f"Placing bracket order: {o}")
            place_and_track_order(o)
        trade_log_message = f"Bracket Order (id: {bracket_order[0].orderId}) placed: {action} {ticker} x{quantity}. " \
                            f"Order type: {preferred_order_type} triggered at ${price}. "\
                            f"TP: ${bracket_order[1].lmtPrice}, SL: ${bracket_order[2].auxPrice}"

    if trade_log_message:
        main_logger.info(trade_log_message)
        if notification_datetime.date() == datetime.today().date():
            telegram_bot.send_message(TELEGRAM_ECP_CHANNEL_CHAT_ID, trade_log_message)


def place_ibkr_order(ticker: str, action: str, quantity: int, price: float, notification_datetime: datetime, sl_pct: Optional[float], tp_pct: Optional[float], args: argparse.Namespace):
    if action.lower() == "buy":
        place_order(ticker, "BUY", quantity, price, notification_datetime, sl_pct, tp_pct, args)
    elif action.lower() == "sell":
        place_order(ticker, "SELL", quantity, price, notification_datetime, sl_pct, tp_pct, args)


def place_crypto_order(ticker: str, action: str, quantity: int, price: float, notification_datetime: datetime):
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
            telegram_bot.send_message(TELEGRAM_ECP_CHANNEL_CHAT_ID, trade_log_message)
