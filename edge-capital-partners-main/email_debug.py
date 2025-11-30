#!/usr/bin/env python3
"""
Email Debug & Monitoring Tool for AutoTrader
Real-time email connectivity, parsing, and validation testing
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from imapclient import IMAPClient
import email
from email.mime.text import MIMEText
import re
import argparse
import threading
import signal

# Load environment variables
load_dotenv()

# Email configuration
EMAIL_HOST = os.getenv("EMAIL_HOST", "imap.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 993))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@tradingview.com")

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_status(message, status="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    colors = {
        "success": Colors.GREEN + "✅",
        "error": Colors.RED + "❌", 
        "warning": Colors.YELLOW + "⚠️",
        "info": Colors.BLUE + "ℹ️",
        "debug": Colors.CYAN + "🔍",
        "email": Colors.MAGENTA + "📧",
        "trade": Colors.GREEN + "💰"
    }
    
    icon = colors.get(status, Colors.WHITE + "•")
    print(f"{Colors.WHITE}[{timestamp}]{Colors.RESET} {icon} {message}{Colors.RESET}")

def print_header():
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════╗
║           AutoTrader Email Monitor           ║
║          Real-time Debug & Monitor           ║
╚══════════════════════════════════════════════╝{Colors.RESET}
""")

def validate_email_config():
    """Validate email configuration"""
    print_status("Validating email configuration...", "info")
    
    issues = []
    
    if not EMAIL_USER:
        issues.append("EMAIL_USER not set")
    elif "your-email" in EMAIL_USER.lower():
        issues.append("EMAIL_USER contains template value")
    
    if not EMAIL_PASS:
        issues.append("EMAIL_PASS not set") 
    elif len(EMAIL_PASS) != 16 or "your-" in EMAIL_PASS.lower():
        issues.append("EMAIL_PASS appears to be template value (should be 16-char Gmail app password)")
    
    if not SENDER_EMAIL:
        issues.append("SENDER_EMAIL not set")
    
    if issues:
        print_status("Configuration issues found:", "error")
        for issue in issues:
            print_status(f"  - {issue}", "error")
        return False
    
    print_status("Email configuration looks valid", "success")
    print_status(f"  Host: {EMAIL_HOST}:{EMAIL_PORT}", "info")
    print_status(f"  User: {EMAIL_USER}", "info") 
    print_status(f"  Sender Filter: {SENDER_EMAIL}", "info")
    return True

def test_email_connection():
    """Test email server connection"""
    print_status("Testing email server connection...", "info")
    
    try:
        # Test connection
        with IMAPClient(EMAIL_HOST, port=EMAIL_PORT, ssl=True) as mail:
            print_status("Connected to email server", "success")
            
            # Test login
            mail.login(EMAIL_USER, EMAIL_PASS)
            print_status("Email authentication successful", "success")
            
            # Test folder access
            folders = mail.list_folders()
            print_status(f"Found {len(folders)} email folders", "info")
            
            # Select inbox
            mail.select_folder('INBOX')
            print_status("Successfully selected INBOX", "success")
            
            # Count recent emails
            recent_emails = mail.search(['SINCE', datetime.now().date() - timedelta(days=7)])
            print_status(f"Found {len(recent_emails)} emails from last 7 days", "info")
            
            return True
            
    except Exception as e:
        print_status(f"Email connection failed: {str(e)}", "error")
        
        # Specific error handling
        if "authentication failed" in str(e).lower():
            print_status("Check Gmail App Password - may need to regenerate", "warning")
        elif "login command error" in str(e).lower():
            print_status("Login format error - verify EMAIL_USER and EMAIL_PASS", "warning")
        elif "connection" in str(e).lower():
            print_status("Network connection issue - check internet/firewall", "warning")
            
        return False

def parse_email_for_trade_data_debug(subject, body):
    """Enhanced email parsing with detailed debugging output"""
    print_status(f"Parsing email with subject: {subject[:50]}...", "debug")
    print_status(f"Body preview: {body[:100]}...", "debug")
    
    # Extract SL/TP from subject 
    subject_sl_pct = None
    subject_tp_pct = None
    subject_pattern = r".+ (\d{1,3})%SL (\d{1,3})%TP"
    subject_match = re.search(subject_pattern, subject)
    
    if subject_match:
        subject_sl_pct = float(subject_match.group(1))
        subject_tp_pct = float(subject_match.group(2))
        print_status(f"Found SL/TP in subject: {subject_sl_pct}%/{subject_tp_pct}%", "debug")
    else:
        print_status("No SL/TP found in subject", "warning")
    
    # Extract SL/TP from body parameters
    body_sl_pct = None  
    body_tp_pct = None
    body_pattern = r'\(,\s*([+-]?\d+\.?\d*),\s*([+-]?\d+\.?\d*),\s*([+-]?\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*)\)'
    body_match = re.search(body_pattern, body)
    
    if body_match:
        body_sl_pct = float(body_match.group(4))  # Position 4
        body_tp_pct = float(body_match.group(5))  # Position 5  
        print_status(f"Found SL/TP in body: {body_sl_pct}%/{body_tp_pct}%", "debug")
    else:
        print_status("No SL/TP parameters found in body", "warning")
    
    # Priority: body parameters > subject parameters
    sl_pct = body_sl_pct if body_sl_pct is not None else subject_sl_pct
    tp_pct = body_tp_pct if body_tp_pct is not None else subject_tp_pct
    
    if sl_pct is not None and tp_pct is not None:
        print_status(f"Final SL/TP: {sl_pct}%/{tp_pct}% (from {'body' if body_sl_pct else 'subject'})", "success")
    
    # Extract trade data from body
    trade_pattern = r'.+order\s+(\w+)\s+@\s+(\d+\.?\d*)\s+for\s+(\d+\.?\d+)\s+filled\s+on\s+(\w+)\s+at\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)'
    trade_match = re.search(trade_pattern, body)
    
    if trade_match:
        action = trade_match.group(1).upper()
        price = float(trade_match.group(2))
        quantity = float(trade_match.group(3))
        ticker = trade_match.group(4)
        timestamp_str = trade_match.group(5)
        
        print_status(f"Trade data extracted:", "success")
        print_status(f"  Action: {action}", "info")
        print_status(f"  Ticker: {ticker}", "info")
        print_status(f"  Price: ${price:,.2f}", "info")
        print_status(f"  Quantity: {quantity}", "info")
        print_status(f"  Timestamp: {timestamp_str}", "info")
        
        return {
            'action': action,
            'ticker': ticker, 
            'price': price,
            'quantity': quantity,
            'timestamp': timestamp_str,
            'sl_pct': sl_pct,
            'tp_pct': tp_pct
        }
    else:
        print_status("Failed to extract trade data from email body", "error")
        print_status(f"Body text: {body}", "debug")
        return None

def monitor_emails_live():
    """Live monitoring of incoming emails"""
    print_status("Starting live email monitoring...", "info")
    print_status("Press Ctrl+C to stop", "warning")
    
    last_check = datetime.now(pytz.UTC) - timedelta(minutes=5)
    
    def signal_handler(sig, frame):
        print_status("Monitoring stopped by user", "info")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    while True:
        try:
            with IMAPClient(EMAIL_HOST, port=EMAIL_PORT, ssl=True) as mail:
                mail.login(EMAIL_USER, EMAIL_PASS)
                mail.select_folder('INBOX')
                
                # Search for new emails since last check
                search_criteria = [
                    'FROM', SENDER_EMAIL,
                    'SINCE', last_check.date()
                ]
                
                message_ids = mail.search(search_criteria)
                
                new_messages = []
                current_time = datetime.now(pytz.UTC)
                
                for msg_id in message_ids:
                    msg_data = mail.fetch([msg_id], ['ENVELOPE', 'BODY[TEXT]'])
                    envelope = msg_data[msg_id][b'ENVELOPE']
                    
                    # Parse email date
                    email_date = envelope.date
                    if email_date > last_check:
                        new_messages.append(msg_id)
                
                if new_messages:
                    print_status(f"Found {len(new_messages)} new emails!", "email")
                    
                    for msg_id in new_messages:
                        msg_data = mail.fetch([msg_id], ['ENVELOPE', 'RFC822'])
                        raw_email = msg_data[msg_id][b'RFC822']
                        email_message = email.message_from_bytes(raw_email)
                        
                        subject = email_message['Subject']
                        body = ""
                        
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode('utf-8')
                                    break
                        else:
                            body = email_message.get_payload(decode=True).decode('utf-8')
                        
                        print_status("=" * 50, "email")
                        print_status(f"NEW EMAIL RECEIVED", "email")
                        print_status(f"Subject: {subject}", "info")
                        print_status(f"From: {email_message['From']}", "info")
                        print_status(f"Time: {email_message['Date']}", "info")
                        
                        # Parse the email
                        trade_data = parse_email_for_trade_data_debug(subject, body)
                        
                        if trade_data:
                            print_status("EMAIL PARSING SUCCESS!", "success")
                            print_status(f"Would execute: {trade_data['action']} {trade_data['ticker']} x{trade_data['quantity']} @ ${trade_data['price']}", "trade")
                        else:
                            print_status("EMAIL PARSING FAILED", "error")
                        
                        print_status("=" * 50, "email")
                
                last_check = current_time
                
        except Exception as e:
            print_status(f"Monitoring error: {str(e)}", "error")
            print_status("Reconnecting in 30 seconds...", "warning")
            time.sleep(30)
            continue
        
        # Wait before next check
        time.sleep(10)

def test_sample_emails():
    """Test parsing with sample TradingView emails"""
    print_status("Testing with sample email formats...", "info")
    
    test_cases = [
        {
            "name": "Standard BUY signal with SL/TP",
            "subject": "Alert: Top Overall 15M BTCUSD nSkew v3 3%SL 5%TP",
            "body": "ECP nSkew SL TP v3 (, 14, 70, -30, 5, 1): BUY Signal Activated order buy @ 100242 for 12.264199 filled on BTCUSD at 2025-11-07T12:00:00Z. New strategy position is 12.264199"
        },
        {
            "name": "SELL signal",
            "subject": "Alert: Top Overall 15M AAPL momentum v2 2%SL 3%TP",
            "body": "Trading Alert (, 20, 80, -15, 2, 3): SELL Signal Activated order sell @ 150.50 for 10.0 filled on AAPL at 2025-11-07T14:30:00Z. New strategy position is 0"
        },
        {
            "name": "Integer price format",
            "subject": "Alert: GOOGL breakout 4%SL 6%TP", 
            "body": "Strategy Alert (, 25, 75, -20, 4, 6): BUY Signal Activated order buy @ 2800 for 5.0 filled on GOOGL at 2025-11-07T15:45:00Z. New strategy position is 5.0"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print_status(f"Test Case {i}: {test['name']}", "info")
        print_status("-" * 40, "debug")
        
        result = parse_email_for_trade_data_debug(test["subject"], test["body"])
        
        if result:
            print_status(f"✅ Test {i} PASSED", "success")
        else:
            print_status(f"❌ Test {i} FAILED", "error")
        
        print_status("", "info")  # Blank line

def check_recent_emails():
    """Check recent emails from TradingView"""
    print_status("Checking recent emails from TradingView...", "info")
    
    try:
        with IMAPClient(EMAIL_HOST, port=EMAIL_PORT, ssl=True) as mail:
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.select_folder('INBOX')
            
            # Search for emails from TradingView in last 24 hours
            search_criteria = [
                'FROM', SENDER_EMAIL,
                'SINCE', (datetime.now() - timedelta(days=1)).date()
            ]
            
            message_ids = mail.search(search_criteria)
            
            if not message_ids:
                print_status("No recent emails found from TradingView", "warning")
                print_status("This could indicate:", "info")
                print_status("  - No trading signals generated", "info")
                print_status("  - Wrong SENDER_EMAIL configured", "info")
                print_status("  - TradingView alerts not set up", "info")
                return
            
            print_status(f"Found {len(message_ids)} recent emails from TradingView", "success")
            
            # Show details of most recent emails (last 3)
            recent_ids = list(message_ids)[-3:]
            
            for msg_id in recent_ids:
                msg_data = mail.fetch([msg_id], ['ENVELOPE', 'RFC822'])
                raw_email = msg_data[msg_id][b'RFC822']
                email_message = email.message_from_bytes(raw_email)
                
                subject = email_message['Subject']
                date = email_message['Date']
                
                print_status(f"Recent email: {subject}", "email")
                print_status(f"  Date: {date}", "info")
                
                # Try to parse it
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8')
                            break
                else:
                    body = email_message.get_payload(decode=True).decode('utf-8')
                
                result = parse_email_for_trade_data_debug(subject, body)
                if result:
                    print_status("  ✅ Successfully parseable", "success")
                else:
                    print_status("  ❌ Failed to parse", "error")
                
                print_status("", "info")  # Blank line
                
    except Exception as e:
        print_status(f"Error checking recent emails: {str(e)}", "error")

def main():
    parser = argparse.ArgumentParser(description="AutoTrader Email Debug & Monitor")
    parser.add_argument('--config', action='store_true', help='Validate email configuration')
    parser.add_argument('--connect', action='store_true', help='Test email connection')
    parser.add_argument('--recent', action='store_true', help='Check recent TradingView emails')
    parser.add_argument('--test', action='store_true', help='Test email parsing with samples')
    parser.add_argument('--monitor', action='store_true', help='Live monitoring mode')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    
    args = parser.parse_args()
    
    print_header()
    
    if args.all or not any(vars(args).values()):
        # Run all tests by default
        validate_email_config()
        print()
        test_email_connection()
        print()
        check_recent_emails()
        print() 
        test_sample_emails()
        print()
        print_status("All tests complete! Use --monitor for live monitoring", "info")
    else:
        if args.config:
            validate_email_config()
        
        if args.connect:
            test_email_connection()
        
        if args.recent:
            check_recent_emails()
            
        if args.test:
            test_sample_emails()
            
        if args.monitor:
            monitor_emails_live()

if __name__ == "__main__":
    main()