"""
Tests for utils.py module.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch
from utils import (
    get_project_root, load_config, get_db_connection, 
    initialize_db, get_timestamp, truncate_text
)


class TestUtilsFunctions:
    """Test utility functions."""
    
    def test_get_project_root(self):
        """Test get_project_root returns a valid path."""
        root = get_project_root()
        assert isinstance(root, Path)
        assert root.exists()
    
    def test_truncate_text(self):
        """Test text truncation function."""
        # Test normal truncation
        long_text = "This is a very long text that should be truncated."
        result = truncate_text(long_text, max_length=10)
        assert result == "This is a ..."
        assert len(result) == 13  # 10 + 3 for "..."
        
        # Test text shorter than max_length
        short_text = "Short"
        result = truncate_text(short_text, max_length=10)
        assert result == "Short"
        
        # Test empty text
        result = truncate_text("", max_length=10)
        assert result == ""
        
        # Test None text
        result = truncate_text(None, max_length=10)
        assert result == ""
    
    def test_get_timestamp(self):
        """Test timestamp generation."""
        timestamp = get_timestamp()
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format should contain T
        
    @patch('utils.load_config')
    def test_load_config_called(self, mock_load_config):
        """Test that load_config can be mocked."""
        mock_load_config.return_value = {"test": "value"}
        result = load_config()
        assert result == {"test": "value"}
        mock_load_config.assert_called_once()


class TestDatabaseFunctions:
    """Test database-related functions."""
    
    def test_initialize_db_creates_tables(self):
        """Test that initialize_db creates the expected tables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('utils.DB_PATH', Path(tmpdir) / "test.db"):
                # Initialize the database
                initialize_db()
                
                # Check that the database file was created
                assert (Path(tmpdir) / "test.db").exists()
                
                # Connect and check tables exist
                conn = sqlite3.connect(Path(tmpdir) / "test.db")
                cursor = conn.cursor()
                
                # Check items table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items';")
                assert cursor.fetchone() is not None
                
                # Check source_metadata table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='source_metadata';")
                assert cursor.fetchone() is not None
                
                conn.close()
    
    def test_get_db_connection_returns_connection(self):
        """Test that get_db_connection returns a valid connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('utils.DB_PATH', Path(tmpdir) / "test.db"):
                # Initialize the database first
                initialize_db()
                
                # Get connection
                conn = get_db_connection()
                assert isinstance(conn, sqlite3.Connection)
                
                # Test that row_factory is set
                cursor = conn.cursor()
                cursor.execute("SELECT 1 as test_col")
                row = cursor.fetchone()
                assert row['test_col'] == 1  # Should be accessible by name
                
                conn.close()