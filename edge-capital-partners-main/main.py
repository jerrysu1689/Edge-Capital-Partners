
#main.py
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
import re
from argument_parser import get_cli_args
from imapclient import IMAPClient
import email
from datetime import datetime, timezone
from dotenv import load_dotenv
from email.header import decode_header
import certifi
from ib_insync import *
import telebot
import pandas as pd
from trade import place_ibkr_order, place_crypto_order, setup_ib_connection
import platform

load_dotenv()

# Setup logging with fallback if config file doesn't exist
try:
    with open("config/logging.yml", "r") as logging_config_file:
        logging.config.dictConfig(yaml.load(logging_config_file, Loader=yaml.FullLoader))
except FileNotFoundError:
    # Fallback to basic logging if config file doesn't exist
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('log/application.log', mode='a')
        ]
    )
    # Create log directory if it doesn't exist
    os.makedirs('log', exist_ok=True)

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

try:
    telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
except:
    telegram_bot = None
    main_logger.warning("Telegram bot initialization failed - continuing without notifications")

# Load last checked email time with error handling
try:
    with open("last_checked_email_time.json", "r") as f:
        last_checked_email_time = json.load(f)["last_checked_email_time"]
    last_checked_email_time = datetime.strptime(last_checked_email_time, "%Y-%m-%d %H:%M:%S%z")
except (FileNotFoundError, json.JSONDecodeError, KeyError):
    # Default to start of current year if file doesn't exist or is corrupted
    last_checked_email_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    main_logger.warning("Created default last_checked_email_time")

timeout = None
if platform.system().lower() == "windows":
    main_logger.info("Running on Windows")
    timeout = 1

def extract_sl_tp_from_subject(subject: str) -> tuple[float, float]:
    """
    Extract SL and TP percentages from email subject
    Format: 'Alert: Top Overall 15M BTCUSD nSkew v3 3%SL 5%TP'
    Returns: (sl_pct, tp_pct) or (None, None) if not found
    """
    try:
        subject_template = r".+ (\d{1,3})%SL (\d{1,3})%TP"
        subject_regex_match = re.match(subject_template, subject)
        
        if subject_regex_match:
            sl_pct = float(subject_regex_match.groups()[0])
            tp_pct = float(subject_regex_match.groups()[1])
            main_logger.debug(f"Extracted SL/TP from subject: SL={sl_pct}%, TP={tp_pct}%")
            return sl_pct, tp_pct
        
        return None, None
        
    except Exception as e:
        main_logger.error(f"Error extracting SL/TP from subject: {e}")
        return None, None

def extract_sl_tp_from_body(body: str) -> tuple[float, float]:
    """
    Extract SL and TP percentages from email body
    Format: 'ECP nSkew SL TP v3 (, 14, 70, -30, 5, 1): ...'
    Pattern positions: (, value1, value2, value3, SL%, TP%)
    Returns: (sl_pct, tp_pct) or (None, None) if not found
    """
    try:
        # Look for pattern: (, number, number, number, SL%, TP%)
        body_sl_tp_pattern = r'\(,\s*([+-]?\d+\.?\d*),\s*([+-]?\d+\.?\d*),\s*([+-]?\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*)\)'
        sl_tp_match = re.search(body_sl_tp_pattern, body)
        
        if sl_tp_match:
            # Groups: [value1, value2, value3, SL%, TP%]
            groups = sl_tp_match.groups()
            sl_pct = float(groups[3])  # 4th position (index 3)
            tp_pct = float(groups[4])  # 5th position (index 4)
            main_logger.debug(f"Extracted SL/TP from body: SL={sl_pct}%, TP={tp_pct}% from pattern {groups}")
            return sl_pct, tp_pct
        
        return None, None
        
    except Exception as e:
        main_logger.error(f"Error extracting SL/TP from body: {e}")
        return None, None

def parse_email_for_trade_data(subject: str, body: str) -> dict:
    """
    Enhanced email parsing to extract all trade data including SL/TP from both subject and body
    Returns dict with all extracted data or None if parsing fails
    """
    try:
        # Extract SL/TP from both sources
        subject_sl, subject_tp = extract_sl_tp_from_subject(subject)
        body_sl, body_tp = extract_sl_tp_from_body(body)
        
        # Priority: Use body SL/TP if available, fallback to subject
        final_sl = body_sl if body_sl is not None else subject_sl
        final_tp = body_tp if body_tp is not None else subject_tp
        
        if body_sl is not None and subject_sl is not None:
            main_logger.info(f"SL/TP found in both sources - Using body: SL={body_sl}%, TP={body_tp}% (Subject had: SL={subject_sl}%, TP={subject_tp}%)")
        elif body_sl is not None:
            main_logger.info(f"Using SL/TP from body: SL={body_sl}%, TP={body_tp}%")
        elif subject_sl is not None:
            main_logger.info(f"Using SL/TP from subject: SL={subject_sl}%, TP={subject_tp}%")
        else:
            main_logger.warning("No SL/TP found in subject or body")
        
        # Parse body for trade details - FIXED REGEX
        # New pattern to match: "order buy @ 100242 for 12.264199 filled on BTCUSD at 2025-11-07T12:00:00Z"
        body_template = r'.+order\s+(\w+)\s+@\s+(\d+\.?\d*)\s+for\s+(\d+\.?\d+)\s+filled\s+on\s+(\w+)\s+at\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)'
        
        body_regex_match = re.search(body_template, body)
        
        if not body_regex_match:
            main_logger.warning(f"Body regex did not match. Body: {body[:200]}...")
            return None
            
        body_matched_groups = body_regex_match.groups()
        main_logger.debug(f"Body regex matched groups: {body_matched_groups}")
        
        # Extract trade data
        action = body_matched_groups[0].upper()  # BUY/SELL
        price = float(body_matched_groups[1])
        quantity = float(body_matched_groups[2])
        ticker = body_matched_groups[3]
        timestamp_str = body_matched_groups[4]
        
        # Parse timestamp
        notification_datetime = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        
        trade_data = {
            'action': action,
            'price': price,
            'quantity': quantity,
            'ticker': ticker,
            'timestamp': notification_datetime,
            'sl_pct': final_sl,
            'tp_pct': final_tp,
            'subject_source': subject[:100],  # First 100 chars for reference
            'body_source': body[:200]  # First 200 chars for reference
        }
        
        main_logger.info(f"Successfully parsed trade: {action} {ticker} x{quantity} @ ${price} (SL: {final_sl}%, TP: {final_tp}%)")
        return trade_data
        
    except Exception as e:
        main_logger.error(f"Error parsing email for trade data: {e}")
        return None

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
    # Save last checked time
    try:
        with open("last_checked_email_time.json", "w") as f:
            json.dump({"last_checked_email_time": last_checked_email_time.strftime("%Y-%m-%d %H:%M:%S%z")}, f)
    except Exception as e:
        main_logger.error(f"Error saving last checked email time: {e}")
    
    return messages

def trade_on_messages(messages, args: argparse.Namespace):
    """Enhanced trade processing with better error handling and logging"""
    try:
        trade_config = pd.read_csv(f"config/trade_config_version_{args.version}.csv")
    except FileNotFoundError:
        main_logger.error(f"Trade config file not found: config/trade_config_version_{args.version}.csv")
        return
    except Exception as e:
        main_logger.error(f"Error loading trade config: {e}")
        return
    
    for notification_datetime, subject, body in messages:
        try:
            # Use enhanced email parsing
            trade_data = parse_email_for_trade_data(subject, body)
            
            if not trade_data:
                main_logger.warning(f"Failed to parse email - Subject: {subject[:50]}...")
                continue
            
            action = trade_data['action']
            price = trade_data['price'] 
            quantity = trade_data['quantity']
            ticker = trade_data['ticker']
            sl_pct = trade_data['sl_pct']
            tp_pct = trade_data['tp_pct']
            notification_datetime = trade_data['timestamp']
            
            # Get quantity from trade config
            result = trade_config.loc[(trade_config["ibkr_account"] == IBKR_ACCOUNT) & (trade_config["ticker"] == ticker)]
            if not result.empty:
                config_quantity = int(result["quantity"].values[0])
                # Use quantity from trade data, but could override with config if needed
                final_quantity = config_quantity  # or could use: quantity from email
            else:
                main_logger.warning(f"Trade config not found for {IBKR_ACCOUNT} and {ticker}. Skipping order.")
                continue

            # Determine instrument type
            instrument_type = "STK"
            if "BTC" in ticker or "ETH" in ticker:
                instrument_type = "CRYPTO"

            # Create email source reference for tracking
            email_source = f"Subject: {subject[:50]}... | Body: {body[:50]}..."

            # Place orders
            if instrument_type == "STK":
                main_logger.info(f"Placing IBKR order: {action} {ticker} x{final_quantity} @ ${price} (SL: {sl_pct}%, TP: {tp_pct}%)")
                place_ibkr_order(ticker, action, final_quantity, price, notification_datetime, sl_pct, tp_pct, args, email_source)
            elif instrument_type == "CRYPTO":
                main_logger.info(f"Crypto trading not implemented for {ticker}")
                # place_crypto_order(ticker, action, final_quantity, price, notification_datetime)

        except Exception as e:
            main_logger.exception(f"Error processing message: {e}")
            # Send error alert but continue processing
            try:
                if telegram_bot:
                    telegram_bot.send_message(TELEGRAM_ECP_CHANNEL_CHAT_ID, f"❌ Error processing trade email: {str(e)[:100]}")
            except:
                pass

def run_loop(args: argparse.Namespace):
    """Main email monitoring loop with enhanced error handling and demo mode support"""
    
    # DEMO MODE CHECK: Prevent infinite loop when no email credentials
    if not EMAIL_USER or not EMAIL_PASS or EMAIL_USER.strip() == "" or EMAIL_PASS.strip() == "":
        main_logger.warning("🔄 DEMO MODE: No email credentials provided")
        main_logger.info("🔄 DEMO MODE: Skipping email monitoring - setting up mock environment")
        
        # Set up IBKR connection (will be mock in demo mode)
        ib = setup_ib_connection()
        main_logger.info("🔄 DEMO MODE: IBKR connection established")
        
        # In demo mode, just keep the process alive for testing
        main_logger.info("🔄 DEMO MODE: Bot ready for manual testing - no email monitoring")
        main_logger.info("🔄 DEMO MODE: Use debug tools to test functionality:")
        main_logger.info("🔄 DEMO MODE: - ./manage_trader.sh debug-email")
        main_logger.info("🔄 DEMO MODE: - ./manage_trader.sh test-parsing")
        main_logger.info("🔄 DEMO MODE: - ./manage_trader.sh dashboard")
        
        # Keep process alive with periodic status updates
        retry_count = 0
        max_demo_cycles = 1440  # 24 hours worth of 1-minute cycles
        
        while retry_count < max_demo_cycles:
            try:
                time.sleep(60)  # Sleep for 1 minute
                retry_count += 1
                
                # Log status every 10 minutes
                if retry_count % 10 == 0:
                    hours = retry_count // 60
                    main_logger.info(f"🔄 DEMO MODE: Bot active ({hours}h) - email monitoring disabled")
                
                # Refresh IBKR connection periodically
                if retry_count % 60 == 0:  # Every hour
                    ib = setup_ib_connection()
                    main_logger.debug("🔄 DEMO MODE: IBKR connection refreshed")
                    
            except KeyboardInterrupt:
                main_logger.info("🔄 DEMO MODE: Bot stopped by user")
                break
            except Exception as e:
                main_logger.error(f"🔄 DEMO MODE: Unexpected error: {e}")
                time.sleep(30)  # Wait 30 seconds before continuing
                
        main_logger.info("🔄 DEMO MODE: Bot shutting down after 24h demo cycle")
        return
    
    # TEMPLATE VALUE CHECK: Prevent infinite loop with template credentials
    if ("your-email" in EMAIL_USER.lower() or 
        "your-16-character" in EMAIL_PASS.lower() or
        len(EMAIL_PASS) != 16):
        main_logger.error("❌ TEMPLATE CREDENTIALS DETECTED:")
        main_logger.error("   EMAIL_USER contains 'your-email' or EMAIL_PASS is not 16 characters")
        main_logger.error("   Please update .env file with real Gmail credentials")
        main_logger.error("   Bot will not start with template values to prevent infinite loops")
        return
    
    # LIVE MODE: Start email monitoring
    main_logger.info("💰 LIVE MODE: Starting email monitoring with real credentials")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    ib = setup_ib_connection()
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    
    # Connection retry limits to prevent infinite loops
    max_connection_retries = 10
    connection_retry_count = 0
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    while connection_retry_count < max_connection_retries:
        mail = None
        try:
            main_logger.info(f"Attempting email connection (attempt {connection_retry_count + 1}/{max_connection_retries})")
            
            mail = IMAPClient(EMAIL_HOST, EMAIL_PORT, use_uid=True, ssl=True, ssl_context=ssl_context)
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.select_folder("INBOX")
            
            main_logger.info("✅ Connected to email server successfully")
            consecutive_failures = 0  # Reset failure count on successful connection
            
            # Inner monitoring loop
            idle_retry_count = 0
            max_idle_retries = 20
            
            while idle_retry_count < max_idle_retries:
                try:
                    mail.idle()
                    main_logger.info("Waiting for new events...")
                    response = mail.idle_check(timeout=timeout)
                    mail.idle_done()
                    
                    if response:
                        main_logger.info(f"New event occurred: {response}")
                        messages = fetch_emails(mail)
                        if messages:
                            trade_on_messages(messages, args)
                        ib.sleep(2)
                    
                    idle_retry_count = 0  # Reset on successful cycle
                        
                except Exception as e:
                    idle_retry_count += 1
                    main_logger.error(f"Error in email idle loop (attempt {idle_retry_count}/{max_idle_retries}): {e}")
                    
                    if idle_retry_count >= max_idle_retries:
                        main_logger.error("Too many idle failures - reconnecting to email server")
                        break
                    
                    # Wait before retrying idle
                    time.sleep(5)
                    
        except IMAPClient.Error as e:
            consecutive_failures += 1
            connection_retry_count += 1
            main_logger.error(f"IMAP error (failure {consecutive_failures}): {e}")
            
            if "authentication" in str(e).lower() or "login" in str(e).lower():
                main_logger.error("❌ EMAIL AUTHENTICATION FAILED:")
                main_logger.error("   - Check Gmail App Password is correct (16 characters)")
                main_logger.error("   - Verify EMAIL_USER is full email address")
                main_logger.error("   - Try regenerating Gmail App Password")
                
                if consecutive_failures >= 3:
                    main_logger.error("❌ Too many authentication failures - stopping to prevent account lockout")
                    break
                    
        except ssl.SSLEOFError as e:
            consecutive_failures += 1
            connection_retry_count += 1
            main_logger.error(f"SSL connection error: {e}")
            
        except Exception as e:
            consecutive_failures += 1
            connection_retry_count += 1
            main_logger.exception(f"Unexpected error in email connection: {e}")
            
        finally:
            # Clean up email connection
            if mail:
                try:
                    mail.logout()
                    main_logger.info("Disconnected from email server")
                except Exception as cleanup_error:
                    main_logger.debug(f"Error during email cleanup: {cleanup_error}")
        
        # Check if we should stop retrying
        if consecutive_failures >= max_consecutive_failures:
            main_logger.error(f"❌ Too many consecutive failures ({consecutive_failures}) - stopping email monitoring")
            main_logger.error("   Check your internet connection and email credentials")
            break
            
        if connection_retry_count < max_connection_retries:
            wait_time = min(30, 5 * consecutive_failures)  # Exponential backoff (max 30 seconds)
            main_logger.info(f"Reconnecting to email server in {wait_time} seconds...")
            time.sleep(wait_time)
    
    # If we exit the retry loop, log final status
    if connection_retry_count >= max_connection_retries:
        main_logger.error("❌ Maximum connection retries exceeded - email monitoring stopped")
        main_logger.error("   Bot will shut down to prevent infinite loops")
    elif consecutive_failures >= max_consecutive_failures:
        main_logger.error("❌ Too many consecutive failures - email monitoring stopped")
        main_logger.error("   Please check credentials and network connection")
    
    main_logger.info("Email monitoring loop ended")

def start_email_listener(args: argparse.Namespace) -> bool:
    """Start the email listener with error handling"""
    futures = []
    futures.append(executor.submit(run_loop, args))
    
    for future in concurrent.futures.as_completed(futures):
        if future.exception():
            main_logger.exception(f"Email listener exception: {future.exception()}")
        else:
            try:
                main_logger.info(f"Email listener completed: {future.result()}")
            except Exception as e:
                main_logger.exception(f"Error getting future result: {e}")
    return False

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs('log', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    
    main_logger.info("=== AutoTrader Starting ===")
    main_logger.info(f"IBKR Account: {IBKR_ACCOUNT}")
    main_logger.info(f"Email User: {EMAIL_USER}")
    main_logger.info(f"Sender Email: {SENDER_EMAIL}")
    
    args = get_cli_args()
    main_logger.info(f"Trading version: {args.version}")
    
    listener_running = False
    while not listener_running:
        listener_running = start_email_listener(args)