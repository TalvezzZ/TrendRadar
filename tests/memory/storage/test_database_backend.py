"""
DatabaseBackend 单元测试
"""
import pytest
import sqlite3
from datetime import datetime
from pathlib import Path

from trendradar.memory.models import Memory, MemoryType
from trendradar.memory.storage import (
    MemoryNotFoundError,
    MemoryAlreadyExistsError,
    MemoryStorageError
)
from trendradar.memory.storage.database import DatabaseBackend


@pytest.fixture
def test_db(tmp_path):
    """创建测试数据库"""
    db_path = tmp_path / "test_memory.db"
    backend = DatabaseBackend(str(db_path))
    return backend


@pytest.fixture
def sample_memory():
    """创建示例记忆对象"""
    return Memory(
        id="test-001",
        type=MemoryType.DAILY_SUMMARY,
        title="Test Memory",
        description="Test description",
        content="Test content",
        metadata={"key": "value"},
        created_at=datetime(2026, 5, 12, 10, 0, 0),
        updated_at=datetime(2026, 5, 12, 10, 0, 0)
    )


def test_create_memory(test_db, sample_memory):
    """测试创建记忆"""
    test_db.create_memory(sample_memory)

    # 直接通过 SQL 验证
    conn = sqlite3.connect(test_db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, title FROM memories WHERE id = ?", (sample_memory.id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == sample_memory.id
    assert row[1] == sample_memory.type
    assert row[2] == sample_memory.title


def test_create_memory_duplicate(test_db, sample_memory):
    """测试创建重复记忆"""
    test_db.create_memory(sample_memory)

    with pytest.raises(MemoryAlreadyExistsError):
        test_db.create_memory(sample_memory)


def test_get_memory(test_db, sample_memory):
    """测试获取记忆"""
    test_db.create_memory(sample_memory)

    retrieved = test_db.get_memory(sample_memory.id)

    assert retrieved is not None
    assert retrieved.id == sample_memory.id
    assert retrieved.type == sample_memory.type
    assert retrieved.title == sample_memory.title
    assert retrieved.description == sample_memory.description
    assert retrieved.content == sample_memory.content
    assert retrieved.metadata == sample_memory.metadata
    assert retrieved.created_at == sample_memory.created_at
    assert retrieved.updated_at == sample_memory.updated_at


def test_get_memory_not_found(test_db):
    """测试获取不存在的记忆"""
    result = test_db.get_memory("non-existent-id")
    assert result is None


def test_update_memory(test_db, sample_memory):
    """测试更新记忆"""
    test_db.create_memory(sample_memory)

    # 创建更新后的记忆
    updated_memory = Memory(
        id=sample_memory.id,
        type=MemoryType.WEEKLY_DIGEST,
        title="Updated Title",
        description="Updated description",
        content="Updated content",
        metadata={"new_key": "new_value"},
        created_at=sample_memory.created_at,
        updated_at=datetime(2026, 5, 12, 11, 0, 0)
    )

    test_db.update_memory(updated_memory)

    # 验证更新
    retrieved = test_db.get_memory(sample_memory.id)
    assert retrieved.title == "Updated Title"
    assert retrieved.description == "Updated description"
    assert retrieved.content == "Updated content"
    assert retrieved.type == MemoryType.WEEKLY_DIGEST
    assert retrieved.metadata == {"new_key": "new_value"}
    assert retrieved.updated_at == updated_memory.updated_at


def test_update_memory_not_found(test_db, sample_memory):
    """测试更新不存在的记忆"""
    with pytest.raises(MemoryNotFoundError):
        test_db.update_memory(sample_memory)


def test_delete_memory(test_db, sample_memory):
    """测试删除记忆"""
    test_db.create_memory(sample_memory)

    test_db.delete_memory(sample_memory.id)

    # 验证已删除
    result = test_db.get_memory(sample_memory.id)
    assert result is None


def test_delete_memory_with_links(test_db, tmp_path):
    """测试删除带有链接的记忆"""
    # 创建两个记忆
    memory1 = Memory(
        id="mem-001",
        type=MemoryType.DAILY_SUMMARY,
        title="Memory 1",
        content="Content 1",
        created_at=datetime(2026, 5, 12, 10, 0, 0),
        updated_at=datetime(2026, 5, 12, 10, 0, 0)
    )
    memory2 = Memory(
        id="mem-002",
        type=MemoryType.DAILY_SUMMARY,
        title="Memory 2",
        content="Content 2",
        created_at=datetime(2026, 5, 12, 10, 0, 0),
        updated_at=datetime(2026, 5, 12, 10, 0, 0)
    )

    test_db.create_memory(memory1)
    test_db.create_memory(memory2)

    # 创建链接
    conn = sqlite3.connect(test_db.db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO memory_links (from_memory_id, to_memory_id, link_type) VALUES (?, ?, ?)",
        (memory1.id, memory2.id, "supports")
    )
    conn.commit()
    conn.close()

    # 删除记忆1，链接也应该被删除
    test_db.delete_memory(memory1.id)

    # 验证记忆已删除
    assert test_db.get_memory(memory1.id) is None

    # 验证链接已删除
    conn = sqlite3.connect(test_db.db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM memory_links WHERE from_memory_id = ? OR to_memory_id = ?",
        (memory1.id, memory1.id)
    )
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 0


def test_list_memories_no_filter(test_db):
    """测试列出所有记忆"""
    memories = [
        Memory(
            id=f"mem-{i}",
            type=MemoryType.DAILY_SUMMARY,
            title=f"Memory {i}",
            content=f"Content {i}",
            created_at=datetime(2026, 5, i+1, 10, 0, 0),
            updated_at=datetime(2026, 5, i+1, 10, 0, 0)
        )
        for i in range(1, 4)
    ]

    for memory in memories:
        test_db.create_memory(memory)

    result = test_db.list_memories()

    assert len(result) == 3
    # 应该按创建时间倒序
    assert result[0].id == "mem-3"
    assert result[1].id == "mem-2"
    assert result[2].id == "mem-1"


def test_list_memories_by_type(test_db):
    """测试按类型列出记忆"""
    memories = [
        Memory(
            id="mem-1",
            type=MemoryType.DAILY_SUMMARY,
            title="Daily 1",
            content="Content 1",
            created_at=datetime(2026, 5, 1, 10, 0, 0),
            updated_at=datetime(2026, 5, 1, 10, 0, 0)
        ),
        Memory(
            id="mem-2",
            type=MemoryType.WEEKLY_DIGEST,
            title="Weekly 1",
            content="Content 2",
            created_at=datetime(2026, 5, 2, 10, 0, 0),
            updated_at=datetime(2026, 5, 2, 10, 0, 0)
        ),
        Memory(
            id="mem-3",
            type=MemoryType.DAILY_SUMMARY,
            title="Daily 2",
            content="Content 3",
            created_at=datetime(2026, 5, 3, 10, 0, 0),
            updated_at=datetime(2026, 5, 3, 10, 0, 0)
        )
    ]

    for memory in memories:
        test_db.create_memory(memory)

    result = test_db.list_memories(memory_type=MemoryType.DAILY_SUMMARY)

    assert len(result) == 2
    assert all(m.type == MemoryType.DAILY_SUMMARY for m in result)


def test_list_memories_with_limit(test_db):
    """测试限制返回数量"""
    memories = [
        Memory(
            id=f"mem-{i}",
            type=MemoryType.DAILY_SUMMARY,
            title=f"Memory {i}",
            content=f"Content {i}",
            created_at=datetime(2026, 5, i+1, 10, 0, 0),
            updated_at=datetime(2026, 5, i+1, 10, 0, 0)
        )
        for i in range(1, 6)
    ]

    for memory in memories:
        test_db.create_memory(memory)

    result = test_db.list_memories(limit=3)

    assert len(result) == 3


def test_list_memories_date_range(test_db):
    """测试日期范围过滤"""
    memories = [
        Memory(
            id="mem-1",
            type=MemoryType.DAILY_SUMMARY,
            title="Memory 1",
            content="Content 1",
            created_at=datetime(2026, 5, 1, 10, 0, 0),
            updated_at=datetime(2026, 5, 1, 10, 0, 0)
        ),
        Memory(
            id="mem-2",
            type=MemoryType.DAILY_SUMMARY,
            title="Memory 2",
            content="Content 2",
            created_at=datetime(2026, 5, 5, 10, 0, 0),
            updated_at=datetime(2026, 5, 5, 10, 0, 0)
        ),
        Memory(
            id="mem-3",
            type=MemoryType.DAILY_SUMMARY,
            title="Memory 3",
            content="Content 3",
            created_at=datetime(2026, 5, 10, 10, 0, 0),
            updated_at=datetime(2026, 5, 10, 10, 0, 0)
        )
    ]

    for memory in memories:
        test_db.create_memory(memory)

    result = test_db.list_memories(
        start_date=datetime(2026, 5, 3, 0, 0, 0),
        end_date=datetime(2026, 5, 8, 0, 0, 0)
    )

    assert len(result) == 1
    assert result[0].id == "mem-2"


def test_search_memories(test_db):
    """测试搜索记忆"""
    memories = [
        Memory(
            id="mem-1",
            type=MemoryType.DAILY_SUMMARY,
            title="Python Programming",
            content="Learning Python basics",
            created_at=datetime(2026, 5, 1, 10, 0, 0),
            updated_at=datetime(2026, 5, 1, 10, 0, 0)
        ),
        Memory(
            id="mem-2",
            type=MemoryType.DAILY_SUMMARY,
            title="Java Tutorial",
            content="Advanced Python concepts",
            created_at=datetime(2026, 5, 2, 10, 0, 0),
            updated_at=datetime(2026, 5, 2, 10, 0, 0)
        ),
        Memory(
            id="mem-3",
            type=MemoryType.DAILY_SUMMARY,
            title="JavaScript Guide",
            content="Web development",
            created_at=datetime(2026, 5, 3, 10, 0, 0),
            updated_at=datetime(2026, 5, 3, 10, 0, 0)
        )
    ]

    for memory in memories:
        test_db.create_memory(memory)

    # 搜索标题中包含 "Python" 的
    result = test_db.search_memories("Python")

    assert len(result) == 2
    assert any(m.id == "mem-1" for m in result)
    assert any(m.id == "mem-2" for m in result)


def test_search_memories_with_limit(test_db):
    """测试限制搜索结果数量"""
    memories = [
        Memory(
            id=f"mem-{i}",
            type=MemoryType.DAILY_SUMMARY,
            title=f"Python Tutorial {i}",
            content=f"Content {i}",
            created_at=datetime(2026, 5, i+1, 10, 0, 0),
            updated_at=datetime(2026, 5, i+1, 10, 0, 0)
        )
        for i in range(1, 6)
    ]

    for memory in memories:
        test_db.create_memory(memory)

    result = test_db.search_memories("Python", limit=3)

    assert len(result) == 3


def test_memory_with_null_description(test_db):
    """测试处理 NULL description"""
    memory = Memory(
        id="mem-null",
        type=MemoryType.DAILY_SUMMARY,
        title="Test Memory",
        description=None,
        content="Test content",
        created_at=datetime(2026, 5, 12, 10, 0, 0),
        updated_at=datetime(2026, 5, 12, 10, 0, 0)
    )

    test_db.create_memory(memory)
    retrieved = test_db.get_memory(memory.id)

    assert retrieved is not None
    assert retrieved.description is None


def test_memory_with_empty_metadata(test_db):
    """测试处理空 metadata"""
    memory = Memory(
        id="mem-empty-meta",
        type=MemoryType.DAILY_SUMMARY,
        title="Test Memory",
        content="Test content",
        metadata={},
        created_at=datetime(2026, 5, 12, 10, 0, 0),
        updated_at=datetime(2026, 5, 12, 10, 0, 0)
    )

    test_db.create_memory(memory)
    retrieved = test_db.get_memory(memory.id)

    assert retrieved is not None
    assert retrieved.metadata == {}
