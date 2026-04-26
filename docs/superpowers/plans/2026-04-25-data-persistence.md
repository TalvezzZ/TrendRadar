# TrendRadar 数据持久化与记忆系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 TrendRadar 添加完整的数据持久化和分层记忆系统，支持 AI 分析结果存储、关键词趋势追踪、自动化日/周摘要生成，以及为未来 Agent 分析提供查询接口。

**Architecture:** 
- 日期数据库（`YYYY-MM-DD.db`）存储原始新闻和 AI 分析详情
- 记忆数据库（`memory.db`）存储提炼后的摘要、统计和洞察
- 分层记忆架构：原始数据 → 日摘要 → 周提炼 → 主题洞察
- TDD 开发，每个功能先写测试

**Tech Stack:** 
- SQLite 3（数据存储）
- Python dataclasses（数据模型）
- Claude API（记忆生成）
- pytest（测试框架）

---

## 文件结构规划

### 新增文件

```
trendradar/
├── persistence/                    # 持久化模块
│   ├── __init__.py
│   ├── schema.py                  # 数据库 schema 定义
│   ├── ai_storage.py              # AI 分析结果存储
│   └── keyword_stats.py           # 关键词统计
│
├── memory/                         # 记忆引擎模块
│   ├── __init__.py
│   ├── models.py                  # 记忆数据模型
│   ├── generator.py               # 摘要生成器
│   ├── query.py                   # 查询引擎
│   └── scheduler.py               # 定时任务调度
│
└── storage/
    └── memory_schema.sql          # memory.db schema

tests/
├── persistence/
│   ├── test_ai_storage.py
│   └── test_keyword_stats.py
│
└── memory/
    ├── test_models.py
    ├── test_generator.py
    └── test_query.py
```

### 修改文件

```
trendradar/
├── __main__.py                     # 集成存储调用
├── storage/
│   ├── manager.py                  # 扩展 StorageManager
│   └── schema.sql                  # 修改现有 schema
```

---

## Phase 1: 核心存储功能（预计 2 天）

### Task 1: 创建数据库 Schema

**Files:**
- Create: `trendradar/storage/ai_analysis_schema.sql`
- Modify: `trendradar/storage/schema.sql`

- [ ] **Step 1: 创建 AI 分析表 schema**

Create file `trendradar/storage/ai_analysis_schema.sql`:

```sql
-- AI 分析结果表
CREATE TABLE IF NOT EXISTS ai_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_time TEXT NOT NULL UNIQUE,    -- ISO 8601 格式
    report_mode TEXT NOT NULL,              -- 报告模式
    news_count INTEGER DEFAULT 0,
    rss_count INTEGER DEFAULT 0,
    matched_keywords TEXT DEFAULT '[]',     -- JSON array
    platforms TEXT DEFAULT '[]',            -- JSON array
    full_result TEXT NOT NULL,              -- JSON 对象
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_analysis_time 
    ON ai_analysis_results(analysis_time);

-- AI 分析板块表
CREATE TABLE IF NOT EXISTS ai_analysis_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    section_type TEXT NOT NULL CHECK(section_type IN (
        'core_trends',
        'sentiment_controversy',
        'signals',
        'rss_insights',
        'outlook_strategy',
        'standalone_summaries'
    )),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES ai_analysis_results(id),
    UNIQUE(analysis_id, section_type)
);

CREATE INDEX IF NOT EXISTS idx_ai_sections_type 
    ON ai_analysis_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_ai_sections_analysis 
    ON ai_analysis_sections(analysis_id);
```

- [ ] **Step 2: 修改 news_items 表添加 matched_keywords 字段**

在 `trendradar/storage/schema.sql` 的 `news_items` 表创建语句中添加字段：

```sql
-- 在 news_items 表定义中添加（在 updated_at 字段后）
    matched_keywords TEXT DEFAULT '[]',     -- JSON array of matched keywords
```

- [ ] **Step 3: 创建 memory.db schema**

Create file `trendradar/storage/memory_schema.sql`:

```sql
-- ============================================
-- 记忆表（统一存储所有类型的记忆）
-- ============================================
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK(type IN (
        'daily_summary',
        'weekly_digest',
        'topic_insight',
        'pattern',
        'signal'
    )),
    title TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',              -- JSON
    created_at TEXT NOT NULL,                -- ISO 8601
    updated_at TEXT NOT NULL                 -- ISO 8601
);

CREATE INDEX IF NOT EXISTS idx_memories_type 
    ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_created 
    ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_memories_type_date 
    ON memories(type, created_at);

-- ============================================
-- 记忆关联表
-- ============================================
CREATE TABLE IF NOT EXISTS memory_links (
    from_memory_id TEXT NOT NULL,
    to_memory_id TEXT NOT NULL,
    link_type TEXT NOT NULL CHECK(link_type IN (
        'supports',
        'contradicts',
        'extends',
        'derives_from'
    )),
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (from_memory_id, to_memory_id),
    FOREIGN KEY (from_memory_id) REFERENCES memories(id),
    FOREIGN KEY (to_memory_id) REFERENCES memories(id)
);

CREATE INDEX IF NOT EXISTS idx_memory_links_from 
    ON memory_links(from_memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_links_to 
    ON memory_links(to_memory_id);

-- ============================================
-- 记忆验证表
-- ============================================
CREATE TABLE IF NOT EXISTS memory_validations (
    memory_id TEXT PRIMARY KEY,
    last_validated TEXT NOT NULL,
    is_valid INTEGER NOT NULL,
    validation_notes TEXT,
    FOREIGN KEY (memory_id) REFERENCES memories(id)
);

-- ============================================
-- 关键词趋势表
-- ============================================
CREATE TABLE IF NOT EXISTS keyword_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    keyword TEXT NOT NULL,
    count INTEGER NOT NULL,
    platforms TEXT DEFAULT '[]',             -- JSON array
    rank INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(date, keyword)
);

CREATE INDEX IF NOT EXISTS idx_keyword_trends_date 
    ON keyword_trends(date);
CREATE INDEX IF NOT EXISTS idx_keyword_trends_keyword 
    ON keyword_trends(keyword);
CREATE INDEX IF NOT EXISTS idx_keyword_trends_keyword_date 
    ON keyword_trends(keyword, date);
```

- [ ] **Step 4: 提交 schema 文件**

```bash
git add trendradar/storage/ai_analysis_schema.sql
git add trendradar/storage/memory_schema.sql
git add trendradar/storage/schema.sql
git commit -m "feat(schema): add AI analysis and memory database schemas"
```

---

### Task 2: 实现 AI 分析存储模块

**Files:**
- Create: `trendradar/persistence/__init__.py`
- Create: `trendradar/persistence/schema.py`
- Create: `trendradar/persistence/ai_storage.py`
- Create: `tests/persistence/test_ai_storage.py`

- [ ] **Step 1: 创建持久化模块初始化文件**

Create file `trendradar/persistence/__init__.py`:

```python
# coding=utf-8
"""
持久化模块 - AI 分析结果和关键词统计的持久化存储
"""

from trendradar.persistence.ai_storage import AIAnalysisStorage
from trendradar.persistence.keyword_stats import KeywordStatsManager

__all__ = [
    'AIAnalysisStorage',
    'KeywordStatsManager',
]
```

- [ ] **Step 2: 创建 schema 加载器**

Create file `trendradar/persistence/schema.py`:

```python
# coding=utf-8
"""
数据库 Schema 管理
"""

import sqlite3
from pathlib import Path
from typing import Optional


def load_schema_file(schema_path: str) -> str:
    """加载 SQL schema 文件"""
    path = Path(schema_path)
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    return path.read_text(encoding='utf-8')


def initialize_ai_analysis_tables(conn: sqlite3.Connection) -> None:
    """初始化 AI 分析相关表"""
    schema_dir = Path(__file__).parent.parent / 'storage'
    schema_sql = load_schema_file(str(schema_dir / 'ai_analysis_schema.sql'))
    conn.executescript(schema_sql)
    conn.commit()


def initialize_memory_db(db_path: str) -> sqlite3.Connection:
    """初始化 memory.db 数据库"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    schema_dir = Path(__file__).parent.parent / 'storage'
    schema_sql = load_schema_file(str(schema_dir / 'memory_schema.sql'))
    conn.executescript(schema_sql)
    conn.commit()
    
    return conn


def ensure_matched_keywords_column(conn: sqlite3.Connection) -> None:
    """确保 news_items 表有 matched_keywords 字段"""
    cursor = conn.execute("PRAGMA table_info(news_items)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'matched_keywords' not in columns:
        conn.execute("""
            ALTER TABLE news_items 
            ADD COLUMN matched_keywords TEXT DEFAULT '[]'
        """)
        conn.commit()
```

- [ ] **Step 3: 编写 AI 存储测试（先写测试）**

Create file `tests/persistence/test_ai_storage.py`:

```python
# coding=utf-8
import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from trendradar.persistence.schema import (
    initialize_ai_analysis_tables,
    ensure_matched_keywords_column
)
from trendradar.persistence.ai_storage import AIAnalysisStorage


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # 创建基础表结构（简化版）
    conn.execute("""
        CREATE TABLE news_items (
            id INTEGER PRIMARY KEY,
            title TEXT,
            platform_id TEXT,
            rank INTEGER
        )
    """)
    
    # 初始化 AI 分析表
    initialize_ai_analysis_tables(conn)
    ensure_matched_keywords_column(conn)
    
    yield conn
    
    conn.close()
    Path(db_path).unlink()


def test_save_ai_analysis_result(temp_db):
    """测试保存 AI 分析结果"""
    storage = AIAnalysisStorage(temp_db)
    
    analysis_data = {
        'analysis_time': '2026-04-25T12:00:00',
        'report_mode': '当前榜单',
        'news_count': 71,
        'rss_count': 0,
        'matched_keywords': ['DeepSeek', '华为', 'AI'],
        'platforms': ['微博', '知乎', 'B站'],
        'full_result': {
            'core_trends': '核心热点内容...',
            'sentiment_controversy': '舆论风向...',
            'signals': '异动信号...',
            'rss_insights': 'RSS洞察...',
            'outlook_strategy': '策略建议...',
            'standalone_summaries': {}
        }
    }
    
    result_id = storage.save_analysis_result(analysis_data)
    assert result_id > 0
    
    # 验证保存的数据
    cursor = temp_db.execute(
        "SELECT * FROM ai_analysis_results WHERE id = ?",
        (result_id,)
    )
    row = cursor.fetchone()
    
    assert row is not None
    assert row['analysis_time'] == '2026-04-25T12:00:00'
    assert row['news_count'] == 71
    assert json.loads(row['matched_keywords']) == ['DeepSeek', '华为', 'AI']


def test_save_analysis_sections(temp_db):
    """测试保存 AI 分析板块"""
    storage = AIAnalysisStorage(temp_db)
    
    # 先保存完整结果
    analysis_data = {
        'analysis_time': '2026-04-25T12:00:00',
        'report_mode': '当前榜单',
        'news_count': 71,
        'rss_count': 0,
        'matched_keywords': [],
        'platforms': [],
        'full_result': {
            'core_trends': '核心热点',
            'sentiment_controversy': '舆论风向'
        }
    }
    result_id = storage.save_analysis_result(analysis_data)
    
    # 保存板块
    sections = storage.save_analysis_sections(
        result_id,
        analysis_data['full_result']
    )
    
    assert len(sections) == 2
    
    # 验证板块保存
    cursor = temp_db.execute(
        "SELECT * FROM ai_analysis_sections WHERE analysis_id = ?",
        (result_id,)
    )
    rows = cursor.fetchall()
    assert len(rows) == 2


def test_get_analysis_by_time_range(temp_db):
    """测试按时间范围查询分析结果"""
    storage = AIAnalysisStorage(temp_db)
    
    # 保存多条记录
    for i in range(3):
        analysis_data = {
            'analysis_time': f'2026-04-{23+i}T12:00:00',
            'report_mode': '当前榜单',
            'news_count': 70 + i,
            'rss_count': 0,
            'matched_keywords': [],
            'platforms': [],
            'full_result': {}
        }
        storage.save_analysis_result(analysis_data)
    
    # 查询范围
    results = storage.get_analysis_by_time_range(
        start='2026-04-23T00:00:00',
        end='2026-04-24T23:59:59'
    )
    
    assert len(results) == 2
```

- [ ] **Step 4: 运行测试验证失败**

```bash
pytest tests/persistence/test_ai_storage.py -v
```

Expected output: FAIL - `AIAnalysisStorage` not defined

- [ ] **Step 5: 实现 AIAnalysisStorage 类**

Create file `trendradar/persistence/ai_storage.py`:

```python
# coding=utf-8
"""
AI 分析结果存储
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any


class AIAnalysisStorage:
    """AI 分析结果存储管理器"""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
    
    def save_analysis_result(self, analysis_data: Dict[str, Any]) -> int:
        """
        保存 AI 分析完整结果
        
        Args:
            analysis_data: 分析数据，包含：
                - analysis_time: 分析时间（ISO 8601）
                - report_mode: 报告模式
                - news_count: 新闻数量
                - rss_count: RSS 数量
                - matched_keywords: 匹配的关键词列表
                - platforms: 平台列表
                - full_result: 完整分析结果（dict）
        
        Returns:
            插入的记录 ID
        """
        cursor = self.conn.execute("""
            INSERT INTO ai_analysis_results (
                analysis_time,
                report_mode,
                news_count,
                rss_count,
                matched_keywords,
                platforms,
                full_result
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis_data['analysis_time'],
            analysis_data['report_mode'],
            analysis_data['news_count'],
            analysis_data['rss_count'],
            json.dumps(analysis_data['matched_keywords'], ensure_ascii=False),
            json.dumps(analysis_data['platforms'], ensure_ascii=False),
            json.dumps(analysis_data['full_result'], ensure_ascii=False)
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def save_analysis_sections(
        self,
        analysis_id: int,
        sections_data: Dict[str, str]
    ) -> List[int]:
        """
        保存 AI 分析板块
        
        Args:
            analysis_id: AI 分析结果 ID
            sections_data: 板块数据，key 为板块类型，value 为内容
        
        Returns:
            插入的记录 ID 列表
        """
        section_ids = []
        
        for section_type, content in sections_data.items():
            if section_type and content:  # 跳过空内容
                cursor = self.conn.execute("""
                    INSERT INTO ai_analysis_sections (
                        analysis_id,
                        section_type,
                        content
                    ) VALUES (?, ?, ?)
                """, (analysis_id, section_type, content))
                
                section_ids.append(cursor.lastrowid)
        
        self.conn.commit()
        return section_ids
    
    def get_analysis_by_time_range(
        self,
        start: str,
        end: str
    ) -> List[Dict[str, Any]]:
        """
        按时间范围查询 AI 分析结果
        
        Args:
            start: 开始时间（ISO 8601）
            end: 结束时间（ISO 8601）
        
        Returns:
            分析结果列表
        """
        cursor = self.conn.execute("""
            SELECT * FROM ai_analysis_results
            WHERE analysis_time BETWEEN ? AND ?
            ORDER BY analysis_time ASC
        """, (start, end))
        
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
    
    def get_analysis_by_id(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取 AI 分析结果"""
        cursor = self.conn.execute("""
            SELECT * FROM ai_analysis_results WHERE id = ?
        """, (analysis_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        result = dict(row)
        result['matched_keywords'] = json.loads(result['matched_keywords'])
        result['platforms'] = json.loads(result['platforms'])
        result['full_result'] = json.loads(result['full_result'])
        
        return result
    
    def get_sections_by_analysis_id(
        self,
        analysis_id: int
    ) -> List[Dict[str, Any]]:
        """获取某次分析的所有板块"""
        cursor = self.conn.execute("""
            SELECT * FROM ai_analysis_sections
            WHERE analysis_id = ?
            ORDER BY section_type
        """, (analysis_id,))
        
        return [dict(row) for row in cursor.fetchall()]
```

- [ ] **Step 6: 运行测试验证通过**

```bash
pytest tests/persistence/test_ai_storage.py -v
```

Expected output: All tests PASS

- [ ] **Step 7: 提交 AI 存储功能**

```bash
git add trendradar/persistence/
git add tests/persistence/
git commit -m "feat(persistence): implement AI analysis storage with tests"
```

---

### Task 3: 实现关键词统计模块

**Files:**
- Create: `trendradar/persistence/keyword_stats.py`
- Create: `tests/persistence/test_keyword_stats.py`

- [ ] **Step 1: 编写关键词统计测试**

Create file `tests/persistence/test_keyword_stats.py`:

```python
# coding=utf-8
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from trendradar.persistence.schema import initialize_memory_db
from trendradar.persistence.keyword_stats import KeywordStatsManager


@pytest.fixture
def memory_db():
    """创建临时 memory.db"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    conn = initialize_memory_db(db_path)
    
    yield conn
    
    conn.close()
    Path(db_path).unlink()


def test_update_keyword_stats(memory_db):
    """测试更新关键词统计"""
    manager = KeywordStatsManager(memory_db)
    
    keyword_data = {
        'date': '2026-04-25',
        'keyword': 'DeepSeek',
        'count': 67,
        'platforms': ['微博', '知乎', 'B站'],
        'rank': 1
    }
    
    manager.update_keyword_stat(keyword_data)
    
    # 验证保存
    cursor = memory_db.execute("""
        SELECT * FROM keyword_trends 
        WHERE date = ? AND keyword = ?
    """, ('2026-04-25', 'DeepSeek'))
    
    row = cursor.fetchone()
    assert row is not None
    assert row['count'] == 67
    assert row['rank'] == 1
    assert json.loads(row['platforms']) == ['微博', '知乎', 'B站']


def test_batch_update_keywords(memory_db):
    """测试批量更新关键词"""
    manager = KeywordStatsManager(memory_db)
    
    keywords_data = [
        {
            'date': '2026-04-25',
            'keyword': 'DeepSeek',
            'count': 67,
            'platforms': ['微博', '知乎'],
            'rank': 1
        },
        {
            'date': '2026-04-25',
            'keyword': '华为',
            'count': 32,
            'platforms': ['微博'],
            'rank': 2
        }
    ]
    
    manager.batch_update_keywords(keywords_data)
    
    # 验证
    cursor = memory_db.execute("""
        SELECT COUNT(*) as count FROM keyword_trends 
        WHERE date = '2026-04-25'
    """)
    assert cursor.fetchone()['count'] == 2


def test_get_keyword_trend(memory_db):
    """测试获取关键词趋势"""
    manager = KeywordStatsManager(memory_db)
    
    # 插入多天数据
    for i in range(3):
        keyword_data = {
            'date': f'2026-04-{23+i}',
            'keyword': 'DeepSeek',
            'count': 10 + i * 20,
            'platforms': ['微博'],
            'rank': 1
        }
        manager.update_keyword_stat(keyword_data)
    
    # 获取趋势
    trend = manager.get_keyword_trend('DeepSeek', days=3)
    
    assert len(trend) == 3
    assert trend[0]['count'] == 10
    assert trend[1]['count'] == 30
    assert trend[2]['count'] == 50


def test_get_top_keywords_by_date(memory_db):
    """测试获取某日 Top 关键词"""
    manager = KeywordStatsManager(memory_db)
    
    keywords_data = [
        {'date': '2026-04-25', 'keyword': 'DeepSeek', 'count': 67, 'platforms': [], 'rank': 1},
        {'date': '2026-04-25', 'keyword': '华为', 'count': 32, 'platforms': [], 'rank': 2},
        {'date': '2026-04-25', 'keyword': 'AI', 'count': 28, 'platforms': [], 'rank': 3},
    ]
    
    manager.batch_update_keywords(keywords_data)
    
    # 获取 Top 2
    top_keywords = manager.get_top_keywords_by_date('2026-04-25', limit=2)
    
    assert len(top_keywords) == 2
    assert top_keywords[0]['keyword'] == 'DeepSeek'
    assert top_keywords[1]['keyword'] == '华为'
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/persistence/test_keyword_stats.py -v
```

Expected output: FAIL - `KeywordStatsManager` not defined

- [ ] **Step 3: 实现 KeywordStatsManager 类**

Create file `trendradar/persistence/keyword_stats.py`:

```python
# coding=utf-8
"""
关键词统计管理
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any


class KeywordStatsManager:
    """关键词统计管理器"""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
    
    def update_keyword_stat(self, keyword_data: Dict[str, Any]) -> None:
        """
        更新关键词统计（插入或更新）
        
        Args:
            keyword_data: 关键词数据，包含：
                - date: 日期（YYYY-MM-DD）
                - keyword: 关键词
                - count: 出现次数
                - platforms: 平台列表
                - rank: 排名（可选）
        """
        platforms_json = json.dumps(
            keyword_data.get('platforms', []),
            ensure_ascii=False
        )
        
        self.conn.execute("""
            INSERT INTO keyword_trends (
                date, keyword, count, platforms, rank
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date, keyword) DO UPDATE SET
                count = excluded.count,
                platforms = excluded.platforms,
                rank = excluded.rank
        """, (
            keyword_data['date'],
            keyword_data['keyword'],
            keyword_data['count'],
            platforms_json,
            keyword_data.get('rank')
        ))
        
        self.conn.commit()
    
    def batch_update_keywords(self, keywords_data: List[Dict[str, Any]]) -> None:
        """
        批量更新关键词统计
        
        Args:
            keywords_data: 关键词数据列表
        """
        for keyword_data in keywords_data:
            self.update_keyword_stat(keyword_data)
    
    def get_keyword_trend(
        self,
        keyword: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取关键词的热度趋势
        
        Args:
            keyword: 关键词
            days: 过去多少天
        
        Returns:
            趋势数据列表，按日期排序
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        cursor = self.conn.execute("""
            SELECT * FROM keyword_trends
            WHERE keyword = ? 
              AND date BETWEEN ? AND ?
            ORDER BY date ASC
        """, (keyword, str(start_date), str(end_date)))
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            result = dict(row)
            result['platforms'] = json.loads(result['platforms'])
            results.append(result)
        
        return results
    
    def get_top_keywords_by_date(
        self,
        date: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取某日 Top 关键词
        
        Args:
            date: 日期（YYYY-MM-DD）
            limit: 返回数量
        
        Returns:
            Top 关键词列表，按 count 降序
        """
        cursor = self.conn.execute("""
            SELECT * FROM keyword_trends
            WHERE date = ?
            ORDER BY count DESC
            LIMIT ?
        """, (date, limit))
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            result = dict(row)
            result['platforms'] = json.loads(result['platforms'])
            results.append(result)
        
        return results
    
    def get_keywords_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取日期范围内的所有关键词统计
        
        Args:
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
        
        Returns:
            关键词统计列表
        """
        cursor = self.conn.execute("""
            SELECT * FROM keyword_trends
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC, count DESC
        """, (start_date, end_date))
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            result = dict(row)
            result['platforms'] = json.loads(result['platforms'])
            results.append(result)
        
        return results
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/persistence/test_keyword_stats.py -v
```

Expected output: All tests PASS

- [ ] **Step 5: 提交关键词统计功能**

```bash
git add trendradar/persistence/keyword_stats.py
git add tests/persistence/test_keyword_stats.py
git commit -m "feat(persistence): implement keyword statistics manager with tests"
```

---

### Task 4: 集成到主流程

**Files:**
- Modify: `trendradar/__main__.py`
- Modify: `trendradar/storage/manager.py`

- [ ] **Step 1: 扩展 StorageManager 类**

在 `trendradar/storage/manager.py` 中添加方法：

```python
# 在 StorageManager 类中添加以下方法

def get_memory_db_path(self) -> str:
    """获取 memory.db 路径"""
    if self.backend_type == 'local':
        output_dir = Path(self.local_backend.output_dir)
        return str(output_dir / 'memory.db')
    else:
        # 远程模式暂不支持 memory.db
        raise NotImplementedError("Memory DB not supported in remote mode yet")

def ensure_memory_db(self) -> sqlite3.Connection:
    """确保 memory.db 存在并返回连接"""
    from trendradar.persistence.schema import initialize_memory_db
    
    memory_db_path = self.get_memory_db_path()
    
    # 如果文件不存在，initialize_memory_db 会创建并初始化
    conn = initialize_memory_db(memory_db_path)
    
    return conn

def get_today_db_connection(self) -> sqlite3.Connection:
    """获取今天的数据库连接"""
    if self.backend_type == 'local':
        today = datetime.now(DEFAULT_TIMEZONE).strftime('%Y-%m-%d')
        db_path = self.local_backend._get_db_path(today)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # 确保有 AI 分析表
        from trendradar.persistence.schema import (
            initialize_ai_analysis_tables,
            ensure_matched_keywords_column
        )
        initialize_ai_analysis_tables(conn)
        ensure_matched_keywords_column(conn)
        
        return conn
    else:
        raise NotImplementedError("Only local backend supported for now")
```

- [ ] **Step 2: 在主流程中集成存储调用**

在 `trendradar/__main__.py` 中，找到 AI 分析完成后的代码（搜索 `AIAnalyzer`），添加存储逻辑：

```python
# 在 AI 分析完成后（大约在 main() 函数中）

# 假设已有变量：
# - storage_manager: StorageManager 实例
# - analysis_result: AIAnalysisResult 对象
# - matched_keywords: 匹配的关键词列表
# - platforms: 平台列表

from trendradar.persistence.ai_storage import AIAnalysisStorage
from trendradar.persistence.keyword_stats import KeywordStatsManager
from datetime import datetime

# 1. 保存 AI 分析结果到日期数据库
try:
    db_conn = storage_manager.get_today_db_connection()
    ai_storage = AIAnalysisStorage(db_conn)
    
    analysis_data = {
        'analysis_time': datetime.now().isoformat(),
        'report_mode': '当前榜单',  # 或从配置获取
        'news_count': len(all_news),  # 假设有这个变量
        'rss_count': 0,  # 如果有 RSS 数据，填入实际值
        'matched_keywords': matched_keywords,
        'platforms': platforms,
        'full_result': {
            'core_trends': analysis_result.core_trends,
            'sentiment_controversy': analysis_result.sentiment_controversy,
            'signals': analysis_result.signals,
            'rss_insights': analysis_result.rss_insights,
            'outlook_strategy': analysis_result.outlook_strategy,
            'standalone_summaries': analysis_result.standalone_summaries
        }
    }
    
    analysis_id = ai_storage.save_analysis_result(analysis_data)
    ai_storage.save_analysis_sections(analysis_id, analysis_data['full_result'])
    
    db_conn.close()
    
    print(f"[持久化] AI 分析结果已保存（ID: {analysis_id}）")
    
except Exception as e:
    print(f"[持久化] 保存 AI 分析结果失败: {e}")

# 2. 更新关键词统计到 memory.db
try:
    memory_conn = storage_manager.ensure_memory_db()
    keyword_manager = KeywordStatsManager(memory_conn)
    
    # 统计关键词出现次数（假设已有 keyword_stats 变量）
    # 这里需要根据实际的关键词统计结果来构建数据
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 示例：假设 keyword_stats 是 {keyword: count} 字典
    # 实际实现时需要从匹配结果中统计
    keywords_data = []
    for rank, (keyword, count) in enumerate(keyword_stats.items(), 1):
        keywords_data.append({
            'date': today,
            'keyword': keyword,
            'count': count,
            'platforms': platforms,  # 简化处理，实际应该按关键词分平台
            'rank': rank
        })
    
    if keywords_data:
        keyword_manager.batch_update_keywords(keywords_data)
        print(f"[持久化] 关键词统计已更新（{len(keywords_data)} 个关键词）")
    
    memory_conn.close()
    
except Exception as e:
    print(f"[持久化] 更新关键词统计失败: {e}")
```

- [ ] **Step 3: 测试集成功能**

```bash
# 运行完整流程
python -m trendradar

# 检查是否生成了 AI 分析记录
sqlite3 output/news/$(date +%Y-%m-%d).db "SELECT COUNT(*) FROM ai_analysis_results"

# 检查是否生成了关键词统计
sqlite3 output/memory.db "SELECT COUNT(*) FROM keyword_trends"
```

Expected output: 
- AI 分析结果已保存
- 关键词统计已更新

- [ ] **Step 4: 提交集成代码**

```bash
git add trendradar/__main__.py
git add trendradar/storage/manager.py
git commit -m "feat(integration): integrate AI analysis and keyword stats storage into main flow"
```

---

## Phase 2: 记忆生成功能（预计 2 天）

### Task 5: 实现记忆数据模型

**Files:**
- Create: `trendradar/memory/__init__.py`
- Create: `trendradar/memory/models.py`
- Create: `tests/memory/test_models.py`

- [ ] **Step 1: 创建记忆模块初始化文件**

Create file `trendradar/memory/__init__.py`:

```python
# coding=utf-8
"""
记忆引擎模块 - 提供日摘要、周提炼生成和查询功能
"""

from trendradar.memory.models import Memory, MemoryType, MemoryLink, LinkType
from trendradar.memory.generator import MemoryGenerator
from trendradar.memory.query import MemoryQueryEngine

__all__ = [
    'Memory',
    'MemoryType',
    'MemoryLink',
    'LinkType',
    'MemoryGenerator',
    'MemoryQueryEngine',
]
```

- [ ] **Step 2: 编写数据模型测试**

Create file `tests/memory/test_models.py`:

```python
# coding=utf-8
import json
from datetime import datetime

import pytest

from trendradar.memory.models import (
    Memory,
    MemoryType,
    MemoryLink,
    LinkType,
    MemoryRepository
)


def test_memory_creation():
    """测试创建记忆对象"""
    memory = Memory(
        id='daily_20260425',
        type=MemoryType.DAILY_SUMMARY,
        title='2026-04-25 日摘要',
        description='DeepSeek 全网热议',
        content='## 核心热点\n...',
        metadata={
            'date': '2026-04-25',
            'keywords': ['DeepSeek', 'AI']
        },
        created_at='2026-04-25T23:00:00',
        updated_at='2026-04-25T23:00:00'
    )
    
    assert memory.id == 'daily_20260425'
    assert memory.type == MemoryType.DAILY_SUMMARY
    assert 'DeepSeek' in memory.metadata['keywords']


def test_memory_to_dict():
    """测试记忆对象转字典"""
    memory = Memory(
        id='test',
        type=MemoryType.DAILY_SUMMARY,
        title='测试',
        description='描述',
        content='内容',
        metadata={},
        created_at='2026-04-25T00:00:00',
        updated_at='2026-04-25T00:00:00'
    )
    
    data = memory.to_dict()
    
    assert data['id'] == 'test'
    assert data['type'] == 'daily_summary'
    assert 'metadata' in data


def test_memory_from_dict():
    """测试从字典创建记忆对象"""
    data = {
        'id': 'test',
        'type': 'daily_summary',
        'title': '测试',
        'description': '描述',
        'content': '内容',
        'metadata': '{}',
        'created_at': '2026-04-25T00:00:00',
        'updated_at': '2026-04-25T00:00:00'
    }
    
    memory = Memory.from_dict(data)
    
    assert memory.id == 'test'
    assert memory.type == MemoryType.DAILY_SUMMARY


def test_memory_link_creation():
    """测试创建记忆关联"""
    link = MemoryLink(
        from_memory_id='weekly_2026w17',
        to_memory_id='daily_20260425',
        link_type=LinkType.DERIVES_FROM,
        notes='周提炼派生自日摘要'
    )
    
    assert link.from_memory_id == 'weekly_2026w17'
    assert link.link_type == LinkType.DERIVES_FROM
```

- [ ] **Step 3: 运行测试验证失败**

```bash
pytest tests/memory/test_models.py -v
```

Expected output: FAIL - modules not defined

- [ ] **Step 4: 实现记忆数据模型**

Create file `trendradar/memory/models.py`:

```python
# coding=utf-8
"""
记忆数据模型
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class MemoryType(Enum):
    """记忆类型"""
    DAILY_SUMMARY = 'daily_summary'
    WEEKLY_DIGEST = 'weekly_digest'
    TOPIC_INSIGHT = 'topic_insight'
    PATTERN = 'pattern'
    SIGNAL = 'signal'


class LinkType(Enum):
    """记忆关联类型"""
    SUPPORTS = 'supports'          # 支持
    CONTRADICTS = 'contradicts'    # 矛盾
    EXTENDS = 'extends'            # 扩展
    DERIVES_FROM = 'derives_from'  # 派生自


@dataclass
class Memory:
    """记忆对象"""
    id: str
    type: MemoryType
    title: str
    description: str
    content: str                    # Markdown 格式
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于数据库存储）"""
        data = asdict(self)
        data['type'] = self.type.value
        data['metadata'] = json.dumps(self.metadata, ensure_ascii=False)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """从字典创建对象（从数据库读取）"""
        # 复制数据避免修改原字典
        data = dict(data)
        
        # 转换类型
        if isinstance(data.get('type'), str):
            data['type'] = MemoryType(data['type'])
        
        # 解析 metadata
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
        
        return cls(**data)


@dataclass
class MemoryLink:
    """记忆关联"""
    from_memory_id: str
    to_memory_id: str
    link_type: LinkType
    notes: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['link_type'] = self.link_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryLink':
        """从字典创建对象"""
        data = dict(data)
        if isinstance(data.get('link_type'), str):
            data['link_type'] = LinkType(data['link_type'])
        return cls(**data)


@dataclass
class KeywordStat:
    """关键词统计"""
    date: str
    keyword: str
    count: int
    platforms: List[str] = field(default_factory=list)
    rank: Optional[int] = None


class MemoryRepository:
    """记忆仓库 - 数据访问层"""
    
    def __init__(self, conn):
        self.conn = conn
    
    def save(self, memory: Memory) -> None:
        """保存记忆"""
        data = memory.to_dict()
        
        self.conn.execute("""
            INSERT OR REPLACE INTO memories (
                id, type, title, description, content, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['id'],
            data['type'],
            data['title'],
            data['description'],
            data['content'],
            data['metadata'],
            data['created_at'],
            data['updated_at']
        ))
        
        self.conn.commit()
    
    def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """根据 ID 获取记忆"""
        cursor = self.conn.execute(
            "SELECT * FROM memories WHERE id = ?",
            (memory_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return Memory.from_dict(dict(row))
    
    def get_by_type(
        self,
        memory_type: MemoryType,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """按类型获取记忆"""
        query = "SELECT * FROM memories WHERE type = ? ORDER BY created_at DESC"
        params = [memory_type.value]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()
        
        return [Memory.from_dict(dict(row)) for row in rows]
    
    def get_by_date_range(
        self,
        memory_type: MemoryType,
        start_date: str,
        end_date: str
    ) -> List[Memory]:
        """按日期范围获取记忆"""
        cursor = self.conn.execute("""
            SELECT * FROM memories
            WHERE type = ? AND created_at BETWEEN ? AND ?
            ORDER BY created_at ASC
        """, (memory_type.value, start_date, end_date))
        
        rows = cursor.fetchall()
        return [Memory.from_dict(dict(row)) for row in rows]
    
    def create_link(self, link: MemoryLink) -> None:
        """创建记忆关联"""
        data = link.to_dict()
        
        self.conn.execute("""
            INSERT OR REPLACE INTO memory_links (
                from_memory_id, to_memory_id, link_type, notes, created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            data['from_memory_id'],
            data['to_memory_id'],
            data['link_type'],
            data['notes'],
            data['created_at']
        ))
        
        self.conn.commit()
    
    def get_links(
        self,
        memory_id: str,
        direction: str = 'both'
    ) -> List[MemoryLink]:
        """
        获取记忆的关联
        
        Args:
            memory_id: 记忆 ID
            direction: 'from' | 'to' | 'both'
        """
        if direction == 'from':
            query = "SELECT * FROM memory_links WHERE from_memory_id = ?"
        elif direction == 'to':
            query = "SELECT * FROM memory_links WHERE to_memory_id = ?"
        else:
            query = """
                SELECT * FROM memory_links 
                WHERE from_memory_id = ? OR to_memory_id = ?
            """
        
        params = [memory_id] if direction != 'both' else [memory_id, memory_id]
        
        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()
        
        return [MemoryLink.from_dict(dict(row)) for row in rows]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/memory/test_models.py -v
```

Expected output: All tests PASS

- [ ] **Step 6: 提交记忆模型**

```bash
git add trendradar/memory/models.py
git add tests/memory/test_models.py
git commit -m "feat(memory): implement memory data models with tests"
```

---

### Task 6: 实现记忆生成器

**Files:**
- Create: `trendradar/memory/generator.py`
- Create: `tests/memory/test_generator.py`

- [ ] **Step 1: 编写记忆生成器测试**

Create file `tests/memory/test_generator.py`:

```python
# coding=utf-8
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

import pytest

from trendradar.persistence.schema import initialize_memory_db
from trendradar.memory.models import Memory, MemoryType, MemoryRepository
from trendradar.memory.generator import MemoryGenerator


@pytest.fixture
def memory_db():
    """创建临时 memory.db"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    conn = initialize_memory_db(db_path)
    
    yield conn
    
    conn.close()
    Path(db_path).unlink()


@pytest.mark.asyncio
async def test_generate_daily_summary(memory_db):
    """测试生成每日摘要"""
    generator = MemoryGenerator(memory_db, api_key='test-key')
    
    # Mock AI 响应
    mock_ai_response = """
## 核心热点
- DeepSeek V4 预览版发布，全网热议

## 舆论风向
- 技术乐观派 vs 商业化质疑派

## 关键词热度 Top 5
1. DeepSeek (67条)
2. 美股 (32条)
    """
    
    with patch.object(generator, '_call_ai', new=AsyncMock(return_value=mock_ai_response)):
        summary = await generator.generate_daily_summary('2026-04-25')
    
    assert summary is not None
    assert summary.id == 'daily_20260425'
    assert summary.type == MemoryType.DAILY_SUMMARY
    assert 'DeepSeek' in summary.content
    
    # 验证已保存到数据库
    repo = MemoryRepository(memory_db)
    saved = repo.get_by_id('daily_20260425')
    assert saved is not None


@pytest.mark.asyncio
async def test_generate_weekly_digest(memory_db):
    """测试生成周提炼"""
    repo = MemoryRepository(memory_db)
    generator = MemoryGenerator(memory_db, api_key='test-key')
    
    # 先创建 7 天的日摘要
    for i in range(7):
        daily = Memory(
            id=f'daily_2026042{i}',
            type=MemoryType.DAILY_SUMMARY,
            title=f'2026-04-2{i} 日摘要',
            description='测试',
            content=f'第 {i} 天的内容',
            metadata={'date': f'2026-04-2{i}'},
            created_at=f'2026-04-2{i}T23:00:00',
            updated_at=f'2026-04-2{i}T23:00:00'
        )
        repo.save(daily)
    
    # Mock AI 响应
    mock_ai_response = """
## 宏观趋势
- DeepSeek 热度从周一到周五持续增长

## 平台温差
- 微博情绪化，知乎深度分析
    """
    
    with patch.object(generator, '_call_ai', new=AsyncMock(return_value=mock_ai_response)):
        digest = await generator.generate_weekly_digest('2026-04-20', '2026-04-26')
    
    assert digest is not None
    assert digest.type == MemoryType.WEEKLY_DIGEST
    assert 'DeepSeek' in digest.content
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/memory/test_generator.py -v
```

Expected output: FAIL - `MemoryGenerator` not defined

- [ ] **Step 3: 实现 MemoryGenerator 类**

Create file `trendradar/memory/generator.py`:

```python
# coding=utf-8
"""
记忆生成器 - 使用 AI 生成日摘要和周提炼
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from trendradar.memory.models import (
    Memory,
    MemoryType,
    MemoryRepository,
    MemoryLink,
    LinkType
)
from trendradar.persistence.ai_storage import AIAnalysisStorage
from trendradar.persistence.keyword_stats import KeywordStatsManager


class MemoryGenerator:
    """记忆生成器"""
    
    def __init__(
        self,
        memory_conn: sqlite3.Connection,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: str = 'claude-sonnet-4-5'
    ):
        self.memory_conn = memory_conn
        self.repo = MemoryRepository(memory_conn)
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
    
    async def generate_daily_summary(self, date: str) -> Memory:
        """
        生成每日摘要
        
        Args:
            date: 日期（YYYY-MM-DD）
        
        Returns:
            每日摘要 Memory 对象
        """
        # 1. 收集当天的 AI 分析结果
        analyses = self._get_analyses_by_date(date)
        
        # 2. 收集关键词统计
        keyword_stats = self._get_keyword_stats_by_date(date)
        
        # 3. 构建提示词
        prompt = self._build_daily_summary_prompt(analyses, keyword_stats)
        
        # 4. 调用 AI 生成摘要
        summary_content = await self._call_ai(prompt)
        
        # 5. 创建 Memory 对象
        memory_id = f"daily_{date.replace('-', '')}"
        memory = Memory(
            id=memory_id,
            type=MemoryType.DAILY_SUMMARY,
            title=f"{date} 日摘要",
            description=self._extract_description(summary_content),
            content=summary_content,
            metadata={
                'date': date,
                'source_analyses': [a['id'] for a in analyses],
                'keywords': [k['keyword'] for k in keyword_stats[:10]]
            },
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # 6. 保存到数据库
        self.repo.save(memory)
        
        return memory
    
    async def generate_weekly_digest(
        self,
        start_date: str,
        end_date: str
    ) -> Memory:
        """
        生成周提炼
        
        Args:
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
        
        Returns:
            周提炼 Memory 对象
        """
        # 1. 获取这周的所有日摘要
        daily_summaries = self.repo.get_by_date_range(
            MemoryType.DAILY_SUMMARY,
            start_date,
            end_date
        )
        
        if not daily_summaries:
            raise ValueError(f"No daily summaries found for {start_date} to {end_date}")
        
        # 2. 获取关键词趋势
        keyword_trends = self._get_keyword_trends_range(start_date, end_date)
        
        # 3. 构建提示词
        prompt = self._build_weekly_digest_prompt(daily_summaries, keyword_trends)
        
        # 4. 调用 AI 生成周提炼
        digest_content = await self._call_ai(prompt)
        
        # 5. 创建 Memory 对象
        week_id = f"weekly_{self._get_iso_week(start_date)}"
        memory = Memory(
            id=week_id,
            type=MemoryType.WEEKLY_DIGEST,
            title=f"{start_date} 至 {end_date} 周提炼",
            description=self._extract_description(digest_content),
            content=digest_content,
            metadata={
                'date_range': [start_date, end_date],
                'source_summaries': [s.id for s in daily_summaries]
            },
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # 6. 保存到数据库
        self.repo.save(memory)
        
        # 7. 创建关联
        for summary in daily_summaries:
            link = MemoryLink(
                from_memory_id=week_id,
                to_memory_id=summary.id,
                link_type=LinkType.DERIVES_FROM,
                notes='周提炼派生自日摘要'
            )
            self.repo.create_link(link)
        
        return memory
    
    def _get_analyses_by_date(self, date: str) -> List[Dict[str, Any]]:
        """获取某日的所有 AI 分析结果（从日期数据库）"""
        # 这里需要访问日期数据库，暂时返回空列表
        # 实际实现时需要打开对应日期的数据库
        return []
    
    def _get_keyword_stats_by_date(self, date: str) -> List[Dict[str, Any]]:
        """获取某日的关键词统计"""
        keyword_manager = KeywordStatsManager(self.memory_conn)
        return keyword_manager.get_top_keywords_by_date(date, limit=20)
    
    def _get_keyword_trends_range(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """获取日期范围内的关键词趋势"""
        keyword_manager = KeywordStatsManager(self.memory_conn)
        all_stats = keyword_manager.get_keywords_by_date_range(start_date, end_date)
        
        # 按关键词分组
        trends = {}
        for stat in all_stats:
            keyword = stat['keyword']
            if keyword not in trends:
                trends[keyword] = []
            trends[keyword].append(stat)
        
        return trends
    
    def _build_daily_summary_prompt(
        self,
        analyses: List[Dict[str, Any]],
        keyword_stats: List[Dict[str, Any]]
    ) -> str:
        """构建每日摘要提示词"""
        return f"""请根据以下信息生成今日的新闻摘要（200字以内）：

## AI 分析结果
{json.dumps(analyses, ensure_ascii=False, indent=2)}

## 关键词统计 Top 20
{json.dumps(keyword_stats, ensure_ascii=False, indent=2)}

要求：
1. 提炼核心热点（3-5个）
2. 总结舆论风向
3. 识别异动与弱信号
4. 列出关键词热度 Top 5

格式：Markdown，简洁清晰。
"""
    
    def _build_weekly_digest_prompt(
        self,
        daily_summaries: List[Memory],
        keyword_trends: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """构建周提炼提示词"""
        summaries_text = "\n\n".join([
            f"### {s.title}\n{s.content}"
            for s in daily_summaries
        ])
        
        return f"""请根据过去 7 天的日摘要生成本周提炼（300字以内）：

## 每日摘要
{summaries_text}

## 关键词趋势
{json.dumps(keyword_trends, ensure_ascii=False, indent=2)}

要求：
1. 提炼宏观趋势（而非简单重复每日内容）
2. 识别跨日期的模式和关联
3. 分析关键词的演变
4. 总结平台温差

格式：Markdown，注重洞察而非罗列。
"""
    
    async def _call_ai(self, prompt: str) -> str:
        """
        调用 AI API 生成内容
        
        注：这里需要实际实现 Claude API 调用
        暂时返回模拟内容
        """
        # TODO: 实现真实的 AI API 调用
        # 使用 anthropic SDK 或项目中已有的 AI 模块
        
        # 临时模拟响应
        return "## 摘要内容\n这是 AI 生成的摘要..."
    
    def _extract_description(self, content: str) -> str:
        """从内容中提取单行描述（前50字）"""
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                return line[:100]
        return ''
    
    def _get_iso_week(self, date_str: str) -> str:
        """获取 ISO 周编号（YYYY-Wxx）"""
        date = datetime.strptime(date_str, '%Y-%m-%d')
        year, week, _ = date.isocalendar()
        return f"{year}w{week:02d}"
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/memory/test_generator.py -v
```

Expected output: All tests PASS

- [ ] **Step 5: 提交记忆生成器**

```bash
git add trendradar/memory/generator.py
git add tests/memory/test_generator.py
git commit -m "feat(memory): implement memory generator for daily/weekly summaries"
```

---

## Phase 3: 查询接口与定时任务（预计 1 天）

### Task 7: 实现查询引擎

**Files:**
- Create: `trendradar/memory/query.py`
- Create: `tests/memory/test_query.py`

- [ ] **Step 1: 编写查询引擎测试**

Create file `tests/memory/test_query.py`:

```python
# coding=utf-8
import sqlite3
import tempfile
from pathlib import Path

import pytest

from trendradar.persistence.schema import initialize_memory_db
from trendradar.memory.models import Memory, MemoryType, MemoryRepository
from trendradar.memory.query import MemoryQueryEngine
from trendradar.persistence.keyword_stats import KeywordStatsManager


@pytest.fixture
def memory_db_with_data():
    """创建包含测试数据的 memory.db"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    conn = initialize_memory_db(db_path)
    repo = MemoryRepository(conn)
    
    # 添加测试记忆
    for i in range(5):
        memory = Memory(
            id=f'daily_2026042{i}',
            type=MemoryType.DAILY_SUMMARY,
            title=f'2026-04-2{i} 日摘要',
            description=f'DeepSeek 热度第 {i} 天',
            content=f'## 核心热点\nDeepSeek 相关内容...',
            metadata={'date': f'2026-04-2{i}', 'keywords': ['DeepSeek']},
            created_at=f'2026-04-2{i}T23:00:00',
            updated_at=f'2026-04-2{i}T23:00:00'
        )
        repo.save(memory)
    
    # 添加关键词趋势
    keyword_manager = KeywordStatsManager(conn)
    for i in range(5):
        keyword_manager.update_keyword_stat({
            'date': f'2026-04-2{i}',
            'keyword': 'DeepSeek',
            'count': 10 + i * 15,
            'platforms': ['微博', '知乎'],
            'rank': 1
        })
    
    yield conn
    
    conn.close()
    Path(db_path).unlink()


def test_search_memories(memory_db_with_data):
    """测试搜索记忆"""
    engine = MemoryQueryEngine(memory_db_with_data)
    
    results = engine.search_memories(
        types=[MemoryType.DAILY_SUMMARY],
        keywords=['DeepSeek']
    )
    
    assert len(results) > 0
    assert all(r.type == MemoryType.DAILY_SUMMARY for r in results)


def test_get_keyword_trend(memory_db_with_data):
    """测试获取关键词趋势"""
    engine = MemoryQueryEngine(memory_db_with_data)
    
    trend = engine.get_keyword_trend('DeepSeek', days=5)
    
    assert len(trend) == 5
    assert trend[0]['count'] == 10
    assert trend[4]['count'] == 70


def test_get_memories_by_date_range(memory_db_with_data):
    """测试按日期范围查询记忆"""
    engine = MemoryQueryEngine(memory_db_with_data)
    
    results = engine.get_memories_by_date_range(
        memory_type=MemoryType.DAILY_SUMMARY,
        start_date='2026-04-21',
        end_date='2026-04-23'
    )
    
    assert len(results) == 3
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/memory/test_query.py -v
```

Expected output: FAIL - `MemoryQueryEngine` not defined

- [ ] **Step 3: 实现 MemoryQueryEngine 类**

Create file `trendradar/memory/query.py`:

```python
# coding=utf-8
"""
记忆查询引擎
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

from trendradar.memory.models import (
    Memory,
    MemoryType,
    MemoryRepository,
    MemoryLink
)
from trendradar.persistence.keyword_stats import KeywordStatsManager


class MemoryQueryEngine:
    """记忆查询引擎"""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo = MemoryRepository(conn)
        self.keyword_manager = KeywordStatsManager(conn)
    
    def search_memories(
        self,
        query: Optional[str] = None,
        types: Optional[List[MemoryType]] = None,
        keywords: Optional[List[str]] = None,
        date_range: Optional[Tuple[str, str]] = None,
        limit: int = 10
    ) -> List[Memory]:
        """
        智能检索记忆
        
        Args:
            query: 自然语言查询（暂未实现语义搜索）
            types: 记忆类型过滤
            keywords: 关键词过滤（在 metadata.keywords 中搜索）
            date_range: 日期范围 (start, end)
            limit: 返回数量限制
        
        Returns:
            匹配的记忆列表
        """
        # 构建 SQL 查询
        conditions = []
        params = []
        
        # 类型过滤
        if types:
            type_values = [t.value for t in types]
            placeholders = ','.join(['?'] * len(type_values))
            conditions.append(f"type IN ({placeholders})")
            params.extend(type_values)
        
        # 日期范围过滤
        if date_range:
            conditions.append("created_at BETWEEN ? AND ?")
            params.extend(date_range)
        
        # 构建完整查询
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query_sql = f"""
            SELECT * FROM memories
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)
        
        cursor = self.conn.execute(query_sql, params)
        rows = cursor.fetchall()
        
        memories = [Memory.from_dict(dict(row)) for row in rows]
        
        # 关键词过滤（在 Python 中进行，因为 metadata 是 JSON）
        if keywords:
            memories = [
                m for m in memories
                if any(kw in m.metadata.get('keywords', []) for kw in keywords)
            ]
        
        return memories
    
    def get_keyword_trend(
        self,
        keyword: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取关键词的热度趋势
        
        Args:
            keyword: 关键词
            days: 过去多少天
        
        Returns:
            趋势数据列表（按日期排序）
        """
        return self.keyword_manager.get_keyword_trend(keyword, days)
    
    def get_memories_by_date_range(
        self,
        memory_type: MemoryType,
        start_date: str,
        end_date: str
    ) -> List[Memory]:
        """
        按日期范围获取记忆
        
        Args:
            memory_type: 记忆类型
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
        
        Returns:
            记忆列表
        """
        return self.repo.get_by_date_range(memory_type, start_date, end_date)
    
    def get_related_memories(
        self,
        memory_id: str
    ) -> List[Tuple[Memory, str]]:
        """
        查找相关记忆
        
        Args:
            memory_id: 记忆 ID
        
        Returns:
            (Memory, link_type) 元组列表
        """
        links = self.repo.get_links(memory_id, direction='both')
        
        results = []
        for link in links:
            # 确定关联的另一端
            related_id = (
                link.to_memory_id
                if link.from_memory_id == memory_id
                else link.from_memory_id
            )
            
            related_memory = self.repo.get_by_id(related_id)
            if related_memory:
                results.append((related_memory, link.link_type.value))
        
        return results
    
    def get_top_keywords_by_date(
        self,
        date: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取某日 Top 关键词
        
        Args:
            date: 日期（YYYY-MM-DD）
            limit: 返回数量
        
        Returns:
            Top 关键词列表
        """
        return self.keyword_manager.get_top_keywords_by_date(date, limit)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/memory/test_query.py -v
```

Expected output: All tests PASS

- [ ] **Step 5: 提交查询引擎**

```bash
git add trendradar/memory/query.py
git add tests/memory/test_query.py
git commit -m "feat(memory): implement memory query engine with search and trend APIs"
```

---

### Task 8: 实现定时任务调度（简化版）

**Files:**
- Create: `trendradar/memory/scheduler.py`
- Modify: `trendradar/__main__.py`

- [ ] **Step 1: 创建调度器模块**

Create file `trendradar/memory/scheduler.py`:

```python
# coding=utf-8
"""
记忆生成定时任务调度器（简化版）

注：完整的定时任务需要配合系统 cron 或外部调度器
这里提供手动触发接口
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from trendradar.memory.generator import MemoryGenerator
from trendradar.storage import get_storage_manager


async def generate_daily_summary_task(
    date: Optional[str] = None,
    api_key: Optional[str] = None
) -> None:
    """
    生成每日摘要任务
    
    Args:
        date: 日期（YYYY-MM-DD），默认为昨天
        api_key: AI API Key
    """
    if not date:
        yesterday = datetime.now() - timedelta(days=1)
        date = yesterday.strftime('%Y-%m-%d')
    
    print(f"[调度器] 开始生成 {date} 的每日摘要...")
    
    # 获取 memory.db 连接
    storage_manager = get_storage_manager()
    memory_conn = storage_manager.ensure_memory_db()
    
    # 生成摘要
    generator = MemoryGenerator(memory_conn, api_key=api_key)
    summary = await generator.generate_daily_summary(date)
    
    print(f"[调度器] 每日摘要已生成: {summary.id}")
    
    memory_conn.close()


async def generate_weekly_digest_task(
    end_date: Optional[str] = None,
    api_key: Optional[str] = None
) -> None:
    """
    生成周提炼任务
    
    Args:
        end_date: 结束日期（YYYY-MM-DD），默认为昨天
        api_key: AI API Key
    """
    if not end_date:
        yesterday = datetime.now() - timedelta(days=1)
        end_date = yesterday.strftime('%Y-%m-%d')
    
    # 计算开始日期（往前推 7 天）
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    start_dt = end_dt - timedelta(days=6)
    start_date = start_dt.strftime('%Y-%m-%d')
    
    print(f"[调度器] 开始生成 {start_date} 至 {end_date} 的周提炼...")
    
    # 获取 memory.db 连接
    storage_manager = get_storage_manager()
    memory_conn = storage_manager.ensure_memory_db()
    
    # 生成周提炼
    generator = MemoryGenerator(memory_conn, api_key=api_key)
    digest = await generator.generate_weekly_digest(start_date, end_date)
    
    print(f"[调度器] 周提炼已生成: {digest.id}")
    
    memory_conn.close()


def run_daily_summary_sync(date: Optional[str] = None, api_key: Optional[str] = None):
    """同步版本的每日摘要生成（用于命令行调用）"""
    asyncio.run(generate_daily_summary_task(date, api_key))


def run_weekly_digest_sync(end_date: Optional[str] = None, api_key: Optional[str] = None):
    """同步版本的周提炼生成（用于命令行调用）"""
    asyncio.run(generate_weekly_digest_task(end_date, api_key))
```

- [ ] **Step 2: 添加 CLI 命令支持**

在 `trendradar/__main__.py` 中添加子命令：

```python
# 在 argparse 部分添加新的子命令

# 创建子命令解析器（如果还没有）
subparsers = parser.add_subparsers(dest='command', help='子命令')

# 记忆生成命令
memory_parser = subparsers.add_parser('memory', help='记忆生成和查询')
memory_subparsers = memory_parser.add_subparsers(dest='memory_command')

# 生成每日摘要
daily_parser = memory_subparsers.add_parser('daily', help='生成每日摘要')
daily_parser.add_argument('--date', help='日期（YYYY-MM-DD），默认为昨天')
daily_parser.add_argument('--api-key', help='AI API Key')

# 生成周提炼
weekly_parser = memory_subparsers.add_parser('weekly', help='生成周提炼')
weekly_parser.add_argument('--end-date', help='结束日期（YYYY-MM-DD），默认为昨天')
weekly_parser.add_argument('--api-key', help='AI API Key')

# 在 main() 函数中处理命令
if args.command == 'memory':
    from trendradar.memory.scheduler import (
        run_daily_summary_sync,
        run_weekly_digest_sync
    )
    
    if args.memory_command == 'daily':
        run_daily_summary_sync(args.date, args.api_key)
    elif args.memory_command == 'weekly':
        run_weekly_digest_sync(args.end_date, args.api_key)
    else:
        memory_parser.print_help()
```

- [ ] **Step 3: 测试 CLI 命令**

```bash
# 生成每日摘要
python -m trendradar memory daily --date 2026-04-25 --api-key sk-xxx

# 生成周提炼
python -m trendradar memory weekly --end-date 2026-04-25 --api-key sk-xxx

# 查看帮助
python -m trendradar memory --help
```

Expected output: 命令正常执行，生成相应的记忆

- [ ] **Step 4: 提交调度器**

```bash
git add trendradar/memory/scheduler.py
git add trendradar/__main__.py
git commit -m "feat(memory): add scheduler and CLI commands for memory generation"
```

---

## 最终验证与文档

### Task 9: 端到端测试

**Files:**
- Create: `tests/integration/test_e2e_persistence.py`
- Create: `docs/memory_system_usage.md`

- [ ] **Step 1: 编写端到端集成测试**

Create file `tests/integration/test_e2e_persistence.py`:

```python
# coding=utf-8
"""
端到端集成测试：完整的数据持久化和记忆生成流程
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# 这里添加端到端测试用例
# 测试从新闻爬取 → AI 分析 → 存储 → 记忆生成 → 查询的完整流程
```

- [ ] **Step 2: 运行所有测试**

```bash
# 运行所有单元测试
pytest tests/persistence/ tests/memory/ -v

# 运行集成测试
pytest tests/integration/ -v

# 生成覆盖率报告
pytest --cov=trendradar/persistence --cov=trendradar/memory --cov-report=html
```

Expected output: All tests PASS, 覆盖率 > 80%

- [ ] **Step 3: 编写使用文档**

Create file `docs/memory_system_usage.md`:

```markdown
# TrendRadar 记忆系统使用指南

## 概述

TrendRadar 记忆系统提供了完整的数据持久化和智能记忆生成功能。

## 功能特性

1. **AI 分析结果持久化**：每次分析后自动保存
2. **关键词趋势追踪**：自动统计和更新关键词热度
3. **每日摘要**：自动或手动生成每日新闻摘要
4. **周提炼**：从日摘要中提取宏观趋势
5. **查询接口**：支持按类型、关键词、日期查询记忆

## 使用方法

### 1. 自动存储（已集成到主流程）

正常运行 TrendRadar 即可自动保存 AI 分析结果和关键词统计：

\`\`\`bash
python -m trendradar
\`\`\`

### 2. 生成每日摘要

\`\`\`bash
# 生成昨天的摘要
python -m trendradar memory daily --api-key sk-xxx

# 生成指定日期的摘要
python -m trendradar memory daily --date 2026-04-25 --api-key sk-xxx
\`\`\`

### 3. 生成周提炼

\`\`\`bash
# 生成最近一周的提炼
python -m trendradar memory weekly --api-key sk-xxx

# 生成指定周的提炼
python -m trendradar memory weekly --end-date 2026-04-25 --api-key sk-xxx
\`\`\`

### 4. 查询记忆（Python API）

\`\`\`python
from trendradar.storage import get_storage_manager
from trendradar.memory.query import MemoryQueryEngine
from trendradar.memory.models import MemoryType

# 初始化
storage_manager = get_storage_manager()
memory_conn = storage_manager.ensure_memory_db()
query_engine = MemoryQueryEngine(memory_conn)

# 搜索记忆
memories = query_engine.search_memories(
    types=[MemoryType.DAILY_SUMMARY],
    keywords=['DeepSeek'],
    limit=10
)

# 获取关键词趋势
trend = query_engine.get_keyword_trend('DeepSeek', days=30)

# 获取某日 Top 关键词
top_keywords = query_engine.get_top_keywords_by_date('2026-04-25', limit=10)

memory_conn.close()
\`\`\`

## 数据库位置

- **日期数据库**：`output/news/YYYY-MM-DD.db`（新闻和 AI 分析详情）
- **记忆数据库**：`output/memory.db`（摘要、统计、洞察）

## 定时任务配置（推荐）

使用系统 cron 定时生成记忆：

\`\`\`bash
# 编辑 crontab
crontab -e

# 添加任务
# 每天 23:00 生成日摘要
0 23 * * * cd /path/to/TrendRadar && python -m trendradar memory daily --api-key sk-xxx

# 每周日 23:30 生成周提炼
30 23 * * 0 cd /path/to/TrendRadar && python -m trendradar memory weekly --api-key sk-xxx
\`\`\`

## 下一步

- 实现记忆验证机制
- 开发数据可视化大盘
- 构建分析 Agent
\`\`\`

- [ ] **Step 4: 更新项目 README**

在项目 `README.md` 中添加记忆系统相关章节。

- [ ] **Step 5: 提交文档和测试**

```bash
git add tests/integration/test_e2e_persistence.py
git add docs/memory_system_usage.md
git add README.md
git commit -m "docs: add memory system usage guide and integration tests"
```

---

## 完成验收

### Task 10: 最终验收检查清单

- [ ] **功能完整性检查**

验证所有功能已实现：
- [ ] AI 分析结果存储
- [ ] 关键词统计更新
- [ ] 日摘要生成
- [ ] 周提炼生成
- [ ] 查询接口

- [ ] **测试覆盖率检查**

```bash
pytest --cov=trendradar --cov-report=term-missing
```

确保覆盖率 > 80%

- [ ] **代码质量检查**

```bash
# 运行 linter（如果项目有配置）
flake8 trendradar/persistence trendradar/memory

# 类型检查（如果使用 mypy）
mypy trendradar/persistence trendradar/memory
```

- [ ] **性能验证**

```bash
# 测试查询性能
python -c "
from trendradar.storage import get_storage_manager
from trendradar.memory.query import MemoryQueryEngine
import time

conn = get_storage_manager().ensure_memory_db()
engine = MemoryQueryEngine(conn)

start = time.time()
results = engine.search_memories(limit=100)
elapsed = time.time() - start

print(f'查询耗时: {elapsed:.2f}s')
assert elapsed < 1.0, '查询超过1秒'
"
```

- [ ] **文档完整性检查**

- [ ] 设计文档存在且完整
- [ ] 使用文档清晰易懂
- [ ] 代码注释充分
- [ ] API 文档完整

- [ ] **提交最终版本**

```bash
git add .
git commit -m "feat: complete TrendRadar data persistence and memory system

Implemented features:
- AI analysis result storage with full 6-section indexing
- Keyword statistics tracking (dual-layer: news-level + aggregated)
- Daily summary generation using AI
- Weekly digest generation with cross-day insights
- Memory query engine with search and trend APIs
- CLI commands for manual memory generation
- Comprehensive test coverage (>80%)

Phase 1: Core storage (AI analysis + keyword stats)
Phase 2: Memory generation (daily/weekly)
Phase 3: Query interface + scheduler

See docs/memory_system_usage.md for usage guide.
"
```

- [ ] **创建 PR 或合并到主分支**

根据项目工作流创建 Pull Request 或合并到 master 分支。

---

## 附录

### A. 技术债务与未来优化

以下功能作为后续迭代：

1. **记忆验证机制**（FR6）
   - 定期验证记忆是否仍然有效
   - 自动标记过时的记忆

2. **Markdown 洞察文档生成**（FR7）
   - 生成人类可读的 `.md` 文件
   - 维护 `INSIGHTS.md` 索引

3. **主题洞察自动提取**
   - 使用 AI 自动发现主题演变
   - 生成 `topic_insight` 类型的记忆

4. **模式识别**
   - 自动识别重复出现的规律
   - 生成 `pattern` 类型的记忆

5. **AI API 调用优化**
   - 实现真实的 Claude API 调用
   - 添加 prompt caching 降低成本
   - 错误重试和降级策略

6. **查询性能优化**
   - 添加全文搜索索引
   - 实现向量搜索（embedding）
   - 查询结果缓存

### B. 依赖项

确保以下依赖已安装：

```bash
# 测试依赖
pip install pytest pytest-asyncio pytest-cov

# AI API（如需要）
pip install anthropic

# 或使用项目的包管理器
uv sync
```

---

## 执行建议

**推荐执行方式**：使用 `superpowers:subagent-driven-development` skill

- 每个 Task 分配一个独立的 subagent
- 任务间有自动审查点
- 更快的迭代速度
- 更好的错误隔离

**备选方式**：使用 `superpowers:executing-plans` skill

- 在当前会话中批量执行
- 定期 checkpoint 审查
- 适合线性依赖的任务
