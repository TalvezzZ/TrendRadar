"""
AI 分析结果存储模块

提供 AI 分析结果的存储和检索功能。
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional


class AIAnalysisStorage:
    """AI 分析结果存储管理器"""

    def __init__(self, db_path: str):
        """
        初始化 AI 分析存储

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path

    def save_analysis_result(self, analysis_data: Dict[str, Any]) -> int:
        """
        保存分析结果

        Args:
            analysis_data: 分析数据字典，包含：
                - analysis_time: 分析时间（ISO 8601 格式）
                - report_mode: 报告模式
                - news_count: 新闻数量
                - rss_count: RSS 数量
                - matched_keywords: 匹配的关键词列表
                - platforms: 平台列表
                - full_result: 完整结果（JSON 对象）

        Returns:
            分析结果的 ID

        Raises:
            sqlite3.IntegrityError: 如果 analysis_time 已存在
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO ai_analysis_results
                (analysis_time, report_mode, news_count, rss_count, matched_keywords, platforms, full_result)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_data['analysis_time'],
                    analysis_data['report_mode'],
                    analysis_data.get('news_count', 0),
                    analysis_data.get('rss_count', 0),
                    json.dumps(analysis_data.get('matched_keywords', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('platforms', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('full_result', {}), ensure_ascii=False)
                )
            )
            conn.commit()
            analysis_id = cursor.lastrowid
            return analysis_id
        finally:
            conn.close()

    def save_analysis_sections(self, analysis_id: int, sections_data: Dict[str, str]) -> List[int]:
        """
        保存分析板块内容

        Args:
            analysis_id: 分析结果 ID
            sections_data: 板块字典，key 为板块类型，value 为内容
                支持的板块类型：
                - core_trends: 核心趋势
                - sentiment_controversy: 情感与争议
                - signals: 信号
                - rss_insights: RSS 洞察
                - outlook_strategy: 展望与策略
                - standalone_summaries: 独立摘要

        Returns:
            插入的板块记录的 ID 列表

        Raises:
            sqlite3.IntegrityError: 如果板块类型无效或已存在
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        section_ids = []

        try:
            for section_type, content in sections_data.items():
                cursor.execute(
                    """
                    INSERT INTO ai_analysis_sections
                    (analysis_id, section_type, content)
                    VALUES (?, ?, ?)
                    """,
                    (analysis_id, section_type, content)
                )
                section_ids.append(cursor.lastrowid)
            conn.commit()
            return section_ids
        finally:
            conn.close()

    def get_analysis_by_id(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """
        获取指定 ID 的分析结果

        Args:
            analysis_id: 分析结果 ID

        Returns:
            分析结果字典，包含所有字段；如果不存在则返回 None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, analysis_time, report_mode, news_count, rss_count,
                       matched_keywords, platforms, full_result, created_at
                FROM ai_analysis_results
                WHERE id = ?
                """,
                (analysis_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            result = dict(row)
            # 解析 JSON 字段
            result['matched_keywords'] = json.loads(result['matched_keywords'])
            result['platforms'] = json.loads(result['platforms'])
            result['full_result'] = json.loads(result['full_result'])

            return result
        finally:
            conn.close()

    def get_analysis_by_time_range(self, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        """
        获取指定时间范围内的分析结果

        Args:
            start_time: 起始时间（ISO 8601 格式，包含）
            end_time: 结束时间（ISO 8601 格式，包含）

        Returns:
            分析结果列表（按时间升序）
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, analysis_time, report_mode, news_count, rss_count,
                       matched_keywords, platforms, full_result, created_at
                FROM ai_analysis_results
                WHERE analysis_time >= ? AND analysis_time <= ?
                ORDER BY analysis_time ASC
                """,
                (start_time, end_time)
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                # 解析 JSON 字段
                result['matched_keywords'] = json.loads(result['matched_keywords'])
                result['platforms'] = json.loads(result['platforms'])
                result['full_result'] = json.loads(result['full_result'])
                results.append(result)

            return results
        finally:
            conn.close()

    def get_sections_by_analysis_id(self, analysis_id: int) -> Dict[str, str]:
        """
        获取指定分析的所有板块内容

        Args:
            analysis_id: 分析结果 ID

        Returns:
            板块字典，key 为板块类型，value 为内容
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT section_type, content
                FROM ai_analysis_sections
                WHERE analysis_id = ?
                """,
                (analysis_id,)
            )
            rows = cursor.fetchall()

            sections = {}
            for row in rows:
                row_dict = dict(row)
                sections[row_dict['section_type']] = row_dict['content']

            return sections
        finally:
            conn.close()

