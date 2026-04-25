"""
记忆生成器测试
"""

import json
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import pytest

from trendradar.memory.generator import MemoryGenerator
from trendradar.memory.models import MemoryType, LinkType, MemoryRepository


@pytest.fixture
def db_path(tmp_path):
    """创建临时数据库"""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))

    # 创建必要的表
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memory_links (
            from_memory_id TEXT NOT NULL,
            to_memory_id TEXT NOT NULL,
            link_type TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (from_memory_id, to_memory_id),
            FOREIGN KEY (from_memory_id) REFERENCES memories (id),
            FOREIGN KEY (to_memory_id) REFERENCES memories (id)
        );

        CREATE TABLE IF NOT EXISTS ai_analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_time TEXT NOT NULL UNIQUE,
            report_mode TEXT NOT NULL,
            news_count INTEGER DEFAULT 0,
            rss_count INTEGER DEFAULT 0,
            matched_keywords TEXT,
            platforms TEXT,
            full_result TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ai_analysis_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            section_type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(analysis_id, section_type),
            FOREIGN KEY (analysis_id) REFERENCES ai_analysis_results (id)
        );

        CREATE TABLE IF NOT EXISTS keyword_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            keyword TEXT NOT NULL,
            count INTEGER NOT NULL,
            platforms TEXT,
            rank INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, keyword)
        );
    """)

    conn.commit()
    conn.close()

    return str(db_file)


@pytest.fixture
def ai_client_config():
    """AI 客户端配置"""
    return {
        "MODEL": "deepseek/deepseek-chat",
        "API_KEY": "test-key",
        "TEMPERATURE": 0.7,
        "MAX_TOKENS": 2000,
    }


@pytest.fixture
def generator(db_path, ai_client_config):
    """创建记忆生成器实例"""
    return MemoryGenerator(db_path, ai_client_config)


class TestMemoryGeneratorInit:
    """测试初始化"""

    def test_init_with_valid_config(self, db_path, ai_client_config):
        """测试使用有效配置初始化"""
        generator = MemoryGenerator(db_path, ai_client_config)

        assert generator.db_path == db_path
        assert generator.repository is not None
        assert generator.ai_client is not None

    def test_init_creates_repository(self, db_path, ai_client_config):
        """测试初始化创建仓库"""
        generator = MemoryGenerator(db_path, ai_client_config)

        # 验证仓库已正确配置
        assert generator.repository.db_path == db_path


class TestGenerateDailySummary:
    """测试生成每日摘要"""

    def test_generate_daily_summary_success(self, generator, db_path):
        """测试成功生成每日摘要"""
        # 准备测试数据
        test_date = datetime(2026, 4, 25)
        date_str = test_date.strftime("%Y-%m-%d")

        # 插入 AI 分析数据
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_analysis_results
            (analysis_time, report_mode, news_count, rss_count, matched_keywords, platforms, full_result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{date_str}T10:00:00",
            "daily",
            50,
            10,
            json.dumps(["AI", "科技", "股市"]),
            json.dumps(["微博", "知乎"]),
            json.dumps({"summary": "测试数据"})
        ))
        analysis_id = cursor.lastrowid

        # 插入板块数据
        cursor.execute("""
            INSERT INTO ai_analysis_sections (analysis_id, section_type, content)
            VALUES (?, ?, ?)
        """, (analysis_id, "core_trends", "核心趋势内容"))

        # 插入关键词统计
        cursor.execute("""
            INSERT INTO keyword_trends (date, keyword, count, platforms, rank)
            VALUES (?, ?, ?, ?, ?)
        """, (date_str, "AI", 30, json.dumps(["微博"]), 1))

        conn.commit()
        conn.close()

        # Mock AI 响应
        mock_ai_response = """
        今日关键趋势：
        1. AI 技术持续发展
        2. 科技股表现强劲
        3. 市场情绪积极
        """

        with patch.object(generator, '_call_ai', return_value=mock_ai_response):
            memory = generator.generate_daily_summary(test_date)

        # 验证结果
        assert memory is not None
        assert memory.type == MemoryType.DAILY_SUMMARY
        assert memory.title.startswith("每日摘要")
        assert date_str in memory.title
        assert "AI" in memory.content or "科技" in memory.content
        assert memory.metadata.get("date") == date_str
        assert memory.metadata.get("news_count") == 50
        assert memory.metadata.get("rss_count") == 10

        # 验证已保存到数据库
        saved_memory = generator.repository.get_by_id(memory.id)
        assert saved_memory is not None
        assert saved_memory.id == memory.id

    def test_generate_daily_summary_no_data(self, generator):
        """测试没有数据时返回 None"""
        test_date = datetime(2026, 4, 25)

        memory = generator.generate_daily_summary(test_date)

        assert memory is None

    def test_generate_daily_summary_with_ai_error(self, generator, db_path):
        """测试 AI 调用失败时抛出异常"""
        test_date = datetime(2026, 4, 25)
        date_str = test_date.strftime("%Y-%m-%d")

        # 插入测试数据
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_analysis_results
            (analysis_time, report_mode, news_count, rss_count, matched_keywords, platforms, full_result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{date_str}T10:00:00",
            "daily",
            50,
            10,
            json.dumps(["AI"]),
            json.dumps(["微博"]),
            json.dumps({})
        ))
        conn.commit()
        conn.close()

        # Mock AI 调用失败
        with patch.object(generator, '_call_ai', side_effect=Exception("AI API Error")):
            with pytest.raises(Exception, match="AI API Error"):
                generator.generate_daily_summary(test_date)


class TestGenerateWeeklyDigest:
    """测试生成每周摘要"""

    def test_generate_weekly_digest_success(self, generator, db_path):
        """测试成功生成每周摘要"""
        # 准备测试数据 - 创建 7 天的每日摘要
        start_date = datetime(2026, 4, 19)
        end_date = datetime(2026, 4, 25)

        daily_memory_ids = []
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            memory_id = f"daily-{current_date.strftime('%Y%m%d')}"
            daily_memory_ids.append(memory_id)

            # 创建每日摘要记忆
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memories
                (id, type, title, description, content, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id,
                MemoryType.DAILY_SUMMARY,
                f"每日摘要 - {current_date.strftime('%Y-%m-%d')}",
                "描述",
                f"第{i+1}天的内容",
                json.dumps({"date": current_date.strftime("%Y-%m-%d")}),
                current_date.isoformat(),
                current_date.isoformat()
            ))
            conn.commit()
            conn.close()

        # Mock AI 响应
        mock_ai_response = """
        本周关键趋势：
        1. AI 技术周持续升温
        2. 科技板块表现突出
        3. 市场情绪整体向好
        """

        with patch.object(generator, '_call_ai', return_value=mock_ai_response):
            memory = generator.generate_weekly_digest(start_date, end_date)

        # 验证结果
        assert memory is not None
        assert memory.type == MemoryType.WEEKLY_DIGEST
        assert memory.title.startswith("每周摘要")
        assert "AI" in memory.content or "科技" in memory.content
        assert memory.metadata.get("start_date") == start_date.strftime("%Y-%m-%d")
        assert memory.metadata.get("end_date") == end_date.strftime("%Y-%m-%d")
        assert memory.metadata.get("daily_count") == 7

        # 验证已保存到数据库
        saved_memory = generator.repository.get_by_id(memory.id)
        assert saved_memory is not None

        # 验证创建了链接
        links = generator.repository.get_links_from(memory.id)
        assert len(links) == 7

        # 验证所有链接都是 derives_from 类型
        for link in links:
            assert link.link_type == LinkType.DERIVES_FROM
            assert link.to_memory_id in daily_memory_ids

    def test_generate_weekly_digest_no_daily_memories(self, generator):
        """测试没有每日摘要时返回 None"""
        start_date = datetime(2026, 4, 19)
        end_date = datetime(2026, 4, 25)

        memory = generator.generate_weekly_digest(start_date, end_date)

        assert memory is None

    def test_generate_weekly_digest_with_partial_data(self, generator, db_path):
        """测试只有部分每日摘要时也能生成"""
        start_date = datetime(2026, 4, 19)
        end_date = datetime(2026, 4, 25)

        # 只创建 3 天的数据
        for i in range(3):
            current_date = start_date + timedelta(days=i)
            memory_id = f"daily-{current_date.strftime('%Y%m%d')}"

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memories
                (id, type, title, description, content, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id,
                MemoryType.DAILY_SUMMARY,
                f"每日摘要 - {current_date.strftime('%Y-%m-%d')}",
                "描述",
                f"第{i+1}天的内容",
                json.dumps({"date": current_date.strftime("%Y-%m-%d")}),
                current_date.isoformat(),
                current_date.isoformat()
            ))
            conn.commit()
            conn.close()

        mock_ai_response = "本周部分数据摘要"

        with patch.object(generator, '_call_ai', return_value=mock_ai_response):
            memory = generator.generate_weekly_digest(start_date, end_date)

        assert memory is not None
        assert memory.metadata.get("daily_count") == 3


class TestPrivateMethods:
    """测试私有方法"""

    def test_call_ai(self, generator):
        """测试 AI 调用"""
        test_prompt = "测试提示词"
        expected_response = "AI 响应内容"

        # Mock AIClient.chat 方法
        with patch.object(generator.ai_client, 'chat', return_value=expected_response) as mock_chat:
            response = generator._call_ai(test_prompt)

        assert response == expected_response
        mock_chat.assert_called_once()

        # 验证调用参数
        call_args = mock_chat.call_args
        messages = call_args[0][0]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == test_prompt

    def test_gather_daily_data(self, generator, db_path):
        """测试收集每日数据"""
        test_date = datetime(2026, 4, 25)
        date_str = test_date.strftime("%Y-%m-%d")

        # 插入 AI 分析数据
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_analysis_results
            (analysis_time, report_mode, news_count, rss_count, matched_keywords, platforms, full_result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{date_str}T10:00:00",
            "daily",
            50,
            10,
            json.dumps(["AI", "科技"]),
            json.dumps(["微博", "知乎"]),
            json.dumps({"summary": "测试"})
        ))
        analysis_id = cursor.lastrowid

        # 插入板块数据
        cursor.execute("""
            INSERT INTO ai_analysis_sections (analysis_id, section_type, content)
            VALUES (?, ?, ?), (?, ?, ?)
        """, (
            analysis_id, "core_trends", "核心趋势",
            analysis_id, "signals", "信号内容"
        ))

        # 插入关键词统计
        cursor.execute("""
            INSERT INTO keyword_trends (date, keyword, count, platforms, rank)
            VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?)
        """, (
            date_str, "AI", 30, json.dumps(["微博"]), 1,
            date_str, "科技", 20, json.dumps(["知乎"]), 2
        ))

        conn.commit()
        conn.close()

        # 调用方法
        data = generator._gather_daily_data(test_date)

        # 验证结果
        assert data is not None
        assert data["date"] == date_str
        assert data["news_count"] == 50
        assert data["rss_count"] == 10
        assert "AI" in data["matched_keywords"]
        assert "科技" in data["matched_keywords"]
        assert len(data["ai_sections"]) == 2
        assert len(data["top_keywords"]) == 2
        assert data["top_keywords"][0]["keyword"] == "AI"
        assert data["top_keywords"][0]["count"] == 30

    def test_gather_daily_data_no_data(self, generator):
        """测试没有数据时返回 None"""
        test_date = datetime(2026, 4, 25)

        data = generator._gather_daily_data(test_date)

        assert data is None

    def test_create_memory_id(self, generator):
        """测试生成记忆 ID"""
        test_date = datetime(2026, 4, 25, 14, 30, 0)

        memory_id = generator._create_memory_id(MemoryType.DAILY_SUMMARY, test_date)

        assert memory_id.startswith("daily_summary-")
        assert "20260425" in memory_id
