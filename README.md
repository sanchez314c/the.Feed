# AIFEED - AI Intelligence Dashboard

<p align="center">
  <img src="https://raw.githubusercontent.com/YourUsername/Github/main/.images/the.feed.png" alt="The Feed Hero" width="600" />
</p>

AIFEED is a comprehensive dashboard for tracking the latest developments in artificial intelligence. It aggregates content from multiple sources, analyzes it using Claude, and presents it in an easy-to-navigate interface.

## Features

- **Multi-source Aggregation**: Collect content from arXiv papers, news sites, YouTube channels, and company blogs
- **AI-powered Analysis**: Uses Claude to summarize content, categorize it, and assign importance scores
- **Intuitive Dashboard**: Clean, card-based interface with filtering options
- **Searchable Content**: Full-text search across all sources
- **Customizable Sources**: Easy configuration through YAML file

## Setup

### Prerequisites

- Python 3.8+
- Anthropic API key
- Optional: News API key, YouTube API key

### Installation

1. Clone this repository:
   ```
   git clone https://your-repo-url/AIFEED.git
   cd AIFEED
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your API keys:
   ```
   cp .env.example .env
   ```
   Then edit `.env` with your API keys.

## Usage

1. Start the dashboard:
   ```
   streamlit run app.py
   ```

2. Use the sidebar to:
   - Refresh data from sources
   - Filter content by source, topic, or importance
   - Search across all content

3. Navigate between tabs to view different content types:
   - Research Papers
   - News Articles
   - YouTube Videos
   - Blog Posts

## Configuration

Edit `config.yaml` to customize sources:

- **arXiv**: Set categories to track
- **News**: Define keywords to search for
- **YouTube**: Add channel IDs and keywords
- **Blogs**: Configure RSS feed URLs

Example:
```yaml
sources:
  arxiv:
    enabled: true
    categories:
      - cs.AI
      - cs.CL
    max_results: 10
```

## Data Storage

All data is stored locally in JSON files:
- `processed_data.json`: Most recent processed content
- `raw_data.json`: Raw data from sources
- `history.json`: Historical archive of content

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.