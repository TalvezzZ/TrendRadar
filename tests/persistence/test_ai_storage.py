"""
AI 分析存储模块测试
"""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from trendradar.persistence.schema import initialize_ai_analysis_tables
from trendradar.persistence.ai_storage import AIAnalysisStorage


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
    conn = sqlite3.connect(temp_db)
    initialize_ai_analysis_tables(conn)
    conn.close()
    return temp_db


@pytest.fixture
def ai_storage(initialized_db):
    """创建 AI 分析存储实例"""
    return AIAnalysisStorage(initialized_db)


class TestSchemaFunctions:
    """Schema 函数测试"""

    def test_initialize_ai_analysis_tables(self, temp_db):
        """测试初始化 AI 分析表"""
        conn = sqlite3.connect(temp_db)
        initialize_ai_analysis_tables(conn)

        # 验证表已创建
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_analysis_results'"
        )
        assert cursor.fetchone() is not None

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_analysis_sections'"
        )
        assert cursor.fetchone() is not None

        conn.close()

    def test_load_schema_file_not_found(self):
        """测试加载不存在的 schema 文件"""
        from trendradar.persistence.schema import load_schema_file

        with pytest.raises(FileNotFoundError):
            load_schema_file('/nonexistent/schema.sql')


class TestAIAnalysisStorage:
    """AI 分析存储测试"""

    def test_save_and_get_analysis(self, ai_storage):
        """测试保存和获取分析结果"""
        # 准备测试数据
        analysis_time = datetime.now().isoformat()
        analysis_data = {
            'analysis_time': analysis_time,
            'report_mode': 'daily',
            'news_count': 10,
            'rss_count': 5,
            'matched_keywords': ['AI', '人工智能'],
            'platforms': ['weibo', 'zhihu'],
            'full_result': {
                'core_trends': 'AI 发展迅速',
                'sentiment': '积极'
            }
        }

        # 保存
        analysis_id = ai_storage.save_analysis_result(analysis_data)
        assert analysis_id > 0

        # 获取
        retrieved = ai_storage.get_analysis_by_id(analysis_id)
        assert retrieved is not None
        assert retrieved['analysis_time'] == analysis_time
        assert retrieved['report_mode'] == 'daily'
        assert retrieved['news_count'] == 10
        assert retrieved['rss_count'] == 5
        assert 'AI' in retrieved['matched_keywords']
        assert 'weibo' in retrieved['platforms']
        assert retrieved['full_result']['core_trends'] == 'AI 发展迅速'

    def test_save_sections(self, ai_storage):
        """测试保存板块内容"""
        # 先保存分析结果
        analysis_time = datetime.now().isoformat()
        analysis_data = {
            'analysis_time': analysis_time,
            'report_mode': 'daily',
            'news_count': 10,
            'rss_count': 5,
            'matched_keywords': [],
            'platforms': [],
            'full_result': {}
        }
        analysis_id = ai_storage.save_analysis_result(analysis_data)

        # 保存板块
        sections = {
            'core_trends': '核心趋势内容',
            'sentiment_controversy': '情感分析内容',
            'signals': '信号内容'
        }
        ai_storage.save_analysis_sections(analysis_id, sections)

        # 验证板块已保存
        conn = sqlite3.connect(ai_storage.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            'SELECT section_type, content FROM ai_analysis_sections WHERE analysis_id = ?',
            (analysis_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 3
        section_dict = {dict(row)['section_type']: dict(row)['content'] for row in rows}
        assert section_dict['core_trends'] == '核心趋势内容'
        assert section_dict['sentiment_controversy'] == '情感分析内容'
        assert section_dict['signals'] == '信号内容'

    def test_get_sections(self, ai_storage):
        """测试获取所有板块"""
        # 准备数据
        analysis_time = datetime.now().isoformat()
        analysis_data = {
            'analysis_time': analysis_time,
            'report_mode': 'daily',
            'news_count': 10,
            'rss_count': 5,
            'matched_keywords': [],
            'platforms': [],
            'full_result': {}
        }
        analysis_id = ai_storage.save_analysis_result(analysis_data)

        sections = {
            'core_trends': '核心趋势内容',
            'signals': '信号内容'
        }
        ai_storage.save_analysis_sections(analysis_id, sections)

        # 获取所有板块
        retrieved_sections = ai_storage.get_sections_by_analysis_id(analysis_id)
        assert retrieved_sections == sections
        assert retrieved_sections['core_trends'] == '核心趋势内容'
        assert retrieved_sections['signals'] == '信号内容'

        # 获取不存在的分析的板块
        empty_sections = ai_storage.get_sections_by_analysis_id(99999)
        assert empty_sections == {}

    def test_get_analysis_by_time_range(self, ai_storage):
        """测试按时间范围获取分析记录"""
        # 保存多条记录
        for i in range(5):
            analysis_time = f'2026-04-{21+i:02d}T12:00:00'
            analysis_data = {
                'analysis_time': analysis_time,
                'report_mode': 'daily',
                'news_count': i,
                'rss_count': 0,
                'matched_keywords': [],
                'platforms': [],
                'full_result': {}
            }
            ai_storage.save_analysis_result(analysis_data)

        # 获取指定范围的记录
        analyses = ai_storage.get_analysis_by_time_range(
            '2026-04-22T00:00:00',
            '2026-04-24T23:59:59'
        )
        assert len(analyses) == 3
        # 应该按时间升序
        assert analyses[0]['analysis_time'] == '2026-04-22T12:00:00'
        assert analyses[1]['analysis_time'] == '2026-04-23T12:00:00'
        assert analyses[2]['analysis_time'] == '2026-04-24T12:00:00'

    def test_get_nonexistent_analysis(self, ai_storage):
        """测试获取不存在的分析"""
        result = ai_storage.get_analysis_by_id(99999)
        assert result is None

    def test_duplicate_analysis_time(self, ai_storage):
        """测试重复的 analysis_time"""
        analysis_time = datetime.now().isoformat()
        analysis_data = {
            'analysis_time': analysis_time,
            'report_mode': 'daily',
            'news_count': 10,
            'rss_count': 5,
            'matched_keywords': [],
            'platforms': [],
            'full_result': {}
        }

        # 第一次保存应该成功
        analysis_id = ai_storage.save_analysis_result(analysis_data)
        assert analysis_id > 0

        # 第二次保存相同的 analysis_time 应该失败
        with pytest.raises(sqlite3.IntegrityError):
            ai_storage.save_analysis_result(analysis_data)

    def test_save_sections_with_invalid_type(self, ai_storage):
        """测试保存无效的板块类型"""
        analysis_time = datetime.now().isoformat()
        analysis_data = {
            'analysis_time': analysis_time,
            'report_mode': 'daily',
            'news_count': 10,
            'rss_count': 5,
            'matched_keywords': [],
            'platforms': [],
            'full_result': {}
        }
        analysis_id = ai_storage.save_analysis_result(analysis_data)

        # 尝试保存无效的板块类型
        sections = {
            'invalid_section_type': '内容'
        }

        with pytest.raises(sqlite3.IntegrityError):
            ai_storage.save_analysis_sections(analysis_id, sections)

    def test_empty_time_range_query(self, ai_storage):
        """测试空数据库的时间范围查询"""
        analyses = ai_storage.get_analysis_by_time_range(
            '2026-01-01T00:00:00',
            '2026-12-31T23:59:59'
        )
        assert analyses == []
