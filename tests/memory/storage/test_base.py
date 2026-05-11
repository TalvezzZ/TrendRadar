import pytest
from trendradar.memory.storage.exceptions import (
    MemoryStorageError,
    MemoryNotFoundError,
    MemoryAlreadyExistsError,
    MemoryParseError,
    MemoryCorruptedError
)


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


# StorageBackend tests
from trendradar.memory.storage.base import StorageBackend
from trendradar.memory.models import Memory
from datetime import datetime


def test_storage_backend_is_abstract():
    """测试 StorageBackend 是抽象类"""
    with pytest.raises(TypeError):
        StorageBackend()


def test_storage_backend_abstract_methods():
    """测试 StorageBackend 抽象方法"""
    # 创建具体实现
    class ConcreteBackend(StorageBackend):
        def create_memory(self, memory):
            pass

        def get_memory(self, memory_id):
            pass

        def update_memory(self, memory):
            pass

        def delete_memory(self, memory_id):
            pass

        def list_memories(self, memory_type=None, start_date=None, end_date=None, limit=None):
            pass

        def search_memories(self, keyword, limit=None):
            pass

    # 应该可以实例化
    backend = ConcreteBackend()
    assert isinstance(backend, StorageBackend)
