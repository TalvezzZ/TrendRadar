"""
MemoryIndexManager 测试
"""

import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from trendradar.memory.models import Memory, MemoryType
from trendradar.memory.storage.file import FileBackend
from trendradar.memory.index_manager import MemoryIndexManager


@pytest.fixture
def temp_memory_dir():
    """创建临时记忆目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def file_backend(temp_memory_dir):
    """创建文件后端实例（不启用自动索引）"""
    return FileBackend(str(temp_memory_dir), auto_index=False)


@pytest.fixture
def index_manager(temp_memory_dir):
    """创建索引管理器实例"""
    return MemoryIndexManager(temp_memory_dir)


class TestMemoryIndexManager:
    """MemoryIndexManager 核心功能测试"""

    def test_init(self, temp_memory_dir):
        """测试初始化"""
        manager = MemoryIndexManager(temp_memory_dir)
        assert manager.base_path == temp_memory_dir
        assert manager.index_file == temp_memory_dir / "MEMORY.md"

    def test_scan_file_single_memory(self, file_backend, index_manager):
        """测试扫描包含单个记忆的文件"""
        # 创建一个记忆
        memory = Memory(
            id='test-001',
            type=MemoryType.DAILY_SUMMARY,
            title='测试摘要',
            description='测试描述',
            content='测试内容',
            metadata={'keywords': ['AI', '区块链']},
            created_at=datetime(2026, 5, 1, 10, 30),
            updated_at=datetime(2026, 5, 1, 10, 30)
        )
        file_backend.create_memory(memory)

        # 扫描文件
        file_path = file_backend._get_file_path(memory)
        results = index_manager._scan_file(file_path)

        # 验证结果
        assert len(results) == 1
        assert results[0]['id'] == 'test-001'
        assert results[0]['title'] == '测试摘要'
        assert results[0]['description'] == '测试描述'
        assert results[0]['created_at'] == datetime(2026, 5, 1, 10, 30)
        assert results[0]['keywords'] == ['AI', '区块链']

    def test_scan_file_multiple_memories(self, file_backend, index_manager):
        """测试扫描包含多个记忆的文件"""
        # 创建多个记忆（同一个月）
        base_date = datetime(2026, 5, 1)
        for i in range(3):
            memory = Memory(
                id=f'test-{i:03d}',
                type=MemoryType.DAILY_SUMMARY,
                title=f'测试摘要 {i}',
                description=f'描述 {i}',
                content=f'内容 {i}',
                metadata={'keywords': [f'关键词{i}']},
                created_at=base_date.replace(day=i+1),
                updated_at=base_date.replace(day=i+1)
            )
            file_backend.create_memory(memory)

        # 扫描文件
        file_path = file_backend.base_path / MemoryType.DAILY_SUMMARY / "2026-05.md"
        results = index_manager._scan_file(file_path)

        # 验证结果
        assert len(results) == 3
        assert results[0]['id'] == 'test-000'
        assert results[1]['id'] == 'test-001'
        assert results[2]['id'] == 'test-002'

    def test_scan_file_missing_keywords(self, file_backend, index_manager):
        """测试扫描没有关键词的记忆"""
        memory = Memory(
            id='test-no-keywords',
            type=MemoryType.DAILY_SUMMARY,
            title='无关键词',
            description='描述',
            content='内容',
            metadata={},
            created_at=datetime(2026, 5, 1),
            updated_at=datetime(2026, 5, 1)
        )
        file_backend.create_memory(memory)

        file_path = file_backend._get_file_path(memory)
        results = index_manager._scan_file(file_path)

        # 验证结果，keywords 应为空列表
        assert len(results) == 1
        assert results[0]['keywords'] == []

    def test_scan_file_nonexistent(self, index_manager, temp_memory_dir):
        """测试扫描不存在的文件"""
        fake_path = temp_memory_dir / "nonexistent.md"
        results = index_manager._scan_file(fake_path)
        # 应该返回空列表
        assert results == []

    def test_generate_index_content_single_type(self, file_backend, index_manager):
        """测试生成索引内容（单一类型）"""
        # 创建记忆
        memory = Memory(
            id='test-001',
            type=MemoryType.DAILY_SUMMARY,
            title='测试摘要',
            description='描述',
            content='内容',
            metadata={'keywords': ['AI', '区块链']},
            created_at=datetime(2026, 5, 1, 10, 30),
            updated_at=datetime(2026, 5, 1, 10, 30)
        )
        file_backend.create_memory(memory)

        # 扫描所有记忆
        file_path = file_backend._get_file_path(memory)
        memories_data = {
            MemoryType.DAILY_SUMMARY: index_manager._scan_file(file_path)
        }

        # 生成索引内容
        content = index_manager._generate_index_content(memories_data)

        # 验证内容格式
        assert '# TrendRadar 记忆索引' in content
        assert '更新时间：' in content
        assert '## 每日摘要 (daily_summary)' in content
        assert '[2026-05-01](daily_summary/2026-05.md#test-001)' in content
        assert '描述，关键词：AI、区块链' in content

    def test_generate_index_content_multiple_types(self, file_backend, index_manager):
        """测试生成索引内容（多种类型）"""
        # 创建不同类型的记忆
        memories = [
            Memory(
                id='daily-001',
                type=MemoryType.DAILY_SUMMARY,
                title='每日摘要',
                description='每日',
                content='内容',
                metadata={'keywords': ['A']},
                created_at=datetime(2026, 5, 1),
                updated_at=datetime(2026, 5, 1)
            ),
            Memory(
                id='weekly-001',
                type=MemoryType.WEEKLY_DIGEST,
                title='每周摘要',
                description='每周',
                content='内容',
                metadata={'keywords': ['B']},
                created_at=datetime(2026, 5, 1),
                updated_at=datetime(2026, 5, 1)
            ),
            Memory(
                id='topic-001',
                type=MemoryType.TOPIC_INSIGHT,
                title='主题洞察',
                description='主题',
                content='内容',
                metadata={'keywords': ['C']},
                created_at=datetime(2026, 5, 1),
                updated_at=datetime(2026, 5, 1)
            )
        ]

        for memory in memories:
            file_backend.create_memory(memory)

        # 扫描所有类型
        memories_data = {}
        for memory in memories:
            file_path = file_backend._get_file_path(memory)
            memories_data[memory.type] = index_manager._scan_file(file_path)

        # 生成索引内容
        content = index_manager._generate_index_content(memories_data)

        # 验证所有类型都出现
        assert '## 每日摘要 (daily_summary)' in content
        assert '## 每周摘要 (weekly_digest)' in content
        assert '## 主题洞察 (topic_insight)' in content

    def test_generate_index_content_empty(self, index_manager):
        """测试生成空索引"""
        content = index_manager._generate_index_content({})

        # 应包含标题，但没有记忆条目
        assert '# TrendRadar 记忆索引' in content
        assert '更新时间：' in content

    def test_update_index(self, file_backend, index_manager):
        """测试更新索引文件"""
        # 创建一些记忆
        memory = Memory(
            id='test-001',
            type=MemoryType.DAILY_SUMMARY,
            title='测试',
            description='描述',
            content='内容',
            metadata={'keywords': ['AI']},
            created_at=datetime(2026, 5, 1),
            updated_at=datetime(2026, 5, 1)
        )
        file_backend.create_memory(memory)

        # 更新索引
        index_manager.update_index()

        # 验证 MEMORY.md 已创建
        assert index_manager.index_file.exists()

        # 验证内容
        content = index_manager.index_file.read_text(encoding='utf-8')
        assert '# TrendRadar 记忆索引' in content
        assert 'test-001' in content
        assert '描述，关键词：AI' in content

    def test_update_index_overwrites_existing(self, file_backend, index_manager):
        """测试更新索引会覆盖已有文件"""
        # 创建第一个记忆
        memory1 = Memory(
            id='test-001',
            type=MemoryType.DAILY_SUMMARY,
            title='第一个',
            description='描述1',
            content='内容1',
            metadata={'keywords': ['A']},
            created_at=datetime(2026, 5, 1),
            updated_at=datetime(2026, 5, 1)
        )
        file_backend.create_memory(memory1)
        index_manager.update_index()

        # 创建第二个记忆
        memory2 = Memory(
            id='test-002',
            type=MemoryType.DAILY_SUMMARY,
            title='第二个',
            description='描述2',
            content='内容2',
            metadata={'keywords': ['B']},
            created_at=datetime(2026, 5, 2),
            updated_at=datetime(2026, 5, 2)
        )
        file_backend.create_memory(memory2)
        index_manager.update_index()

        # 验证索引包含两个记忆
        content = index_manager.index_file.read_text(encoding='utf-8')
        assert 'test-001' in content
        assert 'test-002' in content


class TestFileBackendIntegration:
    """测试 FileBackend 集成 MemoryIndexManager"""

    def test_auto_index_on_create(self, temp_memory_dir):
        """测试创建记忆时自动更新索引"""
        backend = FileBackend(str(temp_memory_dir), auto_index=True)

        memory = Memory(
            id='auto-001',
            type=MemoryType.DAILY_SUMMARY,
            title='自动索引测试',
            description='描述',
            content='内容',
            metadata={'keywords': ['自动']},
            created_at=datetime(2026, 5, 1),
            updated_at=datetime(2026, 5, 1)
        )

        backend.create_memory(memory)

        # 验证 MEMORY.md 已自动创建
        index_file = temp_memory_dir / "MEMORY.md"
        assert index_file.exists()

        content = index_file.read_text(encoding='utf-8')
        assert 'auto-001' in content

    def test_auto_index_on_update(self, temp_memory_dir):
        """测试更新记忆时自动更新索引"""
        backend = FileBackend(str(temp_memory_dir), auto_index=True)

        # 创建记忆
        memory = Memory(
            id='auto-002',
            type=MemoryType.DAILY_SUMMARY,
            title='原标题',
            description='原描述',
            content='内容',
            metadata={'keywords': ['原关键词']},
            created_at=datetime(2026, 5, 1),
            updated_at=datetime(2026, 5, 1)
        )
        backend.create_memory(memory)

        # 更新记忆
        updated_memory = Memory(
            id='auto-002',
            type=MemoryType.DAILY_SUMMARY,
            title='新标题',
            description='新描述',
            content='新内容',
            metadata={'keywords': ['新关键词']},
            created_at=datetime(2026, 5, 1),
            updated_at=datetime(2026, 5, 1, 12, 0)
        )
        backend.update_memory(updated_memory)

        # 验证索引已更新
        index_file = temp_memory_dir / "MEMORY.md"
        content = index_file.read_text(encoding='utf-8')
        assert '新描述，关键词：新关键词' in content
        assert '原描述' not in content

    def test_auto_index_on_delete(self, temp_memory_dir):
        """测试删除记忆时自动更新索引"""
        backend = FileBackend(str(temp_memory_dir), auto_index=True)

        # 创建两个记忆
        memory1 = Memory(
            id='auto-003',
            type=MemoryType.DAILY_SUMMARY,
            title='记忆1',
            description='描述1',
            content='内容1',
            metadata={'keywords': ['A']},
            created_at=datetime(2026, 5, 1),
            updated_at=datetime(2026, 5, 1)
        )
        memory2 = Memory(
            id='auto-004',
            type=MemoryType.DAILY_SUMMARY,
            title='记忆2',
            description='描述2',
            content='内容2',
            metadata={'keywords': ['B']},
            created_at=datetime(2026, 5, 2),
            updated_at=datetime(2026, 5, 2)
        )
        backend.create_memory(memory1)
        backend.create_memory(memory2)

        # 删除第一个记忆
        backend.delete_memory('auto-003')

        # 验证索引已更新
        index_file = temp_memory_dir / "MEMORY.md"
        content = index_file.read_text(encoding='utf-8')
        assert 'auto-003' not in content
        assert 'auto-004' in content

    def test_auto_index_disabled(self, temp_memory_dir):
        """测试禁用自动索引"""
        backend = FileBackend(str(temp_memory_dir), auto_index=False)

        memory = Memory(
            id='no-auto-001',
            type=MemoryType.DAILY_SUMMARY,
            title='不自动索引',
            description='描述',
            content='内容',
            metadata={},
            created_at=datetime(2026, 5, 1),
            updated_at=datetime(2026, 5, 1)
        )
        backend.create_memory(memory)

        # MEMORY.md 不应被创建
        index_file = temp_memory_dir / "MEMORY.md"
        assert not index_file.exists()
