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
    ) -> Optional[Memory]:
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

    def create_memory(self, memory: Memory) -> None:
        """创建记忆（Task 4 实现）"""
        raise NotImplementedError()

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆（Task 4 实现）"""
        raise NotImplementedError()

    def update_memory(self, memory: Memory) -> None:
        """更新记忆（Task 4 实现）"""
        raise NotImplementedError()

    def delete_memory(self, memory_id: str) -> None:
        """删除记忆（Task 4 实现）"""
        raise NotImplementedError()

    def list_memories(
        self,
        memory_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """列出记忆（Task 4 实现）"""
        raise NotImplementedError()

    def search_memories(
        self,
        keyword: str,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """搜索记忆（Task 4 实现）"""
        raise NotImplementedError()
