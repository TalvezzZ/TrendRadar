"""
记忆数据模型

提供记忆系统的核心数据结构和数据库访问功能。
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from trendradar.memory.storage.base import StorageBackend


class MemoryType:
    """记忆类型常量"""
    DAILY_SUMMARY = 'daily_summary'      # 每日总结
    WEEKLY_DIGEST = 'weekly_digest'      # 每周摘要
    TOPIC_INSIGHT = 'topic_insight'      # 主题洞察
    PATTERN = 'pattern'                  # 模式识别
    SIGNAL = 'signal'                    # 信号记录


class LinkType:
    """记忆链接类型常量"""
    SUPPORTS = 'supports'                # 支持/佐证
    CONTRADICTS = 'contradicts'          # 矛盾/反驳
    EXTENDS = 'extends'                  # 扩展/补充
    DERIVES_FROM = 'derives_from'        # 派生自


@dataclass(frozen=True)
class Memory:
    """
    记忆数据类

    表示一条记忆记录，包含所有必要的元数据和内容。
    """
    id: str                              # 记忆唯一标识
    type: str                            # 记忆类型（MemoryType）
    title: str                           # 标题
    content: str                         # 内容
    created_at: datetime                 # 创建时间
    updated_at: datetime                 # 更新时间
    description: Optional[str] = None    # 描述
    metadata: Dict[str, Any] = None      # 元数据（JSON）

    def __post_init__(self):
        """初始化后处理，确保 metadata 默认为空字典"""
        if self.metadata is None:
            # 由于 frozen=True，需要使用 object.__setattr__
            object.__setattr__(self, 'metadata', {})


@dataclass(frozen=True)
class MemoryLink:
    """
    记忆链接数据类

    表示两个记忆之间的关联关系。
    """
    from_memory_id: str                  # 源记忆 ID
    to_memory_id: str                    # 目标记忆 ID
    link_type: str                       # 链接类型（LinkType）
    created_at: datetime                 # 创建时间
    notes: Optional[str] = None          # 备注


class MemoryRepository:
    """
    记忆仓库

    提供记忆和记忆链接的存储访问功能。
    使用依赖注入的存储后端进行数据访问。
    """

    def __init__(self, backend: 'StorageBackend'):
        """
        初始化记忆仓库

        Args:
            backend: 存储后端实例
        """
        self.backend = backend
        # 保留 db_path 用于链接功能（仅 DatabaseBackend 支持）
        self.db_path = getattr(backend, 'db_path', None)

    def create(self, memory: Memory) -> None:
        """
        创建新记忆

        Args:
            memory: 记忆对象

        Raises:
            MemoryAlreadyExistsError: 如果记忆 ID 已存在
            MemoryStorageError: 其他存储错误
        """
        self.backend.create_memory(memory)

    def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """
        根据 ID 获取记忆

        Args:
            memory_id: 记忆 ID

        Returns:
            记忆对象，如果不存在则返回 None
        """
        return self.backend.get_memory(memory_id)

    def get_by_type(self, memory_type: str, limit: Optional[int] = None) -> List[Memory]:
        """
        根据类型获取记忆列表

        Args:
            memory_type: 记忆类型（MemoryType）
            limit: 限制返回数量，None 表示不限制

        Returns:
            记忆对象列表，按创建时间倒序
        """
        return self.backend.list_memories(memory_type=memory_type, limit=limit)

    def get_by_date_range(
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
        return self.backend.list_memories(
            memory_type=memory_type,
            start_date=start_date,
            end_date=end_date
        )

    def update(self, memory: Memory) -> None:
        """
        更新记忆

        Args:
            memory: 记忆对象（必须包含有效的 id）

        Raises:
            MemoryNotFoundError: 如果记忆 ID 不存在
            MemoryStorageError: 其他存储错误
        """
        self.backend.update_memory(memory)

    def delete(self, memory_id: str) -> None:
        """
        删除记忆

        Args:
            memory_id: 记忆 ID
        """
        # 先删除相关的链接（仅 DatabaseBackend 支持）
        if self.db_path:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "DELETE FROM memory_links WHERE from_memory_id = ? OR to_memory_id = ?",
                    (memory_id, memory_id)
                )
                conn.commit()
            finally:
                conn.close()

        # 删除记忆
        self.backend.delete_memory(memory_id)

    def search(self, keyword: str, limit: Optional[int] = None) -> List[Memory]:
        """
        搜索记忆（简单文本匹配）

        Args:
            keyword: 搜索关键词
            limit: 限制返回数量，None 表示不限制

        Returns:
            匹配的记忆对象列表
        """
        return self.backend.search_memories(keyword, limit)

    def create_link(self, link: MemoryLink) -> None:
        """
        创建记忆链接

        Args:
            link: 记忆链接对象

        Raises:
            sqlite3.IntegrityError: 如果链接已存在或记忆 ID 无效
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO memory_links
                (from_memory_id, to_memory_id, link_type, notes, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    link.from_memory_id,
                    link.to_memory_id,
                    link.link_type,
                    link.notes,
                    link.created_at.isoformat()
                )
            )
            conn.commit()
        finally:
            conn.close()

    def get_links_from(self, memory_id: str) -> List[MemoryLink]:
        """
        获取从指定记忆发出的所有链接

        Args:
            memory_id: 记忆 ID

        Returns:
            记忆链接列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT from_memory_id, to_memory_id, link_type, notes, created_at
                FROM memory_links
                WHERE from_memory_id = ?
                ORDER BY created_at DESC
                """,
                (memory_id,)
            )

            rows = cursor.fetchall()
            return [self._row_to_link(row) for row in rows]
        finally:
            conn.close()

    def get_links_to(self, memory_id: str) -> List[MemoryLink]:
        """
        获取指向指定记忆的所有链接

        Args:
            memory_id: 记忆 ID

        Returns:
            记忆链接列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT from_memory_id, to_memory_id, link_type, notes, created_at
                FROM memory_links
                WHERE to_memory_id = ?
                ORDER BY created_at DESC
                """,
                (memory_id,)
            )

            rows = cursor.fetchall()
            return [self._row_to_link(row) for row in rows]
        finally:
            conn.close()

    def delete_link(self, from_memory_id: str, to_memory_id: str) -> None:
        """
        删除记忆链接

        Args:
            from_memory_id: 源记忆 ID
            to_memory_id: 目标记忆 ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                DELETE FROM memory_links
                WHERE from_memory_id = ? AND to_memory_id = ?
                """,
                (from_memory_id, to_memory_id)
            )
            conn.commit()
        finally:
            conn.close()

    def _row_to_memory(self, row: tuple) -> Memory:
        """
        将数据库行转换为 Memory 对象

        Args:
            row: 数据库查询结果行 (id, type, title, description, content, metadata, created_at, updated_at)

        Returns:
            Memory 对象

        Note:
            此方法仅用于兼容 MemoryQueryEngine 的直接 SQL 查询。
            新代码应使用 StorageBackend 接口。
        """
        return Memory(
            id=row[0],
            type=row[1],
            title=row[2],
            description=row[3],
            content=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7])
        )

    def _row_to_link(self, row: tuple) -> MemoryLink:
        """
        将数据库行转换为 MemoryLink 对象

        Args:
            row: 数据库查询结果行

        Returns:
            MemoryLink 对象
        """
        return MemoryLink(
            from_memory_id=row[0],
            to_memory_id=row[1],
            link_type=row[2],
            notes=row[3],
            created_at=datetime.fromisoformat(row[4])
        )
