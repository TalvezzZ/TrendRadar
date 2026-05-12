"""
DatabaseBackend - SQLite 数据库存储后端
"""
import json
import sqlite3
from datetime import datetime
from typing import Any, List, Optional

from trendradar.memory.models import Memory
from trendradar.memory.storage.base import StorageBackend
from trendradar.memory.storage.exceptions import (
    MemoryStorageError,
    MemoryNotFoundError,
    MemoryAlreadyExistsError
)
from trendradar.persistence.schema import initialize_memory_tables


class DatabaseBackend(StorageBackend):
    """SQLite 数据库存储后端"""

    def __init__(self, db_path: str):
        """
        初始化数据库后端

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """确保数据库 schema 存在"""
        conn = sqlite3.connect(self.db_path)
        try:
            initialize_memory_tables(conn)
        finally:
            conn.close()

    def create_memory(self, memory: Memory) -> None:
        """
        创建记忆

        Args:
            memory: 记忆对象

        Raises:
            MemoryAlreadyExistsError: 如果记忆已存在
            MemoryStorageError: 其他存储错误
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO memories
                (id, type, title, description, content, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.id,
                    memory.type,
                    memory.title,
                    memory.description,
                    memory.content,
                    json.dumps(memory.metadata, ensure_ascii=False),
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat()
                )
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e) or "PRIMARY KEY" in str(e):
                raise MemoryAlreadyExistsError(f"Memory with id '{memory.id}' already exists")
            raise MemoryStorageError(f"Failed to create memory: {e}")
        except sqlite3.Error as e:
            raise MemoryStorageError(f"Database error: {e}")
        finally:
            conn.close()

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """
        获取记忆

        Args:
            memory_id: 记忆 ID

        Returns:
            记忆对象，如果不存在则返回 None

        Raises:
            MemoryStorageError: 存储错误
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, type, title, description, content, metadata, created_at, updated_at
                FROM memories
                WHERE id = ?
                """,
                (memory_id,)
            )

            row = cursor.fetchone()
            if row is None:
                return None

            return self._row_to_memory(row)
        except sqlite3.Error as e:
            raise MemoryStorageError(f"Database error: {e}")
        finally:
            conn.close()

    def update_memory(self, memory: Memory) -> None:
        """
        更新记忆

        Args:
            memory: 记忆对象

        Raises:
            MemoryNotFoundError: 如果记忆不存在
            MemoryStorageError: 其他存储错误
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE memories
                SET type = ?, title = ?, description = ?, content = ?,
                    metadata = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    memory.type,
                    memory.title,
                    memory.description,
                    memory.content,
                    json.dumps(memory.metadata, ensure_ascii=False),
                    memory.updated_at.isoformat(),
                    memory.id
                )
            )

            if cursor.rowcount == 0:
                raise MemoryNotFoundError(f"Memory with id '{memory.id}' not found")

            conn.commit()
        except MemoryNotFoundError:
            raise
        except sqlite3.Error as e:
            raise MemoryStorageError(f"Database error: {e}")
        finally:
            conn.close()

    def delete_memory(self, memory_id: str) -> None:
        """
        删除记忆

        Args:
            memory_id: 记忆 ID

        Raises:
            MemoryStorageError: 存储错误
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 先删除相关的链接
            cursor.execute(
                "DELETE FROM memory_links WHERE from_memory_id = ? OR to_memory_id = ?",
                (memory_id, memory_id)
            )

            # 删除记忆
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

            conn.commit()
        except sqlite3.Error as e:
            raise MemoryStorageError(f"Database error: {e}")
        finally:
            conn.close()

    def list_memories(
        self,
        memory_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """
        列出记忆

        Args:
            memory_type: 记忆类型，None 表示所有类型
            start_date: 开始日期（包含）
            end_date: 结束日期（包含）
            limit: 限制返回数量，None 表示不限制

        Returns:
            记忆对象列表，按创建时间倒序

        Raises:
            MemoryStorageError: 存储错误
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 构建查询
            query = """
                SELECT id, type, title, description, content, metadata, created_at, updated_at
                FROM memories
            """
            conditions = []
            params = []

            if memory_type is not None:
                conditions.append("type = ?")
                params.append(memory_type)

            if start_date is not None:
                conditions.append("created_at >= ?")
                params.append(start_date.isoformat())

            if end_date is not None:
                conditions.append("created_at <= ?")
                params.append(end_date.isoformat())

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at DESC"

            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_memory(row) for row in rows]
        except sqlite3.Error as e:
            raise MemoryStorageError(f"Database error: {e}")
        finally:
            conn.close()

    def search_memories(self, keyword: str, limit: Optional[int] = None) -> List[Memory]:
        """
        搜索记忆

        Args:
            keyword: 搜索关键词（不能为空）
            limit: 限制返回数量，None 表示不限制

        Returns:
            匹配的记忆对象列表，按创建时间倒序

        Raises:
            MemoryStorageError: 存储错误
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            query = """
                SELECT id, type, title, description, content, metadata, created_at, updated_at
                FROM memories
                WHERE title LIKE ? OR content LIKE ?
                ORDER BY created_at DESC
            """

            search_pattern = f"%{keyword}%"
            params = [search_pattern, search_pattern]

            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_memory(row) for row in rows]
        except sqlite3.Error as e:
            raise MemoryStorageError(f"Database error: {e}")
        finally:
            conn.close()

    def _row_to_memory(self, row: Any) -> Memory:
        """
        将数据库行转换为 Memory 对象

        Args:
            row: 数据库查询结果行

        Returns:
            Memory 对象
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
