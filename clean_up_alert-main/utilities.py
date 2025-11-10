import pandas as pd
from pathlib import Path

def get_project_root() -> Path:
    return Path(__file__).parent.parent

def build_final_dataframe(completed_trades):
    """
    Converts the list of completed trades into a pandas DataFrame
    with a specific column order.
    """
    df = pd.DataFrame(completed_trades, columns=[
        'Alert ID',
        'Trading Date',
        'Closing Date',
        'Ticker',
        'Open',
        'Closing',
        'Shares',
        'Cost',
        'PnL',
        'Return(%)',
        'Average Day in the Market'
    ])
    return df