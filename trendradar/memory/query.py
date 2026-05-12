"""
记忆查询引擎

提供智能的记忆检索和分析功能。
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any

from trendradar.memory.models import Memory, MemoryRepository
from trendradar.memory.storage.database import DatabaseBackend


class MemoryQueryEngine:
    """
    记忆查询引擎

    提供高级查询功能，包括智能搜索、趋势分析和关联查询。
    """

    def __init__(self, db_path: str):
        """
        初始化查询引擎

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        backend = DatabaseBackend(db_path)
        self.repository = MemoryRepository(backend)

    def search_memories(
        self,
        keyword: Optional[str] = None,
        memory_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """
        智能搜索记忆

        支持多种过滤条件的组合搜索。

        Args:
            keyword: 搜索关键词（在标题和内容中搜索）
            memory_type: 记忆类型（MemoryType）
            start_date: 开始日期（包含）
            end_date: 结束日期（包含）
            limit: 限制返回数量，None 表示不限制

        Returns:
            匹配的记忆对象列表，按创建时间倒序
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 构建查询条件
            conditions = []
            params = []

            if keyword is not None:
                conditions.append("(title LIKE ? OR content LIKE ?)")
                search_pattern = f"%{keyword}%"
                params.extend([search_pattern, search_pattern])

            if memory_type is not None:
                conditions.append("type = ?")
                params.append(memory_type)

            if start_date is not None:
                conditions.append("created_at >= ?")
                params.append(start_date.isoformat())

            if end_date is not None:
                conditions.append("created_at <= ?")
                params.append(end_date.isoformat())

            # 构建完整查询
            query = """
                SELECT id, type, title, description, content, metadata, created_at, updated_at
                FROM memories
            """

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at DESC"

            if limit is not None:
                query += f" LIMIT {limit}"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self.repository._row_to_memory(row) for row in rows]

        finally:
            conn.close()

    def get_keyword_trend(self, keyword: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取关键词的热度趋势

        Args:
            keyword: 关键词
            days: 过去多少天（返回最近的N条记录）

        Returns:
            趋势数据列表，按日期升序排列，每条包含：
            - date: 日期
            - keyword: 关键词
            - count: 出现次数
            - platforms: 平台列表
            - rank: 排名（如果有）
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT date, keyword, count, platforms, rank
                FROM keyword_trends
                WHERE keyword = ?
                ORDER BY date DESC
                LIMIT ?
            """, (keyword, days))

            rows = cursor.fetchall()

            # 转换为字典列表并按日期升序排列
            results = []
            for row in reversed(rows):
                result = dict(row)
                result['platforms'] = json.loads(result['platforms']) if result['platforms'] else []
                results.append(result)

            return results

        finally:
            conn.close()

    def get_memories_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        memory_type: Optional[str] = None
    ) -> List[Memory]:
        """
        根据日期范围获取记忆

        Args:
            start_date: 开始日期（包含）
            end_date: 结束日期（包含）
            memory_type: 记忆类型，None 表示所有类型

        Returns:
            记忆对象列表，按创建时间倒序
        """
        return self.repository.get_by_date_range(start_date, end_date, memory_type)

    def get_related_memories(
        self,
        memory_id: str,
        link_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取与指定记忆相关联的所有记忆

        返回该记忆的所有关联记忆，包括外向链接和入向链接。

        Args:
            memory_id: 记忆 ID
            link_type: 链接类型（LinkType），None 表示所有类型

        Returns:
            关联记忆列表，每条包含：
            - memory: Memory 对象
            - link_type: 链接类型
            - direction: 'outgoing' 或 'incoming'
            - notes: 链接备注
        """
        # 获取外向链接
        outgoing_links = self.repository.get_links_from(memory_id)
        # 获取入向链接
        incoming_links = self.repository.get_links_to(memory_id)

        results = []

        # 处理外向链接
        for link in outgoing_links:
            if link_type is not None and link.link_type != link_type:
                continue

            related_memory = self.repository.get_by_id(link.to_memory_id)
            if related_memory is not None:
                results.append({
                    'memory': related_memory,
                    'link_type': link.link_type,
                    'direction': 'outgoing',
                    'notes': link.notes
                })

        # 处理入向链接
        for link in incoming_links:
            if link_type is not None and link.link_type != link_type:
                continue

            related_memory = self.repository.get_by_id(link.from_memory_id)
            if related_memory is not None:
                results.append({
                    'memory': related_memory,
                    'link_type': link.link_type,
                    'direction': 'incoming',
                    'notes': link.notes
                })

        return results

    def get_top_keywords_by_date(
        self,
        date: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取指定日期的 Top 关键词

        Args:
            date: 日期（YYYY-MM-DD 格式）
            limit: 返回数量

        Returns:
            关键词列表，按出现次数降序排列，每条包含：
            - keyword: 关键词
            - count: 出现次数
            - platforms: 平台列表
            - rank: 排名（如果有）
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT keyword, count, platforms, rank
                FROM keyword_trends
                WHERE date = ?
                ORDER BY count DESC
                LIMIT ?
            """, (date, limit))

            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                result['platforms'] = json.loads(result['platforms']) if result['platforms'] else []
                results.append(result)

            return results

        finally:
            conn.close()
