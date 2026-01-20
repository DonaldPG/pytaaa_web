"""Parser for pyTAAAweb_backtestPortfolioValue.params files.

Format: space-delimited columns
Regular models (5 columns): date buy_hold_value traded_value new_highs new_lows
Abacus model (6 columns): date buy_hold_value traded_value new_highs new_lows selected_model
Example: 2013-01-03 10000.00 10000.00 42 15
Example: 2026-01-16 327162.38 20431068801.83 7547.7 3230.3 naz100_hma
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
        List of dicts with keys: date, buy_hold_value, traded_value, new_highs, new_lows, selected_model (optional)
        
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
                
                # Expect 5 columns (regular) or 6 columns (abacus with selected_model)
                if len(parts) not in (5, 6):
                    raise BacktestParseError(
                        f"Line {line_num}: Expected 5 or 6 columns, got {len(parts)}: {line}"
                    )
                
                try:
                    # Parse common fields
                    date_str = parts[0]
                    buy_hold_str = parts[1]
                    traded_str = parts[2]
                    highs_str = parts[3]
                    lows_str = parts[4]
                    selected_model = parts[5] if len(parts) == 6 else None
                    
                    # Parse date (YYYY-MM-DD format)
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # Parse numeric values
                    buy_hold_value = float(buy_hold_str)
                    traded_value = float(traded_str)
                    new_highs = int(float(highs_str))  # Convert float to int
                    new_lows = int(float(lows_str))    # Convert float to int
                    
                    # Clean invalid values (< -99999 indicates missing/invalid data)
                    if new_highs < -99999:
                        new_highs = 0
                    if new_lows < -99999:
                        new_lows = 0
                    
                    data_point = {
                        'date': parsed_date,
                        'buy_hold_value': buy_hold_value,
                        'traded_value': traded_value,
                        'new_highs': new_highs,
                        'new_lows': new_lows
                    }
                    
                    # Add selected_model if present (abacus only)
                    if selected_model:
                        data_point['selected_model'] = selected_model
                    
                    backtest_data.append(data_point)
                    
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
