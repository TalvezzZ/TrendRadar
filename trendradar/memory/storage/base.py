"""
存储后端抽象基类
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from trendradar.memory.models import Memory


class StorageBackend(ABC):
    """存储后端抽象基类"""

    @abstractmethod
    def create_memory(self, memory: Memory) -> None:
        """
        创建记忆

        Args:
            memory: 记忆对象

        Raises:
            MemoryAlreadyExistsError: 如果记忆已存在
            MemoryStorageError: 其他存储错误
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def update_memory(self, memory: Memory) -> None:
        """
        更新记忆

        Args:
            memory: 记忆对象

        Raises:
            MemoryNotFoundError: 如果记忆不存在
            MemoryStorageError: 其他存储错误
        """
        pass

    @abstractmethod
    def delete_memory(self, memory_id: str) -> None:
        """
        删除记忆

        Args:
            memory_id: 记忆 ID

        Raises:
            MemoryStorageError: 存储错误
        """
        pass

    @abstractmethod
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
            记忆对象列表

        Raises:
            MemoryStorageError: 存储错误
        """
        pass

    @abstractmethod
    def search_memories(self, keyword: str, limit: Optional[int] = None) -> List[Memory]:
        """
        搜索记忆

        Args:
            keyword: 搜索关键词（不能为空）
            limit: 限制返回数量，None 表示不限制

        Returns:
            匹配的记忆对象列表

        Raises:
            MemoryStorageError: 存储错误
        """
        pass
