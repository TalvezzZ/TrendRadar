"""
记忆生成器

使用 AI 从存储的数据中生成智能记忆摘要。
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from trendradar.ai.client import AIClient
from trendradar.memory.models import (
    Memory,
    MemoryLink,
    MemoryRepository,
    MemoryType,
    LinkType
)
from trendradar.memory.storage.database import DatabaseBackend
from trendradar.persistence.ai_storage import AIAnalysisStorage


class MemoryGenerator:
    """
    记忆生成器

    使用 AI 分析历史数据，生成智能记忆摘要。
    """

    def __init__(self, db_path: str, ai_config: Dict[str, Any]):
        """
        初始化记忆生成器

        Args:
            db_path: 数据库文件路径
            ai_config: AI 客户端配置
        """
        self.db_path = db_path

        # 确保数据库表存在
        self._ensure_schema()

        backend = DatabaseBackend(db_path)
        self.repository = MemoryRepository(backend)
        self.ai_client = AIClient(ai_config)
        self.ai_storage = AIAnalysisStorage(db_path)

    def _ensure_schema(self) -> None:
        """确保数据库中存在所有必要的表"""
        from trendradar.persistence.schema import (
            initialize_ai_analysis_tables,
            initialize_memory_tables
        )

        conn = sqlite3.connect(self.db_path)
        try:
            initialize_ai_analysis_tables(conn)
            initialize_memory_tables(conn)
        finally:
            conn.close()

    def generate_daily_summary(self, date: datetime) -> Optional[Memory]:
        """
        生成每日摘要记忆

        从指定日期的 AI 分析和关键词统计中生成摘要。

        Args:
            date: 目标日期

        Returns:
            生成的记忆对象，如果没有数据则返回 None

        Raises:
            Exception: AI 调用失败时抛出异常
        """
        # 收集数据
        data = self._gather_daily_data(date)
        if data is None:
            return None

        # 构建提示词
        prompt = self._build_daily_summary_prompt(data)

        # 调用 AI 生成摘要
        ai_response = self._call_ai(prompt)

        # 创建记忆对象
        now = datetime.now()
        memory_id = self._create_memory_id(MemoryType.DAILY_SUMMARY, date)

        memory = Memory(
            id=memory_id,
            type=MemoryType.DAILY_SUMMARY,
            title=f"每日摘要 - {data['date']}",
            description=f"基于 {data['news_count']} 条新闻和 {data['rss_count']} 条 RSS 的智能分析摘要",
            content=ai_response,
            metadata={
                "date": data["date"],
                "news_count": data["news_count"],
                "rss_count": data["rss_count"],
                "top_keywords": [kw["keyword"] for kw in data["top_keywords"][:5]],
                "platforms": data.get("platforms", [])
            },
            created_at=now,
            updated_at=now
        )

        # 保存到数据库
        self.repository.create(memory)

        return memory

    def generate_weekly_digest(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[Memory]:
        """
        生成每周摘要记忆

        从一周的每日摘要中生成周度洞察。

        Args:
            start_date: 开始日期（包含）
            end_date: 结束日期（包含）

        Returns:
            生成的记忆对象，如果没有数据则返回 None

        Raises:
            Exception: AI 调用失败时抛出异常
        """
        # 获取日期范围内的每日摘要
        daily_memories = self.repository.get_by_date_range(
            start_date,
            end_date,
            MemoryType.DAILY_SUMMARY
        )

        if not daily_memories:
            return None

        # 构建提示词
        prompt = self._build_weekly_digest_prompt(daily_memories, start_date, end_date)

        # 调用 AI 生成摘要
        ai_response = self._call_ai(prompt)

        # 创建记忆对象
        now = datetime.now()
        memory_id = self._create_memory_id(MemoryType.WEEKLY_DIGEST, start_date)

        memory = Memory(
            id=memory_id,
            type=MemoryType.WEEKLY_DIGEST,
            title=f"每周摘要 - {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}",
            description=f"基于 {len(daily_memories)} 天每日摘要的周度洞察",
            content=ai_response,
            metadata={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "daily_count": len(daily_memories),
                "daily_memory_ids": [m.id for m in daily_memories]
            },
            created_at=now,
            updated_at=now
        )

        # 保存到数据库
        self.repository.create(memory)

        # 创建链接：周摘要 derives_from 每日摘要
        for daily_memory in daily_memories:
            link = MemoryLink(
                from_memory_id=memory.id,
                to_memory_id=daily_memory.id,
                link_type=LinkType.DERIVES_FROM,
                notes=f"基于 {daily_memory.metadata.get('date', '未知日期')} 的数据",
                created_at=now
            )
            self.repository.create_link(link)

        return memory

    def _call_ai(self, prompt: str) -> str:
        """
        调用 AI 生成内容

        Args:
            prompt: 提示词

        Returns:
            AI 生成的内容

        Raises:
            Exception: AI 调用失败时抛出异常
        """
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        return self.ai_client.chat(messages)

    def _gather_daily_data(self, date: datetime) -> Optional[Dict[str, Any]]:
        """
        收集指定日期的所有相关数据

        Args:
            date: 目标日期

        Returns:
            包含所有数据的字典，如果没有数据则返回 None
        """
        date_str = date.strftime("%Y-%m-%d")
        start_time = f"{date_str}T00:00:00"
        end_time = f"{date_str}T23:59:59"

        # 获取 AI 分析结果
        analyses = self.ai_storage.get_analysis_by_time_range(start_time, end_time)
        if not analyses:
            return None

        # 合并所有分析结果
        total_news = sum(a.get("news_count", 0) for a in analyses)
        total_rss = sum(a.get("rss_count", 0) for a in analyses)

        all_keywords = []
        all_platforms = set()

        for analysis in analyses:
            all_keywords.extend(analysis.get("matched_keywords", []))
            all_platforms.update(analysis.get("platforms", []))

        # 获取 AI 分析板块
        ai_sections = {}
        if analyses:
            # 使用最新的分析结果
            latest_analysis = analyses[-1]
            ai_sections = self.ai_storage.get_sections_by_analysis_id(latest_analysis["id"])

        # 获取关键词统计
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT keyword, count, platforms, rank
            FROM keyword_trends
            WHERE date = ?
            ORDER BY count DESC
            LIMIT 20
        """, (date_str,))

        top_keywords = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            row_dict["platforms"] = json.loads(row_dict["platforms"]) if row_dict["platforms"] else []
            top_keywords.append(row_dict)

        conn.close()

        return {
            "date": date_str,
            "news_count": total_news,
            "rss_count": total_rss,
            "matched_keywords": list(set(all_keywords)),
            "platforms": list(all_platforms),
            "ai_sections": ai_sections,
            "top_keywords": top_keywords
        }

    def _build_daily_summary_prompt(self, data: Dict[str, Any]) -> str:
        """
        构建每日摘要的提示词

        Args:
            data: 收集的每日数据

        Returns:
            提示词字符串
        """
        sections_text = ""
        if data["ai_sections"]:
            sections_text = "\n\n### AI 分析板块\n"
            for section_type, content in data["ai_sections"].items():
                sections_text += f"\n**{section_type}**:\n{content}\n"

        keywords_text = ""
        if data["top_keywords"]:
            keywords_text = "\n\n### Top 关键词\n"
            for kw in data["top_keywords"][:10]:
                keywords_text += f"- {kw['keyword']}: {kw['count']} 次\n"

        prompt = f"""
请基于以下数据生成一份简洁的每日摘要（200-300字）：

## 日期
{data['date']}

## 数据规模
- 新闻数量: {data['news_count']}
- RSS 数量: {data['rss_count']}
- 覆盖平台: {', '.join(data['platforms'])}

{sections_text}

{keywords_text}

## 要求
1. 提取 2-3 个关键趋势
2. 突出重要信号和变化
3. 语言简洁专业
4. 不要重复数据统计
5. 使用中文输出
"""
        return prompt

    def _build_weekly_digest_prompt(
        self,
        daily_memories: List[Memory],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """
        构建每周摘要的提示词

        Args:
            daily_memories: 每日摘要列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            提示词字符串
        """
        daily_summaries = ""
        for memory in daily_memories:
            date = memory.metadata.get("date", "未知")
            daily_summaries += f"\n### {date}\n{memory.content}\n"

        prompt = f"""
请基于以下 {len(daily_memories)} 天的每日摘要，生成一份周度洞察（300-400字）：

## 时间范围
{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}

## 每日摘要
{daily_summaries}

## 要求
1. 识别本周的主要趋势和模式
2. 突出关键事件和转折点
3. 分析趋势的演变和联系
4. 提供前瞻性见解
5. 语言专业、结构清晰
6. 使用中文输出
"""
        return prompt

    def _create_memory_id(self, memory_type: str, date: datetime) -> str:
        """
        生成记忆 ID

        Args:
            memory_type: 记忆类型
            date: 日期

        Returns:
            记忆 ID
        """
        date_str = date.strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%H%M%S")
        return f"{memory_type}-{date_str}-{timestamp}"
