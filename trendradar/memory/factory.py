"""
工厂函数用于创建 MemoryRepository
"""
from typing import Dict, Any

from trendradar.memory.models import MemoryRepository
from trendradar.memory.storage.database import DatabaseBackend
from trendradar.memory.storage.file import FileBackend


def create_memory_repository(config: Dict[str, Any]) -> MemoryRepository:
    """
    根据配置创建 MemoryRepository

    Args:
        config: 配置字典，包含 storage_type 和相应的配置

    Returns:
        MemoryRepository 实例

    Raises:
        ValueError: 如果存储类型未知或配置缺少必需字段

    Examples:
        创建数据库存储:
        >>> config = {
        ...     "storage_type": "database",
        ...     "database_storage": {
        ...         "db_path": "/path/to/memory.db"
        ...     }
        ... }
        >>> repo = create_memory_repository(config)

        创建文件存储:
        >>> config = {
        ...     "storage_type": "file",
        ...     "file_storage": {
        ...         "base_path": "/path/to/memory",
        ...         "auto_index": True
        ...     }
        ... }
        >>> repo = create_memory_repository(config)

        默认使用数据库:
        >>> config = {
        ...     "database_storage": {"db_path": "/path/to/memory.db"}
        ... }
        >>> repo = create_memory_repository(config)
    """
    storage_type = config.get("storage_type", "database")

    if storage_type == "database":
        db_config = config.get("database_storage", {})
        if "db_path" not in db_config:
            raise ValueError("database_storage.db_path is required")
        backend = DatabaseBackend(db_config["db_path"])

    elif storage_type == "file":
        file_config = config.get("file_storage", {})
        if "base_path" not in file_config:
            raise ValueError("file_storage.base_path is required")
        backend = FileBackend(
            base_path=file_config["base_path"],
            auto_index=file_config.get("auto_index", True)
        )

    else:
        raise ValueError(f"Unknown storage type: {storage_type}")

    return MemoryRepository(backend)
