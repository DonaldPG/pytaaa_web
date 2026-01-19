"""Parser for pyTAAAweb_backtestPortfolioValue.params files.

Format: space-delimited columns
Columns: date buy_hold_value traded_value new_highs new_lows
Example: 2013-01-03 10000.00 10000.00 42 15
"""
from datetime import datetime, date as DateType
from pathlib import Path
from typing import List, Dict


class BacktestParseError(Exception):
    """Raised when backtest file parsing fails."""
    pass


def parse_backtest_file(file_path: Path) -> List[Dict]:
    """Parse pyTAAAweb_backtestPortfolioValue.params file into backtest data.
    
    Args:
        file_path: Path to pyTAAAweb_backtestPortfolioValue.params file
        
    Returns:
        List of dicts with keys: date, buy_hold_value, traded_value, new_highs, new_lows
        
    Raises:
        BacktestParseError: If file format is invalid
    """
    if not file_path.exists():
        raise BacktestParseError(f"File not found: {file_path}")
    
    backtest_data = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Split by whitespace
                parts = line.split()
                
                # Expect exactly 5 columns
                if len(parts) != 5:
                    raise BacktestParseError(
                        f"Line {line_num}: Expected 5 columns, got {len(parts)}: {line}"
                    )
                
                try:
                    date_str, buy_hold_str, traded_str, highs_str, lows_str = parts
                    
                    # Parse date (YYYY-MM-DD format)
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # Parse numeric values
                    buy_hold_value = float(buy_hold_str)
                    traded_value = float(traded_str)
                    new_highs = int(float(highs_str))  # Convert float to int
                    new_lows = int(float(lows_str))    # Convert float to int
                    
                    backtest_data.append({
                        'date': parsed_date,
                        'buy_hold_value': buy_hold_value,
                        'traded_value': traded_value,
                        'new_highs': new_highs,
                        'new_lows': new_lows
                    })
                    
                except ValueError as e:
                    raise BacktestParseError(
                        f"Line {line_num}: Invalid data format: {e}"
                    )
    
    except Exception as e:
        if isinstance(e, BacktestParseError):
            raise
        raise BacktestParseError(f"Failed to parse {file_path}: {e}")
    
    if not backtest_data:
        raise BacktestParseError(f"No data found in {file_path}")
    
    return backtest_data
