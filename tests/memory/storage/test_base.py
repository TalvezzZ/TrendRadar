import pytest
from datetime import datetime
from typing import List, Optional

from trendradar.memory.storage.exceptions import (
    MemoryStorageError,
    MemoryNotFoundError,
    MemoryAlreadyExistsError,
    MemoryParseError,
    MemoryCorruptedError
)
from trendradar.memory.storage.base import StorageBackend
from trendradar.memory.models import Memory


def test_memory_storage_error():
    """测试 MemoryStorageError 基类"""
    error = MemoryStorageError("test error")
    assert str(error) == "test error"
    assert isinstance(error, Exception)


def test_memory_not_found_error():
    """测试 MemoryNotFoundError"""
    error = MemoryNotFoundError("memory not found")
    assert isinstance(error, MemoryStorageError)


def test_memory_already_exists_error():
    """测试 MemoryAlreadyExistsError"""
    error = MemoryAlreadyExistsError("memory exists")
    assert isinstance(error, MemoryStorageError)


def test_memory_parse_error():
    """测试 MemoryParseError"""
    error = MemoryParseError("parse failed")
    assert isinstance(error, MemoryStorageError)


def test_memory_corrupted_error():
    """测试 MemoryCorruptedError"""
    error = MemoryCorruptedError("data corrupted")
    assert isinstance(error, MemoryStorageError)


def test_storage_backend_is_abstract():
    """测试 StorageBackend 是抽象类"""
    with pytest.raises(TypeError):
        StorageBackend()


def test_storage_backend_concrete_implementation():
    """测试 StorageBackend 具体实现"""
    # 创建具体实现
    class ConcreteBackend(StorageBackend):
        def create_memory(self, memory: Memory) -> None:
            pass

        def get_memory(self, memory_id: str) -> Optional[Memory]:
            pass

        def update_memory(self, memory: Memory) -> None:
            pass

        def delete_memory(self, memory_id: str) -> None:
            pass

        def list_memories(
            self,
            memory_type: Optional[str] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            limit: Optional[int] = None
        ) -> List[Memory]:
            pass

        def search_memories(self, keyword: str, limit: Optional[int] = None) -> List[Memory]:
            pass

    # 应该可以实例化
    backend = ConcreteBackend()
    assert isinstance(backend, StorageBackend)
