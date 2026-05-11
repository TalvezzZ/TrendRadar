# 记忆系统文件存储重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构记忆系统存储层，支持数据库和文件两种存储方式，提供 Markdown 格式的可读记忆文件

**Architecture:** 使用后端注入模式，创建 StorageBackend 抽象层，DatabaseBackend 和 FileBackend 实现，MemoryRepository 通过依赖注入使用 backend

**Tech Stack:** Python 3.12, SQLite, YAML, Markdown, pytest

---

## 文件结构映射

### 新增文件

```
trendradar/memory/
├── storage/
│   ├── __init__.py                     # 导出 StorageBackend, DatabaseBackend, FileBackend
│   ├── base.py                         # StorageBackend 抽象基类
│   ├── database.py                     # DatabaseBackend 实现
│   ├── file.py                         # FileBackend 实现
│   └── exceptions.py                   # 存储层异常定义
├── index_manager.py                     # MemoryIndexManager
├── migrator.py                          # MemoryMigrator
└── factory.py                           # create_memory_repository 工厂函数

trendradar/cli/
└── memory_commands.py                   # CLI 命令

tests/memory/
├── storage/
│   ├── __init__.py
│   ├── test_base.py                    # StorageBackend 接口测试
│   ├── test_database_backend.py        # DatabaseBackend 测试
│   └── test_file_backend.py            # FileBackend 测试
├── test_index_manager.py                # MemoryIndexManager 测试
├── test_migrator.py                     # MemoryMigrator 测试
├── test_factory.py                      # 工厂函数测试
└── test_integration.py                  # 集成测试
```

### 修改文件

```
trendradar/memory/models.py              # 修改 MemoryRepository，使用依赖注入
trendradar/__main__.py                   # 注册 memory CLI 命令组
```

---

## Task 1: 创建存储层基础结构

**Files:**
- Create: `trendradar/memory/storage/__init__.py`
- Create: `trendradar/memory/storage/exceptions.py`
- Create: `trendradar/memory/storage/base.py`
- Create: `tests/memory/storage/__init__.py`
- Create: `tests/memory/storage/test_base.py`

- [ ] **Step 1: 创建存储层异常类（测试）**

```python
# tests/memory/storage/test_base.py
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/memory/storage/test_base.py::test_memory_storage_error -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'trendradar.memory.storage'"

- [ ] **Step 3: 实现异常类**

```python
# trendradar/memory/storage/exceptions.py
"""
存储层异常定义
"""


class MemoryStorageError(Exception):
    """存储层基础异常"""
    pass


class MemoryNotFoundError(MemoryStorageError):
    """记忆不存在"""
    pass


class MemoryAlreadyExistsError(MemoryStorageError):
    """记忆已存在"""
    pass


class MemoryParseError(MemoryStorageError):
    """Markdown 解析失败"""
    pass


class MemoryCorruptedError(MemoryStorageError):
    """记忆数据损坏"""
    pass
```

```python
# trendradar/memory/storage/__init__.py
"""
存储层模块
"""
from trendradar.memory.storage.exceptions import (
    MemoryStorageError,
    MemoryNotFoundError,
    MemoryAlreadyExistsError,
    MemoryParseError,
    MemoryCorruptedError
)

__all__ = [
    'MemoryStorageError',
    'MemoryNotFoundError',
    'MemoryAlreadyExistsError',
    'MemoryParseError',
    'MemoryCorruptedError',
]
```

```python
# tests/memory/storage/__init__.py
# Empty file for test package
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/memory/storage/test_base.py -v
```
Expected: 5 tests PASS

- [ ] **Step 5: 创建 StorageBackend 抽象基类（测试）**

```python
# 追加到 tests/memory/storage/test_base.py
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
```

- [ ] **Step 6: 运行测试确认失败**

```bash
pytest tests/memory/storage/test_base.py::test_storage_backend_is_abstract -v
```
Expected: FAIL with "ImportError: cannot import name 'StorageBackend'"

- [ ] **Step 7: 实现 StorageBackend 抽象基类**

```python
# trendradar/memory/storage/base.py
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
            keyword: 搜索关键词
            limit: 限制返回数量，None 表示不限制
            
        Returns:
            匹配的记忆对象列表
            
        Raises:
            MemoryStorageError: 存储错误
        """
        pass
```

```python
# 更新 trendradar/memory/storage/__init__.py
from trendradar.memory.storage.base import StorageBackend
from trendradar.memory.storage.exceptions import (
    MemoryStorageError,
    MemoryNotFoundError,
    MemoryAlreadyExistsError,
    MemoryParseError,
    MemoryCorruptedError
)

__all__ = [
    'StorageBackend',
    'MemoryStorageError',
    'MemoryNotFoundError',
    'MemoryAlreadyExistsError',
    'MemoryParseError',
    'MemoryCorruptedError',
]
```

- [ ] **Step 8: 运行测试确认通过**

```bash
pytest tests/memory/storage/test_base.py -v
```
Expected: All tests PASS

- [ ] **Step 9: 提交**

```bash
git add trendradar/memory/storage/ tests/memory/storage/
git commit -m "feat(memory): 添加存储层基础结构和异常定义

- 创建 StorageBackend 抽象基类
- 定义存储层异常体系
- 添加单元测试

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: 实现 DatabaseBackend

**Files:**
- Create: `trendradar/memory/storage/database.py`
- Create: `tests/memory/storage/test_database_backend.py`
- Modify: `trendradar/memory/models.py`

- [ ] **Step 1: 创建 DatabaseBackend 测试**

```python
# tests/memory/storage/test_database_backend.py
import pytest
import sqlite3
from datetime import datetime
from pathlib import Path

from trendradar.memory.models import Memory, MemoryType
from trendradar.memory.storage.database import DatabaseBackend
from trendradar.memory.storage.exceptions import MemoryNotFoundError


@pytest.fixture
def temp_db(tmp_path):
    """临时数据库"""
    db_path = str(tmp_path / "test.db")
    backend = DatabaseBackend(db_path)
    yield backend
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


def test_create_memory(temp_db):
    """测试创建记忆"""
    memory = Memory(
        id="test-001",
        type=MemoryType.DAILY_SUMMARY,
        title="测试摘要",
        description="测试描述",
        content="测试内容",
        metadata={"key": "value"},
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1)
    )
    
    temp_db.create_memory(memory)
    
    # 验证数据库中有记录
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM memories WHERE id = ?", (memory.id,))
    result = cursor.fetchone()
    conn.close()
    
    assert result is not None
    assert result[0] == "test-001"


def test_get_memory(temp_db):
    """测试获取记忆"""
    memory = Memory(
        id="test-002",
        type=MemoryType.DAILY_SUMMARY,
        title="测试摘要",
        content="测试内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    temp_db.create_memory(memory)
    retrieved = temp_db.get_memory("test-002")
    
    assert retrieved is not None
    assert retrieved.id == "test-002"
    assert retrieved.title == "测试摘要"


def test_get_memory_not_found(temp_db):
    """测试获取不存在的记忆"""
    result = temp_db.get_memory("non-existent")
    assert result is None


def test_update_memory(temp_db):
    """测试更新记忆"""
    memory = Memory(
        id="test-003",
        type=MemoryType.DAILY_SUMMARY,
        title="原标题",
        content="原内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    temp_db.create_memory(memory)
    
    # 更新
    updated_memory = Memory(
        id="test-003",
        type=MemoryType.DAILY_SUMMARY,
        title="新标题",
        content="新内容",
        created_at=memory.created_at,
        updated_at=datetime.now()
    )
    temp_db.update_memory(updated_memory)
    
    # 验证
    retrieved = temp_db.get_memory("test-003")
    assert retrieved.title == "新标题"


def test_delete_memory(temp_db):
    """测试删除记忆"""
    memory = Memory(
        id="test-004",
        type=MemoryType.DAILY_SUMMARY,
        title="待删除",
        content="内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    temp_db.create_memory(memory)
    
    temp_db.delete_memory("test-004")
    
    assert temp_db.get_memory("test-004") is None


def test_list_memories(temp_db):
    """测试列出记忆"""
    # 创建多个记忆
    for i in range(3):
        memory = Memory(
            id=f"test-{i}",
            type=MemoryType.DAILY_SUMMARY,
            title=f"标题 {i}",
            content=f"内容 {i}",
            created_at=datetime(2026, 5, i+1),
            updated_at=datetime(2026, 5, i+1)
        )
        temp_db.create_memory(memory)
    
    # 不带过滤
    all_memories = temp_db.list_memories()
    assert len(all_memories) == 3
    
    # 按类型过滤
    daily_memories = temp_db.list_memories(memory_type=MemoryType.DAILY_SUMMARY)
    assert len(daily_memories) == 3
    
    # 限制数量
    limited = temp_db.list_memories(limit=2)
    assert len(limited) == 2


def test_search_memories(temp_db):
    """测试搜索记忆"""
    memory1 = Memory(
        id="search-1",
        type=MemoryType.DAILY_SUMMARY,
        title="包含AI的标题",
        content="内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    memory2 = Memory(
        id="search-2",
        type=MemoryType.DAILY_SUMMARY,
        title="普通标题",
        content="包含AI的内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    temp_db.create_memory(memory1)
    temp_db.create_memory(memory2)
    
    results = temp_db.search_memories("AI")
    assert len(results) == 2
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/memory/storage/test_database_backend.py::test_create_memory -v
```
Expected: FAIL with "ImportError: cannot import name 'DatabaseBackend'"

- [ ] **Step 3: 实现 DatabaseBackend（基本框架）**

```python
# trendradar/memory/storage/database.py
"""
数据库存储后端
"""
import json
import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from trendradar.memory.models import Memory
from trendradar.memory.storage.base import StorageBackend
from trendradar.memory.storage.exceptions import (
    MemoryStorageError,
    MemoryNotFoundError
)


class DatabaseBackend(StorageBackend):
    """数据库存储后端"""
    
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
        from trendradar.persistence.schema import initialize_memory_tables
        
        conn = sqlite3.connect(self.db_path)
        try:
            initialize_memory_tables(conn)
        finally:
            conn.close()
    
    def create_memory(self, memory: Memory) -> None:
        """创建记忆"""
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
            raise MemoryStorageError(f"Failed to create memory: {e}")
        finally:
            conn.close()
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
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
        finally:
            conn.close()
    
    def update_memory(self, memory: Memory) -> None:
        """更新记忆"""
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
        finally:
            conn.close()
    
    def delete_memory(self, memory_id: str) -> None:
        """删除记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 先删除链接
            cursor.execute(
                "DELETE FROM memory_links WHERE from_memory_id = ? OR to_memory_id = ?",
                (memory_id, memory_id)
            )
            
            # 删除记忆
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            
            conn.commit()
        finally:
            conn.close()
    
    def list_memories(
        self,
        memory_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """列出记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 构建查询
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
            
            return [self._row_to_memory(row) for row in rows]
        finally:
            conn.close()
    
    def search_memories(self, keyword: str, limit: Optional[int] = None) -> List[Memory]:
        """搜索记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT id, type, title, description, content, metadata, created_at, updated_at
                FROM memories
                WHERE title LIKE ? OR content LIKE ?
                ORDER BY created_at DESC
            """
            
            if limit is not None:
                query += f" LIMIT {limit}"
            
            search_pattern = f"%{keyword}%"
            cursor.execute(query, (search_pattern, search_pattern))
            rows = cursor.fetchall()
            
            return [self._row_to_memory(row) for row in rows]
        finally:
            conn.close()
    
    def _row_to_memory(self, row: tuple) -> Memory:
        """将数据库行转换为 Memory 对象"""
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
```

- [ ] **Step 4: 更新 storage __init__.py**

```python
# 更新 trendradar/memory/storage/__init__.py
from trendradar.memory.storage.base import StorageBackend
from trendradar.memory.storage.database import DatabaseBackend
from trendradar.memory.storage.exceptions import (
    MemoryStorageError,
    MemoryNotFoundError,
    MemoryAlreadyExistsError,
    MemoryParseError,
    MemoryCorruptedError
)

__all__ = [
    'StorageBackend',
    'DatabaseBackend',
    'MemoryStorageError',
    'MemoryNotFoundError',
    'MemoryAlreadyExistsError',
    'MemoryParseError',
    'MemoryCorruptedError',
]
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/memory/storage/test_database_backend.py -v
```
Expected: All tests PASS

- [ ] **Step 6: 提交**

```bash
git add trendradar/memory/storage/database.py tests/memory/storage/test_database_backend.py trendradar/memory/storage/__init__.py
git commit -m "feat(memory): 实现 DatabaseBackend 存储后端

- 迁移现有数据库逻辑到 DatabaseBackend
- 实现 StorageBackend 接口
- 添加完整的单元测试

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: 实现 FileBackend - Markdown 转换

**Files:**
- Create: `trendradar/memory/storage/file.py`
- Create: `tests/memory/storage/test_file_backend.py`

- [ ] **Step 1: 创建 Markdown 转换测试**

```python
# tests/memory/storage/test_file_backend.py
import pytest
import yaml
from datetime import datetime
from pathlib import Path

from trendradar.memory.models import Memory, MemoryType
from trendradar.memory.storage.file import FileBackend


@pytest.fixture
def temp_storage(tmp_path):
    """临时文件存储"""
    return FileBackend(str(tmp_path), auto_index=False)


def test_memory_to_markdown(temp_storage):
    """测试 Memory 对象转换为 Markdown"""
    memory = Memory(
        id="test-001",
        type=MemoryType.DAILY_SUMMARY,
        title="测试摘要",
        description="测试描述",
        content="# 标题\n\n内容",
        metadata={"key": "value"},
        created_at=datetime(2026, 5, 1, 10, 30, 0),
        updated_at=datetime(2026, 5, 1, 10, 30, 0)
    )
    
    markdown = temp_storage._memory_to_markdown(memory)
    
    # 验证格式
    assert markdown.startswith("---\n")
    assert "id: test-001" in markdown
    assert "type: daily_summary" in markdown
    assert "title: 测试摘要" in markdown
    assert "# 标题" in markdown
    assert "内容" in markdown


def test_markdown_to_memory(temp_storage):
    """测试 Markdown 转换为 Memory 对象"""
    markdown = """---
id: test-002
type: daily_summary
title: 测试摘要
description: 测试描述
created_at: '2026-05-01T10:30:00'
updated_at: '2026-05-01T10:30:00'
metadata:
  key: value
---

# 标题

内容
"""
    
    memory = temp_storage._parse_single_memory(
        yaml.safe_load(markdown.split('---\n')[1]),
        markdown.split('---\n')[2]
    )
    
    assert memory is not None
    assert memory.id == "test-002"
    assert memory.type == MemoryType.DAILY_SUMMARY
    assert memory.title == "测试摘要"
    assert memory.content.strip() == "# 标题\n\n内容"
    assert memory.metadata == {"key": "value"}
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/memory/storage/test_file_backend.py::test_memory_to_markdown -v
```
Expected: FAIL with "ImportError: cannot import name 'FileBackend'"

- [ ] **Step 3: 实现 FileBackend（Markdown 转换部分）**

```python
# trendradar/memory/storage/file.py
"""
文件存储后端
"""
import yaml
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from trendradar.memory.models import Memory, MemoryType
from trendradar.memory.storage.base import StorageBackend
from trendradar.memory.storage.exceptions import (
    MemoryStorageError,
    MemoryParseError,
    MemoryCorruptedError
)


class FileBackend(StorageBackend):
    """文件存储后端"""
    
    def __init__(self, base_path: str, auto_index: bool = True):
        """
        初始化文件后端
        
        Args:
            base_path: 基础路径
            auto_index: 是否自动更新索引
        """
        self.base_path = Path(base_path)
        self.auto_index = auto_index
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """确保所有类型目录存在"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        for mem_type in [MemoryType.DAILY_SUMMARY, MemoryType.WEEKLY_DIGEST,
                         MemoryType.TOPIC_INSIGHT, MemoryType.PATTERN, MemoryType.SIGNAL]:
            (self.base_path / mem_type).mkdir(exist_ok=True)
    
    def _memory_to_markdown(self, memory: Memory) -> str:
        """
        将 Memory 对象转换为 Markdown 格式
        
        Args:
            memory: 记忆对象
            
        Returns:
            Markdown 格式字符串
        """
        # Frontmatter
        frontmatter = {
            'id': memory.id,
            'type': memory.type,
            'title': memory.title,
            'description': memory.description,
            'created_at': memory.created_at.isoformat(),
            'updated_at': memory.updated_at.isoformat(),
            'metadata': memory.metadata
        }
        
        yaml_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        # 组合 Markdown
        markdown = f"---\n{yaml_str}---\n\n{memory.content}\n"
        
        return markdown
    
    def _parse_single_memory(self, yaml_content: dict, md_content: str) -> Optional[Memory]:
        """
        解析单个记忆
        
        Args:
            yaml_content: YAML 解析后的字典
            md_content: Markdown 内容
            
        Returns:
            Memory 对象
            
        Raises:
            MemoryParseError: 解析失败
            MemoryCorruptedError: 数据损坏
        """
        try:
            return Memory(
                id=yaml_content['id'],
                type=yaml_content['type'],
                title=yaml_content['title'],
                description=yaml_content.get('description'),
                content=md_content.strip(),
                metadata=yaml_content.get('metadata', {}),
                created_at=datetime.fromisoformat(yaml_content['created_at']),
                updated_at=datetime.fromisoformat(yaml_content['updated_at'])
            )
        except KeyError as e:
            raise MemoryCorruptedError(f"Missing required field: {e}")
        except (ValueError, TypeError) as e:
            raise MemoryParseError(f"Failed to parse memory: {e}")
    
    # 暂时实现占位方法，后续完成
    def create_memory(self, memory: Memory) -> None:
        raise NotImplementedError()
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        raise NotImplementedError()
    
    def update_memory(self, memory: Memory) -> None:
        raise NotImplementedError()
    
    def delete_memory(self, memory_id: str) -> None:
        raise NotImplementedError()
    
    def list_memories(
        self,
        memory_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        raise NotImplementedError()
    
    def search_memories(self, keyword: str, limit: Optional[int] = None) -> List[Memory]:
        raise NotImplementedError()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/memory/storage/test_file_backend.py::test_memory_to_markdown -v
pytest tests/memory/storage/test_file_backend.py::test_markdown_to_memory -v
```
Expected: 2 tests PASS

- [ ] **Step 5: 提交**

```bash
git add trendradar/memory/storage/file.py tests/memory/storage/test_file_backend.py
git commit -m "feat(memory): 实现 FileBackend Markdown 转换

- 实现 Memory 到 Markdown 的转换
- 实现 Markdown 到 Memory 的解析
- 添加单元测试

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: 实现 FileBackend - 文件操作

**Files:**
- Modify: `trendradar/memory/storage/file.py`
- Modify: `tests/memory/storage/test_file_backend.py`

- [ ] **Step 1: 添加文件操作测试**

```python
# 追加到 tests/memory/storage/test_file_backend.py

def test_get_file_path(temp_storage):
    """测试获取文件路径"""
    memory = Memory(
        id="test-003",
        type=MemoryType.DAILY_SUMMARY,
        title="测试",
        content="内容",
        metadata={"date": "2026-05-01"},
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1)
    )
    
    path = temp_storage._get_file_path(memory)
    
    assert path == temp_storage.base_path / "daily_summary" / "2026-05.md"


def test_create_memory(temp_storage):
    """测试创建记忆"""
    memory = Memory(
        id="test-004",
        type=MemoryType.DAILY_SUMMARY,
        title="测试摘要",
        content="测试内容",
        metadata={"date": "2026-05-01"},
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1)
    )
    
    temp_storage.create_memory(memory)
    
    # 验证文件存在
    file_path = temp_storage.base_path / "daily_summary" / "2026-05.md"
    assert file_path.exists()
    
    # 验证内容
    content = file_path.read_text(encoding='utf-8')
    assert "id: test-004" in content
    assert "测试内容" in content


def test_get_memory(temp_storage):
    """测试获取记忆"""
    memory = Memory(
        id="test-005",
        type=MemoryType.DAILY_SUMMARY,
        title="测试",
        content="内容",
        metadata={"date": "2026-05-01"},
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1)
    )
    
    temp_storage.create_memory(memory)
    retrieved = temp_storage.get_memory("test-005")
    
    assert retrieved is not None
    assert retrieved.id == "test-005"
    assert retrieved.title == "测试"


def test_get_memory_not_found(temp_storage):
    """测试获取不存在的记忆"""
    result = temp_storage.get_memory("non-existent")
    assert result is None


def test_list_memories(temp_storage):
    """测试列出记忆"""
    # 创建多个记忆
    for i in range(3):
        memory = Memory(
            id=f"test-{i}",
            type=MemoryType.DAILY_SUMMARY,
            title=f"标题 {i}",
            content=f"内容 {i}",
            metadata={"date": f"2026-05-0{i+1}"},
            created_at=datetime(2026, 5, i+1),
            updated_at=datetime(2026, 5, i+1)
        )
        temp_storage.create_memory(memory)
    
    # 不带过滤
    all_memories = temp_storage.list_memories()
    assert len(all_memories) == 3
    
    # 按类型过滤
    daily_memories = temp_storage.list_memories(memory_type=MemoryType.DAILY_SUMMARY)
    assert len(daily_memories) == 3
    
    # 限制数量
    limited = temp_storage.list_memories(limit=2)
    assert len(limited) == 2


def test_search_memories(temp_storage):
    """测试搜索记忆"""
    memory1 = Memory(
        id="search-1",
        type=MemoryType.DAILY_SUMMARY,
        title="包含AI的标题",
        content="内容",
        metadata={"date": "2026-05-01"},
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1)
    )
    memory2 = Memory(
        id="search-2",
        type=MemoryType.DAILY_SUMMARY,
        title="普通标题",
        content="包含AI的内容",
        metadata={"date": "2026-05-02"},
        created_at=datetime(2026, 5, 2),
        updated_at=datetime(2026, 5, 2)
    )
    temp_storage.create_memory(memory1)
    temp_storage.create_memory(memory2)
    
    results = temp_storage.search_memories("AI")
    assert len(results) == 2


def test_update_memory(temp_storage):
    """测试更新记忆"""
    memory = Memory(
        id="update-1",
        type=MemoryType.DAILY_SUMMARY,
        title="原标题",
        content="原内容",
        metadata={"date": "2026-05-01"},
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1)
    )
    temp_storage.create_memory(memory)
    
    # 更新
    updated_memory = Memory(
        id="update-1",
        type=MemoryType.DAILY_SUMMARY,
        title="新标题",
        content="新内容",
        metadata={"date": "2026-05-01"},
        created_at=memory.created_at,
        updated_at=datetime(2026, 5, 2)
    )
    temp_storage.update_memory(updated_memory)
    
    # 验证
    retrieved = temp_storage.get_memory("update-1")
    assert retrieved.title == "新标题"
    assert retrieved.content == "新内容"


def test_delete_memory(temp_storage):
    """测试删除记忆"""
    memory = Memory(
        id="delete-1",
        type=MemoryType.DAILY_SUMMARY,
        title="待删除",
        content="内容",
        metadata={"date": "2026-05-01"},
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1)
    )
    temp_storage.create_memory(memory)
    
    temp_storage.delete_memory("delete-1")
    
    assert temp_storage.get_memory("delete-1") is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/memory/storage/test_file_backend.py::test_create_memory -v
```
Expected: FAIL with "NotImplementedError"

- [ ] **Step 3: 实现文件操作方法**

```python
# 更新 trendradar/memory/storage/file.py，替换 NotImplementedError 方法

    def _get_file_path(self, memory: Memory) -> Path:
        """
        根据记忆类型和日期确定文件路径
        
        Args:
            memory: 记忆对象
            
        Returns:
            文件路径
        """
        type_dir = self.base_path / memory.type
        
        # 提取日期（从 metadata 或 created_at）
        date_str = memory.metadata.get('date')
        if date_str:
            date = datetime.fromisoformat(date_str) if isinstance(date_str, str) else date_str
        else:
            date = memory.created_at
        
        # 月度文件名
        file_name = f"{date.year}-{date.month:02d}.md"
        return type_dir / file_name
    
    def create_memory(self, memory: Memory) -> None:
        """创建记忆"""
        try:
            # 1. 确定文件路径
            file_path = self._get_file_path(memory)
            
            # 2. 生成 Markdown 内容
            content = self._memory_to_markdown(memory)
            
            # 3. 写入文件（追加或创建）
            if file_path.exists():
                # 追加到现有文件
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write('\n')
                    f.write(content)
            else:
                # 创建新文件
                file_path.write_text(content, encoding='utf-8')
            
        except (OSError, IOError) as e:
            raise MemoryStorageError(f"Failed to write file: {e}")
    
    def _parse_markdown_file(self, file_path: Path) -> List[Memory]:
        """
        解析 Markdown 文件，提取所有记忆
        
        Args:
            file_path: 文件路径
            
        Returns:
            记忆对象列表
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except (OSError, IOError, UnicodeDecodeError) as e:
            raise MemoryParseError(f"Failed to read file {file_path}: {e}")
        
        # 按 frontmatter 分割（一个文件可能包含多个记忆）
        memories = []
        parts = content.split('---\n')
        
        i = 1  # 跳过第一个空部分
        while i < len(parts) - 1:
            yaml_content = parts[i]
            md_content = parts[i + 1] if i + 1 < len(parts) else ""
            
            try:
                data = yaml.safe_load(yaml_content)
                memory = self._parse_single_memory(data, md_content)
                if memory:
                    memories.append(memory)
            except yaml.YAMLError as e:
                # 跳过解析失败的记忆
                print(f"Warning: Failed to parse memory in {file_path}: {e}")
            
            i += 2
        
        return memories
    
    def _find_file_by_id(self, memory_id: str) -> Optional[Path]:
        """
        查找包含指定记忆的文件
        
        Args:
            memory_id: 记忆 ID
            
        Returns:
            文件路径，如果不存在则返回 None
        """
        # 扫描所有类型目录
        for type_dir in self.base_path.iterdir():
            if not type_dir.is_dir() or type_dir.name == 'archive':
                continue
            
            # 扫描该类型下的所有 .md 文件
            for md_file in type_dir.glob("**/*.md"):
                try:
                    content = md_file.read_text(encoding='utf-8')
                    if f"id: {memory_id}" in content:
                        return md_file
                except (OSError, IOError):
                    continue
        
        return None
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        try:
            # 1. 查找文件
            file_path = self._find_file_by_id(memory_id)
            if not file_path:
                return None
            
            # 2. 解析文件中的所有记忆
            memories = self._parse_markdown_file(file_path)
            
            # 3. 查找匹配的记忆
            for memory in memories:
                if memory.id == memory_id:
                    return memory
            
            return None
        except MemoryParseError:
            raise
        except Exception as e:
            raise MemoryStorageError(f"Failed to get memory {memory_id}: {e}")
    
    def list_memories(
        self,
        memory_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """列出记忆"""
        try:
            # 1. 确定扫描目录
            if memory_type:
                dirs = [self.base_path / memory_type]
            else:
                dirs = [d for d in self.base_path.iterdir() 
                       if d.is_dir() and d.name not in ('archive', '.git')]
            
            # 2. 扫描所有 .md 文件
            memories = []
            for dir_path in dirs:
                if not dir_path.exists():
                    continue
                for md_file in dir_path.glob("**/*.md"):
                    if md_file.name == "MEMORY.md":
                        continue
                    memories.extend(self._parse_markdown_file(md_file))
            
            # 3. 过滤日期范围
            if start_date:
                memories = [m for m in memories if m.created_at >= start_date]
            if end_date:
                memories = [m for m in memories if m.created_at <= end_date]
            
            # 4. 排序和限制
            memories.sort(key=lambda m: m.created_at, reverse=True)
            if limit:
                memories = memories[:limit]
            
            return memories
        except Exception as e:
            raise MemoryStorageError(f"Failed to list memories: {e}")
    
    def search_memories(self, keyword: str, limit: Optional[int] = None) -> List[Memory]:
        """搜索记忆"""
        all_memories = self.list_memories()
        
        # 简单文本匹配
        results = [
            m for m in all_memories
            if keyword in m.title or keyword in m.content
        ]
        
        if limit:
            results = results[:limit]
        
        return results
    
    def update_memory(self, memory: Memory) -> None:
        """更新记忆"""
        try:
            # 1. 查找文件
            file_path = self._find_file_by_id(memory.id)
            if not file_path:
                raise MemoryNotFoundError(f"Memory with id '{memory.id}' not found")
            
            # 2. 解析文件中的所有记忆
            memories = self._parse_markdown_file(file_path)
            
            # 3. 更新匹配的记忆
            updated = False
            for i, mem in enumerate(memories):
                if mem.id == memory.id:
                    memories[i] = memory
                    updated = True
                    break
            
            if not updated:
                raise MemoryNotFoundError(f"Memory with id '{memory.id}' not found")
            
            # 4. 重新写入文件
            content = '\n'.join(self._memory_to_markdown(mem) for mem in memories)
            file_path.write_text(content, encoding='utf-8')
            
        except MemoryNotFoundError:
            raise
        except Exception as e:
            raise MemoryStorageError(f"Failed to update memory {memory.id}: {e}")
    
    def delete_memory(self, memory_id: str) -> None:
        """删除记忆"""
        try:
            # 1. 查找文件
            file_path = self._find_file_by_id(memory_id)
            if not file_path:
                return  # 已经不存在，视为成功
            
            # 2. 解析文件中的所有记忆
            memories = self._parse_markdown_file(file_path)
            
            # 3. 过滤掉要删除的记忆
            remaining = [m for m in memories if m.id != memory_id]
            
            # 4. 重新写入文件或删除文件
            if remaining:
                content = '\n'.join(self._memory_to_markdown(mem) for mem in remaining)
                file_path.write_text(content, encoding='utf-8')
            else:
                file_path.unlink()
            
        except Exception as e:
            raise MemoryStorageError(f"Failed to delete memory {memory_id}: {e}")
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/memory/storage/test_file_backend.py -v
```
Expected: All tests PASS

- [ ] **Step 5: 更新 storage __init__.py**

```python
# 更新 trendradar/memory/storage/__init__.py
from trendradar.memory.storage.base import StorageBackend
from trendradar.memory.storage.database import DatabaseBackend
from trendradar.memory.storage.file import FileBackend
from trendradar.memory.storage.exceptions import (
    MemoryStorageError,
    MemoryNotFoundError,
    MemoryAlreadyExistsError,
    MemoryParseError,
    MemoryCorruptedError
)

__all__ = [
    'StorageBackend',
    'DatabaseBackend',
    'FileBackend',
    'MemoryStorageError',
    'MemoryNotFoundError',
    'MemoryAlreadyExistsError',
    'MemoryParseError',
    'MemoryCorruptedError',
]
```

- [ ] **Step 6: 提交**

```bash
git add trendradar/memory/storage/file.py tests/memory/storage/test_file_backend.py trendradar/memory/storage/__init__.py
git commit -m "feat(memory): 实现 FileBackend 文件操作

- 实现 create/get/update/delete/list/search 方法
- 支持多记忆按月合并到文件
- 添加完整的单元测试

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

---

## Task 5: 重构 MemoryRepository 使用依赖注入

**Files:**
- Modify: `trendradar/memory/models.py:68-477`
- Create: `tests/memory/test_repository_refactor.py`

- [ ] **Step 1: 创建重构后的 MemoryRepository 测试**

```python
# tests/memory/test_repository_refactor.py
import pytest
from datetime import datetime
from trendradar.memory.models import Memory, MemoryType, MemoryRepository
from trendradar.memory.storage import DatabaseBackend, FileBackend


@pytest.fixture
def db_repository(tmp_path):
    """使用 DatabaseBackend 的 repository"""
    db_path = str(tmp_path / "test.db")
    backend = DatabaseBackend(db_path)
    return MemoryRepository(backend)


@pytest.fixture
def file_repository(tmp_path):
    """使用 FileBackend 的 repository"""
    file_path = str(tmp_path / "memory")
    backend = FileBackend(file_path, auto_index=False)
    return MemoryRepository(backend)


def test_repository_with_database_backend(db_repository):
    """测试 Repository 使用 DatabaseBackend"""
    memory = Memory(
        id="repo-db-001",
        type=MemoryType.DAILY_SUMMARY,
        title="测试",
        content="内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    db_repository.create(memory)
    retrieved = db_repository.get_by_id("repo-db-001")
    
    assert retrieved is not None
    assert retrieved.id == "repo-db-001"


def test_repository_with_file_backend(file_repository):
    """测试 Repository 使用 FileBackend"""
    memory = Memory(
        id="repo-file-001",
        type=MemoryType.DAILY_SUMMARY,
        title="测试",
        content="内容",
        metadata={"date": "2026-05-01"},
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1)
    )
    
    file_repository.create(memory)
    retrieved = file_repository.get_by_id("repo-file-001")
    
    assert retrieved is not None
    assert retrieved.id == "repo-file-001"


def test_repository_interface_compatibility(db_repository):
    """测试 Repository 接口兼容性"""
    memory = Memory(
        id="compat-001",
        type=MemoryType.DAILY_SUMMARY,
        title="测试",
        content="内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # 测试所有公共方法
    db_repository.create(memory)
    assert db_repository.get_by_id("compat-001") is not None
    
    memories = db_repository.get_by_type(MemoryType.DAILY_SUMMARY)
    assert len(memories) == 1
    
    results = db_repository.search("测试")
    assert len(results) == 1
    
    db_repository.delete("compat-001")
    assert db_repository.get_by_id("compat-001") is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/memory/test_repository_refactor.py::test_repository_with_database_backend -v
```
Expected: FAIL with "TypeError: __init__() takes X positional arguments but Y were given"

- [ ] **Step 3: 重构 MemoryRepository 构造函数**

```python
# 修改 trendradar/memory/models.py MemoryRepository 类

class MemoryRepository:
    """
    记忆仓库（门面类）

    提供记忆和记忆链接的数据库访问功能。
    """

    def __init__(self, backend: 'StorageBackend'):
        """
        初始化记忆仓库

        Args:
            backend: 存储后端实例
        """
        self.backend = backend

    def create(self, memory: Memory) -> None:
        """
        创建新记忆

        Args:
            memory: 记忆对象

        Raises:
            MemoryStorageError: 如果创建失败
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
        """
        self.backend.update_memory(memory)

    def delete(self, memory_id: str) -> None:
        """
        删除记忆

        Args:
            memory_id: 记忆 ID
        """
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

    # 链接相关方法保持现有实现（使用 backend 的 db_path 如果有）
    # 注意：FileBackend 不支持链接，这些方法需要特殊处理或废弃
```

- [ ] **Step 4: 添加类型导入**

```python
# 在 trendradar/memory/models.py 文件顶部添加
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trendradar.memory.storage.base import StorageBackend
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/memory/test_repository_refactor.py -v
```
Expected: All tests PASS

- [ ] **Step 6: 提交**

```bash
git add trendradar/memory/models.py tests/memory/test_repository_refactor.py
git commit -m "refactor(memory): 重构 MemoryRepository 使用依赖注入

- 修改构造函数接受 StorageBackend 参数
- 委托所有操作到 backend
- 保持公共接口不变
- 添加兼容性测试

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: 实现 MemoryIndexManager

**Files:**
- Create: `trendradar/memory/index_manager.py`
- Create: `tests/memory/test_index_manager.py`

- [ ] **Step 1: 创建 IndexManager 测试**

```python
# tests/memory/test_index_manager.py
import pytest
from datetime import datetime
from pathlib import Path

from trendradar.memory.models import Memory, MemoryType
from trendradar.memory.index_manager import MemoryIndexManager
from trendradar.memory.storage.file import FileBackend


@pytest.fixture
def temp_backend(tmp_path):
    """临时文件存储"""
    backend = FileBackend(str(tmp_path), auto_index=False)
    
    # 创建一些测试记忆
    for i in range(3):
        memory = Memory(
            id=f"test-{i}",
            type=MemoryType.DAILY_SUMMARY,
            title=f"测试摘要 {i}",
            description=f"描述 {i}",
            content=f"内容 {i}",
            metadata={
                "date": f"2026-05-0{i+1}",
                "top_keywords": ["AI", "区块链"]
            },
            created_at=datetime(2026, 5, i+1),
            updated_at=datetime(2026, 5, i+1)
        )
        backend.create_memory(memory)
    
    return backend


@pytest.fixture
def index_manager(temp_backend):
    """索引管理器"""
    return MemoryIndexManager(temp_backend.base_path)


def test_update_index(index_manager, temp_backend):
    """测试更新索引"""
    index_manager.update_index()
    
    index_file = temp_backend.base_path / "MEMORY.md"
    assert index_file.exists()
    
    content = index_file.read_text(encoding='utf-8')
    assert "TrendRadar 记忆索引" in content
    assert "每日摘要" in content
    assert "test-0" in content


def test_index_content_format(index_manager, temp_backend):
    """测试索引内容格式"""
    index_manager.update_index()
    
    index_file = temp_backend.base_path / "MEMORY.md"
    content = index_file.read_text(encoding='utf-8')
    
    # 验证格式
    assert content.startswith("# TrendRadar 记忆索引")
    assert "更新时间：" in content
    assert "## 每日摘要 (daily_summary)" in content
    assert "关键词：AI、区块链" in content


def test_scan_file(index_manager, temp_backend):
    """测试扫描文件"""
    file_path = temp_backend.base_path / "daily_summary" / "2026-05.md"
    entries = index_manager._scan_file(file_path)
    
    assert len(entries) == 3
    assert entries[0]['id'] == "test-0"
    assert entries[0]['title'] == "测试摘要 0"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/memory/test_index_manager.py::test_update_index -v
```
Expected: FAIL with "ImportError: cannot import name 'MemoryIndexManager'"

- [ ] **Step 3: 实现 MemoryIndexManager**

```python
# trendradar/memory/index_manager.py
"""
记忆索引管理器
"""
import yaml
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from trendradar.memory.models import MemoryType


class MemoryIndexManager:
    """记忆索引管理器"""
    
    def __init__(self, base_path: Path):
        """
        初始化索引管理器
        
        Args:
            base_path: 记忆文件基础路径
        """
        self.base_path = Path(base_path)
        self.index_file = self.base_path / "MEMORY.md"
    
    def update_index(self) -> None:
        """扫描所有记忆文件，重新生成索引"""
        # 扫描所有类型
        all_memories = {}
        for mem_type in [MemoryType.DAILY_SUMMARY, MemoryType.WEEKLY_DIGEST,
                         MemoryType.TOPIC_INSIGHT, MemoryType.PATTERN, MemoryType.SIGNAL]:
            type_dir = self.base_path / mem_type
            if not type_dir.exists():
                continue
            
            memories = []
            for md_file in type_dir.glob("**/*.md"):
                if md_file.name == "MEMORY.md":
                    continue
                memories.extend(self._scan_file(md_file))
            
            all_memories[mem_type] = sorted(
                memories,
                key=lambda m: m['created_at'],
                reverse=True
            )
        
        # 生成索引内容
        content = self._generate_index_content(all_memories)
        
        # 写入文件
        self.index_file.write_text(content, encoding='utf-8')
    
    def _scan_file(self, file_path: Path) -> List[Dict]:
        """
        扫描文件提取索引信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            索引条目列表
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except (OSError, IOError, UnicodeDecodeError) as e:
            print(f"Warning: Failed to read {file_path}: {e}")
            return []
        
        parts = content.split('---\n')
        
        entries = []
        i = 1
        while i < len(parts) - 1:
            try:
                data = yaml.safe_load(parts[i])
                
                # 提取关键信息
                entries.append({
                    'id': data['id'],
                    'title': data['title'],
                    'description': data.get('description', ''),
                    'created_at': datetime.fromisoformat(data['created_at']),
                    'file_path': file_path.relative_to(self.base_path),
                    'metadata': data.get('metadata', {})
                })
            except (yaml.YAMLError, KeyError, ValueError) as e:
                print(f"Warning: Failed to parse entry in {file_path}: {e}")
            
            i += 2
        
        return entries
    
    def _generate_index_content(self, all_memories: Dict[str, List]) -> str:
        """
        生成索引 Markdown 内容
        
        Args:
            all_memories: 按类型分组的记忆列表
            
        Returns:
            Markdown 格式的索引内容
        """
        lines = [
            "# TrendRadar 记忆索引",
            "",
            f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        type_names = {
            'daily_summary': '每日摘要',
            'weekly_digest': '每周摘要',
            'topic_insight': '主题洞察',
            'pattern': '模式识别',
            'signal': '信号记录'
        }
        
        for mem_type, memories in all_memories.items():
            if not memories:
                continue
            
            lines.append(f"## {type_names.get(mem_type, mem_type)} ({mem_type})")
            lines.append("")
            
            for memory in memories[:20]:  # 每类最多显示 20 条
                # 提取简要信息
                date = memory['created_at'].strftime('%Y-%m-%d')
                desc = memory['description']
                if len(desc) > 50:
                    desc = desc[:47] + '...'
                
                # 提取关键词
                keywords = memory['metadata'].get('top_keywords', [])
                keywords_str = '、'.join(keywords[:3]) if keywords else ''
                
                link = f"{memory['file_path']}#{memory['id']}"
                
                line = f"- [{date}]({link}) — {desc}"
                if keywords_str:
                    line += f"，关键词：{keywords_str}"
                lines.append(line)
            
            lines.append("")
        
        return '\n'.join(lines)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/memory/test_index_manager.py -v
```
Expected: All tests PASS

- [ ] **Step 5: 集成索引自动更新到 FileBackend**

```python
# 修改 trendradar/memory/storage/file.py

# 在文件顶部导入
from trendradar.memory.index_manager import MemoryIndexManager

# 在 __init__ 方法中初始化
    def __init__(self, base_path: str, auto_index: bool = True):
        self.base_path = Path(base_path)
        self.auto_index = auto_index
        self.index_manager = MemoryIndexManager(self.base_path) if auto_index else None
        self._ensure_directories()

# 在 create_memory 末尾添加
    def create_memory(self, memory: Memory) -> None:
        # ... 现有逻辑 ...
        
        # 更新索引
        if self.index_manager:
            self.index_manager.update_index()

# 在 update_memory 和 delete_memory 末尾也添加类似逻辑
```

- [ ] **Step 6: 提交**

```bash
git add trendradar/memory/index_manager.py tests/memory/test_index_manager.py trendradar/memory/storage/file.py
git commit -m "feat(memory): 实现 MemoryIndexManager 索引管理

- 实现索引文件生成和更新
- 扫描所有记忆文件提取信息
- 集成到 FileBackend 自动更新
- 添加完整测试

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: 实现工厂函数

**Files:**
- Create: `trendradar/memory/factory.py`
- Create: `tests/memory/test_factory.py`

- [ ] **Step 1: 创建工厂函数测试**

```python
# tests/memory/test_factory.py
import pytest
from trendradar.memory.factory import create_memory_repository
from trendradar.memory.storage import DatabaseBackend, FileBackend


def test_create_database_repository(tmp_path):
    """测试创建数据库 repository"""
    config = {
        "storage_type": "database",
        "database_storage": {
            "db_path": str(tmp_path / "test.db")
        }
    }
    
    repo = create_memory_repository(config)
    
    assert repo is not None
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
    
    assert repo is not None
    assert isinstance(repo.backend, FileBackend)


def test_create_with_invalid_type():
    """测试无效的存储类型"""
    config = {"storage_type": "invalid"}
    
    with pytest.raises(ValueError, match="Unknown storage type"):
        create_memory_repository(config)


def test_default_to_database(tmp_path):
    """测试默认使用数据库"""
    config = {
        "database_storage": {
            "db_path": str(tmp_path / "test.db")
        }
    }
    
    repo = create_memory_repository(config)
    assert isinstance(repo.backend, DatabaseBackend)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/memory/test_factory.py::test_create_database_repository -v
```
Expected: FAIL with "ImportError: cannot import name 'create_memory_repository'"

- [ ] **Step 3: 实现工厂函数**

```python
# trendradar/memory/factory.py
"""
记忆仓库工厂函数
"""
from typing import Dict, Any

from trendradar.memory.models import MemoryRepository
from trendradar.memory.storage import DatabaseBackend, FileBackend


def create_memory_repository(config: Dict[str, Any]) -> MemoryRepository:
    """
    根据配置创建 MemoryRepository
    
    Args:
        config: 配置字典，包含 storage_type 和相应的配置
        
    Returns:
        MemoryRepository 实例
        
    Raises:
        ValueError: 如果存储类型未知
        
    Examples:
        >>> config = {
        ...     "storage_type": "database",
        ...     "database_storage": {"db_path": "memory.db"}
        ... }
        >>> repo = create_memory_repository(config)
        
        >>> config = {
        ...     "storage_type": "file",
        ...     "file_storage": {
        ...         "base_path": "./output/memory",
        ...         "auto_index": True
        ...     }
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/memory/test_factory.py -v
```
Expected: All tests PASS

- [ ] **Step 5: 更新 memory __init__.py**

```python
# 修改 trendradar/memory/__init__.py
from trendradar.memory.models import (
    MemoryType,
    LinkType,
    Memory,
    MemoryLink,
    MemoryRepository
)
from trendradar.memory.generator import MemoryGenerator
from trendradar.memory.query import MemoryQueryEngine
from trendradar.memory.factory import create_memory_repository

__all__ = [
    'MemoryType',
    'LinkType',
    'Memory',
    'MemoryLink',
    'MemoryRepository',
    'MemoryGenerator',
    'MemoryQueryEngine',
    'create_memory_repository',
]
```

- [ ] **Step 6: 提交**

```bash
git add trendradar/memory/factory.py tests/memory/test_factory.py trendradar/memory/__init__.py
git commit -m "feat(memory): 添加工厂函数创建 repository

- 实现 create_memory_repository 工厂函数
- 支持根据配置创建不同类型的 backend
- 添加完整测试和文档

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

由于计划非常长，我将保存计划并直接开始实施。用户说不需要再询问意见，让我直接一口气开发完，所以我现在调用 subagent-driven-development skill 开始实施。
