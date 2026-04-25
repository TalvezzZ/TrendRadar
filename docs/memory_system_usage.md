# TrendRadar Memory System Usage Guide

## Overview

The TrendRadar Memory System provides intelligent data persistence and retrieval capabilities for AI analysis results, keyword statistics, and generated memories. This document describes how to use the system effectively.

## Architecture

The memory system consists of three main components:

1. **Persistence Layer** - Stores AI analysis results and keyword statistics
2. **Memory Layer** - Manages intelligent memories and their relationships
3. **Query Layer** - Provides advanced search and retrieval capabilities

## Database Schema

### AI Analysis Tables

- `ai_analysis_results` - Stores complete AI analysis results
- `ai_analysis_sections` - Stores individual analysis sections (core_trends, sentiment, signals, etc.)

### Memory Tables

- `memories` - Stores memory records with metadata
- `memory_links` - Stores relationships between memories

### Keyword Statistics Tables

- `keyword_trends` - Tracks keyword popularity over time

## Usage Examples

### 1. Storing AI Analysis Results

```python
from trendradar.persistence.ai_storage import AIAnalysisStorage

# Initialize storage
ai_storage = AIAnalysisStorage('path/to/database.db')

# Prepare analysis data
analysis_data = {
    'analysis_time': '2026-04-25T12:00:00',
    'report_mode': 'daily',
    'news_count': 20,
    'rss_count': 5,
    'matched_keywords': ['AI', '人工智能'],
    'platforms': ['weibo', 'zhihu'],
    'full_result': {
        'core_trends': '...',
        'sentiment': '...'
    }
}

# Save analysis
analysis_id = ai_storage.save_analysis_result(analysis_data)

# Save analysis sections
sections = {
    'core_trends': '核心趋势内容...',
    'sentiment_controversy': '舆情分析...',
    'signals': '信号检测...'
}
ai_storage.save_analysis_sections(analysis_id, sections)

# Retrieve analysis
retrieved = ai_storage.get_analysis_by_id(analysis_id)
retrieved_sections = ai_storage.get_sections_by_analysis_id(analysis_id)

# Query by time range
analyses = ai_storage.get_analysis_by_time_range(
    '2026-04-20T00:00:00',
    '2026-04-25T23:59:59'
)
```

### 2. Managing Memories

```python
from datetime import datetime
from trendradar.memory.models import Memory, MemoryRepository, MemoryType

# Initialize repository
repo = MemoryRepository('path/to/database.db')

# Create a memory
memory = Memory(
    id='mem_001',
    type=MemoryType.DAILY_SUMMARY,
    title='AI技术突破',
    content='GPT-5发布带来重大技术突破',
    created_at=datetime.now(),
    updated_at=datetime.now(),
    description='每日AI技术总结',
    metadata={'keywords': ['AI', 'GPT'], 'source': 'daily_analysis'}
)

repo.create(memory)

# Retrieve memory
retrieved = repo.get_by_id('mem_001')

# Query by type
daily_memories = repo.get_by_type(MemoryType.DAILY_SUMMARY, limit=10)

# Query by date range
from datetime import timedelta
start_date = datetime.now() - timedelta(days=7)
end_date = datetime.now()
recent_memories = repo.get_by_date_range(start_date, end_date)

# Update memory
updated_memory = Memory(
    id=memory.id,
    type=memory.type,
    title='AI技术重大突破',  # Updated title
    content=memory.content,
    created_at=memory.created_at,
    updated_at=datetime.now(),
    metadata=memory.metadata
)
repo.update(updated_memory)

# Delete memory
repo.delete('mem_001')
```

### 3. Linking Memories

```python
from trendradar.memory.models import MemoryLink, LinkType

# Create two memories
memory1 = Memory(
    id='mem_event_001',
    type=MemoryType.SIGNAL,
    title='GPT-5发布',
    content='...',
    created_at=datetime.now(),
    updated_at=datetime.now()
)

memory2 = Memory(
    id='mem_insight_001',
    type=MemoryType.TOPIC_INSIGHT,
    title='AI讨论热度上升',
    content='...',
    created_at=datetime.now(),
    updated_at=datetime.now()
)

repo.create(memory1)
repo.create(memory2)

# Create link between memories
link = MemoryLink(
    from_memory_id='mem_event_001',
    to_memory_id='mem_insight_001',
    link_type=LinkType.SUPPORTS,
    created_at=datetime.now(),
    notes='发布事件导致讨论热度上升'
)

repo.create_link(link)

# Query links
outgoing_links = repo.get_links_from('mem_event_001')
incoming_links = repo.get_links_to('mem_insight_001')

# Delete link
repo.delete_link('mem_event_001', 'mem_insight_001')
```

### 4. Searching Memories

```python
from trendradar.memory.query import MemoryQueryEngine

# Initialize query engine
query_engine = MemoryQueryEngine('path/to/database.db')

# Search by keyword
memories = query_engine.search_memories(keyword='GPT')

# Search by type
daily_summaries = query_engine.search_memories(
    memory_type=MemoryType.DAILY_SUMMARY
)

# Search by date range
from datetime import datetime, timedelta
start_date = datetime.now() - timedelta(days=7)
end_date = datetime.now()

recent_memories = query_engine.search_memories(
    start_date=start_date,
    end_date=end_date
)

# Combined search with limit
ai_summaries = query_engine.search_memories(
    keyword='AI',
    memory_type=MemoryType.DAILY_SUMMARY,
    start_date=start_date,
    end_date=end_date,
    limit=10
)

# Get related memories
related = query_engine.get_related_memories(
    'mem_001',
    direction='outgoing'  # or 'incoming'
)

# Get keyword trends
keyword_trend = query_engine.get_keyword_trend('AI', days=30)

# Get top keywords by date
top_keywords = query_engine.get_top_keywords_by_date(
    '2026-04-25',
    limit=10
)
```

### 5. Managing Keyword Statistics

```python
import sqlite3
from trendradar.persistence.keyword_stats import KeywordStatsManager

# Initialize manager
conn = sqlite3.connect('path/to/database.db')
stats_manager = KeywordStatsManager(conn)

# Update single keyword
keyword_data = {
    'date': '2026-04-25',
    'keyword': 'AI',
    'count': 100,
    'platforms': ['weibo', 'zhihu'],
    'rank': 1
}
stats_manager.update_keyword_stat(keyword_data)

# Batch update
keywords_data = [
    {'date': '2026-04-25', 'keyword': 'AI', 'count': 100, 'platforms': ['weibo']},
    {'date': '2026-04-25', 'keyword': 'GPT', 'count': 50, 'platforms': ['zhihu']},
]
stats_manager.batch_update_keywords(keywords_data)

conn.commit()

# Query keyword trend
trend = stats_manager.get_keyword_trend('AI', days=7)
# Returns: [{'date': '...', 'keyword': 'AI', 'count': ..., 'platforms': [...], 'rank': ...}, ...]

# Get top keywords by date
top_keywords = stats_manager.get_top_keywords_by_date('2026-04-25', limit=10)

# Get keywords in date range
keywords = stats_manager.get_keywords_by_date_range(
    '2026-04-20',
    '2026-04-25',
    limit=100
)

conn.close()
```

### 6. Generating Memories from Analysis (Advanced)

```python
from trendradar.memory.generator import MemoryGenerator

# Initialize generator with AI config
ai_config = {
    'api_key': 'your-api-key',
    'model': 'gpt-4',
    # ... other AI configuration
}

generator = MemoryGenerator('path/to/database.db', ai_config)

# Generate daily summary
memory_id = generator.generate_daily_summary('2026-04-25')

# Generate weekly digest
memory_id = generator.generate_weekly_digest('2026-04-25')

# The generator will:
# 1. Gather analysis data from the database
# 2. Use AI to create intelligent summaries
# 3. Store memories with proper metadata
# 4. Create links between related memories
```

## Memory Types

The system supports the following memory types:

- `DAILY_SUMMARY` - Daily news and trend summaries
- `WEEKLY_DIGEST` - Weekly aggregated insights
- `TOPIC_INSIGHT` - Deep insights on specific topics
- `PATTERN` - Identified patterns and trends
- `SIGNAL` - Important signals and events

## Link Types

Memories can be linked using the following relationship types:

- `SUPPORTS` - One memory supports or provides evidence for another
- `CONTRADICTS` - Memories contain contradictory information
- `EXTENDS` - One memory extends or adds detail to another
- `DERIVES_FROM` - One memory is derived from another

## Best Practices

### 1. Database Initialization

Always initialize the database schema before first use:

```python
from trendradar.persistence.schema import initialize_memory_db, initialize_ai_analysis_tables
import sqlite3

# Initialize memory database
conn = initialize_memory_db('path/to/database.db')

# Initialize AI analysis tables
initialize_ai_analysis_tables(conn)

conn.close()
```

### 2. Error Handling

Always wrap database operations in try-except blocks:

```python
try:
    analysis_id = ai_storage.save_analysis_result(analysis_data)
except sqlite3.IntegrityError as e:
    print(f"Duplicate analysis time: {e}")
except Exception as e:
    print(f"Error saving analysis: {e}")
```

### 3. Memory IDs

Use consistent, meaningful ID patterns:

- Daily summaries: `mem_daily_YYYY-MM-DD`
- Weekly digests: `mem_weekly_YYYY-WW`
- Topic insights: `mem_topic_<topic_name>_<timestamp>`

### 4. Metadata

Store additional context in metadata:

```python
metadata = {
    'source': 'daily_analysis',
    'analysis_id': 123,
    'keywords': ['AI', 'GPT'],
    'confidence': 0.95,
    'version': '1.0'
}
```

### 5. Connection Management

For keyword statistics operations, remember to commit:

```python
conn = sqlite3.connect('database.db')
stats_manager = KeywordStatsManager(conn)

# Perform updates
stats_manager.update_keyword_stat(data)

# Don't forget to commit!
conn.commit()
conn.close()
```

## Database Location

By default, the memory system uses the following database file:

```
data/memory.db
```

For AI analysis data, it uses:

```
data/trend_radar.db
```

These paths can be configured in your application settings.

## Performance Considerations

1. **Batch Operations**: Use `batch_update_keywords()` for bulk keyword updates
2. **Query Limits**: Always use `limit` parameter for large result sets
3. **Indexes**: The database schema includes indexes on frequently queried fields
4. **Date Ranges**: Narrow date ranges improve query performance

## Troubleshooting

### Common Issues

**1. Database locked error**

Solution: Ensure all connections are properly closed after use.

```python
conn = sqlite3.connect('database.db')
try:
    # Your operations
    pass
finally:
    conn.close()
```

**2. IntegrityError on duplicate ID**

Solution: Check if memory/analysis already exists before creating:

```python
existing = repo.get_by_id('mem_001')
if existing is None:
    repo.create(memory)
```

**3. Memory not found**

Solution: Verify the memory ID and check if it was deleted:

```python
memory = repo.get_by_id('mem_001')
if memory is None:
    print("Memory not found or was deleted")
```

## Testing

The memory system includes comprehensive tests:

```bash
# Run all tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Run specific test module
pytest tests/memory/test_models.py -v
```

## API Reference

For detailed API documentation, see:

- `trendradar/persistence/ai_storage.py` - AI analysis storage
- `trendradar/persistence/keyword_stats.py` - Keyword statistics
- `trendradar/memory/models.py` - Memory data models
- `trendradar/memory/query.py` - Query engine
- `trendradar/memory/generator.py` - Memory generation

## Support

For issues or questions:

1. Check the test files for usage examples
2. Review the inline code documentation
3. Open an issue on the project repository
