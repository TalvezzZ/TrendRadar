"""
每日摘要增强模块

为通知推送添加历史每日摘要（每日摘要）内容
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from trendradar.memory.models import Memory, MemoryType, MemoryRepository
from trendradar.memory.storage.database import DatabaseBackend
from trendradar.memory.storage.file import FileBackend


logger = logging.getLogger(__name__)


class DigestEnhancer:
    """每日摘要增强器 - 为通知推送添加历史每日摘要"""

    def __init__(self, data_dir: str = "output", use_file_storage: bool = True):
        """
        初始化增强器

        Args:
            data_dir: 数据目录路径
            use_file_storage: 是否使用文件存储（默认True）
        """
        self.data_dir = Path(data_dir)
        self.use_file_storage = use_file_storage
        self.memory_db = self.data_dir / "memory.db"
        self.memory_markdown = self.data_dir / "memory_markdown"

    def get_recent_summaries(
        self,
        days: int = 7,
        max_summaries: int = 3
    ) -> Dict[str, Any]:
        """
        获取最近的每日摘要

        Args:
            days: 查询最近多少天的摘要
            max_summaries: 最多返回多少条摘要

        Returns:
            包含摘要列表的字典
        """
        result = {
            "summaries": [],
            "has_summaries": False,
            "error": None
        }

        try:
            # 根据配置选择存储后端
            if self.use_file_storage:
                # 文件存储模式
                if not self.memory_markdown.exists():
                    logger.debug(f"记忆文件目录不存在: {self.memory_markdown}")
                    return result
                backend = FileBackend(base_path=str(self.memory_markdown), auto_index=False)
            else:
                # 数据库存储模式
                if not self.memory_db.exists():
                    logger.debug(f"记忆数据库不存在: {self.memory_db}")
                    return result
                backend = DatabaseBackend(db_path=str(self.memory_db))

            repo = MemoryRepository(backend)

            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 查询每日摘要
            memories = repo.get_by_date_range(
                start_date=start_date,
                end_date=end_date,
                memory_type=MemoryType.DAILY_SUMMARY
            )

            # 限制数量并按日期倒序排序
            memories = sorted(memories, key=lambda m: m.created_at, reverse=True)[:max_summaries]

            if memories:
                result["has_summaries"] = True
                result["summaries"] = [
                    {
                        "id": m.id,
                        "title": m.title,
                        "content": m.content,
                        "description": m.description,
                        "date": m.created_at.strftime("%Y-%m-%d"),
                        "created_at": m.created_at
                    }
                    for m in memories
                ]

        except Exception as e:
            logger.error(f"获取每日摘要失败: {e}")
            result["error"] = str(e)

        return result

    def format_summaries_for_notification(
        self,
        summaries_data: Dict[str, Any],
        max_content_length: int = 300
    ) -> str:
        """
        格式化每日摘要为通知内容

        Args:
            summaries_data: get_recent_summaries 返回的数据
            max_content_length: 每条摘要内容的最大字符数

        Returns:
            格式化的通知内容
        """
        if not summaries_data.get("has_summaries"):
            return ""

        summaries = summaries_data.get("summaries", [])
        if not summaries:
            return ""

        sections = []
        sections.append("━━━━━━━━━━━━━━━━━━")
        sections.append("📝 每日摘要回顾")
        sections.append("")

        for i, summary in enumerate(summaries, 1):
            date = summary["date"]
            title = summary["title"]
            content = summary["content"]

            # 计算距今天数
            created_at = summary["created_at"]
            days_ago = (datetime.now() - created_at).days

            if days_ago == 0:
                time_desc = "今天"
            elif days_ago == 1:
                time_desc = "昨天"
            else:
                time_desc = f"{days_ago}天前"

            # 标题行
            sections.append(f"**{time_desc} ({date})**")

            # 摘要内容（截断过长内容）
            if len(content) > max_content_length:
                truncated_content = content[:max_content_length].strip() + "..."
            else:
                truncated_content = content.strip()

            # 分段显示摘要内容
            for line in truncated_content.split("\n"):
                if line.strip():
                    sections.append(f"  {line.strip()}")

            # 每条摘要间添加空行
            if i < len(summaries):
                sections.append("")

        return "\n".join(sections)

    def enhance_notification(
        self,
        days: int = 7,
        max_summaries: int = 3,
        max_content_length: int = 300
    ) -> Optional[str]:
        """
        生成用于通知增强的每日摘要内容

        Args:
            days: 查询最近多少天的摘要
            max_summaries: 最多返回多少条摘要
            max_content_length: 每条摘要内容的最大字符数

        Returns:
            格式化的摘要内容，如果没有摘要则返回 None
        """
        summaries_data = self.get_recent_summaries(days=days, max_summaries=max_summaries)

        if not summaries_data.get("has_summaries"):
            logger.debug("没有找到最近的每日摘要")
            return None

        content = self.format_summaries_for_notification(
            summaries_data,
            max_content_length=max_content_length
        )

        return content if content else None
