"""
Tests for data_collector.py module.
"""

import pytest
from unittest.mock import patch, MagicMock
from data_collector import DataCollector


class TestDataCollector:
    """Test DataCollector class functionality."""
    
    @pytest.fixture
    def mock_collector(self):
        """Create a DataCollector with mocked dependencies."""
        with patch('data_collector.load_environment'), \
             patch('data_collector.load_config') as mock_config, \
             patch('os.getenv') as mock_getenv:
            
            # Mock configuration
            mock_config.return_value = {
                'sources': {
                    'arxiv': {'enabled': True, 'categories': ['cs.AI'], 'max_results': 5},
                    'news': {'enabled': True, 'keywords': ['AI'], 'max_results': 5},
                    'youtube': {'enabled': True, 'channels': ['test_channel'], 'keywords': ['AI'], 'max_results': 5},
                    'company_blogs': {'enabled': True, 'feeds': [{'name': 'Test', 'url': 'https://test.com/feed'}], 'max_results': 5}
                }
            }
            
            # Mock environment variables
            mock_getenv.side_effect = lambda key: {
                'NEWS_API_KEY': 'test_news_key',
                'YOUTUBE_API_KEY': 'test_youtube_key'
            }.get(key)
            
            collector = DataCollector()
            yield collector
    
    def test_collector_initialization(self, mock_collector):
        """Test DataCollector initialization."""
        assert mock_collector.news_api_key == 'test_news_key'
        assert mock_collector.youtube_api_key == 'test_youtube_key'
        assert mock_collector.config is not None
    
    def test_requests_retry_session(self, mock_collector):
        """Test requests retry session creation."""
        session = mock_collector.requests_retry_session()
        
        # Check that session is created and has adapters
        assert session is not None
        assert 'http://' in session.adapters
        assert 'https://' in session.adapters
    
    @patch('data_collector.requests.Session')
    def test_fetch_full_article_text_success(self, mock_session, mock_collector):
        """Test successful full article text fetching."""
        # Mock response
        mock_response = MagicMock()
        mock_response.content = b'<article><p>This is the article content.</p></article>'
        mock_response.raise_for_status.return_value = None
        
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_collector.requests_retry_session = MagicMock(return_value=mock_session_instance)
        
        result = mock_collector._fetch_full_article_text('https://example.com/article')
        
        assert result is not None
        assert 'article content' in result
        mock_session_instance.get.assert_called_once_with('https://example.com/article', timeout=10)
    
    @patch('data_collector.requests.Session')
    def test_fetch_full_article_text_failure(self, mock_session, mock_collector):
        """Test full article text fetching with network error."""
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = Exception("Network error")
        mock_collector.requests_retry_session = MagicMock(return_value=mock_session_instance)
        
        result = mock_collector._fetch_full_article_text('https://example.com/article')
        
        assert result is None
    
    @patch('data_collector.arxiv.Search')
    def test_collect_arxiv_papers(self, mock_arxiv_search, mock_collector):
        """Test arXiv paper collection."""
        # Mock arXiv result
        mock_result = MagicMock()
        mock_result.entry_id = 'http://arxiv.org/abs/2301.00001v1'
        mock_result.title = 'Test AI Paper'
        mock_result.summary = 'This is a test paper about AI.'
        mock_result.authors = [MagicMock(name='Test Author')]
        mock_result.published = '2024-01-01T00:00:00Z'
        mock_result.links = [MagicMock(href='http://arxiv.org/pdf/2301.00001v1.pdf')]
        
        mock_search_instance = MagicMock()
        mock_search_instance.results.return_value = [mock_result]
        mock_arxiv_search.return_value = mock_search_instance
        
        papers = mock_collector.collect_arxiv_papers()
        
        assert len(papers) == 1
        assert papers[0]['title'] == 'Test AI Paper'
        assert papers[0]['type'] == 'paper'
        assert papers[0]['id'] == '2301.00001v1'
    
    @patch('data_collector.requests.Session')
    def test_collect_news_articles(self, mock_session, mock_collector):
        """Test news article collection."""
        # Mock news API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'articles': [{
                'title': 'Test AI News',
                'description': 'This is test AI news.',
                'url': 'https://example.com/news/ai-test',
                'source': {'name': 'Test Source'},
                'publishedAt': '2024-01-01T12:00:00Z',
                'author': 'Test Author',
                'urlToImage': 'https://example.com/image.jpg'
            }]
        }
        mock_response.raise_for_status.return_value = None
        
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_collector.requests_retry_session = MagicMock(return_value=mock_session_instance)
        
        # Mock full text fetching
        mock_collector._fetch_full_article_text = MagicMock(return_value="Full article text")
        
        articles = mock_collector.collect_news_articles()
        
        assert len(articles) == 1
        assert articles[0]['title'] == 'Test AI News'
        assert articles[0]['type'] == 'news'
        assert articles[0]['full_text_content'] == "Full article text"
    
    @patch('data_collector.feedparser.parse')
    def test_collect_company_blogs(self, mock_feedparser, mock_collector):
        """Test company blog collection."""
        # Mock feedparser response
        mock_entry = MagicMock()
        mock_entry.get.side_effect = lambda key, default=None: {
            'title': 'Test Blog Post',
            'id': 'https://test.com/blog/post1',
            'link': 'https://test.com/blog/post1'
        }.get(key, default)
        mock_entry.summary = 'This is a test blog post.'
        
        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]
        mock_feedparser.return_value = mock_feed
        
        # Mock full text fetching
        mock_collector._fetch_full_article_text = MagicMock(return_value="Full blog content")
        
        posts = mock_collector.collect_company_blogs()
        
        assert len(posts) == 1
        assert posts[0]['title'] == 'Test Blog Post'
        assert posts[0]['type'] == 'blog'
        assert posts[0]['source'] == 'Test'
    
    def test_collect_all_data(self, mock_collector):
        """Test collecting data from all sources."""
        # Mock individual collection methods
        mock_collector.collect_arxiv_papers = MagicMock(return_value=[{'type': 'paper', 'title': 'Test Paper'}])
        mock_collector.collect_news_articles = MagicMock(return_value=[{'type': 'news', 'title': 'Test News'}])
        mock_collector.collect_youtube_videos = MagicMock(return_value=[{'type': 'video', 'title': 'Test Video'}])
        mock_collector.collect_company_blogs = MagicMock(return_value=[{'type': 'blog', 'title': 'Test Blog'}])
        
        data = mock_collector.collect_all_data()
        
        assert 'timestamp' in data
        assert len(data['arxiv_papers']) == 1
        assert len(data['news_articles']) == 1
        assert len(data['youtube_videos']) == 1
        assert len(data['blog_posts']) == 1
        
        # Verify collection methods were called
        mock_collector.collect_arxiv_papers.assert_called_once()
        mock_collector.collect_news_articles.assert_called_once()
        mock_collector.collect_youtube_videos.assert_called_once()
        mock_collector.collect_company_blogs.assert_called_once()