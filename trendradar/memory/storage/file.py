"""
文件存储后端
"""
import re
import yaml
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from trendradar.memory.models import Memory, MemoryType
from trendradar.memory.storage.base import StorageBackend
from trendradar.memory.storage.exceptions import (
    MemoryParseError,
    MemoryCorruptedError
)


class FileBackend(StorageBackend):
    """文件存储后端，使用 Markdown + YAML frontmatter 格式"""

    def __init__(self, base_path: str, auto_index: bool = True):
        """
        初始化文件存储后端

        Args:
            base_path: 基础路径，用于存储记忆文件
            auto_index: 是否自动更新 MEMORY.md 索引
        """
        self.base_path = Path(base_path)
        self.auto_index = auto_index
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """创建类型目录：daily_summary, weekly_digest 等"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        for mem_type in [
            MemoryType.DAILY_SUMMARY,
            MemoryType.WEEKLY_DIGEST,
            MemoryType.TOPIC_INSIGHT,
            MemoryType.PATTERN,
            MemoryType.SIGNAL
        ]:
            (self.base_path / mem_type).mkdir(exist_ok=True)

    def _memory_to_markdown(self, memory: Memory) -> str:
        """
        将 Memory 对象转换为 Markdown 格式

        格式：
        ---
        id: test-001
        type: daily_summary
        title: 标题
        description: 描述
        created_at: '2026-05-01T10:30:00'
        updated_at: '2026-05-01T10:30:00'
        metadata:
          key: value
        ---

        # 标题

        内容正文

        Args:
            memory: 记忆对象

        Returns:
            Markdown 格式的字符串
        """
        # 构建 YAML frontmatter
        frontmatter = {
            "id": memory.id,
            "type": memory.type,
            "title": memory.title,
            "description": memory.description,
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat(),
            "metadata": memory.metadata
        }

        # 使用 yaml.dump 转换，保留 Unicode 字符
        yaml_str = yaml.dump(
            frontmatter,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False
        )

        # 组装 Markdown
        return f"---\n{yaml_str}---\n\n{memory.content}\n"

    def _parse_single_memory(
        self,
        yaml_content: dict,
        md_content: str
    ) -> Memory:
        """
        解析 YAML frontmatter + Markdown 内容为 Memory 对象

        Args:
            yaml_content: YAML 解析后的字典
            md_content: Markdown 内容

        Returns:
            Memory 对象

        Raises:
            MemoryParseError: YAML 解析错误或日期格式错误
            MemoryCorruptedError: 缺少必填字段
        """
        # Add input validation
        if not isinstance(yaml_content, dict):
            raise MemoryParseError("yaml_content must be a dict")
        if not isinstance(md_content, str):
            raise MemoryParseError("md_content must be a string")

        try:
            # 验证必填字段
            required_fields = ["id", "type", "title", "created_at", "updated_at"]
            missing_fields = [f for f in required_fields if f not in yaml_content]

            if missing_fields:
                raise MemoryCorruptedError(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )

            # 解析日期时间
            try:
                created_at = datetime.fromisoformat(yaml_content["created_at"])
                updated_at = datetime.fromisoformat(yaml_content["updated_at"])
            except (ValueError, TypeError) as e:
                raise MemoryParseError(f"Invalid datetime format: {e}")

            # 构建 Memory 对象
            return Memory(
                id=yaml_content["id"],
                type=yaml_content["type"],
                title=yaml_content["title"],
                description=yaml_content.get("description"),
                content=md_content.strip(),
                created_at=created_at,
                updated_at=updated_at,
                metadata=yaml_content.get("metadata", {})
            )

        except (MemoryParseError, MemoryCorruptedError):
            # 重新抛出我们自己的异常
            raise
        except Exception as e:
            # 其他异常转换为 MemoryParseError
            raise MemoryParseError(f"Failed to parse memory: {e}")

    # ========== File Operations (Task 4) ==========

    def _get_file_path(self, memory: Memory) -> Path:
        """
        根据记忆类型和日期确定文件路径

        Args:
            memory: 记忆对象

        Returns:
            文件路径

        Raises:
            ValueError: 如果 memory.type 不是有效的记忆类型
        """
        # Validate memory.type against allowed values
        allowed_types = [
            MemoryType.DAILY_SUMMARY,
            MemoryType.WEEKLY_DIGEST,
            MemoryType.TOPIC_INSIGHT,
            MemoryType.PATTERN,
            MemoryType.SIGNAL
        ]
        if memory.type not in allowed_types:
            raise ValueError(f"Invalid memory type: {memory.type}")

        date = memory.created_at
        file_name = f"{date.year}-{date.month:02d}.md"
        type_dir = self.base_path / memory.type
        return type_dir / file_name

    def _find_file_by_id(self, memory_id: str) -> Optional[Path]:
        """查找包含指定记忆的文件"""
        # Escape special regex characters in memory_id
        escaped_id = re.escape(memory_id)

        for type_dir in self.base_path.iterdir():
            if not type_dir.is_dir() or type_dir.name in ('archive', '.git'):
                continue

            for md_file in type_dir.glob("**/*.md"):
                if md_file.name == "MEMORY.md":
                    continue
                try:
                    content = md_file.read_text(encoding='utf-8')
                    # Use regex with word boundaries to match exact ID
                    if re.search(rf'^id:\s+{escaped_id}\s*$', content, re.MULTILINE):
                        return md_file
                except (OSError, IOError):
                    continue

        return None

    def _parse_markdown_file(self, file_path: Path) -> List[Memory]:
        """解析 Markdown 文件，返回所有记忆"""
        try:
            content = file_path.read_text(encoding='utf-8')
        except (OSError, IOError):
            return []

        memories = []
        # 按 "---\n" 分割多个记忆
        sections = content.split("\n---\n")

        i = 0
        while i < len(sections):
            # YAML frontmatter
            if i == 0 and sections[i].startswith("---\n"):
                yaml_section = sections[i][4:]  # 跳过开头的 "---\n"
            else:
                yaml_section = sections[i]

            # Markdown 内容
            if i + 1 < len(sections):
                md_section = sections[i + 1].strip()
            else:
                md_section = ""

            try:
                yaml_content = yaml.safe_load(yaml_section)
                if yaml_content:
                    memory = self._parse_single_memory(yaml_content, md_section)
                    memories.append(memory)
            except (MemoryParseError, MemoryCorruptedError):
                # 跳过损坏的记忆
                pass

            i += 2  # 每个记忆占两个 section

        return memories

    def create_memory(self, memory: Memory) -> None:
        """创建记忆"""
        file_path = self._get_file_path(memory)
        md_content = self._memory_to_markdown(memory)

        if file_path.exists():
            # 追加到已有文件
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write('\n')  # 分隔符
                f.write(md_content)
        else:
            # 创建新文件
            file_path.write_text(md_content, encoding='utf-8')

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        file_path = self._find_file_by_id(memory_id)
        if not file_path:
            return None

        memories = self._parse_markdown_file(file_path)
        for memory in memories:
            if memory.id == memory_id:
                return memory

        return None

    def update_memory(self, memory: Memory) -> None:
        """更新记忆"""
        file_path = self._find_file_by_id(memory.id)
        if not file_path:
            return

        # 读取所有记忆
        memories = self._parse_markdown_file(file_path)

        # 更新目标记忆
        updated_memories = [
            memory if m.id == memory.id else m
            for m in memories
        ]

        # 重新写入文件
        content = ""
        for i, mem in enumerate(updated_memories):
            if i > 0:
                content += "\n"  # 分隔符
            content += self._memory_to_markdown(mem)

        file_path.write_text(content, encoding='utf-8')

    def delete_memory(self, memory_id: str) -> None:
        """删除记忆"""
        file_path = self._find_file_by_id(memory_id)
        if not file_path:
            return

        # 读取所有记忆
        memories = self._parse_markdown_file(file_path)

        # 过滤掉要删除的记忆
        remaining_memories = [m for m in memories if m.id != memory_id]

        if remaining_memories:
            # 重新写入文件
            content = ""
            for i, mem in enumerate(remaining_memories):
                if i > 0:
                    content += "\n"  # 分隔符
                content += self._memory_to_markdown(mem)

            file_path.write_text(content, encoding='utf-8')
        else:
            # 没有剩余记忆，删除文件
            file_path.unlink()

    def list_memories(
        self,
        memory_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """列出记忆"""
        memories = []

        # 确定要扫描的目录
        if memory_type:
            dirs = [self.base_path / memory_type]
        else:
            dirs = [d for d in self.base_path.iterdir()
                    if d.is_dir() and d.name not in ('archive', '.git')]

        # 扫描所有文件
        for type_dir in dirs:
            if not type_dir.exists():
                continue

            for md_file in type_dir.glob("*.md"):
                file_memories = self._parse_markdown_file(md_file)
                memories.extend(file_memories)

        # 日期过滤
        if start_date:
            memories = [m for m in memories if m.created_at >= start_date]
        if end_date:
            memories = [m for m in memories if m.created_at <= end_date]

        # 数量限制
        if limit:
            memories = memories[:limit]

        return memories

    def search_memories(
        self,
        keyword: str,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """搜索记忆"""
        # 获取所有记忆
        all_memories = self.list_memories()

        # 关键词搜索（忽略大小写）
        keyword_lower = keyword.lower()
        matched = []

        for memory in all_memories:
            # 搜索 title, description, content
            if (keyword_lower in memory.title.lower() or
                (memory.description and keyword_lower in memory.description.lower()) or
                keyword_lower in memory.content.lower()):
                matched.append(memory)

        # 数量限制
        if limit:
            matched = matched[:limit]

        return matched
