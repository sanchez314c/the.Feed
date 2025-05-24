import os
import requests
import arxiv
import feedparser
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils import load_config, load_environment, get_timestamp, truncate_text, logger

class DataCollector:
    """
    Class for collecting AI-related content from various sources.
    """
    
    def __init__(self, data_manager=None):
        """Initialize the data collector with configuration."""
        load_environment()
        self.config = load_config()
        self.news_api_key = os.getenv("NEWS_API_KEY")
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        self.data_manager = data_manager  # For accessing source metadata
    
    def requests_retry_session(self, retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None):
        """Create a requests session with retry configuration."""
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def _fetch_full_article_text(self, url):
        """Fetch full article text from URL for better summarization."""
        try:
            session = self.requests_retry_session()
            response = session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Basic extraction logic (can be significantly improved with heuristics)
            # Remove script, style, nav, footer tags
            for unwanted_tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                unwanted_tag.decompose()

            # Get text from common article containers, or body as a fallback
            article_body = soup.find('article') or \
                           soup.find(class_=["post-content", "entry-content", "article-body"]) or \
                           soup.body

            if article_body:
                text = article_body.get_text(separator=' ', strip=True)
                return truncate_text(text, 5000)  # Truncate for Claude context
            return None
        except Exception as e:
            logger.warning(f"Could not fetch or parse full article from {url}: {e}")
            return None
    
    def collect_all_data(self):
        """
        Collect data from all enabled sources.
        
        Returns:
            dict: Collection of data from all sources
        """
        data = {
            'timestamp': get_timestamp(),
            'arxiv_papers': [],
            'news_articles': [],
            'youtube_videos': [],
            'blog_posts': []
        }
        
        # Collect from enabled sources
        if self.config['sources']['arxiv']['enabled']:
            data['arxiv_papers'] = self.collect_arxiv_papers()
            
        if self.config['sources']['news']['enabled'] and self.news_api_key:
            data['news_articles'] = self.collect_news_articles()
            
        if self.config['sources']['youtube']['enabled'] and self.youtube_api_key:
            data['youtube_videos'] = self.collect_youtube_videos()
            
        if self.config['sources']['company_blogs']['enabled']:
            data['blog_posts'] = self.collect_company_blogs()
            
        return data
    
    def collect_arxiv_papers(self):
        """
        Collect recent AI papers from arXiv.
        
        Returns:
            list: Collection of paper information
        """
        try:
            # Get configuration
            categories = self.config['sources']['arxiv']['categories']
            max_results = self.config['sources']['arxiv']['max_results']
            
            # Create query string for the categories
            query = ' OR '.join([f'cat:{cat}' for cat in categories])
            
            # Search for papers
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            papers = []
            for result in search.results():
                # Format the authors
                authors = ', '.join([author.name for author in result.authors])
                
                paper = {
                    'id': result.entry_id.split('/')[-1],
                    'title': result.title,
                    'authors': authors,
                    'abstract': result.summary,
                    'url': result.pdf_url,
                    'published': result.published.isoformat(),
                    'categories': [cat for cat in result.categories],
                    'source': 'arxiv',
                    'type': 'paper',
                    'thumbnail': None  # arXiv doesn't provide thumbnails
                }
                papers.append(paper)
                
            return papers
        except Exception as e:
            logger.error(f"Error collecting arXiv papers: {e}", exc_info=True)
            return []
    
    def collect_news_articles(self):
        """
        Collect AI-related news articles.
        
        Returns:
            list: Collection of news articles
        """
        try:
            if not self.news_api_key:
                return []
                
            # Get configuration
            keywords = self.config['sources']['news']['keywords']
            max_results = self.config['sources']['news']['max_results']
            
            # Create query string (OR between keywords)
            query = ' OR '.join([f'"{kw}"' for kw in keywords])
            
            # Get date for timeframe (last 2 days)
            from_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
            
            # NewsAPI URL
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': query,
                'from': from_date,
                'sortBy': 'publishedAt',
                'language': 'en',
                'pageSize': max_results,
                'apiKey': self.news_api_key
            }
            
            session = self.requests_retry_session()
            response = session.get(url, params=params, timeout=10)
            response.raise_for_status()  # Raises HTTPError for bad responses
                
            data = response.json()
            articles = []
            
            for article in data.get('articles', []):
                # Clean and format the article data
                description = article.get('description', '')
                full_text = self._fetch_full_article_text(article.get('url', ''))
                
                article_data = {
                    'id': article.get('url', '').split('/')[-1],
                    'title': article.get('title', ''),
                    'description': truncate_text(BeautifulSoup(description, 'html.parser').get_text(), 300) if description else '',
                    'url': article.get('url', ''),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'published': article.get('publishedAt', ''),
                    'author': article.get('author', ''),
                    'thumbnail': article.get('urlToImage', None),
                    'type': 'news'
                }
                
                # Add full text content for better Claude analysis
                if full_text:
                    article_data['full_text_content'] = full_text
                    
                articles.append(article_data)
                
            return articles
        except requests.exceptions.HTTPError as e:
            logger.error(f"News API HTTP error: {e.response.status_code} - {e.response.text}", exc_info=True)
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"News API network error: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error collecting news articles: {e}", exc_info=True)
            return []
    
    def collect_youtube_videos(self):
        """
        Collect AI-related YouTube videos.
        
        Returns:
            list: Collection of YouTube videos
        """
        try:
            if not self.youtube_api_key:
                return []
                
            # Get configuration
            channels = self.config['sources']['youtube']['channels']
            keywords = self.config['sources']['youtube']['keywords']
            max_results = self.config['sources']['youtube']['max_results']
            
            # Initialize the YouTube API client
            youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
            
            videos = []
            
            # Search for videos from the specified channels
            for channel_id in channels:
                # Get channel uploads
                response = youtube.search().list(
                    part='snippet',
                    channelId=channel_id,
                    maxResults=max_results // len(channels),
                    order='date',
                    type='video'
                ).execute()
                
                # Collect video IDs for detailed information
                video_ids_to_fetch_details = []
                relevant_items = []
                
                for item in response.get('items', []):
                    # Check if the video is related to AI keywords
                    title = item['snippet']['title'].lower()
                    description = item['snippet']['description'].lower()
                    
                    # Check if any keyword is in the title or description
                    if any(kw.lower() in title or kw.lower() in description for kw in keywords):
                        video_ids_to_fetch_details.append(item['id']['videoId'])
                        relevant_items.append(item)
                
                # Fetch detailed video information (duration, views, etc.)
                if video_ids_to_fetch_details:
                    video_response = youtube.videos().list(
                        part="snippet,contentDetails,statistics",
                        id=",".join(video_ids_to_fetch_details)
                    ).execute()
                    
                    # Create a lookup for detailed info
                    video_details = {v['id']: v for v in video_response.get('items', [])}
                    
                    for item in relevant_items:
                        video_id = item['id']['videoId']
                        details = video_details.get(video_id, {})
                        
                        video = {
                            'id': video_id,
                            'title': item['snippet']['title'],
                            'description': item['snippet']['description'],
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'thumbnail': item['snippet']['thumbnails']['high']['url'],
                            'channel': item['snippet']['channelTitle'],
                            'published': item['snippet']['publishedAt'],
                            'source': 'youtube',
                            'type': 'video'
                        }
                        
                        # Add detailed information if available
                        if details:
                            content_details = details.get('contentDetails', {})
                            statistics = details.get('statistics', {})
                            
                            video['duration'] = content_details.get('duration', '')  # ISO 8601 duration
                            video['view_count'] = statistics.get('viewCount', 0)
                            video['like_count'] = statistics.get('likeCount', 0)
                        
                        videos.append(video)
            
            return videos
        except HttpError as e:
            logger.error(f"YouTube API error: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error collecting YouTube videos: {e}", exc_info=True)
            return []
    
    def collect_company_blogs(self):
        """
        Collect blog posts from AI company blogs using RSS feeds.
        
        Returns:
            list: Collection of blog posts
        """
        try:
            # Get configuration
            feeds = self.config['sources']['company_blogs']['feeds']
            max_results = self.config['sources']['company_blogs']['max_results']
            
            blog_posts = []
            
            for feed_info in feeds:
                feed_name = feed_info['name']
                feed_url = feed_info['url']
                feed_id = feed_url  # Use URL as unique identifier for this feed
                
                # Get last fetch metadata for incremental loading
                metadata = None
                if self.data_manager:
                    metadata = self.data_manager.get_source_fetch_metadata(feed_id)
                
                last_seen_entry_id = metadata.get('last_item_id') if metadata else None
                newest_entry_this_run_id = None
                
                # Parse the RSS feed
                feed = feedparser.parse(feed_url)
                
                entries_to_process = []
                for entry in feed.entries:
                    current_entry_id = entry.get('id', entry.get('link'))
                    if current_entry_id == last_seen_entry_id:
                        break  # Stop if we encounter the last seen item
                    entries_to_process.append(entry)
                    if newest_entry_this_run_id is None:
                        newest_entry_this_run_id = current_entry_id
                
                # Process new entries (limit to max_results per feed)
                entries_to_process = entries_to_process[:max_results // len(feeds)]
                
                # Process each entry
                for entry in entries_to_process:
                    # Extract content
                    title = entry.get('title', '')
                    description = ''
                    
                    # Try different fields for content
                    if 'summary' in entry:
                        description = entry.summary
                    elif 'description' in entry:
                        description = entry.description
                    elif 'content' in entry:
                        description = entry.content[0].value
                        
                    # Clean up HTML if present
                    if description and ('<' in description and '>' in description):
                        soup = BeautifulSoup(description, 'html.parser')
                        description = soup.get_text()
                    
                    # Fetch full article text for better analysis
                    full_text = self._fetch_full_article_text(entry.get('link', ''))
                    
                    # Create post object
                    post = {
                        'id': entry.get('id', entry.get('link', '')).split('/')[-1],
                        'title': title,
                        'description': truncate_text(description, 300),  # Cleaned summary for quick view
                        'url': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'source': feed_name,
                        'type': 'blog',
                        'thumbnail': None  # Default value
                    }
                    
                    # Add full text content for better Claude analysis
                    if full_text:
                        post['full_text_content'] = full_text
                    
                    # Try to extract thumbnail from content
                    if 'content' in entry and entry.content:
                        for content in entry.content:
                            if 'value' in content:
                                soup = BeautifulSoup(content['value'], 'html.parser')
                                img_tag = soup.find('img')
                                if img_tag and 'src' in img_tag.attrs:
                                    post['thumbnail'] = img_tag['src']
                                    break
                    
                    blog_posts.append(post)
                
                # Update source metadata after successful processing of this feed
                if newest_entry_this_run_id and self.data_manager:
                    self.data_manager.update_source_fetch_metadata(feed_id, get_timestamp(), newest_entry_this_run_id)
            
            return blog_posts
        except Exception as e:
            logger.error(f"Error collecting blog posts: {e}", exc_info=True)
            return []