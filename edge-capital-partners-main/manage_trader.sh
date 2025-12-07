
#!/bin/bash

# AutoTrader Management Script (Cross-Platform Version)
# For Edge Capital Partners Trading Bot
# Version: 1.0 - November 2025 - Linux/macOS Compatible

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

# Platform detection
DEMO_PLATFORM=false

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

# Check platform
check_platform() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_warning "Running on non-macOS system (${OSTYPE})"
        print_info "LaunchD features will be disabled - suitable for testing only"
        export DEMO_PLATFORM=true
        return 0
    fi
    export DEMO_PLATFORM=false
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

# Create LaunchD service (macOS only)
create_launchd_service() {
    if [ "$DEMO_PLATFORM" = "true" ]; then
        print_warning "Skipping LaunchD service creation on non-macOS platform"
        print_info "Use './manage_trader.sh start' to run manually for testing"
        return 0
    fi
    
    print_info "Creating LaunchD service for 24/7 operation..."
    
    # Ensure LaunchAgents directory exists
    mkdir -p "$HOME/Library/LaunchAgents"
    
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
        if command -v lsof &> /dev/null; then
            if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                found_port=$port
                break
            fi
        elif command -v netstat &> /dev/null; then
            if netstat -ln | grep -q ":$port "; then
                found_port=$port
                break
            fi
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
    if [ "$DEMO_PLATFORM" = "true" ]; then
        # Check if Python process is running
        if pgrep -f "main.py.*--version" > /dev/null; then
            print_status "AutoTrader is RUNNING (background process)"
            return 0
        else
            print_warning "AutoTrader is NOT RUNNING"
            return 1
        fi
    fi
    
    # macOS LaunchD check
    if command -v launchctl &> /dev/null; then
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
    else
        print_warning "launchctl not available (non-macOS system)"
        return 1
    fi
}

# Start the bot
start_bot() {
    print_info "Starting AutoTrader..."
    
    # FIRST: Check platform (critical - must be first)
    if [ "$DEMO_PLATFORM" = "true" ]; then
        print_info "Starting in test mode (non-macOS platform)"
        source "$VENV_DIR/bin/activate"
        nohup python3 main.py --version=B > log/manual_stdout.log 2>&1 &
        sleep 3
        if check_bot_status; then
            print_status "AutoTrader started in background (test mode)"
            print_info "🔄 Demo mode features:"
            print_info "  - Mock trading positions (BTCUSD, AAPL, GOOGL)"
            print_info "  - Email parsing validation (no actual connections)"
            print_info "  - Full safety system testing"
            print_info "Use './manage_trader.sh logs' to monitor activity"
            print_info "Use './manage_trader.sh dashboard' to view real-time status"
        else
            print_error "Failed to start AutoTrader - check logs"
            print_info "Run './manage_trader.sh logs' to see what happened"
        fi
        return
    fi
    
    # SECOND: Check for demo credentials (enhanced logic)
    if [ -f "$ENV_FILE" ]; then
        email_user=$(grep "^EMAIL_USER=" "$ENV_FILE" | cut -d'=' -f2 | tr -d ' "')
        email_pass=$(grep "^EMAIL_PASS=" "$ENV_FILE" | cut -d'=' -f2 | tr -d ' "')
        ibkr_account=$(grep "^IBKR_ACCOUNT=" "$ENV_FILE" | cut -d'=' -f2 | tr -d ' "')
        
        if [ -z "$email_user" ] || [ -z "$email_pass" ] || [ -z "$ibkr_account" ] || 
           [[ "$email_user" == *"your-email"* ]] || [[ "$email_pass" == *"your-"* ]] || 
           [[ "$ibkr_account" == *"YOUR_ACCOUNT"* ]]; then
            print_warning "Demo mode detected (missing or template credentials)"
            print_info "Starting without TWS requirement..."
            source "$VENV_DIR/bin/activate"
            nohup python3 main.py --version=B > log/manual_stdout.log 2>&1 &
            sleep 3
            if check_bot_status; then
                print_status "AutoTrader started in demo mode"
                print_info "🔄 Demo mode features:"
                print_info "  - Mock trading positions (BTCUSD, AAPL, GOOGL)"
                print_info "  - Email parsing validation (no actual connections)"
                print_info "  - Full safety system testing"
                print_info "Use './manage_trader.sh dashboard' to monitor"
            else
                print_error "Failed to start AutoTrader - check logs"
                print_info "Run './manage_trader.sh logs' to see what happened"
            fi
            return
        fi
    else
        print_warning "No .env file found - starting in demo mode"
        source "$VENV_DIR/bin/activate"
        nohup python3 main.py --version=B > log/manual_stdout.log 2>&1 &
        sleep 3
        if check_bot_status; then
            print_status "AutoTrader started in demo mode (no configuration)"
        fi
        return
    fi
    
    # THIRD: Live mode - require TWS
    print_info "Live mode detected - checking TWS/Gateway..."
    if ! check_tws_running; then
        print_error "Cannot start bot: TWS/Gateway not running"
        print_info "For live trading, you need to:"
        print_info "1. Start TWS or IB Gateway"
        print_info "2. Enable API in TWS settings"
        print_info "3. Add 127.0.0.1 to trusted IPs"
        return 1
    fi
    
    # Load the service if not loaded (macOS only)
    if command -v launchctl >/dev/null 2>&1; then
        if ! launchctl list | grep -q "com.edgecapital.autotrader"; then
            launchctl load "$LAUNCHD_PLIST"
            sleep 2
        fi
        
        # Start the service
        launchctl start com.edgecapital.autotrader
        sleep 3
    else
        # Non-macOS live mode (shouldn't happen, but handle it)
        print_warning "Non-macOS live mode - starting manually"
        source "$VENV_DIR/bin/activate"
        nohup python3 main.py --version=B > log/manual_stdout.log 2>&1 &
        sleep 3
    fi
    
    if check_bot_status; then
        print_status "AutoTrader started successfully in live mode"
        print_warning "⚠️ LIVE MODE: Real trades will be placed!"
    else
        print_error "Failed to start AutoTrader - check logs"
        show_recent_logs
    fi
}

# Stop the bot
stop_bot() {
    print_info "Stopping AutoTrader..."
    
    # Check for running Python processes first
    if pgrep -f "main.py.*--version" > /dev/null; then
        print_info "Found running AutoTrader process"
        
        # Kill the Python process
        pkill -f "main.py.*--version"
        sleep 2
        
        # Verify it's stopped
        if ! pgrep -f "main.py.*--version" > /dev/null; then
            print_status "AutoTrader stopped successfully"
        else
            print_warning "Process still running - trying force kill..."
            pkill -9 -f "main.py.*--version"
            sleep 1
            if ! pgrep -f "main.py.*--version" > /dev/null; then
                print_status "AutoTrader force stopped"
            else
                print_error "Failed to stop AutoTrader process"
            fi
        fi
    else
        print_info "AutoTrader was not running"
    fi
    
    # Handle macOS LaunchD if available
    if command -v launchctl >/dev/null 2>&1; then
        if launchctl list | grep -q "com.edgecapital.autotrader" 2>/dev/null; then
            launchctl stop com.edgecapital.autotrader 2>/dev/null || true
            print_info "LaunchD service stopped"
        fi
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
    
    # Stop LaunchD service (macOS)
    if command -v launchctl &> /dev/null; then
        launchctl stop com.edgecapital.autotrader 2>/dev/null || true
        launchctl unload "$LAUNCHD_PLIST" 2>/dev/null || true
    fi
    
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
        echo ""
    fi
    
    if [ -f "$LOG_DIR/trade.log" ]; then
        echo -e "${BLUE}=== Trade Log (last 10 lines) ===${NC}"
        tail -n 10 "$LOG_DIR/trade.log"
        echo ""
    fi
    
    if [ -f "$LOG_DIR/manual_stdout.log" ]; then
        echo -e "${BLUE}=== Manual Run Log (last 10 lines) ===${NC}"
        tail -n 10 "$LOG_DIR/manual_stdout.log"
        echo ""
    fi
    
    if [ -f "$LOG_DIR/launchd_stderr.log" ]; then
        echo -e "${BLUE}=== Error Log (last 10 lines) ===${NC}"
        tail -n 10 "$LOG_DIR/launchd_stderr.log"
        echo ""
    fi
}

# Health check
health_check() {
    print_info "Running AutoTrader health check..."
    echo ""
    
    # Check platform
    if [ "$DEMO_PLATFORM" = "true" ]; then
        print_warning "Running on non-macOS platform (test mode)"
    else
        print_status "Running on macOS"
    fi
    
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
        if grep -q "YOUR_EMAIL\|your-email\|YOUR_ACCOUNT_NUMBER" "$ENV_FILE"; then
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
    
    # Check TWS (only meaningful test)
    if [ "$DEMO_PLATFORM" = "false" ]; then
        check_tws_running || true
    else
        print_info "TWS/Gateway check skipped (test mode)"
    fi
    
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

# Real-time monitoring dashboard
monitoring_dashboard() {
    print_info "Starting real-time monitoring dashboard..."
    print_warning "Press Ctrl+C to stop monitoring"
    
    if [ -f "$PROJECT_DIR/monitor_dashboard.py" ]; then
        source "$VENV_DIR/bin/activate"
        python3 "$PROJECT_DIR/monitor_dashboard.py"
    else
        print_error "Monitoring dashboard script not found"
    fi
}

# Email debugging and monitoring
debug_email_system() {
    print_info "Running email system diagnostics..."
    
    if [ -f "$PROJECT_DIR/email_debug.py" ]; then
        source "$VENV_DIR/bin/activate"
        python3 "$PROJECT_DIR/email_debug.py" --all
    else
        print_error "Email debug script not found"
        print_info "Please ensure email_debug.py is in your project directory"
    fi
}

# Live monitoring mode
live_monitoring() {
    print_info "Starting live monitoring mode..."
    print_warning "Press Ctrl+C to stop monitoring"
    
    if [ -f "$PROJECT_DIR/email_debug.py" ]; then
        source "$VENV_DIR/bin/activate"
        python3 "$PROJECT_DIR/email_debug.py" --monitor
    else
        print_error "Email debug script not found"
    fi
}

# Test email parsing
test_email_parsing() {
    print_info "Testing email parsing with sample TradingView emails..."
    
    if [ -f "$PROJECT_DIR/email_debug.py" ]; then
        source "$VENV_DIR/bin/activate"
        python3 "$PROJECT_DIR/email_debug.py" --test
    else
        print_error "Email debug script not found"
    fi
}

# Full setup process
full_setup() {
    print_info "Starting full AutoTrader setup..."
    echo ""
    
    check_platform
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
    if [ "$DEMO_PLATFORM" = "false" ]; then
        print_info "3. Start TWS/IB Gateway and enable API"
        print_info "4. Run: ./manage_trader.sh start"
    else
        print_info "3. For testing: ./manage_trader.sh start (runs in demo mode)"
    fi
    echo ""
}
 Debug orders analysis
debug_orders_analysis() {
    print_info "Analyzing IBKR order attempts and responses..."
    
    if [ -f "$PROJECT_DIR/debug_orders.py" ]; then
        source "$VENV_DIR/bin/activate"
        # Pass any additional arguments to the debug script
        python3 "$PROJECT_DIR/debug_orders.py" "$@"
    else
        print_error "Order debug script not found"
        print_info "Please ensure debug_orders.py is in your project directory"
        print_info "This script analyzes IBKR order flow from enhanced debugging logs"
    fi
}

validate_symbols_config() {
    print_info "Validating symbols in trade configuration..."
    
    if [ -f "$PROJECT_DIR/validate_symbols.py" ]; then
        source "$VENV_DIR/bin/activate"
        # Pass any additional arguments to the validation script
        python3 "$PROJECT_DIR/validate_symbols.py" "$@"
    else
        print_error "Symbol validation script not found"
        print_info "Please ensure validate_symbols.py is in your project directory"
        print_info "This script checks trade config symbols and suggests corrections"
    fi
}


show_help() {
    echo "AutoTrader Management Script (Cross-Platform)"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  setup           Complete initial setup"
    echo "  start           Start the trading bot"
    echo "  stop            Stop the trading bot"
    echo "  restart         Restart the trading bot"
    echo "  status          Check bot status"
    echo "  logs            Show recent logs"
    echo "  health          Run health diagnostics"
    echo "  debug-email     Debug email connectivity and parsing"
    echo "  debug-orders    Debug IBKR order attempts and responses"
    echo "  test-ibkr       Test IBKR connection and validate symbols"
    echo "  validate-symbols Check trade config and suggest corrections"
    echo "  monitor         Live email monitoring (real-time)"
    echo "  dashboard       Real-time trading dashboard"
    echo "  test-parsing    Test email parsing with samples"
    echo "  update          Update and restart bot"
    echo "  emergency       Emergency stop all processes"
    echo "  check-tws       Check if TWS/Gateway is running"
    echo "  help            Show this help"
    echo ""
    echo "Debug Commands:"
    echo "  debug-email     Complete email system diagnostics"
    echo "  debug-orders    Analyze IBKR order flow and responses"
    echo "    --detailed      Show detailed order information"
    echo "    --failed        Show only failed orders"
    echo "    --hours X       Look back X hours (default: 24)"
    echo "  test-ibkr       Test IBKR connection and symbol validation"
    echo "    --config        Test symbols from trade config"
    echo "    --crypto        Test cryptocurrency symbols"
    echo "    --symbols X Y   Test specific symbols"
    echo "    --orders        Test order creation without placing"
    echo "    --all           Run comprehensive test suite"
    echo "  validate-symbols Check trade config symbols and suggest fixes"
    echo "    --detailed      Show detailed validation report"
    echo "    --generate      Create corrected config file"
    echo "    --version X     Trade config version (default: B)"
    echo "  monitor         Watch for incoming emails in real-time"
    echo "  dashboard       Real-time system monitoring dashboard"
    echo "  test-parsing    Test parsing with sample TradingView emails"
    echo ""
    echo "Examples:"
    echo "  $0 setup                          # First-time setup"
    echo "  $0 start                          # Start trading"
    echo "  $0 validate-symbols               # Check config symbols"
    echo "  $0 validate-symbols --generate    # Create corrected config"
    echo "  $0 test-ibkr --config             # Test all config symbols"
    echo "  $0 test-ibkr --symbols BTCUSD     # Test specific symbol"
    echo "  $0 debug-orders --failed          # Show failed orders"
    echo "  $0 logs                           # View recent activity"
    echo ""
    if [ "$DEMO_PLATFORM" = "true" ]; then
        echo "Note: Running on non-macOS platform - LaunchD features disabled"
        echo "      Suitable for testing and development"
    fi
}
# # Show help
# show_help() {
#     echo "AutoTrader Management Script (Cross-Platform)"
#     echo ""
#     echo "Usage: $0 <command>"
#     echo ""
#     echo "Commands:"
#     echo "  setup         Complete initial setup"
#     echo "  start         Start the trading bot"
#     echo "  stop          Stop the trading bot"
#     echo "  restart       Restart the trading bot"
#     echo "  status        Check bot status"
#     echo "  logs          Show recent logs"
#     echo "  health        Run health diagnostics"
#     echo "  debug-email   Debug email connectivity and parsing"
#     echo "  monitor       Live email monitoring (real-time)"
#     echo "  dashboard     Real-time trading dashboard"
#     echo "  test-parsing  Test email parsing with samples"
#     echo "  update        Update and restart bot"
#     echo "  emergency     Emergency stop all processes"
#     echo "  check-tws     Check if TWS/Gateway is running"
#     echo "  help          Show this help"
#     echo ""
#     echo "Debug Commands:"
#     echo "  debug-email   Complete email system diagnostics"
#     echo "  monitor       Watch for incoming emails in real-time"
#     echo "  dashboard     Real-time system monitoring dashboard"
#     echo "  test-parsing  Test parsing with sample TradingView emails"
#     echo ""
#     echo "Examples:"
#     echo "  $0 setup      # First-time setup"
#     echo "  $0 start      # Start trading"
#     echo "  $0 status     # Check if running"
#     echo "  $0 logs       # View recent activity"
#     echo ""
#     if [ "$DEMO_PLATFORM" = "true" ]; then
#         echo "Note: Running on non-macOS platform - LaunchD features disabled"
#         echo "      Suitable for testing and development"
#     fi
# }




# # Main script logic
# main() {
#     show_banner
    
#     # Set platform detection
#     check_platform
    
#     case "${1:-help}" in
#         "setup")
#             full_setup
#             ;;
#         "start")
#             start_bot
#             ;;
#         "stop")
#             stop_bot
#             ;;
#         "restart")
#             restart_bot
#             ;;
#         "status")
#             check_bot_status
#             ;;
#         "logs")
#             show_recent_logs
#             ;;
#         "health"|"doctor")
#             health_check
#             ;;
#         "debug-email")
#             debug_email_system
#             ;;
#         "monitor")
#             live_monitoring
#             ;;
#         "dashboard")
#             monitoring_dashboard
#             ;;
#         "test-parsing")
#             test_email_parsing
#             ;;
#         "update")
#             update_bot
#             ;;
#         "emergency"|"emergency-stop")
#             emergency_stop
#             ;;
#         "check-tws")
#             check_tws_running
#             ;;
#         "help"|*)
#             show_help
#             ;;
#     esac
# }


main() {
    show_banner
    
    # Set platform detection
    check_platform
    
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
        "debug-email")
            debug_email_system
            ;;
        "debug-orders")
            shift  # Remove the command name
            debug_orders_analysis "$@"  # Pass remaining args to debug script
            ;;
        "test-ibkr")
            shift  # Remove the command name
            test_ibkr_connection "$@"  # Pass remaining args to test script
            ;;
        "validate-symbols")
            shift  # Remove the command name
            validate_symbols_config "$@"  # Pass remaining args to validation script
            ;;
        "monitor")
            live_monitoring
            ;;
        "dashboard")
            monitoring_dashboard
            ;;
        "test-parsing")
            test_email_parsing
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