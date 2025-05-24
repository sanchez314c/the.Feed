import os
import json
import sqlite3
from datetime import datetime
from utils import get_db_connection, initialize_db, get_timestamp, logger
from data_collector import DataCollector
from claude_processor import ClaudeProcessor

class DataManager:
    """
    Class for managing the data collection, processing, and storage pipeline.
    Now uses SQLite database instead of JSON files.
    """
    
    def __init__(self):
        """Initialize the data manager with collectors and processors."""
        initialize_db()  # Ensure DB is set up
        self.collector = DataCollector(data_manager=self)  # Pass self for metadata access
        self.processor = ClaudeProcessor()
        
    def _item_to_db_format(self, item, source_key, content_type_val):
        """Helper to convert item dict to tuple for DB insertion, handling missing keys."""
        return (
            item.get('id'), item.get('title'), item.get('url'),
            item.get('source'), source_key, content_type_val,
            item.get('description') or item.get('abstract'), # Handle both description and abstract
            item.get('summary'), item.get('authors'),
            item.get('published'), item.get('thumbnail'),
            json.dumps(item.get('categories', [])), json.dumps(item.get('keywords', [])),
            item.get('importance_score', 5), item.get('channel'),
            json.dumps(item), get_timestamp(), # raw_data, processed_at
            item.get('bookmarked', 0), item.get('is_read', 0),
            get_timestamp() # last_fetched_at
        )
        
    def refresh_data(self):
        """
        Collect fresh data from all sources, process it, and save to SQLite database.
        
        Returns:
            dict: Status information about the refresh
        """
        logger.info("Starting data refresh process...")
        raw_data_collection = self.collector.collect_all_data()

        conn = get_db_connection()
        cursor = conn.cursor()

        for source_key, items in raw_data_collection.items():
            if source_key == 'timestamp':
                continue

            logger.info(f"Processing {len(items)} items from {source_key}...")
            processed_items = self.processor.batch_process(items)

            # Determine content_type based on source_key
            content_type_val = ""
            if source_key == 'arxiv_papers': 
                content_type_val = 'paper'
            elif source_key == 'news_articles': 
                content_type_val = 'news'
            elif source_key == 'youtube_videos': 
                content_type_val = 'video'
            elif source_key == 'blog_posts': 
                content_type_val = 'blog'

            for item in processed_items:
                # Add/update content_type if not present from collector
                if 'type' not in item and content_type_val:
                    item['type'] = content_type_val

                db_item = self._item_to_db_format(item, source_key, item['type'])
                try:
                    cursor.execute("""
                    INSERT INTO items (id, title, url, source, source_type, content_type, description, summary, authors, published, thumbnail, categories, keywords, importance_score, channel, raw_data, processed_at, bookmarked, is_read, last_fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title=excluded.title,
                        url=excluded.url,
                        source=excluded.source,
                        source_type=excluded.source_type,
                        content_type=excluded.content_type,
                        description=excluded.description,
                        summary=excluded.summary,
                        authors=excluded.authors,
                        published=excluded.published,
                        thumbnail=excluded.thumbnail,
                        categories=excluded.categories,
                        keywords=excluded.keywords,
                        importance_score=excluded.importance_score,
                        channel=excluded.channel,
                        raw_data=excluded.raw_data,
                        processed_at=excluded.processed_at,
                        last_fetched_at=excluded.last_fetched_at
                    """, db_item)
                except sqlite3.IntegrityError as e:
                    logger.error(f"Integrity error for item {item.get('id', 'N/A')} (URL: {item.get('url', 'N/A')}): {e}")
                except Exception as e:
                    logger.error(f"Failed to insert/update item {item.get('id', 'N/A')}: {e}")

        conn.commit()
        conn.close()
        logger.info("Data refresh process completed and data saved to DB.")
        return {"status": "success", "timestamp": raw_data_collection['timestamp']}

    def get_latest_data_summary(self):
        """Get summary of the latest data in the database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(processed_at) as last_update FROM items")
        row = cursor.fetchone()
        conn.close()
        if row and row['last_update']:
            return {"timestamp": row['last_update']}
        logger.info("No existing data found in DB summary. Consider initial refresh.")
        return {"timestamp": None}

    def get_data_by_type(self, content_type, limit=20, offset=0, filters=None):
        """
        Get data of a specific content type with optional filters.
        
        Args:
            content_type (str): Type of content (paper, news, video, blog)
            limit (int): Maximum number of items to return
            offset (int): Offset for pagination
            filters (dict): Optional filters (min_importance, topics, etc.)
            
        Returns:
            list: Data items of the specified type
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM items WHERE content_type = ?"
        params = [content_type]

        # Apply filters if provided
        if filters:
            if filters.get("min_importance"):
                query += " AND importance_score >= ?"
                params.append(filters["min_importance"])
            if filters.get("topics"): # Assuming topics is a list of strings
                topic_clauses = []
                for topic in filters["topics"]:
                    topic_clauses.append("categories LIKE ?")
                    params.append(f'%"{topic}"%') # Search for topic within JSON array string
                if topic_clauses:
                    query += " AND (" + " OR ".join(topic_clauses) + ")"

        query += " ORDER BY importance_score DESC, published DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        items = [dict(row) for row in cursor.fetchall()]
        
        # Parse JSON fields back to Python objects
        for item in items:
            if item.get('categories'):
                try:
                    item['categories'] = json.loads(item['categories'])
                except:
                    item['categories'] = []
            if item.get('keywords'):
                try:
                    item['keywords'] = json.loads(item['keywords'])
                except:
                    item['keywords'] = []
        
        conn.close()
        return items

    def search_all_data(self, search_query, limit=20, offset=0, filters=None):
        """
        Search across all data types for matching items.
        
        Args:
            search_query (str): Search query
            limit (int): Maximum number of results to return
            offset (int): Offset for pagination
            filters (dict): Optional filters
            
        Returns:
            list: Matching data items
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        query_param = f"%{search_query.lower()}%"

        query = """
        SELECT * FROM items
        WHERE (LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(keywords) LIKE ? OR LOWER(categories) LIKE ?)
        """
        params = [query_param, query_param, query_param, query_param, query_param]

        if filters:
            if filters.get("min_importance"):
                query += " AND importance_score >= ?"
                params.append(filters["min_importance"])
            if filters.get("sources"): # List of source_types like 'arxiv_papers', 'news_articles'
                source_placeholders = ','.join('?' for _ in filters["sources"])
                query += f" AND source_type IN ({source_placeholders})"
                params.extend(filters["sources"])

        query += " ORDER BY importance_score DESC, published DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        items = [dict(row) for row in cursor.fetchall()]
        
        # Parse JSON fields back to Python objects
        for item in items:
            if item.get('categories'):
                try:
                    item['categories'] = json.loads(item['categories'])
                except:
                    item['categories'] = []
            if item.get('keywords'):
                try:
                    item['keywords'] = json.loads(item['keywords'])
                except:
                    item['keywords'] = []
        
        conn.close()
        return items

    def update_item_flags(self, item_id, bookmarked=None, is_read=None):
        """Update bookmark and read status for an item."""
        conn = get_db_connection()
        cursor = conn.cursor()
        updates = []
        params = []
        
        if bookmarked is not None:
            updates.append("bookmarked = ?")
            params.append(1 if bookmarked else 0)
        if is_read is not None:
            updates.append("is_read = ?")
            params.append(1 if is_read else 0)

        if not updates:
            conn.close()
            return False

        params.append(item_id)
        query = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, tuple(params))
        conn.commit()
        updated_rows = cursor.rowcount > 0
        conn.close()
        return updated_rows

    def get_bookmarked_items(self, limit=50, offset=0):
        """Get all bookmarked items."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM items WHERE bookmarked = 1 ORDER BY importance_score DESC, published DESC LIMIT ? OFFSET ?", (limit, offset))
        items = [dict(row) for row in cursor.fetchall()]
        
        # Parse JSON fields back to Python objects
        for item in items:
            if item.get('categories'):
                try:
                    item['categories'] = json.loads(item['categories'])
                except:
                    item['categories'] = []
            if item.get('keywords'):
                try:
                    item['keywords'] = json.loads(item['keywords'])
                except:
                    item['keywords'] = []
        
        conn.close()
        return items

    # Methods to store/retrieve last fetch metadata for incremental fetching
    def get_source_fetch_metadata(self, source_id):
        """Get metadata about the last successful fetch for a source."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT last_successful_fetch, last_item_id FROM source_metadata WHERE source_id = ?", (source_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_source_fetch_metadata(self, source_id, last_successful_fetch, last_item_id=None):
        """Update metadata about the last successful fetch for a source."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO source_metadata (source_id, last_successful_fetch, last_item_id)
        VALUES (?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            last_successful_fetch=excluded.last_successful_fetch,
            last_item_id=excluded.last_item_id
        """, (source_id, last_successful_fetch, last_item_id))
        conn.commit()
        conn.close()

    # Legacy compatibility methods for existing code
    def get_latest_data(self):
        """Legacy method - returns structured data like the old JSON format."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get latest timestamp
        cursor.execute("SELECT MAX(processed_at) as timestamp FROM items")
        timestamp_row = cursor.fetchone()
        timestamp = timestamp_row['timestamp'] if timestamp_row else get_timestamp()
        
        # Get items by type
        result = {'timestamp': timestamp}
        
        for content_type, key in [('paper', 'arxiv_papers'), ('news', 'news_articles'), 
                                  ('video', 'youtube_videos'), ('blog', 'blog_posts')]:
            items = self.get_data_by_type(content_type, limit=50)
            result[key] = items
            
        return result
    
    def get_data_by_type_legacy(self, data_type, limit=20, sort_by_importance=True):
        """Legacy method for backwards compatibility."""
        type_map = {
            'papers': 'paper',
            'news': 'news', 
            'videos': 'video',
            'blogs': 'blog'
        }
        
        content_type = type_map.get(data_type, data_type)
        return self.get_data_by_type(content_type, limit=limit)