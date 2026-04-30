"""
记忆增强模块

为新闻推送提供历史上下文和智能洞察
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


class MemoryEnhancer:
    """记忆增强器 - 为新闻推送添加历史上下文"""

    def __init__(self, data_dir: str = "output"):
        """
        初始化增强器

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
        self.memory_db = self.data_dir / "memory.db"
        self.news_dir = self.data_dir / "news"

    def enhance_news_push(
        self,
        news_items: List[Dict[str, Any]],
        matched_keywords: List[str]
    ) -> Dict[str, Any]:
        """
        增强新闻推送内容

        Args:
            news_items: 匹配的新闻列表
            matched_keywords: 匹配的关键词列表

        Returns:
            增强后的推送内容
        """
        enhancement = {
            "news_with_context": [],
            "trend_alerts": [],
            "topic_insights": {
                "continuing": [],  # 持续话题
                "breaking": [],    # 突发事件
                "cooling": []      # 冷却话题
            },
            "memory_stats": {}
        }

        # 1. 为每条新闻添加记忆上下文
        for news in news_items[:10]:  # 只增强前10条
            context = self._find_related_context(news)
            enhancement["news_with_context"].append({
                "news": news,
                "context": context
            })

        # 2. 生成趋势提醒
        enhancement["trend_alerts"] = self._generate_trend_alerts(matched_keywords)

        # 3. 话题洞察
        enhancement["topic_insights"] = self._analyze_topic_insights(matched_keywords)

        # 4. 记忆统计
        enhancement["memory_stats"] = self._get_memory_stats()

        return enhancement

    def _find_related_context(self, news: Dict[str, Any]) -> Dict[str, Any]:
        """
        查找新闻的相关历史上下文

        Args:
            news: 新闻数据

        Returns:
            相关上下文信息
        """
        context = {
            "has_memory": False,
            "related_memories": [],
            "is_new_topic": True,
            "trend": None
        }

        if not self.memory_db.exists():
            return context

        # 提取新闻标题中的关键词（简单分词）
        title = news.get("title", "")
        keywords = self._extract_keywords_from_title(title)

        if not keywords:
            return context

        conn = sqlite3.connect(self.memory_db)
        cursor = conn.cursor()

        try:
            # 查询相关记忆
            keyword_pattern = "|".join(keywords)  # 简单的关键词匹配

            cursor.execute("""
                SELECT id, type, title, created_at, metadata
                FROM memories
                WHERE content LIKE ? OR title LIKE ?
                ORDER BY created_at DESC
                LIMIT 3
            """, (f"%{keywords[0]}%", f"%{keywords[0]}%"))

            memories = []
            for row in cursor.fetchall():
                memories.append({
                    "id": row[0],
                    "type": row[1],
                    "title": row[2],
                    "created_at": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {}
                })

            if memories:
                context["has_memory"] = True
                context["related_memories"] = memories
                context["is_new_topic"] = False

                # 计算时间跨度
                latest_memory = memories[0]
                memory_date = datetime.fromisoformat(latest_memory["created_at"])
                days_ago = (datetime.now() - memory_date).days

                context["last_mention"] = {
                    "date": latest_memory["created_at"][:10],
                    "days_ago": days_ago
                }

        finally:
            conn.close()

        # 查询趋势信息
        context["trend"] = self._get_keyword_trend(keywords[0])

        return context

    def _extract_keywords_from_title(self, title: str) -> List[str]:
        """
        从标题中提取关键词（简单实现）

        Args:
            title: 新闻标题

        Returns:
            关键词列表
        """
        # 常见的公司/产品/技术关键词（可以扩展）
        known_keywords = [
            "DeepSeek", "OpenAI", "Claude", "ChatGPT",
            "特斯拉", "Tesla", "比亚迪", "华为",
            "鸿蒙", "FSD", "自动驾驶",
            "AI", "人工智能", "芯片", "GPU"
        ]

        keywords = []
        for keyword in known_keywords:
            if keyword in title:
                keywords.append(keyword)

        return keywords[:3]  # 最多返回3个关键词

    def _get_keyword_trend(self, keyword: str) -> Optional[Dict[str, Any]]:
        """
        获取关键词趋势

        Args:
            keyword: 关键词

        Returns:
            趋势信息
        """
        if not self.news_dir.exists():
            return None

        # 获取最近7天的数据
        recent_days = 7
        frequencies = []

        for i in range(recent_days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            db_file = self.news_dir / f"{date_str}.db"

            if not db_file.exists():
                continue

            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            try:
                # 检查表是否存在
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='keyword_trends'"
                )
                if not cursor.fetchone():
                    continue

                cursor.execute("""
                    SELECT frequency
                    FROM keyword_trends
                    WHERE keyword = ? AND date = ?
                """, (keyword, date_str))

                row = cursor.fetchone()
                freq = row[0] if row else 0
                frequencies.append({"date": date_str, "frequency": freq})

            finally:
                conn.close()

        if not frequencies or len(frequencies) < 2:
            return None

        # 计算趋势
        recent_freq = frequencies[0]["frequency"]
        avg_freq = sum(f["frequency"] for f in frequencies[1:]) / len(frequencies[1:])

        if avg_freq == 0:
            change_pct = 0
        else:
            change_pct = ((recent_freq - avg_freq) / avg_freq) * 100

        trend_direction = "rising" if change_pct > 50 else "falling" if change_pct < -50 else "stable"

        return {
            "current": recent_freq,
            "average": round(avg_freq, 1),
            "change_pct": round(change_pct, 1),
            "direction": trend_direction
        }

    def _generate_trend_alerts(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        生成趋势提醒

        Args:
            keywords: 关键词列表

        Returns:
            趋势提醒列表
        """
        alerts = []

        for keyword in keywords[:5]:  # 只检查前5个
            trend = self._get_keyword_trend(keyword)

            if trend and abs(trend["change_pct"]) > 100:  # 变化超过100%
                alerts.append({
                    "keyword": keyword,
                    "trend": trend,
                    "alert_type": "hot" if trend["change_pct"] > 0 else "cooling"
                })

        return alerts

    def _analyze_topic_insights(self, keywords: List[str]) -> Dict[str, List[str]]:
        """
        分析话题洞察

        Args:
            keywords: 关键词列表

        Returns:
            话题分类
        """
        insights = {
            "continuing": [],  # 持续话题
            "breaking": [],    # 突发事件
            "cooling": []      # 冷却话题
        }

        for keyword in keywords:
            trend = self._get_keyword_trend(keyword)

            if not trend:
                insights["breaking"].append(keyword)
            elif trend["direction"] == "rising" and trend["change_pct"] > 100:
                insights["breaking"].append(keyword)
            elif trend["direction"] == "stable":
                insights["continuing"].append(keyword)
            elif trend["direction"] == "falling":
                insights["cooling"].append(keyword)

        return insights

    def _get_memory_stats(self) -> Dict[str, Any]:
        """
        获取记忆统计

        Returns:
            记忆统计数据
        """
        stats = {
            "total_memories": 0,
            "recent_summaries": 0,
            "last_update": None
        }

        if not self.memory_db.exists():
            return stats

        conn = sqlite3.connect(self.memory_db)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM memories")
            stats["total_memories"] = cursor.fetchone()[0]

            # 最近7天的摘要
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM memories
                WHERE type = 'daily_summary' AND created_at >= ?
            """, (week_ago,))
            stats["recent_summaries"] = cursor.fetchone()[0]

            # 最新更新时间
            cursor.execute("SELECT MAX(created_at) FROM memories")
            last_update = cursor.fetchone()[0]
            if last_update:
                stats["last_update"] = last_update[:10]

        finally:
            conn.close()

        return stats

    def format_enhanced_notification(
        self,
        original_content: str,
        enhancement: Dict[str, Any]
    ) -> str:
        """
        格式化增强后的通知内容

        Args:
            original_content: 原始通知内容
            enhancement: 增强信息

        Returns:
            格式化后的内容
        """
        sections = [original_content, ""]

        # 添加记忆上下文
        news_with_context = enhancement.get("news_with_context", [])
        if news_with_context:
            sections.append("━━━━━━━━━━━━━━━━━━")
            sections.append("🧠 智能洞察")
            sections.append("")

            for item in news_with_context[:5]:  # 只显示前5条
                news = item["news"]
                context = item["context"]

                title = news.get("title", "")
                sections.append(f"• {title}")

                if context["has_memory"]:
                    memory = context["related_memories"][0]
                    days_ago = context["last_mention"]["days_ago"]
                    if days_ago == 0:
                        time_desc = "今天"
                    elif days_ago == 1:
                        time_desc = "昨天"
                    elif days_ago < 7:
                        time_desc = f"{days_ago}天前"
                    elif days_ago < 30:
                        time_desc = f"{days_ago // 7}周前"
                    else:
                        time_desc = f"{days_ago // 30}个月前"

                    sections.append(f"  💡 关联记忆：{time_desc} {memory['title']}")

                if context["trend"] and context["trend"]["change_pct"] != 0:
                    trend = context["trend"]
                    if trend["change_pct"] > 100:
                        sections.append(f"  📈 趋势提醒：热度暴涨 {trend['change_pct']:.0f}%")
                    elif trend["change_pct"] < -50:
                        sections.append(f"  📉 趋势提醒：热度下降 {abs(trend['change_pct']):.0f}%")

                if context["is_new_topic"]:
                    sections.append("  🆕 这是新话题")

                sections.append("")

        # 添加趋势提醒
        alerts = enhancement.get("trend_alerts", [])
        if alerts:
            sections.append("━━━━━━━━━━━━━━━━━━")
            sections.append("🔥 热度异常")
            sections.append("")
            for alert in alerts:
                keyword = alert["keyword"]
                trend = alert["trend"]
                emoji = "📈" if alert["alert_type"] == "hot" else "📉"
                sections.append(f"{emoji} {keyword}: {trend['change_pct']:+.0f}%")
            sections.append("")

        # 添加话题洞察
        insights = enhancement.get("topic_insights", {})
        if any(insights.values()):
            sections.append("━━━━━━━━━━━━━━━━━━")
            sections.append("💡 话题洞察")
            sections.append("")

            if insights.get("continuing"):
                sections.append(f"持续话题：{', '.join(insights['continuing'][:5])}")

            if insights.get("breaking"):
                sections.append(f"突发事件：{', '.join(insights['breaking'][:5])}")

            if insights.get("cooling"):
                sections.append(f"冷却话题：{', '.join(insights['cooling'][:5])}")

            sections.append("")

        # 添加记忆统计
        stats = enhancement.get("memory_stats", {})
        if stats.get("total_memories", 0) > 0:
            sections.append("━━━━━━━━━━━━━━━━━━")
            sections.append("📚 知识库")
            sections.append(f"累积记忆：{stats['total_memories']} 条")
            sections.append(f"本周新增：{stats['recent_summaries']} 条")
            if stats.get("last_update"):
                sections.append(f"最新更新：{stats['last_update']}")

        return "\n".join(sections)
