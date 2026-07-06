# coding=utf-8
"""
关键词统计管理
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any


class KeywordStatsManager:
    """关键词统计管理器"""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def update_keyword_stat(self, keyword_data: Dict[str, Any]) -> None:
        """
        更新关键词统计（插入或更新）

        Args:
            keyword_data: 关键词数据，包含：
                - date: 日期（YYYY-MM-DD）
                - keyword: 关键词
                - count: 出现次数
                - platforms: 平台列表
                - rank: 排名（可选）
        """
        platforms_json = json.dumps(
            keyword_data.get('platforms', []),
            ensure_ascii=False
        )

        self.conn.execute("""
            INSERT INTO keyword_trends (
                date, keyword, count, platforms, rank
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date, keyword) DO UPDATE SET
                count = excluded.count,
                platforms = excluded.platforms,
                rank = excluded.rank
        """, (
            keyword_data['date'],
            keyword_data['keyword'],
            keyword_data['count'],
            platforms_json,
            keyword_data.get('rank')
        ))

        self.conn.commit()

    def batch_update_keywords(self, keywords_data: List[Dict[str, Any]]) -> None:
        """
        批量更新关键词统计

        Args:
            keywords_data: 关键词数据列表
        """
        for keyword_data in keywords_data:
            self.update_keyword_stat(keyword_data)

    def get_keyword_trend(
        self,
        keyword: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取关键词的热度趋势

        Args:
            keyword: 关键词
            days: 过去多少天（返回最近的N条记录）

        Returns:
            趋势数据列表，按日期排序
        """
        cursor = self.conn.execute("""
            SELECT * FROM keyword_trends
            WHERE keyword = ?
            ORDER BY date DESC
            LIMIT ?
        """, (keyword, days))

        rows = cursor.fetchall()

        results = []
        for row in reversed(rows):  # 反转以按日期升序排列
            result = dict(row)
            result['platforms'] = json.loads(result['platforms'])
            results.append(result)

        return results

    def get_top_keywords_by_date(
        self,
        date: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取某日 Top 关键词

        Args:
            date: 日期（YYYY-MM-DD）
            limit: 返回数量

        Returns:
            Top 关键词列表，按 count 降序
        """
        cursor = self.conn.execute("""
            SELECT * FROM keyword_trends
            WHERE date = ?
            ORDER BY count DESC
            LIMIT ?
        """, (date, limit))

        rows = cursor.fetchall()

        results = []
        for row in rows:
            result = dict(row)
            result['platforms'] = json.loads(result['platforms'])
            results.append(result)

        return results

    def get_keywords_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取日期范围内的所有关键词统计

        Args:
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）

        Returns:
            关键词统计列表
        """
        cursor = self.conn.execute("""
            SELECT * FROM keyword_trends
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC, count DESC
        """, (start_date, end_date))

        rows = cursor.fetchall()

        results = []
        for row in rows:
            result = dict(row)
            result['platforms'] = json.loads(result['platforms'])
            results.append(result)

        return results
