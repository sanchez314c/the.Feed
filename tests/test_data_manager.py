"""
Tests for data_manager.py module.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
from data_manager import DataManager


class TestDataManager:
    """Test DataManager class functionality."""
    
    @pytest.fixture
    def temp_db_manager(self):
        """Create a DataManager with a temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('utils.DB_PATH', Path(tmpdir) / "test.db"):
                # Mock the DataCollector and ClaudeProcessor to avoid external dependencies
                with patch('data_manager.DataCollector') as mock_collector, \
                     patch('data_manager.ClaudeProcessor') as mock_processor:
                    
                    manager = DataManager()
                    manager.collector = mock_collector.return_value
                    manager.processor = mock_processor.return_value
                    yield manager
    
    def test_data_manager_init(self, temp_db_manager):
        """Test DataManager initialization."""
        assert temp_db_manager.collector is not None
        assert temp_db_manager.processor is not None
    
    def test_item_to_db_format(self, temp_db_manager):
        """Test _item_to_db_format helper method."""
        test_item = {
            'id': 'test123',
            'title': 'Test Title',
            'url': 'https://example.com',
            'description': 'Test description',
            'categories': ['Research', 'AI'],
            'keywords': ['machine learning'],
            'importance_score': 8
        }
        
        result = temp_db_manager._item_to_db_format(test_item, 'test_source', 'test_type')
        
        # Check that result is a tuple with expected length
        assert isinstance(result, tuple)
        assert len(result) == 20  # Should match the number of DB columns
        assert result[0] == 'test123'  # id
        assert result[1] == 'Test Title'  # title
        assert result[4] == 'test_source'  # source_type
        assert result[5] == 'test_type'  # content_type
    
    def test_get_latest_data_summary_empty_db(self, temp_db_manager):
        """Test get_latest_data_summary with empty database."""
        result = temp_db_manager.get_latest_data_summary()
        assert result == {"timestamp": None}
    
    def test_update_item_flags(self, temp_db_manager):
        """Test updating item flags (bookmark, read status)."""
        # First insert a test item
        from utils import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO items (id, title, url, content_type, bookmarked, is_read)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('test123', 'Test Title', 'https://example.com', 'paper', 0, 0))
        conn.commit()
        conn.close()
        
        # Test bookmarking
        result = temp_db_manager.update_item_flags('test123', bookmarked=True)
        assert result is True
        
        # Verify the flag was updated
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT bookmarked FROM items WHERE id = ?", ('test123',))
        row = cursor.fetchone()
        assert row['bookmarked'] == 1
        conn.close()
        
        # Test updating read status
        result = temp_db_manager.update_item_flags('test123', is_read=True)
        assert result is True
        
        # Test updating non-existent item
        result = temp_db_manager.update_item_flags('nonexistent', bookmarked=True)
        assert result is False
    
    def test_get_data_by_type(self, temp_db_manager):
        """Test getting data by content type."""
        # Insert test data
        from utils import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert multiple items with different types
        test_items = [
            ('paper1', 'Paper 1', 'paper', 8, '["Research"]', '["AI"]'),
            ('paper2', 'Paper 2', 'paper', 6, '["Applications"]', '["ML"]'),
            ('news1', 'News 1', 'news', 7, '["Business"]', '["OpenAI"]'),
        ]
        
        for item_id, title, content_type, importance, categories, keywords in test_items:
            cursor.execute("""
                INSERT INTO items (id, title, content_type, importance_score, categories, keywords)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item_id, title, content_type, importance, categories, keywords))
        
        conn.commit()
        conn.close()
        
        # Test getting papers
        papers = temp_db_manager.get_data_by_type('paper', limit=10)
        assert len(papers) == 2
        assert all(item['content_type'] == 'paper' for item in papers)
        
        # Test with filters
        papers_filtered = temp_db_manager.get_data_by_type('paper', filters={'min_importance': 7})
        assert len(papers_filtered) == 1
        assert papers_filtered[0]['id'] == 'paper1'
    
    def test_search_all_data(self, temp_db_manager):
        """Test search functionality."""
        # Insert test data
        from utils import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO items (id, title, description, content_type, categories, keywords)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('test1', 'Machine Learning Paper', 'A paper about neural networks', 'paper', '["Research"]', '["ML", "AI"]'))
        
        cursor.execute("""
            INSERT INTO items (id, title, description, content_type, categories, keywords)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('test2', 'AI News Article', 'Latest developments in artificial intelligence', 'news', '["Business"]', '["AI", "tech"]'))
        
        conn.commit()
        conn.close()
        
        # Test searching for "machine"
        results = temp_db_manager.search_all_data('machine', limit=10)
        assert len(results) == 1
        assert results[0]['id'] == 'test1'
        
        # Test searching for "AI" (should match both)
        results = temp_db_manager.search_all_data('AI', limit=10)
        assert len(results) == 2
    
    def test_get_bookmarked_items(self, temp_db_manager):
        """Test getting bookmarked items."""
        # Insert test data with bookmarks
        from utils import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO items (id, title, content_type, bookmarked)
            VALUES (?, ?, ?, ?)
        """, ('bookmarked1', 'Bookmarked Item', 'paper', 1))
        
        cursor.execute("""
            INSERT INTO items (id, title, content_type, bookmarked)
            VALUES (?, ?, ?, ?)
        """, ('normal1', 'Normal Item', 'paper', 0))
        
        conn.commit()
        conn.close()
        
        # Test getting bookmarked items
        bookmarked = temp_db_manager.get_bookmarked_items()
        assert len(bookmarked) == 1
        assert bookmarked[0]['id'] == 'bookmarked1'
    
    def test_source_fetch_metadata(self, temp_db_manager):
        """Test source metadata storage and retrieval."""
        source_id = 'test_feed'
        fetch_time = '2024-01-01T12:00:00'
        last_item = 'item123'
        
        # Test storing metadata
        temp_db_manager.update_source_fetch_metadata(source_id, fetch_time, last_item)
        
        # Test retrieving metadata
        metadata = temp_db_manager.get_source_fetch_metadata(source_id)
        assert metadata is not None
        assert metadata['last_successful_fetch'] == fetch_time
        assert metadata['last_item_id'] == last_item
        
        # Test retrieving non-existent metadata
        metadata = temp_db_manager.get_source_fetch_metadata('nonexistent')
        assert metadata is None