#!/usr/bin/env python3
"""
Validate Symbols Script for AutoTrader
Checks trade config symbols and suggests corrections for invalid ones
"""

import os
import sys
import argparse
from typing import List, Dict, Optional, Tuple
import pandas as pd
from dotenv import load_dotenv

# Import from trade module
try:
    from trade import setup_ib_connection, DEMO_MODE, IBKR_ACCOUNT
    from ib_insync import *
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

load_dotenv()

# Color codes for output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'  # No Color

# Symbol mapping database for common corrections
SYMBOL_SUGGESTIONS = {
    'BTCUSD': [
        ('BTC-USD', 'PAXOS', 'USD'),
        ('BTC', 'PAXOS', 'USD'),
        ('XBTUSD', 'SMART', 'USD')
    ],
    'ETHUSD': [
        ('ETH-USD', 'PAXOS', 'USD'),
        ('ETH', 'PAXOS', 'USD')
    ],
    'ADAUSD': [
        ('ADA-USD', 'PAXOS', 'USD'),
        ('ADA', 'PAXOS', 'USD')
    ],
    'SOLUSD': [
        ('SOL-USD', 'PAXOS', 'USD'),
        ('SOL', 'PAXOS', 'USD')
    ],
    'BTC': [
        ('BTC-USD', 'PAXOS', 'USD'),
        ('BTCUSD', 'SMART', 'USD')
    ],
    'ETH': [
        ('ETH-USD', 'PAXOS', 'USD'),
        ('ETHUSD', 'SMART', 'USD')
    ]
}

def print_header():
    """Print the validate symbols header"""
    print(f"{Colors.BLUE}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║            AutoTrader Symbol Validation Tool                ║")
    print("║          Trade Config Analysis & Corrections               ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Colors.NC}")

def load_trade_config(version: str) -> Optional[pd.DataFrame]:
    """Load and validate trade config file"""
    config_file = f"config/trade_config_version_{version}.csv"
    
    if not os.path.exists(config_file):
        print(f"{Colors.RED}❌ Config file not found: {config_file}{Colors.NC}")
        return None
    
    try:
        df = pd.read_csv(config_file)
        
        # Validate required columns
        required_columns = ['ibkr_account', 'ticker', 'price', 'quantity']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"{Colors.RED}❌ Missing required columns: {missing_columns}{Colors.NC}")
            return None
        
        print(f"{Colors.GREEN}✅ Loaded config: {len(df)} rows{Colors.NC}")
        return df
        
    except Exception as e:
        print(f"{Colors.RED}❌ Error loading config: {e}{Colors.NC}")
        return None

def test_symbol_qualification(ib: object, symbol: str, exchange: str = "SMART", currency: str = "USD") -> Dict:
    """Test if a symbol can be qualified with IBKR"""
    result = {
        'symbol': symbol,
        'exchange': exchange,
        'currency': currency,
        'qualified': False,
        'contracts': [],
        'error': None
    }
    
    if DEMO_MODE:
        # Demo mode - simulate known symbols
        demo_valid = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'SPY', 'QQQ']
        crypto_valid = ['BTC-USD', 'ETH-USD'] if exchange == 'PAXOS' else []
        
        if symbol in demo_valid or symbol in crypto_valid:
            result['qualified'] = True
            result['contracts'] = [f"Demo contract for {symbol}"]
        else:
            result['qualified'] = False
            result['error'] = f"Symbol not in demo database"
        return result
    
    try:
        # Create contract
        contract = Stock(symbol, exchange=exchange, currency=currency)
        
        # Try to qualify with IBKR
        qualified_contracts = ib.qualifyContracts(contract)
        
        if qualified_contracts:
            result['qualified'] = True
            result['contracts'] = qualified_contracts
        else:
            result['qualified'] = False
            result['error'] = "No qualified contracts found"
            
    except Exception as e:
        result['qualified'] = False
        result['error'] = str(e)
    
    return result

def find_symbol_alternatives(ib: object, symbol: str) -> List[Dict]:
    """Find alternative symbol formats that might work"""
    alternatives = []
    
    # Check predefined suggestions
    if symbol in SYMBOL_SUGGESTIONS:
        for alt_symbol, alt_exchange, alt_currency in SYMBOL_SUGGESTIONS[symbol]:
            result = test_symbol_qualification(ib, alt_symbol, alt_exchange, alt_currency)
            if result['qualified']:
                alternatives.append({
                    'original': symbol,
                    'suggested': alt_symbol,
                    'exchange': alt_exchange,
                    'currency': alt_currency,
                    'contracts': result['contracts']
                })
    
    # Try common crypto exchanges for crypto-like symbols
    if any(crypto in symbol.upper() for crypto in ['BTC', 'ETH', 'ADA', 'SOL']):
        crypto_exchanges = ['PAXOS', 'CRYPTO']
        for exchange in crypto_exchanges:
            # Try with hyphen format
            if 'USD' in symbol and '-' not in symbol:
                alt_symbol = symbol.replace('USD', '-USD')
                result = test_symbol_qualification(ib, alt_symbol, exchange, 'USD')
                if result['qualified']:
                    alternatives.append({
                        'original': symbol,
                        'suggested': alt_symbol,
                        'exchange': exchange,
                        'currency': 'USD',
                        'contracts': result['contracts']
                    })
    
    return alternatives

def validate_config_symbols(ib: object, df: pd.DataFrame) -> Dict:
    """Validate all symbols in trade config"""
    print(f"{Colors.CYAN}🔍 Validating symbols in trade config...{Colors.NC}")
    
    unique_symbols = df['ticker'].unique().tolist()
    results = {
        'valid_symbols': [],
        'invalid_symbols': [],
        'suggestions': []
    }
    
    print(f"   Testing {len(unique_symbols)} unique symbols...")
    print()
    
    for symbol in unique_symbols:
        print(f"   🔍 Testing {symbol}...", end=" ")
        
        # Test original symbol
        result = test_symbol_qualification(ib, symbol)
        
        if result['qualified']:
            print(f"{Colors.GREEN}✅ Valid{Colors.NC}")
            results['valid_symbols'].append({
                'symbol': symbol,
                'exchange': result['exchange'],
                'currency': result['currency'],
                'contracts': result['contracts']
            })
        else:
            print(f"{Colors.RED}❌ Invalid{Colors.NC}")
            results['invalid_symbols'].append({
                'symbol': symbol,
                'error': result['error']
            })
            
            # Find alternatives
            print(f"      🔍 Searching for alternatives...")
            alternatives = find_symbol_alternatives(ib, symbol)
            
            if alternatives:
                for alt in alternatives:
                    print(f"      {Colors.GREEN}💡 Suggestion: {alt['suggested']} on {alt['exchange']}{Colors.NC}")
                    results['suggestions'].append(alt)
            else:
                print(f"      {Colors.YELLOW}⚠️ No alternatives found{Colors.NC}")
    
    return results

def generate_corrected_config(df: pd.DataFrame, validation_results: Dict, version: str) -> str:
    """Generate corrected config file with suggested symbol replacements"""
    corrected_df = df.copy()
    corrections_made = []
    
    # Apply suggestions
    for suggestion in validation_results['suggestions']:
        original = suggestion['original']
        suggested = suggestion['suggested']
        
        # Replace symbol in dataframe
        mask = corrected_df['ticker'] == original
        corrected_df.loc[mask, 'ticker'] = suggested
        corrections_made.append(f"{original} → {suggested}")
    
    # Generate filename
    output_file = f"config/trade_config_version_{version}_corrected.csv"
    
    try:
        corrected_df.to_csv(output_file, index=False)
        
        print(f"{Colors.GREEN}✅ Generated corrected config: {output_file}{Colors.NC}")
        if corrections_made:
            print(f"{Colors.CYAN}📝 Corrections made:{Colors.NC}")
            for correction in corrections_made:
                print(f"   • {correction}")
        
        return output_file
        
    except Exception as e:
        print(f"{Colors.RED}❌ Error generating corrected config: {e}{Colors.NC}")
        return None

def print_detailed_report(validation_results: Dict, df: pd.DataFrame):
    """Print detailed validation report"""
    print(f"\n{Colors.BLUE}📊 DETAILED VALIDATION REPORT:{Colors.NC}")
    print(f"{'═' * 60}")
    
    valid_symbols = validation_results['valid_symbols']
    invalid_symbols = validation_results['invalid_symbols']
    suggestions = validation_results['suggestions']
    
    # Valid symbols section
    if valid_symbols:
        print(f"\n{Colors.GREEN}✅ VALID SYMBOLS ({len(valid_symbols)}):{Colors.NC}")
        for symbol_info in valid_symbols:
            symbol = symbol_info['symbol']
            exchange = symbol_info['exchange']
            currency = symbol_info['currency']
            
            # Find usage in config
            symbol_rows = df[df['ticker'] == symbol]
            accounts = symbol_rows['ibkr_account'].unique().tolist()
            quantities = symbol_rows['quantity'].tolist()
            
            print(f"   📈 {symbol} ({exchange}/{currency})")
            print(f"      Accounts: {', '.join(accounts)}")
            print(f"      Quantities: {quantities}")
    
    # Invalid symbols section
    if invalid_symbols:
        print(f"\n{Colors.RED}❌ INVALID SYMBOLS ({len(invalid_symbols)}):{Colors.NC}")
        for symbol_info in invalid_symbols:
            symbol = symbol_info['symbol']
            error = symbol_info['error']
            
            # Find usage in config
            symbol_rows = df[df['ticker'] == symbol]
            accounts = symbol_rows['ibkr_account'].unique().tolist()
            
            print(f"   ❌ {symbol}")
            print(f"      Error: {error}")
            print(f"      Used by accounts: {', '.join(accounts)}")
            
            # Show suggestions for this symbol
            symbol_suggestions = [s for s in suggestions if s['original'] == symbol]
            if symbol_suggestions:
                print(f"      {Colors.GREEN}💡 Suggestions:{Colors.NC}")
                for suggestion in symbol_suggestions:
                    suggested = suggestion['suggested']
                    exchange = suggestion['exchange']
                    print(f"         → {suggested} on {exchange}")
    
    # Summary statistics
    total_symbols = len(valid_symbols) + len(invalid_symbols)
    success_rate = (len(valid_symbols) / total_symbols * 100) if total_symbols > 0 else 0
    
    print(f"\n{Colors.BLUE}📈 SUMMARY STATISTICS:{Colors.NC}")
    print(f"   Total Symbols: {total_symbols}")
    print(f"   Valid: {len(valid_symbols)} ({success_rate:.1f}%)")
    print(f"   Invalid: {len(invalid_symbols)}")
    print(f"   Suggestions Available: {len(suggestions)}")

def main():
    """Main function for validate symbols tool"""
    parser = argparse.ArgumentParser(description="Validate AutoTrader Trade Config Symbols")
    parser.add_argument('--version', default='B', help='Trade config version (default: B)')
    parser.add_argument('--generate', action='store_true', help='Generate corrected config file')
    parser.add_argument('--detailed', action='store_true', help='Show detailed validation report')
    
    args = parser.parse_args()
    
    print_header()
    
    # Load trade config
    df = load_trade_config(args.version)
    if df is None:
        return
    
    print(f"{Colors.CYAN}🔌 Setting up IBKR connection...{Colors.NC}")
    
    if DEMO_MODE:
        print(f"{Colors.CYAN}🔄 Running in demo mode{Colors.NC}")
        ib = None
    else:
        try:
            ib = setup_ib_connection()
            if not ib or not ib.isConnected():
                print(f"{Colors.RED}❌ Failed to connect to IBKR{Colors.NC}")
                print(f"{Colors.YELLOW}💡 Make sure TWS or IB Gateway is running{Colors.NC}")
                return
            print(f"{Colors.GREEN}✅ Connected to IBKR{Colors.NC}")
        except Exception as e:
            print(f"{Colors.RED}❌ IBKR connection error: {e}{Colors.NC}")
            return
    
    print()
    
    # Validate symbols
    validation_results = validate_config_symbols(ib, df)
    
    # Show results
    if args.detailed:
        print_detailed_report(validation_results, df)
    else:
        # Show summary
        valid_count = len(validation_results['valid_symbols'])
        invalid_count = len(validation_results['invalid_symbols'])
        suggestion_count = len(validation_results['suggestions'])
        
        print(f"\n{Colors.BLUE}📊 VALIDATION SUMMARY:{Colors.NC}")
        print(f"   {Colors.GREEN}✅ Valid symbols: {valid_count}{Colors.NC}")
        print(f"   {Colors.RED}❌ Invalid symbols: {invalid_count}{Colors.NC}")
        print(f"   {Colors.CYAN}💡 Suggestions available: {suggestion_count}{Colors.NC}")
        
        if invalid_count > 0:
            print(f"\n{Colors.RED}❌ INVALID SYMBOLS:{Colors.NC}")
            for symbol_info in validation_results['invalid_symbols']:
                print(f"   • {symbol_info['symbol']} - {symbol_info['error']}")
        
        if suggestion_count > 0:
            print(f"\n{Colors.GREEN}💡 SUGGESTED CORRECTIONS:{Colors.NC}")
            for suggestion in validation_results['suggestions']:
                original = suggestion['original']
                suggested = suggestion['suggested']
                exchange = suggestion['exchange']
                print(f"   • {original} → {suggested} (on {exchange})")
    
    # Generate corrected config if requested
    if args.generate and validation_results['suggestions']:
        print()
        corrected_file = generate_corrected_config(df, validation_results, args.version)
        if corrected_file:
            print(f"\n{Colors.BLUE}💡 NEXT STEPS:{Colors.NC}")
            print(f"   1. Review the corrected config: {corrected_file}")
            print(f"   2. Replace your original config if corrections look good")
            print(f"   3. Test with: ./manage_trader.sh test-ibkr --config")
    
    elif validation_results['suggestions']:
        print(f"\n{Colors.BLUE}💡 NEXT STEPS:{Colors.NC}")
        print(f"   • Use --generate to create corrected config file")
        print(f"   • Use --detailed for comprehensive report")
        print(f"   • Test specific symbols: ./manage_trader.sh test-ibkr --symbols SYMBOL")
    
    if invalid_count == 0:
        print(f"\n{Colors.GREEN}🎉 All symbols in your config are valid!{Colors.NC}")
    
    print(f"\n{Colors.BLUE}💡 RECOMMENDATIONS:{Colors.NC}")
    print(f"   • Test the corrected symbols before live trading")
    print(f"   • Check IBKR permissions for crypto trading if needed")
    print(f"   • Use ./manage_trader.sh test-ibkr to verify symbol changes")

if __name__ == "__main__":
    main()