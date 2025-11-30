#!/usr/bin/env python3
"""
AutoTrader Real-Time Monitoring Dashboard
Live status monitoring for trading bot operations
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import threading
import signal
import argparse

# Load environment
load_dotenv()

# Configuration
IBKR_ACCOUNT = os.getenv("IBKR_ACCOUNT", "DEMO_ACCOUNT")
EMAIL_USER = os.getenv("EMAIL_USER", "")
BOT_TRADES_FILE = "bot_trades.json"

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

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def print_dashboard_header():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗
║                    AutoTrader Live Dashboard                  ║
║                     {timestamp}                    ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
""")

def check_bot_process_status():
    """Check if bot process is running"""
    try:
        # Check for Python process running main.py
        result = subprocess.run(['pgrep', '-f', 'main.py.*--version'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            return True, len(pids), pids[0] if pids else None
        else:
            return False, 0, None
            
    except Exception as e:
        return False, 0, None

def check_email_connectivity():
    """Test email server connectivity"""
    try:
        from imapclient import IMAPClient
        
        EMAIL_HOST = os.getenv("EMAIL_HOST", "imap.gmail.com")
        EMAIL_PORT = int(os.getenv("EMAIL_PORT", 993))
        EMAIL_PASS = os.getenv("EMAIL_PASS", "")
        
        if not EMAIL_USER or not EMAIL_PASS:
            return "config", "Missing credentials"
        
        if "your-email" in EMAIL_USER.lower() or len(EMAIL_PASS) != 16:
            return "config", "Template values detected"
        
        # Quick connection test with timeout
        with IMAPClient(EMAIL_HOST, port=EMAIL_PORT, ssl=True, timeout=10) as mail:
            mail.login(EMAIL_USER, EMAIL_PASS)
            return "connected", "Email server connected"
            
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower():
            return "auth_failed", "Authentication failed"
        elif "timeout" in error_msg.lower():
            return "timeout", "Connection timeout"
        else:
            return "error", f"Connection error: {error_msg[:50]}"

def check_tws_connectivity():
    """Check TWS/Gateway connectivity"""
    try:
        import socket
        
        ports = [7497, 4001, 7496, 4002]
        connected_ports = []
        
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                connected_ports.append(port)
        
        if connected_ports:
            return "connected", f"Ports {connected_ports} open"
        else:
            return "disconnected", "No TWS/Gateway ports open"
            
    except Exception as e:
        return "error", f"Error checking TWS: {str(e)[:30]}"

def load_trade_statistics():
    """Load recent trade statistics"""
    try:
        if not os.path.exists(BOT_TRADES_FILE):
            return {
                'total_trades': 0,
                'today_trades': 0,
                'last_trade': None,
                'open_positions': {},
                'demo_mode': True
            }
        
        with open(BOT_TRADES_FILE, 'r') as f:
            data = json.load(f)
        
        trades = data.get('trades', [])
        summary = data.get('summary', {})
        
        # Count today's trades
        today = datetime.now().date()
        today_trades = 0
        last_trade = None
        
        for trade in trades:
            trade_date = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00')).date()
            if trade_date == today:
                today_trades += 1
            
            if not last_trade or trade['timestamp'] > last_trade['timestamp']:
                last_trade = trade
        
        return {
            'total_trades': len(trades),
            'today_trades': today_trades,
            'last_trade': last_trade,
            'open_positions': {k: v['open_quantity'] for k, v in summary.items() if v.get('open_quantity', 0) > 0},
            'demo_mode': last_trade.get('demo_mode', True) if last_trade else True
        }
        
    except Exception as e:
        return {
            'total_trades': 0,
            'today_trades': 0,
            'last_trade': None,
            'open_positions': {},
            'demo_mode': True,
            'error': str(e)
        }

def get_log_tail(log_file, lines=5):
    """Get last few lines from log file"""
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) >= lines else all_lines
        return []
    except:
        return []

def display_dashboard():
    """Display the monitoring dashboard"""
    
    # Get system status
    bot_running, process_count, pid = check_bot_process_status()
    email_status, email_msg = check_email_connectivity()
    tws_status, tws_msg = check_tws_connectivity()
    trade_stats = load_trade_statistics()
    
    clear_screen()
    print_dashboard_header()
    
    # System Status Section
    print(f"{Colors.BOLD}🔧 SYSTEM STATUS{Colors.RESET}")
    print("─" * 60)
    
    # Bot Process
    if bot_running:
        print(f"{Colors.GREEN}✅ Bot Process: RUNNING (PID: {pid}){Colors.RESET}")
    else:
        print(f"{Colors.RED}❌ Bot Process: NOT RUNNING{Colors.RESET}")
    
    # Email Connectivity
    email_color = {
        "connected": Colors.GREEN + "✅",
        "config": Colors.YELLOW + "⚠️", 
        "auth_failed": Colors.RED + "❌",
        "timeout": Colors.YELLOW + "⚠️",
        "error": Colors.RED + "❌"
    }.get(email_status, Colors.WHITE + "•")
    
    print(f"{email_color} Email: {email_msg}{Colors.RESET}")
    
    # TWS Connectivity
    tws_color = Colors.GREEN + "✅" if tws_status == "connected" else Colors.YELLOW + "⚠️"
    print(f"{tws_color} TWS/Gateway: {tws_msg}{Colors.RESET}")
    
    # Trading Mode
    mode = "DEMO" if trade_stats['demo_mode'] else "LIVE"
    mode_color = Colors.CYAN if trade_stats['demo_mode'] else Colors.MAGENTA
    print(f"{mode_color}🔄 Trading Mode: {mode}{Colors.RESET}")
    
    print()
    
    # Trading Statistics Section
    print(f"{Colors.BOLD}📊 TRADING STATISTICS{Colors.RESET}")
    print("─" * 60)
    
    print(f"{Colors.WHITE}Total Trades: {trade_stats['total_trades']}{Colors.RESET}")
    print(f"{Colors.WHITE}Today's Trades: {trade_stats['today_trades']}{Colors.RESET}")
    
    # Last Trade
    if trade_stats['last_trade']:
        last_trade = trade_stats['last_trade']
        trade_time = datetime.fromisoformat(last_trade['timestamp'].replace('Z', '+00:00'))
        time_ago = datetime.now(pytz.UTC) - trade_time
        
        if time_ago.days > 0:
            time_str = f"{time_ago.days}d ago"
        elif time_ago.seconds > 3600:
            time_str = f"{time_ago.seconds//3600}h ago"
        else:
            time_str = f"{time_ago.seconds//60}m ago"
        
        action_color = Colors.GREEN if last_trade['action'] == 'BUY' else Colors.RED
        print(f"{Colors.WHITE}Last Trade: {action_color}{last_trade['action']}{Colors.RESET} {last_trade['ticker']} x{last_trade['quantity']} @ ${last_trade['price']:,.2f} ({time_str})")
    else:
        print(f"{Colors.WHITE}Last Trade: None{Colors.RESET}")
    
    # Open Positions
    if trade_stats['open_positions']:
        print(f"{Colors.WHITE}Open Positions:{Colors.RESET}")
        for ticker, qty in trade_stats['open_positions'].items():
            print(f"  {Colors.CYAN}{ticker}: {qty} units{Colors.RESET}")
    else:
        print(f"{Colors.WHITE}Open Positions: None{Colors.RESET}")
    
    print()
    
    # Recent Activity Section
    print(f"{Colors.BOLD}📝 RECENT ACTIVITY{Colors.RESET}")
    print("─" * 60)
    
    # Recent application logs
    app_logs = get_log_tail('log/application.log', 3)
    if app_logs:
        print(f"{Colors.WHITE}Application Log:{Colors.RESET}")
        for log_line in app_logs:
            # Clean up log line
            clean_line = log_line.strip()
            if len(clean_line) > 80:
                clean_line = clean_line[:77] + "..."
            
            # Color code by log level
            if "ERROR" in clean_line:
                print(f"  {Colors.RED}{clean_line}{Colors.RESET}")
            elif "WARNING" in clean_line:
                print(f"  {Colors.YELLOW}{clean_line}{Colors.RESET}")
            elif "DEMO" in clean_line:
                print(f"  {Colors.CYAN}{clean_line}{Colors.RESET}")
            else:
                print(f"  {Colors.WHITE}{clean_line}{Colors.RESET}")
    
    # Recent trade logs
    trade_logs = get_log_tail('log/trade.log', 2)
    if trade_logs:
        print(f"{Colors.WHITE}Trade Log:{Colors.RESET}")
        for log_line in trade_logs:
            clean_line = log_line.strip()
            if len(clean_line) > 80:
                clean_line = clean_line[:77] + "..."
            print(f"  {Colors.GREEN}{clean_line}{Colors.RESET}")
    
    print()
    print(f"{Colors.WHITE}Press Ctrl+C to exit | Refreshing every 10 seconds...{Colors.RESET}")

def monitor_continuously():
    """Run continuous monitoring"""
    
    def signal_handler(sig, frame):
        print(f"\n{Colors.WHITE}Monitoring stopped{Colors.RESET}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    while True:
        try:
            display_dashboard()
            time.sleep(10)
        except KeyboardInterrupt:
            print(f"\n{Colors.WHITE}Monitoring stopped{Colors.RESET}")
            break
        except Exception as e:
            print(f"\n{Colors.RED}Error in monitoring: {e}{Colors.RESET}")
            time.sleep(5)

def main():
    parser = argparse.ArgumentParser(description="AutoTrader Live Monitoring Dashboard")
    parser.add_argument('--once', action='store_true', help='Show dashboard once and exit')
    
    args = parser.parse_args()
    
    if args.once:
        display_dashboard()
    else:
        monitor_continuously()

if __name__ == "__main__":
    main()