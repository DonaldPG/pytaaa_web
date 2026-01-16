"""Parser for PyTAAA_ranks.params files.

Format: Stores top 20 stock rankings per date
"""
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import re


class RanksParseError(Exception):
    """Raised when ranks file parsing fails."""
    pass


def parse_ranks_file(file_path: Path) -> List[Dict]:
    """Parse PyTAAA_ranks.params file into stock rankings.
    
    Args:
        file_path: Path to PyTAAA_ranks.params file
        
    Returns:
        List of dicts with keys: date, ticker, rank, score (optional)
        
    Raises:
        RanksParseError: If file format is invalid
    """
    if not file_path.exists():
        raise RanksParseError(f"File not found: {file_path}")
    
    rankings = []
    current_date = None
    
    # Pattern for date line: # YYYY-MM-DD or similar
    date_pattern = re.compile(r'#?\s*(\d{4}-\d{2}-\d{2})')
    # Pattern for rank line: rank: ticker or rank ticker score
    rank_pattern = re.compile(r'^(\d+)[:\s]+([A-Z]+)(?:\s+([\d.]+))?')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                
                if not line:
                    continue
                
                # Check for date marker
                date_match = date_pattern.match(line)
                if date_match:
                    try:
                        current_date = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
                    except ValueError as e:
                        raise RanksParseError(f"Invalid date at line {line_num}: {e}")
                    continue
                
                # Parse rank line
                rank_match = rank_pattern.match(line)
                if rank_match and current_date:
                    rank_str, ticker, score_str = rank_match.groups()
                    
                    try:
                        rank = int(rank_str)
                        score = float(score_str) if score_str else None
                        
                        rankings.append({
                            'date': current_date,
                            'ticker': ticker.upper(),
                            'rank': rank,
                            'score': score,
                        })
                    except ValueError as e:
                        raise RanksParseError(f"Invalid rank data at line {line_num}: {e}")
    
    except IOError as e:
        raise RanksParseError(f"Error reading file {file_path}: {e}")
    except Exception as e:
        raise RanksParseError(f"Unexpected error parsing {file_path}: {e}")
    
    return rankings
