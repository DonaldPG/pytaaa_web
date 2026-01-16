"""Parser for PyTAAA_holdings.params files.

Format: 
TradeDate: YYYY-M-D
stocks:   TICKER1 TICKER2 TICKER3 CASH
shares:   100.0   200.0   300.0   1000.0
buyprice: 50.0    75.0    100.0   1.0
"""
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re


class HoldingsParseError(Exception):
    """Raised when holdings file parsing fails."""
    pass


def parse_holdings_file(file_path: Path) -> Tuple[List[Dict], Optional[str]]:
    """Parse PyTAAA_holdings.params file into portfolio snapshots and holdings.
    
    Args:
        file_path: Path to PyTAAA_holdings.params file
        
    Returns:
        Tuple of (snapshots_list, active_model_name)
        - snapshots_list: List of dicts with keys: date, total_value, holdings
        - active_model_name: Always None (no model detection in this format)
        
    Raises:
        HoldingsParseError: If file format is invalid
    """
    if not file_path.exists():
        raise HoldingsParseError(f"File not found: {file_path}")
    
    snapshots = []
    current_date = None
    current_stocks = []
    current_shares = []
    current_prices = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                
                # Skip empty lines and section headers
                if not line or line.startswith('['):
                    continue
                
                # Parse TradeDate
                if line.startswith('TradeDate:'):
                    # Save previous snapshot if exists
                    if current_date and current_stocks:
                        snapshot = _create_snapshot(current_date, current_stocks, current_shares, current_prices)
                        if snapshot:
                            snapshots.append(snapshot)
                    
                    # Parse new date
                    date_str = line.split(':', 1)[1].strip()
                    try:
                        current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        try:
                            # Try format without leading zeros: 2013-1-2
                            parts = date_str.split('-')
                            current_date = datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
                        except:
                            continue
                    
                    current_stocks = []
                    current_shares = []
                    current_prices = []
                    
                elif line.startswith('cumulativecashin:'):
                    # Skip this line
                    continue
                    
                elif line.startswith('stocks:'):
                    # Parse stock tickers
                    parts = line.split(':', 1)[1].strip().split()
                    current_stocks = parts
                    
                elif line.startswith('shares:'):
                    # Parse shares
                    parts = line.split(':', 1)[1].strip().split()
                    current_shares = [float(s) for s in parts]
                    
                elif line.startswith('buyprice:'):
                    # Parse buy prices
                    parts = line.split(':', 1)[1].strip().split()
                    current_prices = [float(p) for p in parts]
        
        # Save last snapshot
        if current_date and current_stocks:
            snapshot = _create_snapshot(current_date, current_stocks, current_shares, current_prices)
            if snapshot:
                snapshots.append(snapshot)
    
    except IOError as e:
        raise HoldingsParseError(f"Error reading file {file_path}: {e}")
    except Exception as e:
        raise HoldingsParseError(f"Unexpected error parsing {file_path}: {e}")
    
    return snapshots, None


def _create_snapshot(date, stocks, shares, prices):
    """Create a snapshot dict from parsed data."""
    if not (stocks and shares and prices):
        return None
    
    if not (len(stocks) == len(shares) == len(prices)):
        return None
    
    holdings = []
    total_value = 0.0
    
    for ticker, share_count, buy_price in zip(stocks, shares, prices):
        if ticker.upper() == 'CASH':
            total_value += share_count  # Cash is already in dollars
            continue
        
        holdings.append({
            'ticker': ticker.upper(),
            'shares': share_count,
            'purchase_price': buy_price,
            'current_price': buy_price,  # Use buy price as current (no current price in file)
            'weight': 0.0,  # Will calculate later
            'rank': None,
            'buy_date': date,
        })
        
        total_value += share_count * buy_price
    
    # Calculate weights
    for holding in holdings:
        holding['weight'] = (holding['shares'] * holding['current_price']) / total_value if total_value > 0 else 0.0
    
    return {
        'date': date,
        'total_value': total_value,
        'holdings': holdings,
    }
