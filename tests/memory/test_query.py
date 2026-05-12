"""
记忆查询引擎测试
"""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from trendradar.persistence.schema import initialize_memory_db
from trendradar.memory.models import (
    MemoryType,
    LinkType,
    Memory,
    MemoryLink,
    MemoryRepository
)
from trendradar.memory.storage.database import DatabaseBackend
from trendradar.memory.query import MemoryQueryEngine


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    yield db_path

    # 清理
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def initialized_db(temp_db):
    """初始化数据库表结构"""
    conn = initialize_memory_db(temp_db)
    conn.close()
    return temp_db


@pytest.fixture
def query_engine(initialized_db):
    """创建查询引擎实例"""
    return MemoryQueryEngine(initialized_db)


@pytest.fixture
def sample_memories(initialized_db):
    """创建样本记忆数据"""
    backend = DatabaseBackend(initialized_db)
    repo = MemoryRepository(backend)
    base_time = datetime.now()

    memories = []

    # 创建每日摘要（过去7天）
    for i in range(7):
        date = base_time - timedelta(days=i)
        memory = Memory(
            id=f'daily-{i}',
            type=MemoryType.DAILY_SUMMARY,
            title=f'每日摘要 - Day {i}',
            description=f'第 {i} 天的摘要',
            content=f'AI技术发展迅速，关键词包括人工智能、机器学习。Day {i}',
            metadata={
                'date': date.strftime('%Y-%m-%d'),
                'news_count': 100 + i * 10,
                'top_keywords': ['AI', '人工智能', '机器学习']
            },
            created_at=date,
            updated_at=date
        )
        repo.create(memory)
        memories.append(memory)

    # 创建每周摘要
    week_memory = Memory(
        id='weekly-1',
        type=MemoryType.WEEKLY_DIGEST,
        title='每周摘要 - Week 1',
        description='本周摘要',
        content='本周AI领域重要进展包括...',
        metadata={
            'start_date': (base_time - timedelta(days=6)).strftime('%Y-%m-%d'),
            'end_date': base_time.strftime('%Y-%m-%d')
        },
        created_at=base_time,
        updated_at=base_time
    )
    repo.create(week_memory)
    memories.append(week_memory)

    # 创建主题洞察
    topic_memory = Memory(
        id='topic-1',
        type=MemoryType.TOPIC_INSIGHT,
        title='AI伦理主题洞察',
        description='关于AI伦理的深度分析',
        content='人工智能伦理问题日益重要，涉及隐私、安全等方面。',
        metadata={
            'topic': 'AI伦理',
            'keywords': ['AI伦理', '隐私', '安全']
        },
        created_at=base_time - timedelta(days=2),
        updated_at=base_time - timedelta(days=2)
    )
    repo.create(topic_memory)
    memories.append(topic_memory)

    # 创建记忆链接
    link = MemoryLink(
        from_memory_id='weekly-1',
        to_memory_id='daily-0',
        link_type=LinkType.DERIVES_FROM,
        notes='基于每日数据生成',
        created_at=base_time
    )
    repo.create_link(link)

    link2 = MemoryLink(
        from_memory_id='topic-1',
        to_memory_id='daily-2',
        link_type=LinkType.EXTENDS,
        notes='扩展了每日观察',
        created_at=base_time - timedelta(days=2)
    )
    repo.create_link(link2)

    return initialized_db


@pytest.fixture
def sample_keywords(initialized_db):
    """创建样本关键词数据"""
    conn = sqlite3.connect(initialized_db)
    cursor = conn.cursor()

    base_date = datetime.now()

    # 创建关键词趋势数据（过去7天）
    keywords_data = [
        ('AI', 100),
        ('人工智能', 85),
        ('机器学习', 70),
        ('深度学习', 60),
        ('大模型', 55)
    ]

    for i in range(7):
        date_str = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
        for keyword, base_count in keywords_data:
            count = base_count + i * 5
            cursor.execute("""
                INSERT INTO keyword_trends (date, keyword, count, platforms, rank)
                VALUES (?, ?, ?, ?, ?)
            """, (date_str, keyword, count, '["weibo", "zhihu"]', None))

    conn.commit()
    conn.close()

    return initialized_db


class TestMemoryQueryEngine:
    """MemoryQueryEngine 基础测试"""

    def test_init(self, initialized_db):
        """测试初始化"""
        engine = MemoryQueryEngine(initialized_db)
        assert engine.db_path == initialized_db
        assert engine.repository is not None

    def test_search_memories_by_keyword(self, query_engine, sample_memories):
        """测试按关键词搜索记忆"""
        results = query_engine.search_memories(keyword='AI')

        assert len(results) > 0
        # 验证所有结果都包含关键词
        for memory in results:
            assert 'AI' in memory.title or 'AI' in memory.content

    def test_search_memories_by_type(self, query_engine, sample_memories):
        """测试按类型搜索记忆"""
        results = query_engine.search_memories(memory_type=MemoryType.DAILY_SUMMARY)

        assert len(results) == 7
        assert all(m.type == MemoryType.DAILY_SUMMARY for m in results)

    def test_search_memories_by_date_range(self, query_engine, sample_memories):
        """测试按日期范围搜索记忆"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        results = query_engine.search_memories(
            start_date=start_date,
            end_date=end_date
        )

        assert len(results) > 0
        # 验证所有结果都在日期范围内
        for memory in results:
            assert start_date <= memory.created_at <= end_date

    def test_search_memories_combined_filters(self, query_engine, sample_memories):
        """测试组合过滤条件搜索"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)

        results = query_engine.search_memories(
            keyword='AI',
            memory_type=MemoryType.DAILY_SUMMARY,
            start_date=start_date,
            end_date=end_date
        )

        assert len(results) > 0
        for memory in results:
            assert memory.type == MemoryType.DAILY_SUMMARY
            assert 'AI' in memory.title or 'AI' in memory.content
            assert start_date <= memory.created_at <= end_date

    def test_search_memories_with_limit(self, query_engine, sample_memories):
        """测试限制返回数量"""
        results = query_engine.search_memories(
            memory_type=MemoryType.DAILY_SUMMARY,
            limit=3
        )

        assert len(results) == 3

    def test_search_memories_no_results(self, query_engine, sample_memories):
        """测试无结果的搜索"""
        results = query_engine.search_memories(keyword='不存在的关键词xyz123')
        assert len(results) == 0


class TestKeywordTrend:
    """关键词趋势查询测试"""

    def test_get_keyword_trend(self, query_engine, sample_keywords):
        """测试获取关键词趋势"""
        trend = query_engine.get_keyword_trend('AI', days=7)

        assert len(trend) == 7
        # 验证按日期升序排列
        for i in range(len(trend) - 1):
            assert trend[i]['date'] <= trend[i + 1]['date']

        # 验证数据结构
        assert 'date' in trend[0]
        assert 'keyword' in trend[0]
        assert 'count' in trend[0]
        assert 'platforms' in trend[0]

    def test_get_keyword_trend_limited_days(self, query_engine, sample_keywords):
        """测试限制天数的趋势查询"""
        trend = query_engine.get_keyword_trend('AI', days=3)
        assert len(trend) == 3

    def test_get_keyword_trend_nonexistent(self, query_engine, sample_keywords):
        """测试查询不存在的关键词"""
        trend = query_engine.get_keyword_trend('不存在关键词', days=7)
        assert len(trend) == 0


class TestMemoriesByDateRange:
    """日期范围查询测试"""

    def test_get_memories_by_date_range(self, query_engine, sample_memories):
        """测试按日期范围获取记忆"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        results = query_engine.get_memories_by_date_range(start_date, end_date)

        assert len(results) > 0
        for memory in results:
            assert start_date <= memory.created_at <= end_date

    def test_get_memories_by_date_range_with_type(self, query_engine, sample_memories):
        """测试按日期范围和类型获取记忆"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)

        results = query_engine.get_memories_by_date_range(
            start_date,
            end_date,
            memory_type=MemoryType.DAILY_SUMMARY
        )

        assert len(results) > 0
        assert all(m.type == MemoryType.DAILY_SUMMARY for m in results)


class TestRelatedMemories:
    """关联记忆查询测试"""

    def test_get_related_memories_outgoing(self, query_engine, sample_memories):
        """测试获取外向关联记忆"""
        results = query_engine.get_related_memories('weekly-1')

        assert len(results) > 0
        # 验证返回结果包含链接信息
        assert any(r['memory'].id == 'daily-0' for r in results)

        # 验证数据结构
        for result in results:
            assert 'memory' in result
            assert 'link_type' in result
            assert 'direction' in result
            assert result['direction'] in ['outgoing', 'incoming']

    def test_get_related_memories_incoming(self, query_engine, sample_memories):
        """测试获取入向关联记忆"""
        results = query_engine.get_related_memories('daily-0')

        assert len(results) > 0
        # 应该能找到 weekly-1
        assert any(r['memory'].id == 'weekly-1' for r in results)

    def test_get_related_memories_by_link_type(self, query_engine, sample_memories):
        """测试按链接类型筛选"""
        results = query_engine.get_related_memories(
            'weekly-1',
            link_type=LinkType.DERIVES_FROM
        )

        assert len(results) > 0
        assert all(r['link_type'] == LinkType.DERIVES_FROM for r in results)

    def test_get_related_memories_nonexistent(self, query_engine, sample_memories):
        """测试查询不存在的记忆的关联"""
        results = query_engine.get_related_memories('nonexistent-id')
        assert len(results) == 0


class TestTopKeywordsByDate:
    """每日 Top 关键词查询测试"""

    def test_get_top_keywords_by_date(self, query_engine, sample_keywords):
        """测试获取指定日期的 Top 关键词"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        results = query_engine.get_top_keywords_by_date(date_str, limit=3)

        assert len(results) == 3
        # 验证按 count 降序排列
        for i in range(len(results) - 1):
            assert results[i]['count'] >= results[i + 1]['count']

        # 验证数据结构
        assert 'keyword' in results[0]
        assert 'count' in results[0]
        assert 'platforms' in results[0]

    def test_get_top_keywords_by_date_default_limit(self, query_engine, sample_keywords):
        """测试默认限制数量"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        results = query_engine.get_top_keywords_by_date(date_str)

        assert len(results) == 5  # 默认返回5个

    def test_get_top_keywords_by_date_no_data(self, query_engine, sample_keywords):
        """测试查询无数据的日期"""
        future_date = (datetime.now() + timedelta(days=100)).strftime('%Y-%m-%d')
        results = query_engine.get_top_keywords_by_date(future_date)
        assert len(results) == 0


class TestAdvancedQueries:
    """高级查询功能测试"""

    def test_search_memories_ordering(self, query_engine, sample_memories):
        """测试搜索结果按创建时间倒序排列"""
        results = query_engine.search_memories(memory_type=MemoryType.DAILY_SUMMARY)

        assert len(results) > 1
        # 验证倒序排列（最新的在前）
        for i in range(len(results) - 1):
            assert results[i].created_at >= results[i + 1].created_at

    def test_get_related_memories_with_notes(self, query_engine, sample_memories):
        """测试关联记忆包含备注信息"""
        results = query_engine.get_related_memories('weekly-1')

        assert len(results) > 0
        # 验证包含 notes
        for result in results:
            assert 'notes' in result
