import argparse
import asyncio
import os
import logging
import logging.config
import ssl
import concurrent
import time
import yaml
import json
from argument_parser import get_cli_args
from imapclient import IMAPClient
import email
from datetime import datetime, timezone
from dotenv import load_dotenv
from email.header import decode_header
import certifi
from ib_insync import *
import re
import telebot
import pandas as pd
from trade import place_ibkr_order, place_crypto_order, setup_ib_connection
import platform


load_dotenv()

with open("config/logging.yml", "r") as logging_config_file:
    logging.config.dictConfig(yaml.load(logging_config_file, Loader=yaml.FullLoader))

main_logger = logging.getLogger('main')

executor = concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix=__name__)


# Email server configuration
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
IBKR_ACCOUNT = os.getenv("IBKR_ACCOUNT")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ECP_CHANNEL_CHAT_ID = os.getenv("TELEGRAM_ECP_CHANNEL_CHAT_ID")
telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

last_checked_email_time = json.load(open("last_checked_email_time.json", "r"))["last_checked_email_time"]
last_checked_email_time = datetime.strptime(last_checked_email_time, "%Y-%m-%d %H:%M:%S%z")


timeout = None
if platform.system().lower() == "windows":
    main_logger.info("Running on Windows")
    timeout = 1


# Fetch new emails from the email server
def fetch_emails(mail: IMAPClient):
    global last_checked_email_time
    main_logger.debug(f'Fetching unread emails from {SENDER_EMAIL}')

    # Search for all emails in the inbox
    email_ids = mail.search(['UNSEEN', 'FROM', SENDER_EMAIL])
    current_checked_time = datetime.now(timezone.utc)
    main_logger.info(f"Fetched {len(email_ids)} unread emails from {SENDER_EMAIL}")

    messages = []
    count = 0
    for email_id in email_ids:
        msg_data = mail.fetch(email_id, [b"RFC822"])
        for response_part in msg_data.values():
            try:
                message = response_part[b'RFC822']
            except:
                message = response_part['RFC822']
            msg = email.message_from_bytes(message)
            notification_datetime = datetime.strptime(msg['Date'], "%a, %d %b %Y %H:%M:%S %z").astimezone(tz=timezone.utc)
            if notification_datetime < last_checked_email_time:
                count += 1
                continue
            subject, encoding = decode_header(msg["Subject"])[0]
            subject = subject.strip()
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
            from_ = msg.get("From")
            body = msg.get_payload(decode=True).decode().strip()
            messages.append((notification_datetime, subject, body))
            main_logger.info(f"Email from {from_}\nSubject: {subject}\nBody: {body}")
    
    main_logger.debug(f"{count} unread email's were older than the last checked email time: {last_checked_email_time}")
    
    last_checked_email_time = current_checked_time
    # json.dump({"last_checked_email_time": last_checked_email_time.strftime("%Y-%m-%d %H:%M:%S%z")}, open("last_checked_email_time.json", "w"))
    return messages


def trade_on_messages(messages, args: argparse.Namespace):
    trade_config = pd.read_csv(f"config/trade_config_version_{args.version}.csv")
    for notification_datetime, subject, body in messages:
        subject_template = r".+ (\d{1,3})%SL (\d{1,3})%TP"
        body_template = r".+order (\w+) @ (\d+\.?\d+) for (\d+\.?\d+) filled on (\w{1,5}\.?\w{1,3}).+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\..+"
        try:
            subject_regex_match = re.match(subject_template, subject)
            sl_pct = None
            tp_pct = None
            if subject_regex_match:
                main_logger.debug(f"Subject regex matched groups: {subject_regex_match.groups()}")
                sl_pct = float(subject_regex_match.groups()[0])
                tp_pct = float(subject_regex_match.groups()[1])

            body_regex_match = re.match(body_template, body)
            if not body_regex_match:
                main_logger.warning(f"Message does not match template: {body}")
                continue
            body_matched_groups = body_regex_match.groups()
            main_logger.debug(f"Body regex matched groups: {body_matched_groups}")
            action = body_matched_groups[0]
            price = float(body_matched_groups[1])
            ticker = body_matched_groups[3]
            result = trade_config.loc[(trade_config["ibkr_account"] == IBKR_ACCOUNT) & (trade_config["ticker"] == ticker)]
            if not result.empty:
                quantity = int(result["quantity"].values[0])
            else:
                # quantity = 1
                main_logger.warning(f"Trade config not found for {IBKR_ACCOUNT} and {ticker}. Skipping order.")
                continue

            instrument_type = "STK"
            if "BTC" in ticker or "ETH" in ticker:
                instrument_type = "CRYPTO"

            if instrument_type == "STK":
                place_ibkr_order(ticker, action, quantity, price, notification_datetime, sl_pct, tp_pct, args)
            elif instrument_type == "CRYPTO":
                pass
                # place_crypto_order(ticker, action, quantity, price, notification_datetime)

        except Exception as e:
            main_logger.exception(f"{e}")


def run_loop(args: argparse.Namespace):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    ib = setup_ib_connection()
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    while True:
        try:
            mail = IMAPClient(EMAIL_HOST, EMAIL_PORT, use_uid=True, ssl=True, ssl_context=ssl_context)
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.select_folder("INBOX")
            while True:
                mail.idle()
                main_logger.info("Waiting for new events...")
                response = mail.idle_check(timeout=timeout)
                mail.idle_done()
                if response:
                    main_logger.info(f"New event occurred: {response}")
                    messages = fetch_emails(mail)
                    trade_on_messages(messages, args)
                    ib.sleep(2)
        except ssl.SSLEOFError as e:
            main_logger.error(f"SSL connection error: {e}")
        except Exception as e:
            main_logger.exception(f"Error occurred: {e}")
        finally:
            try:
                mail.logout()
                main_logger.info("Reconnecting to email server...")
            except Exception:
                pass
            ib.sleep(5)


def start_email_listener(args: argparse.Namespace) -> bool:
    futures = []
    futures.append(executor.submit(run_loop, args))
    for future in concurrent.futures.as_completed(futures):
        if future.exception():
            main_logger.exception(f"{future.exception()}")
        else:
            try:
                main_logger.info(f"FUTURE COMPLETED: {future.result()}")
            except Exception as e:
                main_logger.exception(f"{e}")
    return False


if __name__ == "__main__":
    args = get_cli_args()
    listener_running = False
    while not listener_running:
        listener_running = start_email_listener(args)

