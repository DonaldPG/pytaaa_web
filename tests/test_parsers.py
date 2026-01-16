"""Test parsers for .params files."""
import pytest
from datetime import date
from pathlib import Path
import tempfile

from app.parsers.status_parser import parse_status_file, StatusParseError
from app.parsers.holdings_parser import parse_holdings_file, HoldingsParseError
from app.parsers.ranks_parser import parse_ranks_file, RanksParseError


class TestStatusParser:
    """Test PyTAAA_status.params parser."""
    
    def test_parse_valid_status_file(self):
        """Test parsing a valid status file with real format."""
        content = """# Performance metrics
cumu_value: 2020-01-02 08:30.00.00 10000.00
cumu_value: 2020-01-03 08:30.00.00 10050.00
cumu_value: 2020-01-06 08:30.00.00 10100.50
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.params', delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)
        
        try:
            metrics = parse_status_file(file_path)
            
            assert len(metrics) == 3
            assert metrics[0]['date'] == date(2020, 1, 2)
            assert metrics[0]['base_value'] == 10000.00
            assert metrics[0]['signal'] == 0
            assert metrics[0]['traded_value'] == 10000.00
            
            assert metrics[1]['traded_value'] == 10050.00
            assert metrics[2]['traded_value'] == 10100.50
        finally:
            file_path.unlink()
    
    def test_parse_empty_lines_and_comments(self):
        """Test parser skips empty lines and comments."""
        content = """
# Comment line
cumu_value: 2020-01-02 08:30.00.00 10000.00

# Another comment
cumu_value: 2020-01-03 08:30.00.00 10050.00
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.params', delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)
        
        try:
            metrics = parse_status_file(file_path)
            assert len(metrics) == 2
        finally:
            file_path.unlink()
    
    def test_parse_invalid_format(self):
        """Test parser gracefully skips invalid lines."""
        content = """invalid line format
cumu_value: 2020-01-02 08:30.00.00 10000.00
another invalid line
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.params', delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Parser should skip invalid lines and only parse valid cumu_value lines
            metrics = parse_status_file(file_path)
            assert len(metrics) == 1
            assert metrics[0]['traded_value'] == 10000.00
        finally:
            file_path.unlink()
    
    def test_parse_file_not_found(self):
        """Test parser raises error when file doesn't exist."""
        with pytest.raises(StatusParseError, match="File not found"):
            parse_status_file(Path("/nonexistent/file.params"))


class TestHoldingsParser:
    """Test PyTAAA_holdings.params parser."""
    
    def test_parse_valid_holdings_file(self):
        """Test parsing a valid holdings file with real format."""
        content = """TradeDate: 2020-01-02
stocks:   AAPL MSFT CASH
shares:   10.0 5.0 1000.0
buyprice: 150.00 200.00 1.0

TradeDate: 2020-01-03
stocks:   AAPL GOOGL CASH
shares:   10.0 3.0 500.0
buyprice: 155.00 1500.00 1.0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.params', delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)
        
        try:
            snapshots, active_model = parse_holdings_file(file_path)
            
            # No active_model detection in this format
            assert active_model is None
            assert len(snapshots) == 2
            
            # First snapshot
            assert snapshots[0]['date'] == date(2020, 1, 2)
            assert len(snapshots[0]['holdings']) == 2  # CASH is filtered out
            assert snapshots[0]['holdings'][0]['ticker'] == 'AAPL'
            assert snapshots[0]['holdings'][0]['shares'] == 10.0
            assert snapshots[0]['holdings'][0]['purchase_price'] == 150.00
            
            # Second snapshot
            assert snapshots[1]['date'] == date(2020, 1, 3)
            assert len(snapshots[1]['holdings']) == 2  # CASH is filtered out
        finally:
            file_path.unlink()
    
    def test_parse_file_not_found(self):
        """Test parser raises error when file doesn't exist."""
        with pytest.raises(HoldingsParseError, match="File not found"):
            parse_holdings_file(Path("/nonexistent/file.params"))


class TestRanksParser:
    """Test PyTAAA_ranks.params parser."""
    
    def test_parse_valid_ranks_file(self):
        """Test parsing a valid ranks file."""
        content = """# 2020-01-02
1: AAPL 95.5
2: MSFT 92.3
3: GOOGL 90.1

# 2020-01-03
1: AAPL 96.2
2: TSLA 93.0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.params', delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)
        
        try:
            rankings = parse_ranks_file(file_path)
            
            assert len(rankings) == 5
            assert rankings[0]['date'] == date(2020, 1, 2)
            assert rankings[0]['ticker'] == 'AAPL'
            assert rankings[0]['rank'] == 1
            assert rankings[0]['score'] == 95.5
            
            assert rankings[3]['date'] == date(2020, 1, 3)
            assert rankings[3]['ticker'] == 'AAPL'
        finally:
            file_path.unlink()
    
    def test_parse_file_not_found(self):
        """Test parser raises error when file doesn't exist."""
        with pytest.raises(RanksParseError, match="File not found"):
            parse_ranks_file(Path("/nonexistent/file.params"))
