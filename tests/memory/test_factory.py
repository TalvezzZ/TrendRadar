"""
测试 MemoryRepository 工厂函数
"""
import pytest
from pathlib import Path

from trendradar.memory.factory import create_memory_repository
from trendradar.memory.storage.database import DatabaseBackend
from trendradar.memory.storage.file import FileBackend


def test_create_database_repository(tmp_path):
    """测试创建数据库 repository"""
    config = {
        "storage_type": "database",
        "database_storage": {"db_path": str(tmp_path / "test.db")}
    }
    repo = create_memory_repository(config)
    assert isinstance(repo.backend, DatabaseBackend)


def test_create_file_repository(tmp_path):
    """测试创建文件 repository"""
    config = {
        "storage_type": "file",
        "file_storage": {
            "base_path": str(tmp_path / "memory"),
            "auto_index": True
        }
    }
    repo = create_memory_repository(config)
    assert isinstance(repo.backend, FileBackend)


def test_create_with_invalid_type():
    """测试无效的存储类型"""
    config = {"storage_type": "invalid"}
    with pytest.raises(ValueError, match="Unknown storage type"):
        create_memory_repository(config)


def test_default_to_database(tmp_path):
    """测试默认使用数据库"""
    config = {
        "database_storage": {"db_path": str(tmp_path / "test.db")}
    }
    repo = create_memory_repository(config)
    assert isinstance(repo.backend, DatabaseBackend)


def test_missing_db_path():
    """测试缺少数据库路径"""
    config = {
        "storage_type": "database",
        "database_storage": {}
    }
    with pytest.raises(ValueError, match="database_storage.db_path is required"):
        create_memory_repository(config)


def test_missing_base_path():
    """测试缺少文件基础路径"""
    config = {
        "storage_type": "file",
        "file_storage": {}
    }
    with pytest.raises(ValueError, match="file_storage.base_path is required"):
        create_memory_repository(config)


def test_file_repository_with_auto_index_disabled(tmp_path):
    """测试创建禁用自动索引的文件 repository"""
    config = {
        "storage_type": "file",
        "file_storage": {
            "base_path": str(tmp_path / "memory"),
            "auto_index": False
        }
    }
    repo = create_memory_repository(config)
    assert isinstance(repo.backend, FileBackend)
    assert repo.backend.auto_index is False


def test_file_repository_auto_index_default(tmp_path):
    """测试文件 repository 自动索引默认值"""
    config = {
        "storage_type": "file",
        "file_storage": {
            "base_path": str(tmp_path / "memory")
        }
    }
    repo = create_memory_repository(config)
    assert isinstance(repo.backend, FileBackend)
    assert repo.backend.auto_index is True
