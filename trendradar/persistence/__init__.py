"""
持久化模块

提供 AI 分析、记忆、关键词统计等数据的存储和检索功能。
"""

from trendradar.persistence.schema import (
    load_schema_file,
    initialize_ai_analysis_tables,
    initialize_memory_db,
    ensure_matched_keywords_column
)
from trendradar.persistence.ai_storage import AIAnalysisStorage
from trendradar.persistence.keyword_stats import KeywordStatsManager

__all__ = [
    'load_schema_file',
    'initialize_ai_analysis_tables',
    'initialize_memory_db',
    'ensure_matched_keywords_column',
    'AIAnalysisStorage',
    'KeywordStatsManager',
]
