import os
import yaml
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Basic Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
logger = logging.getLogger(__name__)

def get_project_root():
    """Returns the absolute path to the project root directory."""
    return Path(__file__).parent.absolute()

def load_config():
    """Load configuration from config.yaml."""
    config_path = get_project_root() / "config.yaml"
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def load_environment():
    """Load environment variables from .env file."""
    env_path = get_project_root() / ".env"
    load_dotenv(env_path)
    logger.info("Environment variables loaded.")

def get_data_dir():
    """Returns the path to the data directory."""
    data_dir = get_project_root() / "data"
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def save_data(data, filename):
    """Save data to JSON file in the data directory."""
    filepath = get_data_dir() / filename
    with open(filepath, 'w') as file:
        json.dump(data, file)

def load_data(filename, default=None):
    """Load data from JSON file in the data directory."""
    filepath = get_data_dir() / filename
    if not filepath.exists():
        return default if default is not None else {}
    
    with open(filepath, 'r') as file:
        return json.load(file)

def get_timestamp():
    """Returns current timestamp in ISO format."""
    return datetime.now().isoformat()

def truncate_text(text, max_length=200):
    """Truncate text to a maximum length and add ellipsis if needed."""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length] + "..."

# SQLite Database Functions
DB_PATH = get_project_root() / "aifeed.db"

def get_db_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def initialize_db():
    """Initialize the SQLite database with required tables."""
    if DB_PATH.exists():
        # Quick check if tables exist to prevent re-initialization error
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items';")
        if cursor.fetchone():
            logger.info("Database already initialized.")
            conn.close()
            return
        conn.close()

    logger.info("Initializing database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Main items table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id TEXT PRIMARY KEY,
        title TEXT,
        url TEXT UNIQUE,
        source TEXT,
        source_type TEXT, -- e.g., arxiv_papers, news_articles
        content_type TEXT, -- e.g., paper, news, video, blog
        description TEXT,
        summary TEXT,
        authors TEXT, -- For papers
        published TEXT, -- ISO format string
        thumbnail TEXT,
        categories TEXT, -- JSON string list
        keywords TEXT, -- JSON string list
        importance_score INTEGER,
        channel TEXT, -- For YouTube
        raw_data TEXT, -- Store the original JSON blob from source
        processed_at TEXT,
        bookmarked INTEGER DEFAULT 0,
        is_read INTEGER DEFAULT 0,
        last_fetched_at TEXT -- For incremental fetching control
    )
    """)
    
    # Table for storing last fetch timestamps for sources (for incremental loading)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS source_metadata (
        source_id TEXT PRIMARY KEY, -- e.g., 'arxiv_cs.AI', 'openai_blog'
        last_successful_fetch TEXT,
        last_item_id TEXT -- e.g., last arXiv paper ID or RSS entry guid
    )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")