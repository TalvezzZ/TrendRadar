"""
记忆索引管理器

负责生成和维护 MEMORY.md 索引文件
"""

import logging
import yaml
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from trendradar_custom.memory.models import MemoryType

logger = logging.getLogger(__name__)


class MemoryIndexManager:
    """记忆索引管理器"""

    # 类型名称映射（中文）
    TYPE_NAME_MAP = {
        MemoryType.DAILY_SUMMARY: '每日摘要',
        MemoryType.WEEKLY_DIGEST: '每周摘要',
        MemoryType.TOPIC_INSIGHT: '主题洞察',
        MemoryType.PATTERN: '模式识别',
        MemoryType.SIGNAL: '信号记录'
    }

    def __init__(self, base_path: Path):
        """
        初始化索引管理器

        Args:
            base_path: 记忆文件的基础路径
        """
        self.base_path = Path(base_path)
        self.index_file = self.base_path / "MEMORY.md"

    def update_index(self) -> None:
        """扫描所有记忆文件并重新生成 MEMORY.md"""
        try:
            # 扫描所有类型目录
            all_memories = {}

            for mem_type in [
                MemoryType.DAILY_SUMMARY,
                MemoryType.WEEKLY_DIGEST,
                MemoryType.TOPIC_INSIGHT,
                MemoryType.PATTERN,
                MemoryType.SIGNAL
            ]:
                type_dir = self.base_path / mem_type
                if not type_dir.exists():
                    continue

                # 扫描该类型的所有文件
                type_memories = []
                for md_file in type_dir.glob("*.md"):
                    if md_file.name == "MEMORY.md":
                        continue

                    file_memories = self._scan_file(md_file)
                    type_memories.extend(file_memories)

                if type_memories:
                    all_memories[mem_type] = type_memories

            # 生成索引内容
            content = self._generate_index_content(all_memories)

            # 写入文件
            self.index_file.write_text(content, encoding='utf-8')

        except Exception as e:
            logger.warning(f"Failed to update index: {e}")

    def _scan_file(self, file_path: Path) -> List[Dict]:
        """
        从文件中提取索引信息

        Args:
            file_path: Markdown 文件路径

        Returns:
            记忆信息列表，每个元素包含：
            - id: 记忆 ID
            - title: 标题
            - description: 描述
            - created_at: 创建时间
            - keywords: 关键词列表
        """
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

            try:
                yaml_content = yaml.safe_load(yaml_section)
                if not yaml_content:
                    i += 2
                    continue

                metadata = yaml_content.get('metadata', {}) or {}
                created_at = datetime.fromisoformat(yaml_content.get('created_at'))
                display_date = self._get_display_date(yaml_content.get('type'), metadata, created_at)

                # 提取所需字段
                memory_info = {
                    'id': yaml_content.get('id'),
                    'title': yaml_content.get('title'),
                    'description': yaml_content.get('description'),
                    'created_at': created_at,
                    'display_date': display_date,
                    'file_path': str(file_path.relative_to(self.base_path)),
                    'keywords': metadata.get('keywords', [])
                }

                memories.append(memory_info)

            except Exception as e:
                logger.warning(f"Failed to parse memory in {file_path}: {e}")

            i += 2  # 每个记忆占两个 section

        return memories

    def _get_display_date(self, memory_type: str, metadata: Dict, created_at: datetime) -> str:
        """Return the business date shown in MEMORY.md."""
        if memory_type == MemoryType.DAILY_SUMMARY and metadata.get('date'):
            return metadata['date']

        if memory_type == MemoryType.WEEKLY_DIGEST:
            start_date = metadata.get('start_date')
            end_date = metadata.get('end_date')
            if start_date and end_date:
                return f"{start_date} 至 {end_date}"
            if start_date:
                return start_date

        return created_at.strftime('%Y-%m-%d')

    def _generate_index_content(self, all_memories: Dict[str, List]) -> str:
        """
        生成 Markdown 索引内容

        Args:
            all_memories: 所有记忆的字典，key 为类型，value 为记忆列表

        Returns:
            Markdown 格式的索引内容
        """
        lines = []

        # 标题和更新时间
        lines.append("# TrendRadar 记忆索引")
        lines.append("")
        lines.append(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 按类型分组
        for mem_type in [
            MemoryType.DAILY_SUMMARY,
            MemoryType.WEEKLY_DIGEST,
            MemoryType.TOPIC_INSIGHT,
            MemoryType.PATTERN,
            MemoryType.SIGNAL
        ]:
            if mem_type not in all_memories:
                continue

            # 类型标题
            type_name = self.TYPE_NAME_MAP.get(mem_type, mem_type)
            lines.append(f"## {type_name} ({mem_type})")
            lines.append("")

            # 记忆条目
            memories = all_memories[mem_type]
            for memory in memories:
                date_str = memory['display_date']
                file_path = memory['file_path']

                # 锚点
                anchor = memory['id']

                # 描述和关键词
                desc_parts = []
                if memory['description']:
                    desc_parts.append(memory['description'])

                if memory['keywords']:
                    keywords_str = '、'.join(memory['keywords'])
                    desc_parts.append(f"关键词：{keywords_str}")

                desc = '，'.join(desc_parts) if desc_parts else ''

                # 生成条目
                if desc:
                    line = f"- [{date_str}]({file_path}#{anchor}) — {desc}"
                else:
                    line = f"- [{date_str}]({file_path}#{anchor})"

                lines.append(line)

            lines.append("")

        return '\n'.join(lines)
