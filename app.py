import streamlit as st
import os
import time
from datetime import datetime, timedelta
from utils import load_config, load_environment, get_project_root, logger
from data_manager import DataManager

# Load environment variables and config
load_environment()
config = load_config()

# Setup page config
st.set_page_config(
    page_title=config['ui']['page_title'],
    page_icon=config['ui']['page_icon'],
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize data manager
@st.cache_resource
def get_data_manager():
    return DataManager()

data_manager = get_data_manager()

# Constants for pagination
ITEMS_PER_PAGE = 10

# Initialize session state for pagination
def init_session_state():
    """Initialize session state variables for pagination and other features."""
    if 'current_page_papers' not in st.session_state:
        st.session_state.current_page_papers = 0
    if 'current_page_news' not in st.session_state:
        st.session_state.current_page_news = 0
    if 'current_page_videos' not in st.session_state:
        st.session_state.current_page_videos = 0
    if 'current_page_blogs' not in st.session_state:
        st.session_state.current_page_blogs = 0
    if 'current_page_search' not in st.session_state:
        st.session_state.current_page_search = 0
    if 'current_page_bookmarks' not in st.session_state:
        st.session_state.current_page_bookmarks = 0

init_session_state()

# Custom CSS
def add_custom_css():
    st.markdown("""
    <style>
        .content-card {
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            background-color: white;
        }
        .card-title {
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 10px;
        }
        .card-metadata {
            color: #888;
            font-size: 12px;
            margin-bottom: 10px;
        }
        .card-summary {
            font-size: 14px;
            margin-bottom: 10px;
            line-height: 1.4;
        }
        .card-categories {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 10px;
        }
        .card-category {
            background-color: #f0f0f0;
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 12px;
        }
        .card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
        }
        .importance-high {
            color: #ff4b4b;
            font-weight: bold;
        }
        .importance-medium {
            color: #ffa64b;
        }
        .importance-low {
            color: #4b4bff;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 5px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            border-radius: 4px;
            padding: 5px 10px;
        }
        .bookmarked-item {
            border-left: 4px solid #ff4b4b;
        }
        .read-item {
            opacity: 0.7;
        }
        .pagination-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 20px 0;
            gap: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

add_custom_css()

# Helper function to display a content card with bookmarking and read status
def display_content_card(item):
    # Format the importance score
    importance_class = "importance-medium"
    if item.get('importance_score', 5) >= 8:
        importance_class = "importance-high"
    elif item.get('importance_score', 5) <= 3:
        importance_class = "importance-low"
    
    # Format date if available
    published_date = ""
    if 'published' in item and item['published']:
        try:
            # Try to parse the date string
            dt = datetime.fromisoformat(item['published'].replace('Z', '+00:00'))
            published_date = dt.strftime("%b %d, %Y")
        except:
            published_date = item.get('published', "")
    
    # Determine image to show
    image_url = item.get('thumbnail') 
    if not image_url:
        # Set a default image based on content type
        content_type = item.get('type', '')
        if content_type == 'paper':
            image_url = "https://placehold.co/160x90/e0f0ff/0066cc?text=Paper"
        elif content_type == 'news':
            image_url = "https://placehold.co/160x90/f0ffe0/336600?text=News"
        elif content_type == 'video':
            image_url = "https://placehold.co/160x90/fff0e0/cc6600?text=Video"
        elif content_type == 'blog':
            image_url = "https://placehold.co/160x90/ffe0f0/cc0066?text=Blog"
        else:
            image_url = "https://placehold.co/160x90/e0e0e0/666666?text=Content"
    
    # Check if item is bookmarked or read
    is_bookmarked = item.get('bookmarked', 0) == 1
    is_read = item.get('is_read', 0) == 1
    
    # Create the card with conditional styling
    card_class = ""
    if is_bookmarked:
        card_class += " bookmarked-item"
    if is_read:
        card_class += " read-item"
    
    with st.container():
        cols = st.columns([1, 3, 1])
        
        # Left column: Image and actions
        with cols[0]:
            st.image(image_url, width=160)
            
            # Display importance score below the image
            st.markdown(f"""
            <div class="{importance_class}" style="text-align: center; margin-top: 5px;">
                Priority: {item.get('importance_score', 5)}/10
            </div>
            """, unsafe_allow_html=True)
            
            # Bookmark and Read status buttons
            col_bookmark, col_read = st.columns(2)
            with col_bookmark:
                bookmark_label = "🔖" if is_bookmarked else "⭐"
                if st.button(bookmark_label, key=f"bookmark_{item['id']}", help="Toggle bookmark"):
                    data_manager.update_item_flags(item['id'], bookmarked=not is_bookmarked)
                    st.rerun()
            
            with col_read:
                read_label = "✅" if is_read else "📖"
                if st.button(read_label, key=f"read_{item['id']}", help="Toggle read status"):
                    data_manager.update_item_flags(item['id'], is_read=not is_read)
                    st.rerun()
        
        # Middle column: Content details
        with cols[1]:
            # Title and metadata
            st.markdown(f"""
            <div class="card-title{card_class}">{item.get('title', 'Untitled')}</div>
            <div class="card-metadata">
                {item.get('source', '')} • {published_date} • 
                {item.get('authors', item.get('author', ''))}
            </div>
            """, unsafe_allow_html=True)
            
            # Summary
            if 'summary' in item:
                st.markdown(f"""
                <div class="card-summary">{item.get('summary', '')}</div>
                """, unsafe_allow_html=True)
            
            # Categories and keywords
            categories_html = ""
            for category in item.get('categories', [])[:3]:
                categories_html += f'<span class="card-category">{category}</span>'
            
            keywords_html = ""
            for keyword in item.get('keywords', [])[:3]:
                keywords_html += f'<span class="card-category">{keyword}</span>'
            
            if categories_html or keywords_html:
                st.markdown(f"""
                <div class="card-categories">
                    {categories_html}
                    {keywords_html}
                </div>
                """, unsafe_allow_html=True)
        
        # Right column: Additional info for videos
        with cols[2]:
            if item.get('type') == 'video':
                if item.get('view_count'):
                    st.metric("Views", f"{int(item['view_count']):,}")
                if item.get('duration'):
                    st.text(f"Duration: {item['duration']}")
            
            # Original link
            if 'url' in item:
                st.markdown(f"[View Original]({item['url']})")
    
    # Add separator
    st.markdown("---")

def display_pagination(current_page, total_items, items_per_page, page_key):
    """Display pagination controls."""
    total_pages = (total_items - 1) // items_per_page + 1 if total_items > 0 else 1
    
    if total_pages > 1:
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if current_page > 0:
                if st.button("⬅️ Previous", key=f"prev_{page_key}"):
                    st.session_state[f'current_page_{page_key}'] -= 1
                    st.rerun()
        
        with col3:
            st.markdown(f"<div style='text-align: center;'>Page {current_page + 1} of {total_pages}</div>", 
                       unsafe_allow_html=True)
        
        with col5:
            if current_page < total_pages - 1:
                if st.button("Next ➡️", key=f"next_{page_key}"):
                    st.session_state[f'current_page_{page_key}'] += 1
                    st.rerun()

# Sidebar
st.sidebar.title("AIFEED")
st.sidebar.markdown("Your AI Intelligence Dashboard")

# Add refresh button to sidebar
if st.sidebar.button(config['ui']['refresh_button_text']):
    with st.sidebar:
        with st.spinner('Refreshing data from all sources...'):
            try:
                result = data_manager.refresh_data()
                if result.get('status') == 'success':
                    st.success('Data refreshed successfully!')
                else:
                    st.error('Data refresh encountered issues. Check logs for details.')
            except Exception as e:
                st.error(f'Error during refresh: {str(e)}')
                logger.error(f"UI refresh error: {e}", exc_info=True)

# Last updated timestamp
data_summary = data_manager.get_latest_data_summary()
if data_summary and data_summary.get('timestamp'):
    try:
        timestamp = datetime.fromisoformat(data_summary['timestamp'].replace('Z', '+00:00'))
        st.sidebar.markdown(f"**Last updated:** {timestamp.strftime('%Y-%m-%d %H:%M')}")
    except Exception as e:
        logger.warning(f"Could not parse timestamp: {data_summary.get('timestamp')}, Error: {e}")
        st.sidebar.markdown(f"**Last updated:** Not available")
else:
    st.sidebar.markdown(f"**Last updated:** Not available (data might be refreshing or empty)")

# Sidebar filters
st.sidebar.markdown("### Filters")

# Date range filter
st.sidebar.markdown("**Date Range**")
date_filter_option = st.sidebar.selectbox(
    "Show content from:",
    ["All time", "Past 24 hours", "Past week", "Past month", "Custom range"]
)

start_date = None
end_date = None
if date_filter_option == "Past 24 hours":
    start_date = datetime.now() - timedelta(days=1)
elif date_filter_option == "Past week":
    start_date = datetime.now() - timedelta(weeks=1)
elif date_filter_option == "Past month":
    start_date = datetime.now() - timedelta(days=30)
elif date_filter_option == "Custom range":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("From", value=datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("To", value=datetime.now())

# Source filter
source_filter = st.sidebar.multiselect(
    "Sources",
    ["arXiv", "News", "YouTube", "Blogs"],
    default=["arXiv", "News", "YouTube", "Blogs"]
)

# Topic filter
topic_filter = st.sidebar.multiselect(
    "Topics",
    ["Research", "Applications", "Business", "Ethics", "Policy", "Tools", "Tutorials", "Hardware", "Theory", "Community"],
    default=[]
)

# Min importance score
min_importance = st.sidebar.slider(
    "Minimum Importance", 
    min_value=1, 
    max_value=10, 
    value=1,
    step=1
)

# Search
search_query = st.sidebar.text_input("Search", "")

# About
st.sidebar.markdown("---")
st.sidebar.markdown("""
### About
AIFEED helps you stay updated with the latest AI developments by aggregating and analyzing content from multiple sources.

Configure sources in `config.yaml`.
""")

# Main content
st.title("AI Intelligence Dashboard")

# Tabs for different content types
tab_papers, tab_news, tab_videos, tab_blogs, tab_bookmarks, tab_search = st.tabs([
    "📄 Research Papers", 
    "📰 News Articles", 
    "🎬 YouTube Videos", 
    "📝 Blog Posts",
    "🔖 Bookmarks",
    "🔍 Search Results"
])

# Function to apply date filters
def apply_date_filter(items, start_date, end_date):
    """Apply date filtering to items."""
    if not start_date and not end_date:
        return items
    
    filtered_items = []
    for item in items:
        try:
            if 'published' in item and item['published']:
                item_date = datetime.fromisoformat(item['published'].replace('Z', '+00:00'))
                
                # Check if item falls within date range
                passes_filter = True
                if start_date and item_date.date() < start_date:
                    passes_filter = False
                if end_date and item_date.date() > end_date:
                    passes_filter = False
                
                if passes_filter:
                    filtered_items.append(item)
            else:
                # Include items without publish date if no date filter
                if not start_date and not end_date:
                    filtered_items.append(item)
        except:
            # Include items with unparseable dates
            filtered_items.append(item)
    
    return filtered_items

# Function to filter items based on sidebar filters
def apply_filters(items):
    filtered_items = []
    
    for item in items:
        # Check source filter
        source = item.get('source', '').lower()
        source_type = item.get('type', '')
        
        passes_source_filter = True
        if "arXiv" not in source_filter and (source == 'arxiv' or source_type == 'paper'):
            passes_source_filter = False
        elif "News" not in source_filter and source_type == 'news':
            passes_source_filter = False
        elif "YouTube" not in source_filter and (source == 'youtube' or source_type == 'video'):
            passes_source_filter = False
        elif "Blogs" not in source_filter and source_type == 'blog':
            passes_source_filter = False
        
        # Check topic filter
        passes_topic_filter = True
        if topic_filter:
            item_categories = [cat.lower() for cat in item.get('categories', [])]
            topic_matches = any(topic.lower() in item_categories for topic in topic_filter)
            if not topic_matches:
                passes_topic_filter = False
        
        # Check importance filter
        passes_importance_filter = True
        if item.get('importance_score', 5) < min_importance:
            passes_importance_filter = False
        
        # Apply all filters
        if passes_source_filter and passes_topic_filter and passes_importance_filter:
            filtered_items.append(item)
    
    # Apply date filters
    if isinstance(start_date, datetime):
        start_date_to_use = start_date.date()
    else:
        start_date_to_use = start_date
        
    if isinstance(end_date, datetime):
        end_date_to_use = end_date.date()
    else:
        end_date_to_use = end_date
    
    filtered_items = apply_date_filter(filtered_items, start_date_to_use, end_date_to_use)
    
    return filtered_items

# Function to get paginated data
def get_paginated_data(data_type, current_page, filters=None):
    """Get paginated data for a specific content type."""
    offset = current_page * ITEMS_PER_PAGE
    
    # Create filters dict for data_manager
    db_filters = {}
    if min_importance > 1:
        db_filters['min_importance'] = min_importance
    if topic_filter:
        db_filters['topics'] = topic_filter
    
    # Get data from database with pagination
    items = data_manager.get_data_by_type(
        data_type, 
        limit=ITEMS_PER_PAGE + 1,  # Get one extra to check if there are more
        offset=offset,
        filters=db_filters
    )
    
    # Apply additional filters that can't be done in DB
    filtered_items = apply_filters(items)
    
    # Check if there are more items
    has_more = len(filtered_items) > ITEMS_PER_PAGE
    if has_more:
        filtered_items = filtered_items[:ITEMS_PER_PAGE]
    
    return filtered_items, has_more

# Display content in each tab
with tab_papers:
    papers, has_more_papers = get_paginated_data('paper', st.session_state.current_page_papers)
    
    if not papers:
        st.info("No research papers match your filters.")
    else:
        st.markdown(f"### Research Papers - Page {st.session_state.current_page_papers + 1}")
        
        for paper in papers:
            display_content_card(paper)
        
        # Pagination controls
        display_pagination(st.session_state.current_page_papers, 
                         len(papers) + (ITEMS_PER_PAGE if has_more_papers else 0), 
                         ITEMS_PER_PAGE, 'papers')

with tab_news:
    news, has_more_news = get_paginated_data('news', st.session_state.current_page_news)
    
    if not news:
        st.info("No news articles match your filters.")
    else:
        st.markdown(f"### News Articles - Page {st.session_state.current_page_news + 1}")
        
        for article in news:
            display_content_card(article)
        
        # Pagination controls
        display_pagination(st.session_state.current_page_news, 
                         len(news) + (ITEMS_PER_PAGE if has_more_news else 0), 
                         ITEMS_PER_PAGE, 'news')

with tab_videos:
    videos, has_more_videos = get_paginated_data('video', st.session_state.current_page_videos)
    
    if not videos:
        st.info("No videos match your filters.")
    else:
        st.markdown(f"### YouTube Videos - Page {st.session_state.current_page_videos + 1}")
        
        for video in videos:
            display_content_card(video)
        
        # Pagination controls
        display_pagination(st.session_state.current_page_videos, 
                         len(videos) + (ITEMS_PER_PAGE if has_more_videos else 0), 
                         ITEMS_PER_PAGE, 'videos')

with tab_blogs:
    blogs, has_more_blogs = get_paginated_data('blog', st.session_state.current_page_blogs)
    
    if not blogs:
        st.info("No blog posts match your filters.")
    else:
        st.markdown(f"### Blog Posts - Page {st.session_state.current_page_blogs + 1}")
        
        for post in blogs:
            display_content_card(post)
        
        # Pagination controls
        display_pagination(st.session_state.current_page_blogs, 
                         len(blogs) + (ITEMS_PER_PAGE if has_more_blogs else 0), 
                         ITEMS_PER_PAGE, 'blogs')

with tab_bookmarks:
    offset_bookmarks = st.session_state.current_page_bookmarks * ITEMS_PER_PAGE
    bookmarked_items = data_manager.get_bookmarked_items(limit=ITEMS_PER_PAGE + 1, offset=offset_bookmarks)
    
    # Apply additional filters
    filtered_bookmarks = apply_filters(bookmarked_items)
    has_more_bookmarks = len(filtered_bookmarks) > ITEMS_PER_PAGE
    if has_more_bookmarks:
        filtered_bookmarks = filtered_bookmarks[:ITEMS_PER_PAGE]
    
    if not filtered_bookmarks:
        st.info("No bookmarked items match your filters.")
    else:
        st.markdown(f"### Bookmarked Items - Page {st.session_state.current_page_bookmarks + 1}")
        
        for item in filtered_bookmarks:
            display_content_card(item)
        
        # Pagination controls
        display_pagination(st.session_state.current_page_bookmarks, 
                         len(filtered_bookmarks) + (ITEMS_PER_PAGE if has_more_bookmarks else 0), 
                         ITEMS_PER_PAGE, 'bookmarks')

with tab_search:
    if search_query:
        with st.spinner('Searching...'):
            offset_search = st.session_state.current_page_search * ITEMS_PER_PAGE
            
            # Create filters dict for search
            search_filters = {}
            if min_importance > 1:
                search_filters['min_importance'] = min_importance
            
            search_results = data_manager.search_all_data(
                search_query, 
                limit=ITEMS_PER_PAGE + 1, 
                offset=offset_search,
                filters=search_filters
            )
            
            # Apply additional filters
            filtered_results = apply_filters(search_results)
            has_more_search = len(filtered_results) > ITEMS_PER_PAGE
            if has_more_search:
                filtered_results = filtered_results[:ITEMS_PER_PAGE]
        
        if not filtered_results:
            st.info(f"No results found for '{search_query}' that match your filters.")
        else:
            st.markdown(f"### Search Results for '{search_query}' - Page {st.session_state.current_page_search + 1}")
            
            for result in filtered_results:
                # Highlight search terms in results
                display_content_card(result)
            
            # Pagination controls
            display_pagination(st.session_state.current_page_search, 
                             len(filtered_results) + (ITEMS_PER_PAGE if has_more_search else 0), 
                             ITEMS_PER_PAGE, 'search')
    else:
        st.info("Enter a search query in the sidebar to find content.")

# Add script to auto-refresh (reduced frequency since we have manual refresh)
st.markdown("""
<script>
    function refreshPage() {
        location.reload();
    }
    // Auto refresh every 60 minutes (60 * 60 * 1000 milliseconds)
    setTimeout(refreshPage, 3600000);
</script>
""", unsafe_allow_html=True)