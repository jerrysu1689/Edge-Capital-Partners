#!/bin/bash

# AutoTrader Management Script
# For Edge Capital Partners Trading Bot
# Version: 1.0 - November 2025

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="AutoTrader"
PYTHON_CMD="python3"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/log"
CONFIG_DIR="$PROJECT_DIR/config"
ENV_FILE="$PROJECT_DIR/.env"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
MAIN_SCRIPT="$PROJECT_DIR/main.py"
LAUNCHD_PLIST="$HOME/Library/LaunchAgents/com.edgecapital.autotrader.plist"

# Print colored output
print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Banner
show_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════╗"
    echo "║        AutoTrader Manager v1.0       ║"
    echo "║      Edge Capital Partners           ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if running on macOS
check_macos() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_error "This script is designed for macOS only"
        exit 1
    fi
}

# Check if Python 3 is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        print_info "Please install Python 3 from https://www.python.org/downloads/"
        exit 1
    fi
    
    local python_version=$(python3 --version | cut -d' ' -f2)
    print_status "Python ${python_version} found"
}

# Create virtual environment
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    source "$VENV_DIR/bin/activate"
    print_status "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    source "$VENV_DIR/bin/activate"
    
    if [ -f "$REQUIREMENTS_FILE" ]; then
        pip install --upgrade pip
        pip install -r "$REQUIREMENTS_FILE"
        print_status "Dependencies installed successfully"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# Create necessary directories
create_directories() {
    print_info "Creating necessary directories..."
    mkdir -p "$LOG_DIR" "$CONFIG_DIR"
    print_status "Directories created"
}

# Setup .env file
setup_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$PROJECT_DIR/sample.env" ]; then
            print_info "Creating .env file from template..."
            cp "$PROJECT_DIR/sample.env" "$ENV_FILE"
            print_warning "Please edit .env file with your credentials:"
            print_info "nano $ENV_FILE"
            print_info ""
            print_info "Required settings:"
            print_info "- EMAIL_USER: Your Gmail address"
            print_info "- EMAIL_PASS: Gmail App Password (16 characters)"
            print_info "- SENDER_EMAIL: TradingView sender email"
            print_info "- IBKR_ACCOUNT: Your IBKR account number"
            print_info "- IB_API_PORT: 7497 (TWS) or 4001 (Gateway)"
        else
            print_error "sample.env not found"
            exit 1
        fi
    else
        print_status ".env file already exists"
    fi
}

# Setup trade config
setup_trade_config() {
    local config_file="$CONFIG_DIR/trade_config_version_B.csv"
    if [ ! -f "$config_file" ]; then
        print_info "Creating trade configuration template..."
        cat > "$config_file" << EOF
ibkr_account,ticker,price,quantity
YOUR_ACCOUNT_NUMBER,BTCUSD,50000,1
YOUR_ACCOUNT_NUMBER,AAPL,150,10
EOF
        print_warning "Please edit trade config with your account number:"
        print_info "nano $config_file"
    else
        print_status "Trade config already exists"
    fi
}

# Setup last checked email time
setup_email_time() {
    local time_file="$PROJECT_DIR/last_checked_email_time.json"
    if [ ! -f "$time_file" ]; then
        print_info "Creating email time tracker..."
        echo '{"last_checked_email_time": "2025-01-01 00:00:00+00:00"}' > "$time_file"
        print_status "Email time tracker created"
    fi
}

# Create LaunchD service
create_launchd_service() {
    print_info "Creating LaunchD service for 24/7 operation..."
    
    cat > "$LAUNCHD_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.edgecapital.autotrader</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python</string>
        <string>$MAIN_SCRIPT</string>
        <string>--version=B</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/launchd_stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/launchd_stderr.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
    
    print_status "LaunchD service created"
}

# Check if TWS/Gateway is running
check_tws_running() {
    local tws_ports=("7497" "4001" "7496" "4002")
    local found_port=""
    
    for port in "${tws_ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            found_port=$port
            break
        fi
    done
    
    if [ -n "$found_port" ]; then
        print_status "TWS/Gateway running on port $found_port"
        return 0
    else
        print_error "TWS/Gateway not running on any standard ports (7497, 4001, 7496, 4002)"
        print_info "Please start TWS or IB Gateway and enable API"
        return 1
    fi
}

# Check bot status
check_bot_status() {
    if launchctl list | grep -q "com.edgecapital.autotrader"; then
        local status=$(launchctl list com.edgecapital.autotrader 2>/dev/null | grep "PID" | awk '{print $3}')
        if [ "$status" != "-" ]; then
            print_status "AutoTrader is RUNNING (PID: $status)"
            return 0
        else
            print_warning "AutoTrader is LOADED but not running"
            return 1
        fi
    else
        print_warning "AutoTrader is NOT LOADED"
        return 1
    fi
}

# Start the bot
start_bot() {
    print_info "Starting AutoTrader..."
    
    if ! check_tws_running; then
        print_error "Cannot start bot: TWS/Gateway not running"
        return 1
    fi
    
    # Load the service if not loaded
    if ! launchctl list | grep -q "com.edgecapital.autotrader"; then
        launchctl load "$LAUNCHD_PLIST"
        sleep 2
    fi
    
    # Start the service
    launchctl start com.edgecapital.autotrader
    sleep 3
    
    if check_bot_status; then
        print_status "AutoTrader started successfully"
    else
        print_error "Failed to start AutoTrader - check logs"
        show_recent_logs
    fi
}

# Stop the bot
stop_bot() {
    print_info "Stopping AutoTrader..."
    
    if launchctl list | grep -q "com.edgecapital.autotrader"; then
        launchctl stop com.edgecapital.autotrader
        sleep 2
        print_status "AutoTrader stopped"
    else
        print_info "AutoTrader was not running"
    fi
}

# Restart the bot
restart_bot() {
    print_info "Restarting AutoTrader..."
    stop_bot
    sleep 2
    start_bot
}

# Emergency stop - kill all processes
emergency_stop() {
    print_warning "EMERGENCY STOP - Killing all AutoTrader processes..."
    
    # Stop LaunchD service
    launchctl stop com.edgecapital.autotrader 2>/dev/null || true
    launchctl unload "$LAUNCHD_PLIST" 2>/dev/null || true
    
    # Kill any remaining Python processes running main.py
    pkill -f "main.py" || true
    
    print_status "Emergency stop completed"
}

# Show recent logs
show_recent_logs() {
    print_info "Recent AutoTrader logs:"
    echo ""
    
    if [ -f "$LOG_DIR/application.log" ]; then
        echo -e "${BLUE}=== Application Log (last 20 lines) ===${NC}"
        tail -n 20 "$LOG_DIR/application.log"
    fi
    
    if [ -f "$LOG_DIR/trade.log" ]; then
        echo -e "${BLUE}=== Trade Log (last 10 lines) ===${NC}"
        tail -n 10 "$LOG_DIR/trade.log"
    fi
    
    if [ -f "$LOG_DIR/launchd_stderr.log" ]; then
        echo -e "${BLUE}=== Error Log (last 10 lines) ===${NC}"
        tail -n 10 "$LOG_DIR/launchd_stderr.log"
    fi
}

# Health check
health_check() {
    print_info "Running AutoTrader health check..."
    echo ""
    
    # Check Python
    if command -v python3 &> /dev/null; then
        print_status "Python 3 installed"
    else
        print_error "Python 3 not found"
    fi
    
    # Check virtual environment
    if [ -d "$VENV_DIR" ]; then
        print_status "Virtual environment exists"
    else
        print_error "Virtual environment missing"
    fi
    
    # Check .env file
    if [ -f "$ENV_FILE" ]; then
        print_status ".env file exists"
        # Check if it has required values
        if grep -q "YOUR_EMAIL" "$ENV_FILE"; then
            print_warning ".env file needs configuration (contains template values)"
        fi
    else
        print_error ".env file missing"
    fi
    
    # Check trade config
    local config_file="$CONFIG_DIR/trade_config_version_B.csv"
    if [ -f "$config_file" ]; then
        print_status "Trade config exists"
        if grep -q "YOUR_ACCOUNT_NUMBER" "$config_file"; then
            print_warning "Trade config needs your IBKR account number"
        fi
    else
        print_error "Trade config missing"
    fi
    
    # Check TWS
    check_tws_running || true
    
    # Check bot status
    echo ""
    check_bot_status || true
    
    echo ""
    print_info "Health check complete"
}

# Update bot (git pull + restart)
update_bot() {
    print_info "Updating AutoTrader..."
    
    # Stop bot first
    stop_bot
    
    # Pull latest changes
    print_info "Downloading latest updates..."
    git pull origin main || {
        print_error "Failed to update from git"
        print_info "Starting bot with current version..."
        start_bot
        return 1
    }
    
    # Update dependencies
    source "$VENV_DIR/bin/activate"
    pip install -r "$REQUIREMENTS_FILE"
    
    # Restart bot
    print_status "Update complete - restarting bot..."
    start_bot
}

# Full setup process
full_setup() {
    print_info "Starting full AutoTrader setup..."
    echo ""
    
    check_macos
    check_python
    create_directories
    setup_venv
    install_dependencies
    setup_env_file
    setup_trade_config
    setup_email_time
    create_launchd_service
    
    echo ""
    print_status "Setup completed successfully!"
    echo ""
    print_warning "NEXT STEPS:"
    print_info "1. Configure .env file: nano $ENV_FILE"
    print_info "2. Configure trade config: nano $CONFIG_DIR/trade_config_version_B.csv"
    print_info "3. Start TWS/IB Gateway and enable API"
    print_info "4. Run: ./manage_trader.sh start"
    echo ""
}

# Show help
show_help() {
    echo "AutoTrader Management Script"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  setup         Complete initial setup"
    echo "  start         Start the trading bot"
    echo "  stop          Stop the trading bot"
    echo "  restart       Restart the trading bot"
    echo "  status        Check bot status"
    echo "  logs          Show recent logs"
    echo "  health        Run health diagnostics"
    echo "  update        Update and restart bot"
    echo "  emergency     Emergency stop all processes"
    echo "  check-tws     Check if TWS/Gateway is running"
    echo "  help          Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 setup      # First-time setup"
    echo "  $0 start      # Start trading"
    echo "  $0 status     # Check if running"
    echo "  $0 logs       # View recent activity"
    echo ""
}

# Main script logic
main() {
    show_banner
    
    case "${1:-help}" in
        "setup")
            full_setup
            ;;
        "start")
            start_bot
            ;;
        "stop")
            stop_bot
            ;;
        "restart")
            restart_bot
            ;;
        "status")
            check_bot_status
            ;;
        "logs")
            show_recent_logs
            ;;
        "health"|"doctor")
            health_check
            ;;
        "update")
            update_bot
            ;;
        "emergency"|"emergency-stop")
            emergency_stop
            ;;
        "check-tws")
            check_tws_running
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function with all arguments
main "$@"