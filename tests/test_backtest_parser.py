"""Tests for backtest parser."""
import pytest
from datetime import date
from pathlib import Path

from app.parsers.backtest_parser import parse_backtest_file, BacktestParseError


class TestParseBacktestFile:
    """Tests for parse_backtest_file function."""
    
    def test_parse_valid_5_column_file(self, tmp_path: Path):
        """Test parsing valid 5-column backtest file."""
        # Create a test file with 5 columns (no selected_model)
        # Format: whitespace-separated values
        test_file = tmp_path / "backtest_5col.params"
        content = """# Backtest data
# Date BuyHold Traded NewHighs NewLows
2024-01-01 10000.0 10000.0 5 2
2024-01-02 10100.0 10200.0 6 1
2024-01-03 10200.0 10400.0 7 3
"""
        test_file.write_text(content)
        
        result = parse_backtest_file(test_file)
        
        assert len(result) == 3
        
        # Verify first record
        assert result[0]["date"] == date(2024, 1, 1)
        assert result[0]["buy_hold_value"] == 10000.0
        assert result[0]["traded_value"] == 10000.0
        assert result[0]["new_highs"] == 5
        assert result[0]["new_lows"] == 2
        # selected_model is only included when present (6-column format)
        assert "selected_model" not in result[0]
    
    def test_parse_valid_6_column_file(self, tmp_path: Path):
        """Test parsing valid 6-column backtest file (with selected_model)."""
        test_file = tmp_path / "backtest_6col.params"
        content = """# Backtest data with model selection
# Date BuyHold Traded NewHighs NewLows SelectedModel
2024-01-01 10000.0 10000.0 5 2 naz100_pine
2024-01-02 10100.0 10200.0 6 1 naz100_pi
2024-01-03 10200.0 10400.0 7 3 naz100_pine
"""
        test_file.write_text(content)
        
        result = parse_backtest_file(test_file)
        
        assert len(result) == 3
        
        # Verify selected_model field
        assert result[0]["selected_model"] == "naz100_pine"
        assert result[1]["selected_model"] == "naz100_pi"
        assert result[2]["selected_model"] == "naz100_pine"
    
    def test_parse_file_with_malformed_lines(self, tmp_path: Path):
        """Test parsing file with some malformed lines raises BacktestParseError."""
        test_file = tmp_path / "backtest_malformed.params"
        content = """# Backtest data
2024-01-01, 10000.0, 10000.0, 5, 2
invalid line without proper format
2024-01-02, 10100.0, 10200.0, 6, 1
"""
        test_file.write_text(content)
        
        # Should raise BacktestParseError for malformed line
        with pytest.raises(BacktestParseError):
            parse_backtest_file(test_file)
    
    def test_parse_empty_file(self, tmp_path: Path):
        """Test parsing empty file raises BacktestParseError."""
        test_file = tmp_path / "backtest_empty.params"
        test_file.write_text("")
        
        with pytest.raises(BacktestParseError):
            parse_backtest_file(test_file)
    
    def test_parse_file_with_invalid_values_below_threshold(self, tmp_path: Path):
        """Test parsing file with invalid values below -99999 gets cleaned to 0."""
        test_file = tmp_path / "backtest_invalid.params"
        content = """# Backtest data with invalid values
2024-01-01 10000.0 10000.0 5 2
2024-01-02 -99999.9 -99999.9 0 0
2024-01-03 10200.0 10400.0 7 3
"""
        test_file.write_text(content)
        
        result = parse_backtest_file(test_file)
        
        assert len(result) == 3
        # Note: The parser only cleans new_highs/new_lows values < -99999
        # buy_hold_value and traded_value are not cleaned, they remain as-is
        assert result[1]["buy_hold_value"] == -99999.9
        assert result[1]["traded_value"] == -99999.9
        # new_highs and new_lows were 0 in the test data, so no cleaning needed
        assert result[1]["new_highs"] == 0
        assert result[1]["new_lows"] == 0
    
    def test_parse_file_not_found(self):
        """Test parsing non-existent file raises BacktestParseError."""
        nonexistent_file = Path("/nonexistent/path/backtest.params")
        
        with pytest.raises(BacktestParseError):
            parse_backtest_file(nonexistent_file)
    
    def test_parse_file_with_comments_and_empty_lines(self, tmp_path: Path):
        """Test parsing file with comments and empty lines skips them correctly."""
        test_file = tmp_path / "backtest_with_comments.params"
        content = """# This is a comment
# Another comment line

2024-01-01 10000.0 10000.0 5 2

# Comment in the middle
2024-01-02 10100.0 10200.0 6 1

"""
        test_file.write_text(content)
        
        result = parse_backtest_file(test_file)
        
        assert len(result) == 2
        assert result[0]["date"] == date(2024, 1, 1)
        assert result[1]["date"] == date(2024, 1, 2)
