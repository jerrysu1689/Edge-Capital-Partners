


import csv
import re
from datetime import datetime
import pandas as pd
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def parse_input_csv(input_file):
    all_rows = []
    with open(input_file, 'r') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            all_rows.append(row)
    return all_rows


def identify_alert_pattern(description):
    """Enhanced to handle ECP nSkew patterns"""
    if "Saty Volume Stack Crossing" in description:
        return 'non_tradable'

    # CRITICAL: ECP nSkew pattern (fixes missing MSTR trades)
    if "ECP nSkew" in description:
        return 'ecp_nskew'

    if "ECP Futures" in description and ("buy" in description.lower() or "sell" in description.lower()):
        return 'ecp_futures'

    # Dynamic ECP pattern matching
    if "ECP" in description and ("buy" in description.lower() or "sell" in description.lower()):
        return 'ecp_pattern'

    if "order" in description and ("buy" in description.lower() or "sell" in description.lower()):
        if "for" in description and "filled on" in description:
            return 'standard_order'
        elif "filled on" in description and "New strategy position" in description:
            return 'filled_order'

    if "Exit Position" in description and "order" in description:
        return 'exit_position'

    if description.startswith("Edge Cap") and ("buy" in description.lower() or "sell" in description.lower()):
        return 'edge_cap'

    if (description.startswith("JS") or description.startswith("ECP")) and ("@" in description):
        return 'js_ecp_pattern'

    if "MTO Strategy" in description:
        return 'mto_strategy'

    if "SSL" in description and ("buy" in description.lower() or "sell" in description.lower()):
        return 'ssl_pattern'

    return 'unknown'


def extract_action_price_shares(description, ticker=None):
    """Enhanced with ECP nSkew fix for 'position is 0' issue"""
    pattern_type = identify_alert_pattern(description)
    action, price, shares = None, None, None
    strategy_name = extract_strategy_name(description)
    ticker_parsed = None

    if pattern_type == 'non_tradable':
        return action, price, shares, strategy_name, ticker_parsed

    if "buy" in description.lower():
        action = "Buy"
    elif "sell" in description.lower():
        action = "Sell"

    price_pattern = r'@\s*(\d+(?:\.\d+)?)'
    price_match = re.search(price_pattern, description)
    price = float(price_match.group(1)) if price_match else None

    # Enhanced shares extraction for ECP nSkew patterns
    if pattern_type in (
    'standard_order', 'exit_position', 'edge_cap', 'ecp_futures', 'ecp_pattern', 'ecp_nskew', 'mto_strategy',
    'ssl_pattern'):
        shares_pattern = r'for\s+(\d+(?:\.\d+)?)'
        shares_match = re.search(shares_pattern, description)
        shares = float(shares_match.group(1)) if shares_match else None

    elif pattern_type == 'filled_order':
        position_pattern = r'New strategy position is\s+(\d+(?:\.\d+)?)'
        position_match = re.search(position_pattern, description)

        if position_match:
            position = float(position_match.group(1))
            # CRITICAL FIX: For sells with position=0, extract from "for" clause
            if action == "Sell" and position == 0:
                shares_pattern = r'for\s+(\d+(?:\.\d+)?)'
                shares_match = re.search(shares_pattern, description)
                shares = float(shares_match.group(1)) if shares_match else None
            else:
                shares = position

    ticker_pattern = r'filled on\s+([A-Z0-9!.]+)'
    ticker_match = re.search(ticker_pattern, description)
    if ticker_match:
        ticker_parsed = ticker_match.group(1).replace('!', '')
    elif ticker:
        ticker_parts = ticker.split(':')
        if len(ticker_parts) > 1:
            ticker_parsed = ticker_parts[-1].split(',')[0].strip()
        else:
            ticker_parsed = ticker.split(',')[0].strip()

    if shares and shares.is_integer():
        shares = int(shares)

    return action, price, shares, strategy_name, ticker_parsed


def extract_strategy_name(description):
    """Enhanced for ECP nSkew and other patterns"""
    if "ECP nSkew" in description:
        ecp_match = re.match(r'^([^:]+)', description)
        if ecp_match:
            return ecp_match.group(1).strip()

    if "ECP Futures" in description:
        ecp_match = re.match(r'^(\w+)\s+(\w+)\s+(ECP\s+Futures)', description)
        if ecp_match:
            timeframe, ticker, strategy = ecp_match.groups()
            return f"{timeframe} {ticker} {strategy}"

    if "ECP" in description:
        ecp_match = re.match(r'^([^:]+)', description)
        if ecp_match:
            return ecp_match.group(1).strip()

    if "MTO Strategy" in description:
        mto_match = re.match(r'^([^:]+)', description)
        if mto_match:
            return mto_match.group(1).strip()

    if "SSL" in description:
        ssl_match = re.match(r'^([^:]+)', description)
        if ssl_match:
            return ssl_match.group(1).strip()

    strategy_match = re.match(r'^([^(:]+)(?:\s*\([^)]*\))?:', description)
    if strategy_match:
        return strategy_match.group(1).strip()

    if description.startswith("Edge Cap"):
        return "Edge Cap"
    elif description.startswith("Saty Volume"):
        return "Saty Volume Stack"

    parts = re.split(r'[:(,]', description, 1)
    if parts:
        potential_strategy = parts[0].strip()
        if len(potential_strategy) > 2:
            return potential_strategy

    return "Unknown"


def extract_timeframe_from_ticker(ticker):
    if not ticker:
        return None
    timeframe_match = re.search(r',\s*(\w+)$', ticker)
    if timeframe_match:
        return timeframe_match.group(1)
    return None


def get_timestamp(iso_str):
    try:
        return datetime.strptime(iso_str, '%Y-%m-%dT%H:%M:%SZ')
    except (ValueError, TypeError):
        return None


def extract_time_from_description(description):
    time_pattern = r'at\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)'
    time_match = re.search(time_pattern, description)
    if time_match:
        time_str = time_match.group(1)
        try:
            return datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            pass
    return None


def build_alert_name_mapping(raw_rows):
    alert_mapping = {}
    for row in raw_rows:
        alert_id = row.get('Alert ID')
        alert_name = row.get('Name', '')
        time_str = row.get('Time', '')

        if not alert_id:
            continue

        timestamp = None
        if time_str:
            timestamp = get_timestamp(time_str)
        if not timestamp:
            timestamp = extract_time_from_description(row.get('Description', ''))
        if not timestamp:
            timestamp = datetime.min

        if alert_id not in alert_mapping or timestamp > alert_mapping[alert_id]['timestamp']:
            alert_mapping[alert_id] = {'name': alert_name, 'timestamp': timestamp}

    return alert_mapping




def build_trades(raw_rows):
    trades = []
    failed_rows = []
    alert_name_mapping = build_alert_name_mapping(raw_rows)

    for row in raw_rows:
        description = row.get('Description', '')

        # Get alert ID first
        alert_id = row.get('Alert ID')

        # CRITICAL FIX: Use ACTUAL name from this row for Strategy
        # Use STANDARDIZED name from mapping for Alert Name (grouping/reporting)
        actual_row_name = row.get('Name', '')  # What the strategy was called at THIS time
        standardized_alert_name = ""  # What the strategy is called NOW (most recent)

        if alert_id and alert_id in alert_name_mapping:
            standardized_alert_name = alert_name_mapping[alert_id]['name']

        # Strategy should reflect the actual name at the time of this trade
        strategy_name = actual_row_name if actual_row_name else standardized_alert_name

        # If still no strategy name, fall back to extraction logic
        if not strategy_name:
            if 'ECP' in description:
                _, _, _, strategy_name, _ = extract_action_price_shares(description, row.get('Ticker', ''))
            else:
                _, _, _, strategy_name, _ = extract_action_price_shares(description, row.get('Ticker', ''))

        action, price, shares, _, ticker_parsed = extract_action_price_shares(description, row.get('Ticker', ''))

        if action and price:
            if not ticker_parsed and 'Ticker' in row:
                ticker_parts = row['Ticker'].split(':')
                if len(ticker_parts) > 1:
                    ticker_parsed = ticker_parts[-1].split(',')[0].strip()
                else:
                    ticker_parsed = row['Ticker'].split(',')[0].strip()

            timestamp = None
            if 'Time' in row and row['Time']:
                timestamp = get_timestamp(row['Time'])
            if not timestamp:
                timestamp = extract_time_from_description(row.get('Description', ''))
            if not timestamp:
                timestamp = datetime.now()

            trade = {
                'Alert ID': alert_id,
                'DateTime': timestamp,
                'Date': timestamp.strftime('%Y-%m-%d'),
                'Ticker': ticker_parsed,
                'Action': action,
                'Price': price,
                'Strategy': strategy_name,  # Uses actual name from THIS row
                'Alert Name': standardized_alert_name,  # Uses most recent standardized name
                'Actual Shares': shares
            }

            timeframe = extract_timeframe_from_ticker(row.get('Ticker', ''))
            if timeframe:
                trade['Timeframe'] = timeframe

            trades.append(trade)
        else:
            failed_rows.append(row.get('Description', 'Unknown description'))

    if failed_rows:
        print(f"Failed to extract trade info from {len(failed_rows)} alerts.")

    trades = [t for t in trades if 'Ticker' in t and t['Ticker']]
    trades.sort(key=lambda x: (x.get('Alert ID', ''), x.get('Ticker', ''), x.get('DateTime', datetime.min)))
    return trades




def match_buys_and_sells_state_based(trades):
    """
    State-based matching: Track position state chronologically
    - All shares treated as 1
    - Match on Alert ID + Ticker + Timestamp
    - IGNORES any SELLs that occur before the first BUY
    - IGNORES any SELLs when position is flat (invalid/duplicate alerts)
    - Complete order = BUY first, then SELL (NO SHORTING)
    """
    closed_trades = []
    open_positions = []

    # Group by Alert ID + Ticker
    trade_groups = {}
    for trade in trades:
        alert_id = trade.get('Alert ID', 'unknown')
        ticker = trade.get('Ticker', '')

        key = (alert_id, ticker)
        if key not in trade_groups:
            trade_groups[key] = []
        trade_groups[key].append(trade)

    print(f"\nProcessing {len(trade_groups)} unique Alert ID + Ticker combinations...")

    for (alert_id, ticker), group_trades in trade_groups.items():
        # Sort by datetime (including seconds) - critical for accuracy
        group_trades.sort(key=lambda x: x.get('DateTime', datetime.min))

        # Find first BUY and ignore any SELLs before it
        first_buy_index = None
        for idx, trade in enumerate(group_trades):
            if trade['Action'] == 'Buy':
                first_buy_index = idx
                break

        # If no BUY found at all, skip this entire group
        if first_buy_index is None:
            print(f"Warning: Alert {alert_id}, Ticker {ticker} has no BUY orders. Skipping.")
            continue

        # Start processing from the first BUY onwards (ignore earlier SELLs)
        if first_buy_index > 0:
            skipped_sells = first_buy_index
            print(f"Alert {alert_id}, Ticker {ticker}: Skipped {skipped_sells} SELL order(s) before first BUY")

        group_trades = group_trades[first_buy_index:]

        # State machine variables
        position = 0  # 0 = flat, 1 = long (NO SHORTING)
        entry_trade = None

        for trade in group_trades:
            action = trade['Action']

            # Treat all trades as 1 share (ignore actual shares)
            shares = 1
            price = trade['Price']

            if action == 'Buy':
                if position == 0:
                    # Opening long position
                    position = 1
                    entry_trade = trade

                elif position == 1:
                    # INVALID BUY - already have open position
                    # This is likely a duplicate/error from TradingView
                    print(f"Warning: Alert {alert_id}, Ticker {ticker}: Ignoring invalid BUY at {trade['Date']} (position already open)")
                    continue

            elif action == 'Sell':
                if position == 0:
                    # INVALID SELL - no open position to close
                    # This is likely a duplicate/error from TradingView
                    print(f"Warning: Alert {alert_id}, Ticker {ticker}: Ignoring invalid SELL at {trade['Date']} (no open position)")
                    continue

                elif position == 1:
                    # Closing long position
                    buy_date_str = entry_trade['Date']
                    sell_date_str = trade['Date']
                    buy_price = entry_trade['Price']
                    sell_price = price

                    try:
                        d1 = datetime.strptime(buy_date_str, '%Y-%m-%d')
                        d2 = datetime.strptime(sell_date_str, '%Y-%m-%d')
                        days_in_market = (d2 - d1).days
                    except ValueError:
                        days_in_market = 0

                    # Long P&L: buy low, sell high
                    cost = buy_price * shares
                    pnl = (sell_price - buy_price) * shares
                    ret_pct = (pnl / cost) * 100 if cost != 0 else 0

                    result = {
                        'Alert ID': alert_id,
                        'Trading Date': buy_date_str,
                        'Closing Date': sell_date_str,
                        'Ticker': ticker,
                        'Open': round(buy_price, 2),
                        'Closing': round(sell_price, 2),
                        'Shares': shares,
                        'Cost': round(cost, 2),
                        'PnL': round(pnl, 2),
                        'Return(%)': round(ret_pct, 2),
                        'Average Day in the Market': days_in_market,
                        'Outcome': 'Win' if ret_pct > 0 else 'Loss',
                        'Status': 'Closed'
                    }

                    for field in ['Strategy', 'Timeframe', 'Alert Name']:
                        if field in entry_trade:
                            result[field] = entry_trade[field]

                    closed_trades.append(result)
                    position = 0
                    entry_trade = None

        # Any remaining open position
        if position != 0 and entry_trade is not None:
            open_position = {
                'Alert ID': alert_id,
                'Entry Date': entry_trade['Date'],
                'Ticker': ticker,
                'Entry Price': round(entry_trade['Price'], 2),
                'Shares': 1,
                'Cost Basis': round(entry_trade['Price'], 2),
                'Days Held': (datetime.now() - entry_trade['DateTime']).days,
                'Status': 'Open',
                'Position Type': 'Long',
                'Strategy': entry_trade.get('Strategy', ''),
                'Timeframe': entry_trade.get('Timeframe', ''),
                'Alert Name': entry_trade.get('Alert Name', '')
            }
            open_positions.append(open_position)

    print(f"\nState-Based Matching Summary:")
    print(f"  Closed trades: {len(closed_trades)}")
    print(f"  Open positions: {len(open_positions)}")

    return closed_trades, open_positions

def calculate_compounded_principle(df):
    """
    Calculate compounded principle starting at $100,000 for each Alert ID
    Formula: Previous Value × (1 + Return% / 100)
    """
    df['Principle'] = 0.0
    
    # Group by Alert ID
    for alert_id in df['Alert ID'].unique():
        mask = df['Alert ID'] == alert_id
        alert_trades = df[mask].copy()
        
        # Sort by Trading Date to ensure chronological order
        alert_trades = alert_trades.sort_values('Trading Date')
        
        # Calculate compounded principle
        principle_values = []
        current_principle = 100000.0  # Start with $100,000
        
        for idx, row in alert_trades.iterrows():
            return_pct = row['Return(%)']
            principle_values.append(current_principle)
            # Calculate next principle: current × (1 + return%)
            current_principle = current_principle * (1 + return_pct / 100)
        
        # Assign back to dataframe
        df.loc[alert_trades.index, 'Principle'] = principle_values
    
    return df


def build_final_dataframe(closed_trades):
    standard_columns = [
        'Alert ID', 'Alert Name', 'Trading Date', 'Closing Date', 'Ticker',
        'Open', 'Closing', 'Shares', 'Cost', 'PnL', 'Return(%)',
        'Average Day in the Market', 'Outcome', 'Status', 'Strategy', 'Timeframe',
        'Actual Buy Shares', 'Actual Sell Shares', 'Principle'  # Added Principle
    ]

    df = pd.DataFrame(closed_trades)

    for col in standard_columns:
        if col not in df.columns:
            df[col] = None

    # Calculate Compounded Principle for each Alert ID
    df = calculate_compounded_principle(df)

    available_standard_cols = [col for col in standard_columns if col in df.columns]
    additional_cols = [col for col in df.columns if col not in standard_columns]
    df = df[available_standard_cols + additional_cols]

    return df

# def build_final_dataframe(closed_trades):
#     standard_columns = [
#         'Alert ID', 'Alert Name', 'Trading Date', 'Closing Date', 'Ticker',
#         'Open', 'Closing', 'Shares', 'Cost', 'PnL', 'Return(%)',
#         'Average Day in the Market', 'Outcome', 'Status', 'Strategy', 'Timeframe',
#         'Actual Buy Shares', 'Actual Sell Shares'
#     ]

#     df = pd.DataFrame(closed_trades)

#     for col in standard_columns:
#         if col not in df.columns:
#             df[col] = None

#     available_standard_cols = [col for col in standard_columns if col in df.columns]
#     additional_cols = [col for col in df.columns if col not in standard_columns]
#     df = df[available_standard_cols + additional_cols]

#     return df


def process_alerts_to_dataframe(input_file):
    """Returns 2 DataFrames: closed trades and open positions"""
    raw_rows = parse_input_csv(input_file)
    all_trades = build_trades(raw_rows)
    closed_trades, open_positions = match_buys_and_sells_state_based(all_trades)

    df_closed = build_final_dataframe(closed_trades)
    df_open = pd.DataFrame(open_positions) if open_positions else pd.DataFrame()

    return df_closed, df_open


def create_advanced_pivot_tables(df):
    """Pivot tables use CLOSED trades only"""
    import pandas as pd
    import numpy as np

    print(f"Creating pivot table for {len(df)} closed trades")

    if 'Ticker' not in df.columns:
        print("ERROR: No Ticker column found!")
        return pd.DataFrame()

    pivot_data = []

    for ticker_symbol in sorted(df['Ticker'].unique()):
        ticker_data = df[df['Ticker'] == ticker_symbol]
        win_data = ticker_data[ticker_data['Outcome'] == 'Win']
        loss_data = ticker_data[ticker_data['Outcome'] == 'Loss']

        win_count = len(win_data)
        win_pnl = win_data['PnL'].sum() if win_count > 0 else 0
        win_return = win_data['Return(%)'].mean() if win_count > 0 else 0
        win_days = win_data['Average Day in the Market'].mean() if win_count > 0 else 0

        win_metrics = {
            'Ticker': ticker_symbol,
            'Row Labels': 'Win',
            'Count of Outcome': win_count,
            'Sum of PnL': win_pnl,
            'Average of Return(%)': win_return,
            'Average of Average Day in the Market': win_days
        }

        loss_count = len(loss_data)
        loss_pnl = loss_data['PnL'].sum() if loss_count > 0 else 0
        loss_return = loss_data['Return(%)'].mean() if loss_count > 0 else 0
        loss_days = loss_data['Average Day in the Market'].mean() if loss_count > 0 else 0

        loss_metrics = {
            'Ticker': ticker_symbol,
            'Row Labels': 'Loss',
            'Count of Outcome': loss_count,
            'Sum of PnL': loss_pnl,
            'Average of Return(%)': loss_return,
            'Average of Average Day in the Market': loss_days
        }

        total_count = len(ticker_data)
        total_pnl = ticker_data['PnL'].sum()
        avg_return = ticker_data['Return(%)'].mean()
        avg_days = ticker_data['Average Day in the Market'].mean()
        win_rate = (win_count / total_count) * 100 if total_count > 0 else 0

        avg_win = win_data['PnL'].mean() if win_count > 0 else 0
        avg_loss = abs(loss_data['PnL'].mean()) if loss_count > 0 else 1
        rr_dollar = avg_win / avg_loss if avg_loss != 0 else 0

        avg_win_pct = win_data['Return(%)'].mean() if win_count > 0 else 0
        avg_loss_pct = abs(loss_data['Return(%)'].mean()) if loss_count > 0 else 1
        rr_percent = avg_win_pct / avg_loss_pct if avg_loss_pct != 0 else 0

        total_metrics = {
            'Ticker': ticker_symbol,
            'Row Labels': 'Total',
            'Count of Outcome': '',
            'Sum of PnL': '',
            'Average of Return(%)': '',
            'Average of Average Day in the Market': '',
            'Total Count of Outcome': total_count,
            'Total Sum of PnL': total_pnl,
            'Total Average of Return(%)': avg_return,
            'Total Average of Average Day in the Market': avg_days,
            'Win Rate (>0.6=green)': win_rate,
            'R:R (>1.2 = green) %': rr_percent,
            'R:R (>1.2 = green) $': rr_dollar,
            'Top 40 by PnL': total_pnl,
            'Top 40 by %': avg_return
        }

        pivot_data.extend([win_metrics, loss_metrics, total_metrics])

    pivot_df = pd.DataFrame(pivot_data)

    column_order = [
        'Ticker', 'Row Labels', 'Count of Outcome', 'Sum of PnL',
        'Average of Return(%)', 'Average of Average Day in the Market',
        'Total Count of Outcome', 'Total Sum of PnL', 'Total Average of Return(%)',
        'Total Average of Average Day in the Market', 'Win Rate (>0.6=green)',
        'R:R (>1.2 = green) %', 'R:R (>1.2 = green) $', 'Top 40 by PnL', 'Top 40 by %'
    ]

    for col in column_order:
        if col not in pivot_df.columns:
            pivot_df[col] = ''

    pivot_df = pivot_df[column_order]
    pivot_df = pivot_df.fillna('')

    numeric_columns = ['Sum of PnL', 'Average of Return(%)', 'Average of Average Day in the Market',
                       'Total Sum of PnL', 'Total Average of Return(%)', 'Total Average of Average Day in the Market',
                       'Win Rate (>0.6=green)', 'R:R (>1.2 = green) %', 'R:R (>1.2 = green) $',
                       'Top 40 by PnL', 'Top 40 by %']

    for col in numeric_columns:
        if col in pivot_df.columns:
            mask = (pivot_df[col] != '') & (pivot_df[col].notna())
            pivot_df.loc[mask, col] = pd.to_numeric(pivot_df.loc[mask, col], errors='coerce').round(2)

    return pivot_df


def create_formatted_excel_pivot(df, writer, sheet_name='Pivot'):
    pivot_df = create_advanced_pivot_tables(df)
    pivot_df.to_excel(writer, sheet_name=sheet_name, index=False)

    workbook = writer.book
    worksheet = writer.sheets[sheet_name]

    win_rate_col = None
    rr_pct_col = None
    rr_dollar_col = None

    for idx, col in enumerate(pivot_df.columns):
        if 'Win Rate' in col:
            win_rate_col = idx
        elif 'R:R (>1.2 = green) %' in col:
            rr_pct_col = idx
        elif 'R:R (>1.2 = green) $' in col:
            rr_dollar_col = idx

    green_format = workbook.add_format({'bg_color': '#90EE90'})

    if win_rate_col is not None:
        col_letter = chr(65 + win_rate_col)
        worksheet.conditional_format(f'{col_letter}2:{col_letter}{len(pivot_df) + 1}', {
            'type': 'cell', 'criteria': '>=', 'value': 60, 'format': green_format
        })

    if rr_pct_col is not None:
        col_letter = chr(65 + rr_pct_col)
        worksheet.conditional_format(f'{col_letter}2:{col_letter}{len(pivot_df) + 1}', {
            'type': 'cell', 'criteria': '>=', 'value': 1.2, 'format': green_format
        })

    if rr_dollar_col is not None:
        col_letter = chr(65 + rr_dollar_col)
        worksheet.conditional_format(f'{col_letter}2:{col_letter}{len(pivot_df) + 1}', {
            'type': 'cell', 'criteria': '>=', 'value': 1.2, 'format': green_format
        })

    return pivot_df




# def create_alert_id_performance(df_closed, df_open):
#     """Enhanced with compounded return calculations"""
#     if 'Alert ID' not in df_closed.columns or df_closed['Alert ID'].isna().all():
#         return pd.DataFrame()

#     alert_groups = df_closed.groupby(
#         ['Alert ID', 'Alert Name']) if 'Alert Name' in df_closed.columns else df_closed.groupby(['Alert ID'])
#     alert_performance_data = []

#     for group_key, group_data in alert_groups:
#         if isinstance(group_key, tuple):
#             alert_id, alert_name = group_key
#         else:
#             alert_id = group_key
#             alert_name = ""

#         # Count open positions for this Alert ID
#         open_count = len(df_open[df_open['Alert ID'] == alert_id]) if len(df_open) > 0 else 0

#         group_data_sorted = group_data.sort_values('Trading Date')
#         first_trade = group_data_sorted.iloc[0]
#         last_trade = group_data_sorted.iloc[-1]

#         total_pnl = group_data['PnL'].sum()
#         avg_return = group_data['Return(%)'].mean()
#         total_cost = group_data['Cost'].sum()
#         win_count = len(group_data[group_data['Outcome'] == 'Win'])
#         total_trades = len(group_data)
#         win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
#         avg_days_in_market = group_data['Average Day in the Market'].mean()

#         first_trade_cost = first_trade['Cost']
#         if first_trade_cost > 0:
#             total_return = (total_pnl / first_trade_cost) * 100
#         else:
#             total_return = 0

#         first_open_price = first_trade['Open']
#         last_close_price = last_trade['Closing']

#         if first_open_price > 0:
#             buy_hold_return = ((last_close_price / first_open_price) - 1) * 100
#         else:
#             buy_hold_return = 0

#         difference = total_return - buy_hold_return

#         # NEW: Calculate Compounded Return
#         # Get the final principle value (after last trade)
#         last_principle = last_trade['Principle']
#         # Calculate the return after applying the last trade's return
#         final_principle = last_principle * (1 + last_trade['Return(%)'] / 100)
#         compounded_return_pct = ((final_principle - 100000) / 100000) * 100
        
#         # NEW: Calculate differences
#         difference_pct = compounded_return_pct - buy_hold_return
#         difference_to_compounded = buy_hold_return - compounded_return_pct

#         win_data = group_data[group_data['Outcome'] == 'Win']
#         loss_data = group_data[group_data['Outcome'] == 'Loss']

#         avg_win_amount = win_data['PnL'].mean() if len(win_data) > 0 else 0
#         avg_loss_amount = loss_data['PnL'].mean() if len(loss_data) > 0 else 0
#         avg_win_percent = win_data['Return(%)'].mean() if len(win_data) > 0 else 0
#         avg_loss_percent = loss_data['Return(%)'].mean() if len(loss_data) > 0 else 0

#         rr_dollar = abs(avg_win_amount / avg_loss_amount) if avg_loss_amount != 0 else 0
#         rr_percent = abs(avg_win_percent / avg_loss_percent) if avg_loss_percent != 0 else 0

#         best_trade_pnl = group_data['PnL'].max()
#         worst_trade_pnl = group_data['PnL'].min()
#         best_trade_percent = group_data['Return(%)'].max()
#         worst_trade_percent = group_data['Return(%)'].min()

#         alert_performance_data.append({
#             'Alert ID': alert_id,
#             'Alert Name': alert_name,
#             'Closed Trades': total_trades,
#             'Open Positions': open_count,
#             'Total PnL': round(total_pnl, 2),
#             'Average Return(%)': round(avg_return, 2),
#             'Total Return (%)': round(total_return, 2),
#             'Compounded Return (%)': round(compounded_return_pct, 2),  # NEW
#             'Buy & Hold Return (%)': round(buy_hold_return, 2),
#             'Difference (%)': round(difference_pct, 2),  # NEW: Compounded - Buy&Hold
#             'Difference to Compounded': round(difference_to_compounded, 2),  # NEW
#             'Total Cost': round(total_cost, 2),
#             'Win Rate (%)': round(win_rate, 2),
#             'Win Count': win_count,
#             'Loss Count': total_trades - win_count,
#             'Average Days in Market': round(avg_days_in_market, 2),
#             'Average Win ($)': round(avg_win_amount, 2),
#             'Average Loss ($)': round(avg_loss_amount, 2),
#             'Average Win (%)': round(avg_win_percent, 2),
#             'Average Loss (%)': round(avg_loss_percent, 2),
#             'Risk:Reward ($)': round(rr_dollar, 2),
#             'Risk:Reward (%)': round(rr_percent, 2),
#             'Best Trade ($)': round(best_trade_pnl, 2),
#             'Worst Trade ($)': round(worst_trade_pnl, 2),
#             'Best Trade (%)': round(best_trade_percent, 2),
#             'Worst Trade (%)': round(worst_trade_percent, 2)
#         })

#     alert_performance_df = pd.DataFrame(alert_performance_data)
#     alert_performance_df = alert_performance_df.sort_values('Total PnL', ascending=False)

#     print(f"Alert ID Performance created with {len(alert_performance_df)} alerts")
#     if len(df_open) > 0:
#         print(f"Tracking {alert_performance_df['Open Positions'].sum()} total open positions")

#     return alert_performance_df

def create_alert_id_performance(df_closed, df_open):
    """Enhanced with compounded return calculations and new metrics"""
    if 'Alert ID' not in df_closed.columns or df_closed['Alert ID'].isna().all():
        return pd.DataFrame()

    alert_groups = df_closed.groupby(
        ['Alert ID', 'Alert Name']) if 'Alert Name' in df_closed.columns else df_closed.groupby(['Alert ID'])
    alert_performance_data = []

    for group_key, group_data in alert_groups:
        if isinstance(group_key, tuple):
            alert_id, alert_name = group_key
        else:
            alert_id = group_key
            alert_name = ""

        # Count open positions for this Alert ID
        open_count = len(df_open[df_open['Alert ID'] == alert_id]) if len(df_open) > 0 else 0

        group_data_sorted = group_data.sort_values('Trading Date')
        first_trade = group_data_sorted.iloc[0]
        last_trade = group_data_sorted.iloc[-1]

        total_pnl = group_data['PnL'].sum()
        avg_return = group_data['Return(%)'].mean()
        total_cost = group_data['Cost'].sum()
        win_count = len(group_data[group_data['Outcome'] == 'Win'])
        total_trades = len(group_data)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
        avg_days_in_market = group_data['Average Day in the Market'].mean()

        # UPDATED: Total Return = Sum of all Return(%)
        total_return = group_data['Return(%)'].sum()

        first_open_price = first_trade['Open']
        last_close_price = last_trade['Closing']

        if first_open_price > 0:
            buy_hold_return = ((last_close_price / first_open_price) - 1) * 100
        else:
            buy_hold_return = 0

        # Calculate Compounded Return
        last_principle = last_trade['Principle']
        final_principle = last_principle * (1 + last_trade['Return(%)'] / 100)
        compounded_return_pct = ((final_principle - 100000) / 100000) * 100
        
        # RENAMED: Total - Buy & Hold (%)
        total_minus_buyhold = total_return - buy_hold_return
        
        # RENAMED: Compounded - Buy & Hold (%)
        compounded_minus_buyhold = compounded_return_pct - buy_hold_return

        # NEW CALCULATIONS
        # 3. Total Time in Market
        total_time_in_market = avg_days_in_market * total_trades

        # 4. Buy & Hold # of Days (calendar days between first and last trade)
        try:
            first_date = datetime.strptime(first_trade['Trading Date'], '%Y-%m-%d')
            last_date = datetime.strptime(last_trade['Closing Date'], '%Y-%m-%d')
            buyhold_days = (last_date - first_date).days
        except:
            buyhold_days = 0

        # 5. Time Utilization Ratio
        time_utilization = (total_time_in_market / buyhold_days) if buyhold_days > 0 else 0

        # 6. Beta Comparison
        # Compounded - Buy & Hold (%) - [Buy & Hold Return (%) × Time Utilization]
        adjusted_buyhold = buy_hold_return * time_utilization
        beta_comparison = compounded_minus_buyhold - adjusted_buyhold

        win_data = group_data[group_data['Outcome'] == 'Win']
        loss_data = group_data[group_data['Outcome'] == 'Loss']

        avg_win_amount = win_data['PnL'].mean() if len(win_data) > 0 else 0
        avg_loss_amount = loss_data['PnL'].mean() if len(loss_data) > 0 else 0
        avg_win_percent = win_data['Return(%)'].mean() if len(win_data) > 0 else 0
        avg_loss_percent = loss_data['Return(%)'].mean() if len(loss_data) > 0 else 0

        rr_dollar = abs(avg_win_amount / avg_loss_amount) if avg_loss_amount != 0 else 0
        rr_percent = abs(avg_win_percent / avg_loss_percent) if avg_loss_percent != 0 else 0

        best_trade_pnl = group_data['PnL'].max()
        worst_trade_pnl = group_data['PnL'].min()
        best_trade_percent = group_data['Return(%)'].max()
        worst_trade_percent = group_data['Return(%)'].min()

        alert_performance_data.append({
            'Alert ID': alert_id,
            'Alert Name': alert_name,
            'Closed Trades': total_trades,
            'Open Positions': open_count,
            'Total PnL': round(total_pnl, 2),
            'Average Return(%)': round(avg_return, 2),
            'Total Return (%)': round(total_return, 2),  # UPDATED calculation
            'Compounded Return (%)': round(compounded_return_pct, 2),
            'Buy & Hold Return (%)': round(buy_hold_return, 2),
            'Total - Buy & Hold (%)': round(total_minus_buyhold, 2),  # RENAMED
            'Compounded - Buy & Hold (%)': round(compounded_minus_buyhold, 2),  # RENAMED
            'Total Cost': round(total_cost, 2),
            'Win Rate (%)': round(win_rate, 2),
            'Win Count': win_count,
            'Loss Count': total_trades - win_count,
            'Average Days in Market': round(avg_days_in_market, 2),
            'Total Time in Market': round(total_time_in_market, 2),  # NEW
            'Buy & Hold # of Days': buyhold_days,  # NEW
            'Time Utilization Ratio': round(time_utilization, 4),  # NEW (4 decimals for precision)
            'Beta Comparison': round(beta_comparison, 2),  # NEW
            'Average Win ($)': round(avg_win_amount, 2),
            'Average Loss ($)': round(avg_loss_amount, 2),
            'Average Win (%)': round(avg_win_percent, 2),
            'Average Loss (%)': round(avg_loss_percent, 2),
            'Risk:Reward ($)': round(rr_dollar, 2),
            'Risk:Reward (%)': round(rr_percent, 2),
            'Best Trade ($)': round(best_trade_pnl, 2),
            'Worst Trade ($)': round(worst_trade_pnl, 2),
            'Best Trade (%)': round(best_trade_percent, 2),
            'Worst Trade (%)': round(worst_trade_percent, 2)
        })

    alert_performance_df = pd.DataFrame(alert_performance_data)
    alert_performance_df = alert_performance_df.sort_values('Total PnL', ascending=False)

    print(f"Alert ID Performance created with {len(alert_performance_df)} alerts")
    if len(df_open) > 0:
        print(f"Tracking {alert_performance_df['Open Positions'].sum()} total open positions")

    return alert_performance_df


def create_pivot_tables(df_closed, df_open):
    """Takes both closed and open DataFrames"""
    pivot_tables = {}

    pivot_tables['advanced_pivot'] = create_advanced_pivot_tables(df_closed)
    pivot_tables['alert_id_performance'] = create_alert_id_performance(df_closed, df_open)

    if 'Strategy' in df_closed.columns and not df_closed['Strategy'].isna().all():
        strategy_pivot = pd.pivot_table(df_closed, index=['Strategy'],
                                        values=['PnL', 'Return(%)', 'Cost'],
                                        aggfunc={'PnL': 'sum', 'Return(%)': 'mean', 'Cost': 'sum'})
        strategy_pivot['Win Rate'] = df_closed.groupby('Strategy')['Outcome'].apply(
            lambda x: (x == 'Win').mean() * 100)
        strategy_pivot['Trade Count'] = df_closed.groupby('Strategy').size()
        pivot_tables['strategy_performance'] = strategy_pivot

    ticker_pivot = pd.pivot_table(df_closed, index=['Ticker'],
                                   values=['PnL', 'Return(%)', 'Cost'],
                                   aggfunc={'PnL': 'sum', 'Return(%)': 'mean', 'Cost': 'sum'})
    ticker_pivot['Win Rate'] = df_closed.groupby('Ticker')['Outcome'].apply(
        lambda x: (x == 'Win').mean() * 100)
    ticker_pivot['Trade Count'] = df_closed.groupby('Ticker').size()
    pivot_tables['ticker_performance'] = ticker_pivot

    if 'Timeframe' in df_closed.columns and df_closed['Timeframe'].notna().any():
        timeframe_pivot = pd.pivot_table(df_closed, index=['Timeframe'],
                                         values=['PnL', 'Return(%)', 'Cost'],
                                         aggfunc={'PnL': 'sum', 'Return(%)': 'mean', 'Cost': 'sum'})
        timeframe_pivot['Win Rate'] = df_closed.groupby('Timeframe')['Outcome'].apply(
            lambda x: (x == 'Win').mean() * 100)
        timeframe_pivot['Trade Count'] = df_closed.groupby('Timeframe').size()
        pivot_tables['timeframe_performance'] = timeframe_pivot

    summary = {
        'Total PnL': df_closed['PnL'].sum(),
        'Average Return(%)': df_closed['Return(%)'].mean(),
        'Total Cost': df_closed['Cost'].sum(),
        'Overall Win Rate': (df_closed['Outcome'] == 'Win').mean() * 100,
        'Total Trades': len(df_closed)
    }
    pivot_tables['overall_summary'] = pd.DataFrame([summary])

    return pivot_tables


def get_date_filters():
    from datetime import datetime
    print("\n" + "=" * 50)
    print("DATE FILTERING OPTIONS")
    print("=" * 50)
    print("Choose an option:")
    print("1. All data (no filtering)")
    print("2. Filter by date range")

    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        if choice == "1":
            print("Processing all data...")
            return None, None
        elif choice == "2":
            print("\nEnter date range (format: YYYY-MM-DD)")
            while True:
                start_input = input("Start date (press Enter for no start limit): ").strip()
                if not start_input:
                    start_date = None
                    break
                try:
                    start_date = datetime.strptime(start_input, '%Y-%m-%d').date()
                    break
                except ValueError:
                    print("Invalid date format. Please use YYYY-MM-DD")

            while True:
                end_input = input("End date (press Enter for no end limit): ").strip()
                if not end_input:
                    end_date = None
                    break
                try:
                    end_date = datetime.strptime(end_input, '%Y-%m-%d').date()
                    break
                except ValueError:
                    print("Invalid date format. Please use YYYY-MM-DD")

            if start_date and end_date and start_date > end_date:
                print("Error: Start date cannot be after end date. Please try again.")
                continue

            start_str = start_date.strftime('%Y-%m-%d') if start_date else "Beginning"
            end_str = end_date.strftime('%Y-%m-%d') if end_date else "End"
            print(f"Selected range: {start_str} to {end_str}")
            return start_date, end_date
        else:
            print("Invalid choice. Please enter 1 or 2.")


def filter_dataframe_by_date(df, start_date=None, end_date=None):
    if start_date is None and end_date is None:
        print("No date filtering applied.")
        return df

    df_filtered = df.copy()
    df_filtered['Trading Date'] = pd.to_datetime(df_filtered['Trading Date'])
    original_count = len(df_filtered)

    if start_date:
        df_filtered = df_filtered[df_filtered['Trading Date'].dt.date >= start_date]
    if end_date:
        df_filtered = df_filtered[df_filtered['Trading Date'].dt.date <= end_date]

    df_filtered['Trading Date'] = df_filtered['Trading Date'].dt.strftime('%Y-%m-%d')
    filtered_count = len(df_filtered)
    print(f"Date filtering applied: {original_count} → {filtered_count} trades")

    if filtered_count == 0:
        print("Warning: No trades found in the specified date range!")

    return df_filtered


if __name__ == "__main__":
    pr_root = get_project_root()
    input_file = pr_root / 'clean_up_alert-main' / 'inputs' / 'consolidated_alerts_LTD_20251005.csv'
    # input_file = "/workspaces/Edge-Capital-Partners/clean_up_alert-main/inputs/consolidated_alerts_LTD_20251005.csv"    # Process alerts - Returns 2 DataFrames
    df_closed, df_open = process_alerts_to_dataframe(input_file)

    # Date filtering
    start_date, end_date = get_date_filters()
    df_closed = filter_dataframe_by_date(df_closed, start_date, end_date)

    if len(df_closed) == 0:
        print("No closed trades after filtering. Exiting.")
        exit()

    # Create pivot tables
    pivot_tables = create_pivot_tables(df_closed, df_open)

    # Save results
    output_dir = pr_root / 'clean_up_alert-main' / 'outputs'
    # output_dir="/workspaces/Edge-Capital-Partners/clean_up_alert-main/outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    date_suffix = ""
    if start_date or end_date:
        start_str = start_date.strftime('%Y%m%d') if start_date else "start"
        end_str = end_date.strftime('%Y%m%d') if end_date else "end"
        date_suffix = f"_{start_str}_to_{end_str}"

    # Save closed trades CSV
    output_file = output_dir / f'closed_trades{date_suffix}.csv'
    df_closed.to_csv(output_file, index=False)

    # Save open positions CSV
    if len(df_open) > 0:
        open_file = output_dir / f'open_positions{date_suffix}.csv'
        df_open.to_csv(open_file, index=False)

    # Save Excel with all sheets
    excel_output = output_dir / f'TradingView_Analysis{date_suffix}.xlsx'
    with pd.ExcelWriter(excel_output, engine='xlsxwriter') as writer:
        # Sheet 1: Closed Trades
        df_closed.to_excel(writer, sheet_name='Closed Trades', index=False)

        # Sheet 2: Open Positions
        if len(df_open) > 0:
            df_open.to_excel(writer, sheet_name='Open Positions', index=False)

        # Sheet 3: Pivot
        if 'advanced_pivot' in pivot_tables:
            create_formatted_excel_pivot(df_closed, writer, 'Pivot')

        # Sheet 4: Alert ID Performance
        if 'alert_id_performance' in pivot_tables:
            alert_perf_df = pivot_tables['alert_id_performance']
            alert_perf_df.to_excel(writer, sheet_name='Alert ID Performance', index=False)

            workbook = writer.book
            worksheet = writer.sheets['Alert ID Performance']
            green_format = workbook.add_format({'bg_color': '#90EE90'})
            red_format = workbook.add_format({'bg_color': '#FFB6C1'})

            for idx, col in enumerate(alert_perf_df.columns):
                col_letter = chr(65 + idx)
                if 'Total PnL' in col:
                    worksheet.conditional_format(f'{col_letter}2:{col_letter}{len(alert_perf_df) + 1}', {
                        'type': 'cell', 'criteria': '>', 'value': 0, 'format': green_format
                    })
                    worksheet.conditional_format(f'{col_letter}2:{col_letter}{len(alert_perf_df) + 1}', {
                        'type': 'cell', 'criteria': '<', 'value': 0, 'format': red_format
                    })
                elif 'Win Rate' in col:
                    worksheet.conditional_format(f'{col_letter}2:{col_letter}{len(alert_perf_df) + 1}', {
                        'type': 'cell', 'criteria': '>=', 'value': 60, 'format': green_format
                    })

        # Remaining sheets
        if 'strategy_performance' in pivot_tables:
            pivot_tables['strategy_performance'].to_excel(writer, sheet_name='Strategy Performance')
        if 'ticker_performance' in pivot_tables:
            pivot_tables['ticker_performance'].to_excel(writer, sheet_name='Ticker Performance')
        if 'timeframe_performance' in pivot_tables:
            pivot_tables['timeframe_performance'].to_excel(writer, sheet_name='Timeframe Performance')
        if 'overall_summary' in pivot_tables:
            pivot_tables['overall_summary'].to_excel(writer, sheet_name='Overall Summary', index=False)

    print(f"\nProcessing complete!")
    print(f"Closed trades: {output_file}")
    print(f"Analysis: {excel_output}")
    if len(df_open) > 0:
        print(f"Open positions: {open_file}")