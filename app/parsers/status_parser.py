"""Parser for PyTAAA_status.params files.

Format: cumu_value: YYYY-MM-DD HH:MM.SS.SS value
Example: cumu_value: 2013-01-03 08:30.00.00 10000.00
"""
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import re


class StatusParseError(Exception):
    """Raised when status file parsing fails."""
    pass


def parse_status_file(file_path: Path) -> List[Dict]:
    """Parse PyTAAA_status.params file into performance metrics.
    
    Args:
        file_path: Path to PyTAAA_status.params file
        
    Returns:
        List of dicts with keys: date, traded_value
        
    Raises:
        StatusParseError: If file format is invalid
    """
    if not file_path.exists():
        raise StatusParseError(f"File not found: {file_path}")
    
    metrics = []
    # Pattern: cumu_value: YYYY-MM-DD HH:MM.SS.SS value
    pattern = re.compile(r'^cumu_value:\s+(\d{4}-\d{1,2}-\d{1,2})\s+[\d:.]+\s+([\d.]+)')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                
                # Skip empty lines, comments, and section headers
                if not line or line.startswith('#') or line.startswith('['):
                    continue
                
                match = pattern.match(line)
                if not match:
                    # Not a cumu_value line, skip
                    continue
                
                date_str, value_str = match.groups()
                
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    traded_value = float(value_str)
                except ValueError as e:
                    raise StatusParseError(
                        f"Invalid data at line {line_num}: {e}"
                    )
                
                metrics.append({
                    'date': date,
                    'base_value': traded_value,  # Use same value for both
                    'signal': 0,  # Default signal
                    'traded_value': traded_value,
                })
    except IOError as e:
        raise StatusParseError(f"Error reading file {file_path}: {e}")
    except Exception as e:
        raise StatusParseError(f"Unexpected error parsing {file_path}: {e}")
    
    return metrics
