"""
FileBackend Markdown 转换测试
"""
import pytest
import yaml
from datetime import datetime
from pathlib import Path

from trendradar.memory.models import Memory, MemoryType
from trendradar.memory.storage.file import FileBackend
from trendradar.memory.storage.exceptions import (
    MemoryParseError,
    MemoryCorruptedError
)


@pytest.fixture
def temp_storage(tmp_path):
    """临时文件存储"""
    return FileBackend(str(tmp_path), auto_index=False)


@pytest.fixture
def sample_memory():
    """示例记忆对象"""
    return Memory(
        id="test-001",
        type=MemoryType.DAILY_SUMMARY,
        title="测试摘要",
        description="测试描述",
        content="# 标题\n\n这是测试内容",
        created_at=datetime(2026, 5, 1, 10, 30, 0),
        updated_at=datetime(2026, 5, 1, 10, 30, 0),
        metadata={
            "key": "value",
            "top_keywords": ["AI", "区块链"],
            "nested": {
                "level": 2,
                "items": [1, 2, 3]
            }
        }
    )


def test_memory_to_markdown_basic(temp_storage, sample_memory):
    """测试 Memory 对象转换为 Markdown - 基础功能"""
    md = temp_storage._memory_to_markdown(sample_memory)

    # 验证格式：--- YAML --- 内容
    assert md.startswith("---\n")
    assert "\n---\n\n" in md
    assert md.endswith("这是测试内容\n")

    # 验证 YAML 部分
    yaml_end = md.find("\n---\n")
    yaml_content = md[4:yaml_end]  # 跳过开头的 "---\n"
    parsed_yaml = yaml.safe_load(yaml_content)

    assert parsed_yaml["id"] == "test-001"
    assert parsed_yaml["type"] == "daily_summary"
    assert parsed_yaml["title"] == "测试摘要"
    assert parsed_yaml["description"] == "测试描述"
    assert parsed_yaml["created_at"] == "2026-05-01T10:30:00"
    assert parsed_yaml["updated_at"] == "2026-05-01T10:30:00"

    # 验证 metadata 结构
    assert parsed_yaml["metadata"]["key"] == "value"
    assert parsed_yaml["metadata"]["top_keywords"] == ["AI", "区块链"]
    assert parsed_yaml["metadata"]["nested"]["level"] == 2
    assert parsed_yaml["metadata"]["nested"]["items"] == [1, 2, 3]


def test_memory_to_markdown_no_description(temp_storage):
    """测试 Memory 对象转换为 Markdown - 无描述"""
    memory = Memory(
        id="test-002",
        type=MemoryType.TOPIC_INSIGHT,
        title="主题洞察",
        description=None,
        content="洞察内容",
        created_at=datetime(2026, 5, 2, 12, 0, 0),
        updated_at=datetime(2026, 5, 2, 12, 0, 0),
        metadata={}
    )

    md = temp_storage._memory_to_markdown(memory)

    # 验证 YAML
    yaml_end = md.find("\n---\n")
    yaml_content = md[4:yaml_end]
    parsed_yaml = yaml.safe_load(yaml_content)

    # None 应该保留为 null 或者不存在
    assert parsed_yaml.get("description") is None


def test_markdown_to_memory_basic(temp_storage):
    """测试 Markdown 转换为 Memory 对象 - 基础功能"""
    yaml_content = {
        "id": "test-003",
        "type": "weekly_digest",
        "title": "周报摘要",
        "description": "周报描述",
        "created_at": "2026-05-03T15:00:00",
        "updated_at": "2026-05-03T16:00:00",
        "metadata": {
            "week": 18,
            "topics": ["科技", "经济"]
        }
    }
    md_content = "# 本周总结\n\n这是本周的重要内容"

    memory = temp_storage._parse_single_memory(yaml_content, md_content)

    assert memory is not None
    assert memory.id == "test-003"
    assert memory.type == "weekly_digest"
    assert memory.title == "周报摘要"
    assert memory.description == "周报描述"
    assert memory.content == "# 本周总结\n\n这是本周的重要内容"
    assert memory.created_at == datetime(2026, 5, 3, 15, 0, 0)
    assert memory.updated_at == datetime(2026, 5, 3, 16, 0, 0)
    assert memory.metadata["week"] == 18
    assert memory.metadata["topics"] == ["科技", "经济"]


def test_markdown_to_memory_no_description(temp_storage):
    """测试 Markdown 转换为 Memory 对象 - 无描述"""
    yaml_content = {
        "id": "test-004",
        "type": "pattern",
        "title": "模式识别",
        "created_at": "2026-05-04T10:00:00",
        "updated_at": "2026-05-04T10:00:00"
    }
    md_content = "模式内容"

    memory = temp_storage._parse_single_memory(yaml_content, md_content)

    assert memory is not None
    assert memory.description is None
    assert memory.metadata == {}


def test_markdown_to_memory_whitespace_handling(temp_storage):
    """测试 Markdown 转换为 Memory - 空格处理"""
    yaml_content = {
        "id": "test-005",
        "type": "signal",
        "title": "信号",
        "created_at": "2026-05-05T10:00:00",
        "updated_at": "2026-05-05T10:00:00"
    }
    md_content = "   \n\n内容前后有空格   \n\n  "

    memory = temp_storage._parse_single_memory(yaml_content, md_content)

    # 应该去除前后空白
    assert memory.content == "内容前后有空格"


def test_markdown_to_memory_missing_required_field(temp_storage):
    """测试 Markdown 转换为 Memory - 缺少必填字段"""
    # 缺少 title
    yaml_content = {
        "id": "test-006",
        "type": "daily_summary",
        "created_at": "2026-05-06T10:00:00",
        "updated_at": "2026-05-06T10:00:00"
    }
    md_content = "内容"

    with pytest.raises(MemoryCorruptedError):
        temp_storage._parse_single_memory(yaml_content, md_content)


def test_markdown_to_memory_invalid_datetime(temp_storage):
    """测试 Markdown 转换为 Memory - 无效日期格式"""
    yaml_content = {
        "id": "test-007",
        "type": "daily_summary",
        "title": "标题",
        "created_at": "invalid-date",
        "updated_at": "2026-05-07T10:00:00"
    }
    md_content = "内容"

    # datetime.fromisoformat 会抛出 ValueError，应该被转换为 MemoryParseError
    with pytest.raises(MemoryParseError):
        temp_storage._parse_single_memory(yaml_content, md_content)


def test_roundtrip_conversion(temp_storage, sample_memory):
    """测试往返转换：Memory → MD → Memory"""
    # Memory → Markdown
    md = temp_storage._memory_to_markdown(sample_memory)

    # 分离 YAML 和内容
    yaml_start = md.find("---\n") + 4
    yaml_end = md.find("\n---\n", yaml_start)
    content_start = yaml_end + 5  # "\n---\n\n" 的长度

    yaml_str = md[yaml_start:yaml_end]
    content_str = md[content_start:].rstrip('\n')  # 去除末尾换行

    yaml_content = yaml.safe_load(yaml_str)

    # Markdown → Memory
    recovered_memory = temp_storage._parse_single_memory(yaml_content, content_str)

    # 验证所有字段
    assert recovered_memory.id == sample_memory.id
    assert recovered_memory.type == sample_memory.type
    assert recovered_memory.title == sample_memory.title
    assert recovered_memory.description == sample_memory.description
    assert recovered_memory.content == sample_memory.content
    assert recovered_memory.created_at == sample_memory.created_at
    assert recovered_memory.updated_at == sample_memory.updated_at
    assert recovered_memory.metadata == sample_memory.metadata


def test_unicode_handling(temp_storage):
    """测试 Unicode 字符处理"""
    memory = Memory(
        id="test-008",
        type=MemoryType.DAILY_SUMMARY,
        title="中文标题 🚀",
        description="包含 emoji 的描述 ✨",
        content="中文内容\n包含日文：こんにちは\n包含韩文：안녕하세요",
        created_at=datetime(2026, 5, 8, 10, 0, 0),
        updated_at=datetime(2026, 5, 8, 10, 0, 0),
        metadata={
            "tags": ["中文", "日文", "韩文"],
            "emoji": "🎉"
        }
    )

    # 转换
    md = temp_storage._memory_to_markdown(memory)

    # 验证 Unicode 字符保留
    assert "中文标题 🚀" in md
    assert "包含 emoji 的描述 ✨" in md
    assert "こんにちは" in md
    assert "안녕하세요" in md
    assert "🎉" in md


def test_ensure_directories(tmp_path):
    """测试目录创建"""
    backend = FileBackend(str(tmp_path / "memories"), auto_index=False)

    # 验证基础目录存在
    assert (tmp_path / "memories").exists()

    # 验证所有类型目录存在
    assert (tmp_path / "memories" / MemoryType.DAILY_SUMMARY).exists()
    assert (tmp_path / "memories" / MemoryType.WEEKLY_DIGEST).exists()
    assert (tmp_path / "memories" / MemoryType.TOPIC_INSIGHT).exists()
    assert (tmp_path / "memories" / MemoryType.PATTERN).exists()
    assert (tmp_path / "memories" / MemoryType.SIGNAL).exists()


# ========== File Operation Tests (Task 4) ==========


def test_create_memory_new_file(temp_storage, tmp_path):
    """测试创建记忆 - 新文件"""
    memory = Memory(
        id="create-001",
        type=MemoryType.DAILY_SUMMARY,
        title="新建记忆",
        description="测试新建",
        content="这是新建的内容",
        created_at=datetime(2026, 5, 10, 10, 0, 0),
        updated_at=datetime(2026, 5, 10, 10, 0, 0),
        metadata={"source": "test"}
    )

    # 创建记忆
    temp_storage.create_memory(memory)

    # 验证文件存在
    file_path = tmp_path / MemoryType.DAILY_SUMMARY / "2026-05.md"
    assert file_path.exists()

    # 验证内容
    content = file_path.read_text(encoding='utf-8')
    assert "id: create-001" in content
    assert "这是新建的内容" in content


def test_create_memory_append_to_existing(temp_storage, tmp_path):
    """测试创建记忆 - 追加到已有文件"""
    # 第一条记忆
    memory1 = Memory(
        id="append-001",
        type=MemoryType.WEEKLY_DIGEST,
        title="第一条记忆",
        description=None,
        content="第一条内容",
        created_at=datetime(2026, 5, 10, 10, 0, 0),
        updated_at=datetime(2026, 5, 10, 10, 0, 0),
        metadata={}
    )

    # 第二条记忆（同一个月）
    memory2 = Memory(
        id="append-002",
        type=MemoryType.WEEKLY_DIGEST,
        title="第二条记忆",
        description="追加测试",
        content="第二条内容",
        created_at=datetime(2026, 5, 15, 15, 0, 0),
        updated_at=datetime(2026, 5, 15, 15, 0, 0),
        metadata={"order": 2}
    )

    # 创建两条记忆
    temp_storage.create_memory(memory1)
    temp_storage.create_memory(memory2)

    # 验证文件内容
    file_path = tmp_path / MemoryType.WEEKLY_DIGEST / "2026-05.md"
    content = file_path.read_text(encoding='utf-8')

    # 验证两条记忆都存在
    assert "id: append-001" in content
    assert "id: append-002" in content
    assert "第一条内容" in content
    assert "第二条内容" in content

    # 验证格式正确：第一条有 1 个 \n---\n，第二条有 2 个（开始和结束）
    assert content.count("---") == 4  # 两条记忆各有开始和结束的 ---


def test_get_memory_found(temp_storage, sample_memory):
    """测试获取记忆 - 找到"""
    # 先创建记忆
    temp_storage.create_memory(sample_memory)

    # 获取记忆
    retrieved = temp_storage.get_memory("test-001")

    # 验证
    assert retrieved is not None
    assert retrieved.id == "test-001"
    assert retrieved.title == "测试摘要"
    assert retrieved.content == "# 标题\n\n这是测试内容"


def test_get_memory_not_found(temp_storage):
    """测试获取记忆 - 未找到"""
    result = temp_storage.get_memory("nonexistent-id")
    assert result is None


def test_get_memory_skip_archive(temp_storage, tmp_path):
    """测试获取记忆 - 跳过 archive 目录"""
    # 在 archive 目录中创建一个文件
    archive_dir = tmp_path / "archive" / MemoryType.DAILY_SUMMARY
    archive_dir.mkdir(parents=True)

    archive_file = archive_dir / "2026-01.md"
    archive_content = """---
id: archive-001
type: daily_summary
title: 归档记忆
created_at: '2026-01-15T10:00:00'
updated_at: '2026-01-15T10:00:00'
---

这是归档内容
"""
    archive_file.write_text(archive_content, encoding='utf-8')

    # 尝试获取（应该找不到）
    result = temp_storage.get_memory("archive-001")
    assert result is None


def test_get_memory_corrupted_file(temp_storage, tmp_path):
    """测试获取记忆 - 损坏的文件"""
    # 创建一个损坏的文件（缺少 frontmatter）
    corrupted_file = tmp_path / MemoryType.SIGNAL / "2026-05.md"
    corrupted_file.write_text("这是没有 frontmatter 的内容", encoding='utf-8')

    # 获取记忆（应该跳过损坏文件）
    result = temp_storage.get_memory("any-id")
    assert result is None


def test_update_memory_success(temp_storage, sample_memory):
    """测试更新记忆 - 成功"""
    # 创建原始记忆
    temp_storage.create_memory(sample_memory)

    # 修改记忆
    updated_memory = Memory(
        id="test-001",
        type=MemoryType.DAILY_SUMMARY,
        title="更新后的标题",
        description="更新后的描述",
        content="更新后的内容",
        created_at=datetime(2026, 5, 1, 10, 30, 0),  # 保持 created_at 不变
        updated_at=datetime(2026, 5, 12, 14, 0, 0),  # updated_at 更新
        metadata={"updated": True}
    )

    # 更新
    temp_storage.update_memory(updated_memory)

    # 验证更新
    retrieved = temp_storage.get_memory("test-001")
    assert retrieved is not None
    assert retrieved.title == "更新后的标题"
    assert retrieved.content == "更新后的内容"
    assert retrieved.updated_at == datetime(2026, 5, 12, 14, 0, 0)


def test_update_memory_preserve_other_memories(temp_storage, tmp_path):
    """测试更新记忆 - 保留同文件其他记忆"""
    # 创建两条记忆
    memory1 = Memory(
        id="preserve-001",
        type=MemoryType.TOPIC_INSIGHT,
        title="记忆1",
        description=None,
        content="内容1",
        created_at=datetime(2026, 5, 1, 10, 0, 0),
        updated_at=datetime(2026, 5, 1, 10, 0, 0),
        metadata={}
    )
    memory2 = Memory(
        id="preserve-002",
        type=MemoryType.TOPIC_INSIGHT,
        title="记忆2",
        description=None,
        content="内容2",
        created_at=datetime(2026, 5, 2, 10, 0, 0),
        updated_at=datetime(2026, 5, 2, 10, 0, 0),
        metadata={}
    )

    temp_storage.create_memory(memory1)
    temp_storage.create_memory(memory2)

    # 更新第一条
    updated_memory1 = Memory(
        id="preserve-001",
        type=MemoryType.TOPIC_INSIGHT,
        title="更新后的记忆1",
        description=None,
        content="更新后的内容1",
        created_at=datetime(2026, 5, 1, 10, 0, 0),
        updated_at=datetime(2026, 5, 12, 12, 0, 0),
        metadata={}
    )
    temp_storage.update_memory(updated_memory1)

    # 验证第一条已更新
    retrieved1 = temp_storage.get_memory("preserve-001")
    assert retrieved1.title == "更新后的记忆1"

    # 验证第二条未受影响
    retrieved2 = temp_storage.get_memory("preserve-002")
    assert retrieved2.title == "记忆2"
    assert retrieved2.content == "内容2"


def test_delete_memory_success(temp_storage, sample_memory):
    """测试删除记忆 - 成功"""
    # 创建记忆
    temp_storage.create_memory(sample_memory)

    # 验证存在
    assert temp_storage.get_memory("test-001") is not None

    # 删除
    temp_storage.delete_memory("test-001")

    # 验证已删除
    assert temp_storage.get_memory("test-001") is None


def test_delete_memory_preserve_other_memories(temp_storage):
    """测试删除记忆 - 保留同文件其他记忆"""
    # 创建两条记忆
    memory1 = Memory(
        id="delete-001",
        type=MemoryType.PATTERN,
        title="记忆1",
        description=None,
        content="内容1",
        created_at=datetime(2026, 5, 1, 10, 0, 0),
        updated_at=datetime(2026, 5, 1, 10, 0, 0),
        metadata={}
    )
    memory2 = Memory(
        id="delete-002",
        type=MemoryType.PATTERN,
        title="记忆2",
        description=None,
        content="内容2",
        created_at=datetime(2026, 5, 2, 10, 0, 0),
        updated_at=datetime(2026, 5, 2, 10, 0, 0),
        metadata={}
    )

    temp_storage.create_memory(memory1)
    temp_storage.create_memory(memory2)

    # 删除第一条
    temp_storage.delete_memory("delete-001")

    # 验证第一条已删除
    assert temp_storage.get_memory("delete-001") is None

    # 验证第二条仍存在
    assert temp_storage.get_memory("delete-002") is not None


def test_delete_memory_remove_empty_file(temp_storage, tmp_path):
    """测试删除记忆 - 删除空文件"""
    memory = Memory(
        id="last-001",
        type=MemoryType.SIGNAL,
        title="唯一记忆",
        description=None,
        content="内容",
        created_at=datetime(2026, 5, 10, 10, 0, 0),
        updated_at=datetime(2026, 5, 10, 10, 0, 0),
        metadata={}
    )

    temp_storage.create_memory(memory)

    # 验证文件存在
    file_path = tmp_path / MemoryType.SIGNAL / "2026-05.md"
    assert file_path.exists()

    # 删除唯一的记忆
    temp_storage.delete_memory("last-001")

    # 验证文件已删除
    assert not file_path.exists()


def test_list_memories_all(temp_storage):
    """测试列出记忆 - 所有类型"""
    # 创建不同类型的记忆
    memories = [
        Memory(
            id="list-001",
            type=MemoryType.DAILY_SUMMARY,
            title="每日摘要",
            description=None,
            content="内容1",
            created_at=datetime(2026, 5, 1, 10, 0, 0),
            updated_at=datetime(2026, 5, 1, 10, 0, 0),
            metadata={}
        ),
        Memory(
            id="list-002",
            type=MemoryType.WEEKLY_DIGEST,
            title="周报",
            description=None,
            content="内容2",
            created_at=datetime(2026, 5, 5, 10, 0, 0),
            updated_at=datetime(2026, 5, 5, 10, 0, 0),
            metadata={}
        ),
        Memory(
            id="list-003",
            type=MemoryType.DAILY_SUMMARY,
            title="每日摘要2",
            description=None,
            content="内容3",
            created_at=datetime(2026, 5, 10, 10, 0, 0),
            updated_at=datetime(2026, 5, 10, 10, 0, 0),
            metadata={}
        )
    ]

    for mem in memories:
        temp_storage.create_memory(mem)

    # 列出所有记忆
    result = temp_storage.list_memories()

    # 验证
    assert len(result) == 3
    ids = [m.id for m in result]
    assert "list-001" in ids
    assert "list-002" in ids
    assert "list-003" in ids


def test_list_memories_by_type(temp_storage):
    """测试列出记忆 - 按类型过滤"""
    # 创建不同类型的记忆
    memories = [
        Memory(
            id="filter-001",
            type=MemoryType.DAILY_SUMMARY,
            title="每日1",
            description=None,
            content="内容1",
            created_at=datetime(2026, 5, 1, 10, 0, 0),
            updated_at=datetime(2026, 5, 1, 10, 0, 0),
            metadata={}
        ),
        Memory(
            id="filter-002",
            type=MemoryType.TOPIC_INSIGHT,
            title="主题洞察",
            description=None,
            content="内容2",
            created_at=datetime(2026, 5, 2, 10, 0, 0),
            updated_at=datetime(2026, 5, 2, 10, 0, 0),
            metadata={}
        ),
        Memory(
            id="filter-003",
            type=MemoryType.DAILY_SUMMARY,
            title="每日2",
            description=None,
            content="内容3",
            created_at=datetime(2026, 5, 3, 10, 0, 0),
            updated_at=datetime(2026, 5, 3, 10, 0, 0),
            metadata={}
        )
    ]

    for mem in memories:
        temp_storage.create_memory(mem)

    # 只列出 DAILY_SUMMARY
    result = temp_storage.list_memories(memory_type=MemoryType.DAILY_SUMMARY)

    # 验证
    assert len(result) == 2
    assert all(m.type == MemoryType.DAILY_SUMMARY for m in result)


def test_list_memories_date_range(temp_storage):
    """测试列出记忆 - 日期范围过滤"""
    memories = [
        Memory(
            id="date-001",
            type=MemoryType.SIGNAL,
            title="信号1",
            description=None,
            content="内容1",
            created_at=datetime(2026, 4, 30, 10, 0, 0),
            updated_at=datetime(2026, 4, 30, 10, 0, 0),
            metadata={}
        ),
        Memory(
            id="date-002",
            type=MemoryType.SIGNAL,
            title="信号2",
            description=None,
            content="内容2",
            created_at=datetime(2026, 5, 5, 10, 0, 0),
            updated_at=datetime(2026, 5, 5, 10, 0, 0),
            metadata={}
        ),
        Memory(
            id="date-003",
            type=MemoryType.SIGNAL,
            title="信号3",
            description=None,
            content="内容3",
            created_at=datetime(2026, 5, 15, 10, 0, 0),
            updated_at=datetime(2026, 5, 15, 10, 0, 0),
            metadata={}
        )
    ]

    for mem in memories:
        temp_storage.create_memory(mem)

    # 查询 5/1 ~ 5/10
    result = temp_storage.list_memories(
        start_date=datetime(2026, 5, 1),
        end_date=datetime(2026, 5, 10)
    )

    # 验证
    assert len(result) == 1
    assert result[0].id == "date-002"


def test_list_memories_limit(temp_storage):
    """测试列出记忆 - 数量限制"""
    memories = [
        Memory(
            id=f"limit-{i:03d}",
            type=MemoryType.PATTERN,
            title=f"模式{i}",
            description=None,
            content=f"内容{i}",
            created_at=datetime(2026, 5, i, 10, 0, 0),
            updated_at=datetime(2026, 5, i, 10, 0, 0),
            metadata={}
        )
        for i in range(1, 11)  # 创建 10 条记忆
    ]

    for mem in memories:
        temp_storage.create_memory(mem)

    # 限制返回 5 条
    result = temp_storage.list_memories(limit=5)

    # 验证
    assert len(result) == 5


def test_list_memories_skip_archive(temp_storage, tmp_path):
    """测试列出记忆 - 跳过 archive 目录"""
    # 在正常目录创建记忆
    normal_memory = Memory(
        id="normal-001",
        type=MemoryType.DAILY_SUMMARY,
        title="正常记忆",
        description=None,
        content="正常内容",
        created_at=datetime(2026, 5, 1, 10, 0, 0),
        updated_at=datetime(2026, 5, 1, 10, 0, 0),
        metadata={}
    )
    temp_storage.create_memory(normal_memory)

    # 在 archive 目录创建文件
    archive_dir = tmp_path / "archive" / MemoryType.DAILY_SUMMARY
    archive_dir.mkdir(parents=True)
    archive_file = archive_dir / "2026-01.md"
    archive_content = """---
id: archive-001
type: daily_summary
title: 归档记忆
created_at: '2026-01-15T10:00:00'
updated_at: '2026-01-15T10:00:00'
---

归档内容
"""
    archive_file.write_text(archive_content, encoding='utf-8')

    # 列出记忆
    result = temp_storage.list_memories()

    # 验证：只返回正常记忆，不包含归档记忆
    assert len(result) == 1
    assert result[0].id == "normal-001"


def test_search_memories_found(temp_storage):
    """测试搜索记忆 - 找到结果"""
    memories = [
        Memory(
            id="search-001",
            type=MemoryType.DAILY_SUMMARY,
            title="AI 技术突破",
            description="关于人工智能的新发现",
            content="GPT-5 发布了，性能提升显著",
            created_at=datetime(2026, 5, 1, 10, 0, 0),
            updated_at=datetime(2026, 5, 1, 10, 0, 0),
            metadata={"keywords": ["AI", "GPT"]}
        ),
        Memory(
            id="search-002",
            type=MemoryType.WEEKLY_DIGEST,
            title="本周经济报告",
            description="经济数据分析",
            content="股市上涨，通胀下降",
            created_at=datetime(2026, 5, 2, 10, 0, 0),
            updated_at=datetime(2026, 5, 2, 10, 0, 0),
            metadata={}
        ),
        Memory(
            id="search-003",
            type=MemoryType.TOPIC_INSIGHT,
            title="区块链发展",
            description="AI 与区块链结合的新趋势",
            content="AI 驱动的智能合约",
            created_at=datetime(2026, 5, 3, 10, 0, 0),
            updated_at=datetime(2026, 5, 3, 10, 0, 0),
            metadata={}
        )
    ]

    for mem in memories:
        temp_storage.create_memory(mem)

    # 搜索 "AI"
    result = temp_storage.search_memories("AI")

    # 验证：应该找到 search-001 和 search-003
    assert len(result) == 2
    ids = [m.id for m in result]
    assert "search-001" in ids
    assert "search-003" in ids


def test_search_memories_case_insensitive(temp_storage):
    """测试搜索记忆 - 忽略大小写"""
    memory = Memory(
        id="case-001",
        type=MemoryType.SIGNAL,
        title="Python 编程",
        description=None,
        content="Python 是一门强大的语言",
        created_at=datetime(2026, 5, 1, 10, 0, 0),
        updated_at=datetime(2026, 5, 1, 10, 0, 0),
        metadata={}
    )
    temp_storage.create_memory(memory)

    # 使用小写搜索
    result = temp_storage.search_memories("python")

    # 验证：应该找到
    assert len(result) == 1
    assert result[0].id == "case-001"


def test_search_memories_with_limit(temp_storage):
    """测试搜索记忆 - 限制数量"""
    memories = [
        Memory(
            id=f"limit-search-{i:03d}",
            type=MemoryType.DAILY_SUMMARY,
            title=f"测试{i}",
            description=None,
            content="测试内容",
            created_at=datetime(2026, 5, i, 10, 0, 0),
            updated_at=datetime(2026, 5, i, 10, 0, 0),
            metadata={}
        )
        for i in range(1, 11)  # 10 条都包含 "测试"
    ]

    for mem in memories:
        temp_storage.create_memory(mem)

    # 搜索并限制返回 3 条
    result = temp_storage.search_memories("测试", limit=3)

    # 验证
    assert len(result) == 3


def test_search_memories_not_found(temp_storage):
    """测试搜索记忆 - 未找到"""
    memory = Memory(
        id="no-match-001",
        type=MemoryType.PATTERN,
        title="无关内容",
        description=None,
        content="这里没有要搜索的关键词",
        created_at=datetime(2026, 5, 1, 10, 0, 0),
        updated_at=datetime(2026, 5, 1, 10, 0, 0),
        metadata={}
    )
    temp_storage.create_memory(memory)

    # 搜索不存在的关键词
    result = temp_storage.search_memories("不存在的关键词XYZ")

    # 验证
    assert len(result) == 0
