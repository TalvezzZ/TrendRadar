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
