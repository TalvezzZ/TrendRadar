"""
End-to-end integration tests for the memory and persistence system.

Tests the complete flow from data storage to memory generation and querying.
"""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from trendradar.persistence.schema import (
    initialize_ai_analysis_tables,
    initialize_memory_db,
)
from trendradar.persistence.ai_storage import AIAnalysisStorage
from trendradar.persistence.keyword_stats import KeywordStatsManager
from trendradar.memory.models import MemoryRepository, MemoryType, LinkType, Memory, MemoryLink
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
def integrated_db(temp_db):
    """创建完整的集成数据库"""
    # 初始化记忆表
    conn = initialize_memory_db(temp_db)

    # 初始化 AI 分析表
    initialize_ai_analysis_tables(conn)

    conn.close()
    return temp_db


class TestEndToEndPersistence:
    """端到端持久化测试"""

    def test_ai_analysis_storage_workflow(self, integrated_db):
        """
        测试 AI 分析存储工作流:
        1. 保存 AI 分析结果
        2. 保存分析板块
        3. 查询分析结果
        4. 验证数据完整性
        """
        # 1. 保存 AI 分析结果
        ai_storage = AIAnalysisStorage(integrated_db)

        analysis_time = datetime.now().isoformat()
        analysis_data = {
            'analysis_time': analysis_time,
            'report_mode': 'daily',
            'news_count': 15,
            'rss_count': 3,
            'matched_keywords': ['AI', '人工智能', 'GPT'],
            'platforms': ['weibo', 'zhihu', 'douyin'],
            'full_result': {
                'core_trends': '人工智能技术持续突破',
                'sentiment': '积极正面',
                'key_points': ['GPT-5发布', 'AI芯片创新']
            }
        }

        analysis_id = ai_storage.save_analysis_result(analysis_data)
        assert analysis_id > 0

        # 2. 保存分析板块
        sections = {
            'core_trends': '核心趋势: AI发展迅速',
            'sentiment_controversy': '舆情: 整体积极',
            'signals': '信号: 技术突破'
        }
        ai_storage.save_analysis_sections(analysis_id, sections)

        # 3. 查询分析结果
        retrieved = ai_storage.get_analysis_by_id(analysis_id)
        assert retrieved is not None
        assert retrieved['analysis_time'] == analysis_time
        assert retrieved['report_mode'] == 'daily'
        assert retrieved['news_count'] == 15

        # 4. 查询分析板块
        retrieved_sections = ai_storage.get_sections_by_analysis_id(analysis_id)
        assert retrieved_sections == sections

    def test_memory_storage_workflow(self, integrated_db):
        """
        测试记忆存储工作流:
        1. 创建记忆
        2. 查询记忆
        3. 搜索记忆
        """
        repo = MemoryRepository(integrated_db)

        # 1. 创建记忆
        memory = Memory(
            id='mem_test_001',
            type=MemoryType.DAILY_SUMMARY,
            title='AI技术突破',
            content='人工智能技术持续突破，GPT-5发布',
            created_at=datetime.now(),
            updated_at=datetime.now(),
            description='每日AI技术总结',
            metadata={'keywords': ['AI', 'GPT'], 'source': 'daily_analysis'}
        )
        repo.create(memory)

        # 2. 查询记忆
        retrieved_memory = repo.get_by_id(memory.id)
        assert retrieved_memory is not None
        assert retrieved_memory.type == MemoryType.DAILY_SUMMARY
        assert retrieved_memory.title == 'AI技术突破'

        # 3. 搜索记忆
        query_engine = MemoryQueryEngine(integrated_db)
        search_results = query_engine.search_memories(
            keyword='GPT',
            memory_type=MemoryType.DAILY_SUMMARY
        )
        assert len(search_results) >= 1

    def test_memory_linking(self, integrated_db):
        """
        测试记忆链接功能:
        1. 创建两个记忆
        2. 创建链接
        3. 验证记忆可以被检索
        """
        repo = MemoryRepository(integrated_db)

        # 1. 创建第一个记忆
        memory1 = Memory(
            id='mem_link_001',
            type=MemoryType.SIGNAL,
            title='GPT-5发布信号',
            content='GPT-5正式发布',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        repo.create(memory1)

        # 创建第二个记忆
        memory2 = Memory(
            id='mem_link_002',
            type=MemoryType.TOPIC_INSIGHT,
            title='AI热度上升',
            content='AI相关话题热度显著上升',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        repo.create(memory2)

        # 2. 创建链接
        link = MemoryLink(
            from_memory_id=memory1.id,
            to_memory_id=memory2.id,
            link_type=LinkType.SUPPORTS,
            created_at=datetime.now(),
            notes='发布事件导致热度上升'
        )
        repo.create_link(link)

        # 3. 验证两个记忆都可以被检索
        retrieved1 = repo.get_by_id(memory1.id)
        assert retrieved1 is not None

        retrieved2 = repo.get_by_id(memory2.id)
        assert retrieved2 is not None

    def test_keyword_stats_workflow(self, integrated_db):
        """
        测试关键词统计工作流:
        1. 更新关键词统计
        2. 验证数据被保存
        """
        conn = sqlite3.connect(integrated_db)
        stats_manager = KeywordStatsManager(conn)

        # 1. 更新关键词统计
        test_date = '2026-04-25'
        keyword_data = {
            'date': test_date,
            'keyword': 'AI',
            'count': 100,
            'platforms': ['weibo', 'zhihu'],
            'rank': 1
        }
        stats_manager.update_keyword_stat(keyword_data)
        conn.commit()

        # 2. 验证数据被保存 - 直接查询数据库
        cursor = conn.execute(
            "SELECT * FROM keyword_trends WHERE keyword = ? AND date = ?",
            ('AI', test_date)
        )
        row = cursor.fetchone()
        assert row is not None

        conn.close()

    def test_integrated_workflow(self, integrated_db):
        """
        测试集成工作流:
        1. 保存 AI 分析
        2. 基于分析创建记忆
        3. 记录关键词统计
        4. 验证数据关联
        """
        # 1. 保存 AI 分析
        ai_storage = AIAnalysisStorage(integrated_db)
        analysis_time = datetime.now().isoformat()
        analysis_data = {
            'analysis_time': analysis_time,
            'report_mode': 'daily',
            'news_count': 20,
            'rss_count': 5,
            'matched_keywords': ['AI', '技术'],
            'platforms': ['weibo'],
            'full_result': {'summary': '每日科技新闻总结'}
        }
        analysis_id = ai_storage.save_analysis_result(analysis_data)

        # 2. 基于分析创建记忆
        repo = MemoryRepository(integrated_db)
        memory = Memory(
            id=f'mem_integrated_{analysis_id}',
            type=MemoryType.DAILY_SUMMARY,
            title=f'Daily Summary {analysis_time[:10]}',
            content='每日科技新闻总结',
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={'analysis_id': analysis_id}
        )
        repo.create(memory)

        # 3. 记录关键词统计
        conn = sqlite3.connect(integrated_db)
        stats_manager = KeywordStatsManager(conn)
        for keyword in analysis_data['matched_keywords']:
            stats_manager.update_keyword_stat({
                'date': analysis_time[:10],
                'keyword': keyword,
                'count': 10,
                'platforms': analysis_data['platforms']
            })
        conn.commit()

        # 4. 验证数据关联
        # 验证分析存在
        retrieved_analysis = ai_storage.get_analysis_by_id(analysis_id)
        assert retrieved_analysis is not None

        # 验证记忆存在并关联分析
        retrieved_memory = repo.get_by_id(memory.id)
        assert retrieved_memory is not None
        assert retrieved_memory.metadata['analysis_id'] == analysis_id

        # 验证关键词统计存在 - 直接查询数据库
        cursor = conn.execute(
            "SELECT * FROM keyword_trends WHERE keyword = ?",
            ('AI',)
        )
        rows = cursor.fetchall()
        assert len(rows) >= 1

        conn.close()

    def test_time_range_queries(self, integrated_db):
        """
        测试时间范围查询:
        1. 创建多个时间点的记忆
        2. 按时间范围查询
        """
        repo = MemoryRepository(integrated_db)

        # 1. 创建多个记忆
        base_time = datetime.now()
        for i in range(3):
            memory = Memory(
                id=f'mem_time_{i}',
                type=MemoryType.DAILY_SUMMARY,
                title=f'Summary {i}',
                content=f'Content {i}',
                created_at=base_time + timedelta(hours=i),
                updated_at=base_time + timedelta(hours=i)
            )
            repo.create(memory)

        # 2. 按时间范围查询
        start_time = base_time - timedelta(hours=1)
        end_time = base_time + timedelta(hours=5)

        memories = repo.get_by_date_range(
            start_date=start_time,
            end_date=end_time
        )
        assert len(memories) >= 3

    def test_error_handling(self, integrated_db):
        """
        测试错误处理:
        1. 查询不存在的记忆
        2. 查询不存在的分析
        """
        repo = MemoryRepository(integrated_db)
        ai_storage = AIAnalysisStorage(integrated_db)

        # 1. 查询不存在的记忆
        non_existent = repo.get_by_id('nonexistent_id')
        assert non_existent is None

        # 2. 查询不存在的分析
        non_existent_analysis = ai_storage.get_analysis_by_id(99999)
        assert non_existent_analysis is None

    def test_data_consistency(self, integrated_db):
        """
        测试数据一致性:
        1. 保存数据
        2. 多次查询验证一致性
        """
        ai_storage = AIAnalysisStorage(integrated_db)

        # 保存初始数据
        analysis_time = datetime.now().isoformat()
        analysis_data = {
            'analysis_time': analysis_time,
            'report_mode': 'daily',
            'news_count': 20,
            'rss_count': 5,
            'matched_keywords': ['测试'],
            'platforms': ['weibo'],
            'full_result': {'test': 'data'}
        }

        analysis_id = ai_storage.save_analysis_result(analysis_data)

        # 多次查询验证数据一致性
        for _ in range(3):
            result = ai_storage.get_analysis_by_id(analysis_id)
            assert result is not None
            assert result['news_count'] == 20
            assert result['rss_count'] == 5
            assert result['matched_keywords'] == ['测试']
