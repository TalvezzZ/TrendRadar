"""
记忆数据模型测试
"""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from trendradar.persistence.schema import initialize_memory_db
from trendradar.memory.models import (
    MemoryType,
    LinkType,
    Memory,
    MemoryLink,
    MemoryRepository
)
from trendradar.memory.storage.database import DatabaseBackend
from trendradar.memory.storage.exceptions import MemoryAlreadyExistsError


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    yield db_path

    # 清理
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def initialized_db(temp_db):
    """初始化数据库表结构"""
    conn = initialize_memory_db(temp_db)
    conn.close()
    return temp_db


@pytest.fixture
def memory_repo(initialized_db):
    """创建记忆仓库实例"""
    backend = DatabaseBackend(initialized_db)
    return MemoryRepository(backend)


class TestMemoryType:
    """MemoryType 枚举测试"""

    def test_all_types_exist(self):
        """测试所有记忆类型是否定义"""
        assert MemoryType.DAILY_SUMMARY == 'daily_summary'
        assert MemoryType.WEEKLY_DIGEST == 'weekly_digest'
        assert MemoryType.TOPIC_INSIGHT == 'topic_insight'
        assert MemoryType.PATTERN == 'pattern'
        assert MemoryType.SIGNAL == 'signal'

    def test_type_values(self):
        """测试类型值与数据库约束一致"""
        db_types = {'daily_summary', 'weekly_digest', 'topic_insight', 'pattern', 'signal'}
        enum_values = {
            MemoryType.DAILY_SUMMARY,
            MemoryType.WEEKLY_DIGEST,
            MemoryType.TOPIC_INSIGHT,
            MemoryType.PATTERN,
            MemoryType.SIGNAL
        }
        assert enum_values == db_types


class TestLinkType:
    """LinkType 枚举测试"""

    def test_all_types_exist(self):
        """测试所有链接类型是否定义"""
        assert LinkType.SUPPORTS == 'supports'
        assert LinkType.CONTRADICTS == 'contradicts'
        assert LinkType.EXTENDS == 'extends'
        assert LinkType.DERIVES_FROM == 'derives_from'

    def test_type_values(self):
        """测试类型值与数据库约束一致"""
        db_types = {'supports', 'contradicts', 'extends', 'derives_from'}
        enum_values = {
            LinkType.SUPPORTS,
            LinkType.CONTRADICTS,
            LinkType.EXTENDS,
            LinkType.DERIVES_FROM
        }
        assert enum_values == db_types


class TestMemory:
    """Memory 数据类测试"""

    def test_create_memory_minimal(self):
        """测试创建最小化记忆"""
        memory = Memory(
            id='mem_001',
            type=MemoryType.DAILY_SUMMARY,
            title='Daily Summary',
            content='Summary content',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert memory.id == 'mem_001'
        assert memory.type == MemoryType.DAILY_SUMMARY
        assert memory.title == 'Daily Summary'
        assert memory.content == 'Summary content'
        assert memory.description is None
        assert memory.metadata == {}

    def test_create_memory_full(self):
        """测试创建完整记忆"""
        created = datetime.now()
        updated = created + timedelta(hours=1)
        metadata = {'source': 'test', 'tags': ['ai', 'tech']}

        memory = Memory(
            id='mem_002',
            type=MemoryType.TOPIC_INSIGHT,
            title='AI Topic Insight',
            description='Analysis of AI trends',
            content='Detailed content...',
            metadata=metadata,
            created_at=created,
            updated_at=updated
        )

        assert memory.id == 'mem_002'
        assert memory.type == MemoryType.TOPIC_INSIGHT
        assert memory.description == 'Analysis of AI trends'
        assert memory.metadata == metadata
        assert memory.created_at == created
        assert memory.updated_at == updated

    def test_memory_immutability(self):
        """测试 Memory 是否为不可变的 dataclass"""
        memory = Memory(
            id='mem_003',
            type=MemoryType.PATTERN,
            title='Pattern',
            content='Content',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 应该无法修改字段
        with pytest.raises(AttributeError):
            memory.title = 'New Title'


class TestMemoryLink:
    """MemoryLink 数据类测试"""

    def test_create_link_minimal(self):
        """测试创建最小化链接"""
        link = MemoryLink(
            from_memory_id='mem_001',
            to_memory_id='mem_002',
            link_type=LinkType.SUPPORTS,
            created_at=datetime.now()
        )

        assert link.from_memory_id == 'mem_001'
        assert link.to_memory_id == 'mem_002'
        assert link.link_type == LinkType.SUPPORTS
        assert link.notes is None

    def test_create_link_with_notes(self):
        """测试创建带备注的链接"""
        link = MemoryLink(
            from_memory_id='mem_001',
            to_memory_id='mem_002',
            link_type=LinkType.EXTENDS,
            notes='Extends the previous analysis',
            created_at=datetime.now()
        )

        assert link.notes == 'Extends the previous analysis'

    def test_link_immutability(self):
        """测试 MemoryLink 是否为不可变的 dataclass"""
        link = MemoryLink(
            from_memory_id='mem_001',
            to_memory_id='mem_002',
            link_type=LinkType.SUPPORTS,
            created_at=datetime.now()
        )

        with pytest.raises(AttributeError):
            link.link_type = LinkType.CONTRADICTS


class TestMemoryRepository:
    """MemoryRepository 测试"""

    def test_create_memory(self, memory_repo):
        """测试创建记忆"""
        memory = Memory(
            id='mem_test_001',
            type=MemoryType.DAILY_SUMMARY,
            title='Test Daily Summary',
            description='Test description',
            content='Test content',
            metadata={'test': True},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        memory_repo.create(memory)

        # 验证记忆已保存
        retrieved = memory_repo.get_by_id('mem_test_001')
        assert retrieved is not None
        assert retrieved.id == memory.id
        assert retrieved.type == memory.type
        assert retrieved.title == memory.title
        assert retrieved.description == memory.description
        assert retrieved.content == memory.content
        assert retrieved.metadata == memory.metadata

    def test_create_memory_duplicate_id(self, memory_repo):
        """测试创建重复 ID 的记忆"""
        memory1 = Memory(
            id='mem_dup_001',
            type=MemoryType.SIGNAL,
            title='First',
            content='Content 1',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        memory2 = Memory(
            id='mem_dup_001',
            type=MemoryType.PATTERN,
            title='Second',
            content='Content 2',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        memory_repo.create(memory1)

        with pytest.raises(MemoryAlreadyExistsError):
            memory_repo.create(memory2)

    def test_get_by_id_not_found(self, memory_repo):
        """测试获取不存在的记忆"""
        result = memory_repo.get_by_id('nonexistent_id')
        assert result is None

    def test_get_by_type(self, memory_repo):
        """测试按类型获取记忆"""
        # 创建不同类型的记忆
        for i in range(3):
            memory = Memory(
                id=f'daily_{i}',
                type=MemoryType.DAILY_SUMMARY,
                title=f'Daily {i}',
                content=f'Content {i}',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            memory_repo.create(memory)

        for i in range(2):
            memory = Memory(
                id=f'weekly_{i}',
                type=MemoryType.WEEKLY_DIGEST,
                title=f'Weekly {i}',
                content=f'Content {i}',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            memory_repo.create(memory)

        # 查询 DAILY_SUMMARY 类型
        daily_memories = memory_repo.get_by_type(MemoryType.DAILY_SUMMARY)
        assert len(daily_memories) == 3
        assert all(m.type == MemoryType.DAILY_SUMMARY for m in daily_memories)

        # 查询 WEEKLY_DIGEST 类型
        weekly_memories = memory_repo.get_by_type(MemoryType.WEEKLY_DIGEST)
        assert len(weekly_memories) == 2
        assert all(m.type == MemoryType.WEEKLY_DIGEST for m in weekly_memories)

    def test_get_by_type_with_limit(self, memory_repo):
        """测试按类型获取记忆并限制数量"""
        for i in range(5):
            memory = Memory(
                id=f'pattern_{i}',
                type=MemoryType.PATTERN,
                title=f'Pattern {i}',
                content=f'Content {i}',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            memory_repo.create(memory)

        # 限制获取 3 条
        results = memory_repo.get_by_type(MemoryType.PATTERN, limit=3)
        assert len(results) == 3

    def test_get_by_date_range(self, memory_repo):
        """测试按日期范围获取记忆"""
        base_time = datetime.now()

        # 创建不同日期的记忆
        dates = [
            base_time - timedelta(days=5),
            base_time - timedelta(days=3),
            base_time - timedelta(days=1),
            base_time
        ]

        for i, date in enumerate(dates):
            memory = Memory(
                id=f'mem_date_{i}',
                type=MemoryType.SIGNAL,
                title=f'Signal {i}',
                content=f'Content {i}',
                created_at=date,
                updated_at=date
            )
            memory_repo.create(memory)

        # 查询最近 2 天
        start_date = base_time - timedelta(days=2)
        results = memory_repo.get_by_date_range(start_date, base_time)
        assert len(results) == 2

        # 查询最近 4 天
        start_date = base_time - timedelta(days=4)
        results = memory_repo.get_by_date_range(start_date, base_time)
        assert len(results) == 3

    def test_update_memory(self, memory_repo):
        """测试更新记忆"""
        original_time = datetime.now()
        memory = Memory(
            id='mem_update_001',
            type=MemoryType.TOPIC_INSIGHT,
            title='Original Title',
            description='Original description',
            content='Original content',
            metadata={'version': 1},
            created_at=original_time,
            updated_at=original_time
        )

        memory_repo.create(memory)

        # 更新记忆
        new_time = datetime.now() + timedelta(hours=1)
        updated_memory = Memory(
            id='mem_update_001',
            type=MemoryType.TOPIC_INSIGHT,
            title='Updated Title',
            description='Updated description',
            content='Updated content',
            metadata={'version': 2},
            created_at=original_time,  # created_at 不变
            updated_at=new_time
        )

        memory_repo.update(updated_memory)

        # 验证更新
        retrieved = memory_repo.get_by_id('mem_update_001')
        assert retrieved.title == 'Updated Title'
        assert retrieved.description == 'Updated description'
        assert retrieved.content == 'Updated content'
        assert retrieved.metadata == {'version': 2}
        assert retrieved.created_at == original_time  # 创建时间不变
        assert retrieved.updated_at == new_time

    def test_delete_memory(self, memory_repo):
        """测试删除记忆"""
        memory = Memory(
            id='mem_delete_001',
            type=MemoryType.PATTERN,
            title='To be deleted',
            content='Content',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        memory_repo.create(memory)
        assert memory_repo.get_by_id('mem_delete_001') is not None

        # 删除
        memory_repo.delete('mem_delete_001')
        assert memory_repo.get_by_id('mem_delete_001') is None

    def test_create_link(self, memory_repo):
        """测试创建记忆链接"""
        # 先创建两个记忆
        memory1 = Memory(
            id='mem_link_001',
            type=MemoryType.DAILY_SUMMARY,
            title='Memory 1',
            content='Content 1',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        memory2 = Memory(
            id='mem_link_002',
            type=MemoryType.WEEKLY_DIGEST,
            title='Memory 2',
            content='Content 2',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        memory_repo.create(memory1)
        memory_repo.create(memory2)

        # 创建链接
        link = MemoryLink(
            from_memory_id='mem_link_001',
            to_memory_id='mem_link_002',
            link_type=LinkType.SUPPORTS,
            notes='Test link',
            created_at=datetime.now()
        )

        memory_repo.create_link(link)

        # 验证链接
        links = memory_repo.get_links_from('mem_link_001')
        assert len(links) == 1
        assert links[0].from_memory_id == 'mem_link_001'
        assert links[0].to_memory_id == 'mem_link_002'
        assert links[0].link_type == LinkType.SUPPORTS
        assert links[0].notes == 'Test link'

    def test_create_link_duplicate(self, memory_repo):
        """测试创建重复链接"""
        # 创建记忆
        for i in range(2):
            memory = Memory(
                id=f'mem_dup_link_{i}',
                type=MemoryType.SIGNAL,
                title=f'Memory {i}',
                content=f'Content {i}',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            memory_repo.create(memory)

        # 创建第一个链接
        link1 = MemoryLink(
            from_memory_id='mem_dup_link_0',
            to_memory_id='mem_dup_link_1',
            link_type=LinkType.EXTENDS,
            created_at=datetime.now()
        )
        memory_repo.create_link(link1)

        # 尝试创建重复链接
        link2 = MemoryLink(
            from_memory_id='mem_dup_link_0',
            to_memory_id='mem_dup_link_1',
            link_type=LinkType.SUPPORTS,  # 即使类型不同
            created_at=datetime.now()
        )

        with pytest.raises(sqlite3.IntegrityError):
            memory_repo.create_link(link2)

    def test_get_links_from(self, memory_repo):
        """测试获取从某记忆发出的链接"""
        # 创建记忆
        for i in range(4):
            memory = Memory(
                id=f'mem_from_{i}',
                type=MemoryType.PATTERN,
                title=f'Memory {i}',
                content=f'Content {i}',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            memory_repo.create(memory)

        # 创建多个链接，从 mem_from_0 指向其他记忆
        for i in range(1, 4):
            link = MemoryLink(
                from_memory_id='mem_from_0',
                to_memory_id=f'mem_from_{i}',
                link_type=LinkType.SUPPORTS,
                created_at=datetime.now()
            )
            memory_repo.create_link(link)

        # 获取从 mem_from_0 发出的链接
        links = memory_repo.get_links_from('mem_from_0')
        assert len(links) == 3
        assert all(link.from_memory_id == 'mem_from_0' for link in links)

    def test_get_links_to(self, memory_repo):
        """测试获取指向某记忆的链接"""
        # 创建记忆
        for i in range(4):
            memory = Memory(
                id=f'mem_to_{i}',
                type=MemoryType.TOPIC_INSIGHT,
                title=f'Memory {i}',
                content=f'Content {i}',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            memory_repo.create(memory)

        # 创建多个链接，指向 mem_to_0
        for i in range(1, 4):
            link = MemoryLink(
                from_memory_id=f'mem_to_{i}',
                to_memory_id='mem_to_0',
                link_type=LinkType.DERIVES_FROM,
                created_at=datetime.now()
            )
            memory_repo.create_link(link)

        # 获取指向 mem_to_0 的链接
        links = memory_repo.get_links_to('mem_to_0')
        assert len(links) == 3
        assert all(link.to_memory_id == 'mem_to_0' for link in links)

    def test_delete_link(self, memory_repo):
        """测试删除链接"""
        # 创建记忆
        for i in range(2):
            memory = Memory(
                id=f'mem_del_link_{i}',
                type=MemoryType.SIGNAL,
                title=f'Memory {i}',
                content=f'Content {i}',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            memory_repo.create(memory)

        # 创建链接
        link = MemoryLink(
            from_memory_id='mem_del_link_0',
            to_memory_id='mem_del_link_1',
            link_type=LinkType.CONTRADICTS,
            created_at=datetime.now()
        )
        memory_repo.create_link(link)

        # 验证链接存在
        links = memory_repo.get_links_from('mem_del_link_0')
        assert len(links) == 1

        # 删除链接
        memory_repo.delete_link('mem_del_link_0', 'mem_del_link_1')

        # 验证链接已删除
        links = memory_repo.get_links_from('mem_del_link_0')
        assert len(links) == 0

    def test_search_memories(self, memory_repo):
        """测试搜索记忆（简单文本匹配）"""
        # 创建包含特定关键词的记忆
        memories_data = [
            ('mem_search_1', 'AI Development', 'Content about AI development'),
            ('mem_search_2', 'Machine Learning', 'Content about machine learning'),
            ('mem_search_3', 'AI Ethics', 'Content about AI ethics and responsibility'),
            ('mem_search_4', 'Data Science', 'Content about data science'),
        ]

        for mem_id, title, content in memories_data:
            memory = Memory(
                id=mem_id,
                type=MemoryType.TOPIC_INSIGHT,
                title=title,
                content=content,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            memory_repo.create(memory)

        # 搜索包含 "AI" 的记忆
        results = memory_repo.search('AI')
        assert len(results) >= 2  # 至少有 AI Development 和 AI Ethics

        # 验证搜索结果包含关键词
        for memory in results:
            assert 'AI' in memory.title or 'AI' in memory.content
