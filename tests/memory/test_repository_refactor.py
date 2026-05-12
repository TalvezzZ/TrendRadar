"""
测试 MemoryRepository 重构后的兼容性

验证 MemoryRepository 在使用依赖注入后能够正常工作。
"""
import pytest
from dataclasses import replace
from datetime import datetime, timedelta

from trendradar.memory.models import Memory, MemoryType, MemoryRepository, MemoryLink, LinkType
from trendradar.memory.storage.database import DatabaseBackend
from trendradar.memory.storage.file import FileBackend


@pytest.fixture
def db_repository(tmp_path):
    """创建使用 DatabaseBackend 的 MemoryRepository"""
    db_path = str(tmp_path / "test.db")
    backend = DatabaseBackend(db_path)
    return MemoryRepository(backend)


@pytest.fixture
def file_repository(tmp_path):
    """创建使用 FileBackend 的 MemoryRepository"""
    file_path = str(tmp_path / "memory")
    backend = FileBackend(file_path, auto_index=False)
    return MemoryRepository(backend)


@pytest.fixture
def sample_memory():
    """创建示例记忆"""
    return Memory(
        id="test-memory-1",
        type=MemoryType.DAILY_SUMMARY,
        title="测试记忆",
        description="这是一个测试记忆",
        content="测试内容",
        metadata={"tag": "test"},
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestRepositoryWithDatabaseBackend:
    """测试 DatabaseBackend 的兼容性"""

    def test_create_and_get_by_id(self, db_repository, sample_memory):
        """测试创建和查询记忆"""
        db_repository.create(sample_memory)
        retrieved = db_repository.get_by_id(sample_memory.id)

        assert retrieved is not None
        assert retrieved.id == sample_memory.id
        assert retrieved.title == sample_memory.title
        assert retrieved.content == sample_memory.content

    def test_get_by_type(self, db_repository, sample_memory):
        """测试按类型查询"""
        db_repository.create(sample_memory)
        memories = db_repository.get_by_type(MemoryType.DAILY_SUMMARY, limit=10)

        assert len(memories) == 1
        assert memories[0].id == sample_memory.id

    def test_get_by_date_range(self, db_repository, sample_memory):
        """测试按日期范围查询"""
        db_repository.create(sample_memory)

        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)

        memories = db_repository.get_by_date_range(start_date, end_date)

        assert len(memories) == 1
        assert memories[0].id == sample_memory.id

    def test_update(self, db_repository, sample_memory):
        """测试更新记忆"""
        db_repository.create(sample_memory)

        # 使用 replace 创建更新后的记忆（Memory 是 frozen dataclass）
        updated_memory = replace(
            sample_memory,
            title="更新后的标题",
            updated_at=datetime.now()
        )
        db_repository.update(updated_memory)

        retrieved = db_repository.get_by_id(sample_memory.id)
        assert retrieved.title == "更新后的标题"

    def test_delete(self, db_repository, sample_memory):
        """测试删除记忆"""
        db_repository.create(sample_memory)
        db_repository.delete(sample_memory.id)

        retrieved = db_repository.get_by_id(sample_memory.id)
        assert retrieved is None

    def test_search(self, db_repository, sample_memory):
        """测试搜索记忆"""
        db_repository.create(sample_memory)

        results = db_repository.search("测试", limit=10)

        assert len(results) == 1
        assert results[0].id == sample_memory.id

    def test_link_operations(self, db_repository, sample_memory):
        """测试链接操作（仅 DatabaseBackend 支持）"""
        # 创建两个记忆
        memory1 = sample_memory
        memory2 = Memory(
            id="test-memory-2",
            type=MemoryType.DAILY_SUMMARY,
            title="第二个记忆",
            description="用于测试链接",
            content="内容2",
            metadata={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        db_repository.create(memory1)
        db_repository.create(memory2)

        # 创建链接（使用有效的 LinkType）
        link = MemoryLink(
            from_memory_id=memory1.id,
            to_memory_id=memory2.id,
            link_type=LinkType.SUPPORTS,
            notes="测试链接",
            created_at=datetime.now()
        )
        db_repository.create_link(link)

        # 查询链接
        outgoing_links = db_repository.get_links_from(memory1.id)
        assert len(outgoing_links) == 1
        assert outgoing_links[0].to_memory_id == memory2.id

        incoming_links = db_repository.get_links_to(memory2.id)
        assert len(incoming_links) == 1
        assert incoming_links[0].from_memory_id == memory1.id

        # 删除链接
        db_repository.delete_link(memory1.id, memory2.id)
        outgoing_links = db_repository.get_links_from(memory1.id)
        assert len(outgoing_links) == 0


class TestRepositoryWithFileBackend:
    """测试 FileBackend 的兼容性"""

    def test_create_and_get_by_id(self, file_repository, sample_memory):
        """测试创建和查询记忆"""
        file_repository.create(sample_memory)
        retrieved = file_repository.get_by_id(sample_memory.id)

        assert retrieved is not None
        assert retrieved.id == sample_memory.id
        assert retrieved.title == sample_memory.title
        assert retrieved.content == sample_memory.content

    def test_get_by_type(self, file_repository, sample_memory):
        """测试按类型查询"""
        file_repository.create(sample_memory)
        memories = file_repository.get_by_type(MemoryType.DAILY_SUMMARY, limit=10)

        assert len(memories) == 1
        assert memories[0].id == sample_memory.id

    def test_get_by_date_range(self, file_repository, sample_memory):
        """测试按日期范围查询"""
        file_repository.create(sample_memory)

        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)

        memories = file_repository.get_by_date_range(start_date, end_date)

        assert len(memories) == 1
        assert memories[0].id == sample_memory.id

    def test_update(self, file_repository, sample_memory):
        """测试更新记忆"""
        file_repository.create(sample_memory)

        # 使用 replace 创建更新后的记忆（Memory 是 frozen dataclass）
        updated_memory = replace(
            sample_memory,
            title="更新后的标题",
            updated_at=datetime.now()
        )
        file_repository.update(updated_memory)

        retrieved = file_repository.get_by_id(sample_memory.id)
        assert retrieved.title == "更新后的标题"

    def test_delete(self, file_repository, sample_memory):
        """测试删除记忆"""
        file_repository.create(sample_memory)
        file_repository.delete(sample_memory.id)

        retrieved = file_repository.get_by_id(sample_memory.id)
        assert retrieved is None

    def test_search(self, file_repository, sample_memory):
        """测试搜索记忆"""
        file_repository.create(sample_memory)

        results = file_repository.search("测试", limit=10)

        assert len(results) == 1
        assert results[0].id == sample_memory.id


class TestRepositoryInterfaceCompatibility:
    """测试 MemoryRepository 接口兼容性"""

    def test_all_public_methods_exist(self):
        """验证所有公共方法存在"""
        required_methods = [
            'create',
            'get_by_id',
            'get_by_type',
            'get_by_date_range',
            'update',
            'delete',
            'search',
            'create_link',
            'get_links_from',
            'get_links_to',
            'delete_link'
        ]

        for method_name in required_methods:
            assert hasattr(MemoryRepository, method_name), \
                f"MemoryRepository 缺少方法: {method_name}"

    def test_method_signatures_unchanged(self, tmp_path):
        """验证方法签名未改变"""
        db_path = str(tmp_path / "test.db")
        backend = DatabaseBackend(db_path)
        repo = MemoryRepository(backend)

        # 检查核心方法的签名
        import inspect

        # create(memory: Memory) -> None
        sig = inspect.signature(repo.create)
        assert 'memory' in sig.parameters

        # get_by_id(memory_id: str) -> Optional[Memory]
        sig = inspect.signature(repo.get_by_id)
        assert 'memory_id' in sig.parameters

        # get_by_type(memory_type: str, limit: Optional[int]) -> List[Memory]
        sig = inspect.signature(repo.get_by_type)
        assert 'memory_type' in sig.parameters
        assert 'limit' in sig.parameters

        # search(keyword: str, limit: Optional[int]) -> List[Memory]
        sig = inspect.signature(repo.search)
        assert 'keyword' in sig.parameters
        assert 'limit' in sig.parameters

    def test_backend_attribute_exists(self, tmp_path):
        """验证 backend 属性存在"""
        db_path = str(tmp_path / "test.db")
        backend = DatabaseBackend(db_path)
        repo = MemoryRepository(backend)

        assert hasattr(repo, 'backend')
        assert repo.backend is backend

    def test_db_path_preserved_for_database_backend(self, tmp_path):
        """验证 DatabaseBackend 的 db_path 被保留"""
        db_path = str(tmp_path / "test.db")
        backend = DatabaseBackend(db_path)
        repo = MemoryRepository(backend)

        assert repo.db_path == db_path

    def test_db_path_none_for_file_backend(self, tmp_path):
        """验证 FileBackend 的 db_path 为 None"""
        file_path = str(tmp_path / "memory")
        backend = FileBackend(file_path, auto_index=False)
        repo = MemoryRepository(backend)

        assert repo.db_path is None
