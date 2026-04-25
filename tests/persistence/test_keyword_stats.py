# coding=utf-8
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from trendradar.persistence.schema import initialize_memory_db
from trendradar.persistence.keyword_stats import KeywordStatsManager


@pytest.fixture
def memory_db():
    """创建临时 memory.db"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    conn = initialize_memory_db(db_path)
    conn.row_factory = sqlite3.Row

    yield conn

    conn.close()
    Path(db_path).unlink()


def test_update_keyword_stat(memory_db):
    """测试更新关键词统计"""
    manager = KeywordStatsManager(memory_db)

    keyword_data = {
        'date': '2026-04-25',
        'keyword': 'DeepSeek',
        'count': 67,
        'platforms': ['微博', '知乎', 'B站'],
        'rank': 1
    }

    manager.update_keyword_stat(keyword_data)

    # 验证保存
    cursor = memory_db.execute("""
        SELECT * FROM keyword_trends
        WHERE date = ? AND keyword = ?
    """, ('2026-04-25', 'DeepSeek'))

    row = cursor.fetchone()
    assert row is not None
    assert row['count'] == 67
    assert row['rank'] == 1
    assert json.loads(row['platforms']) == ['微博', '知乎', 'B站']


def test_batch_update_keywords(memory_db):
    """测试批量更新关键词"""
    manager = KeywordStatsManager(memory_db)

    keywords_data = [
        {
            'date': '2026-04-25',
            'keyword': 'DeepSeek',
            'count': 67,
            'platforms': ['微博', '知乎'],
            'rank': 1
        },
        {
            'date': '2026-04-25',
            'keyword': '华为',
            'count': 32,
            'platforms': ['微博'],
            'rank': 2
        }
    ]

    manager.batch_update_keywords(keywords_data)

    # 验证
    cursor = memory_db.execute("""
        SELECT COUNT(*) as count FROM keyword_trends
        WHERE date = '2026-04-25'
    """)
    assert cursor.fetchone()['count'] == 2


def test_get_keyword_trend(memory_db):
    """测试获取关键词趋势"""
    manager = KeywordStatsManager(memory_db)

    # 插入多天数据
    for i in range(3):
        keyword_data = {
            'date': f'2026-04-{23+i}',
            'keyword': 'DeepSeek',
            'count': 10 + i * 20,
            'platforms': ['微博'],
            'rank': 1
        }
        manager.update_keyword_stat(keyword_data)

    # 获取趋势
    trend = manager.get_keyword_trend('DeepSeek', days=3)

    assert len(trend) == 3
    assert trend[0]['count'] == 10
    assert trend[1]['count'] == 30
    assert trend[2]['count'] == 50


def test_get_top_keywords_by_date(memory_db):
    """测试获取某日 Top 关键词"""
    manager = KeywordStatsManager(memory_db)

    keywords_data = [
        {'date': '2026-04-25', 'keyword': 'DeepSeek', 'count': 67, 'platforms': [], 'rank': 1},
        {'date': '2026-04-25', 'keyword': '华为', 'count': 32, 'platforms': [], 'rank': 2},
        {'date': '2026-04-25', 'keyword': 'AI', 'count': 28, 'platforms': [], 'rank': 3},
    ]

    manager.batch_update_keywords(keywords_data)

    # 获取 Top 2
    top_keywords = manager.get_top_keywords_by_date('2026-04-25', limit=2)

    assert len(top_keywords) == 2
    assert top_keywords[0]['keyword'] == 'DeepSeek'
    assert top_keywords[1]['keyword'] == '华为'


def test_get_keywords_by_date_range(memory_db):
    """测试获取日期范围内的关键词"""
    manager = KeywordStatsManager(memory_db)

    # 插入多个日期的数据
    for day in range(23, 26):  # 23, 24, 25
        for keyword in ['DeepSeek', 'AI']:
            keyword_data = {
                'date': f'2026-04-{day}',
                'keyword': keyword,
                'count': day * 10,
                'platforms': ['微博'],
                'rank': 1
            }
            manager.update_keyword_stat(keyword_data)

    # 查询范围
    results = manager.get_keywords_by_date_range('2026-04-23', '2026-04-25')

    assert len(results) == 6  # 3 days * 2 keywords
