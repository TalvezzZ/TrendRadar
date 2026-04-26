# TrendRadar 数据持久化与记忆系统设计

**日期**: 2026-04-25  
**版本**: 1.0  
**状态**: 已批准

---

## 目录

1. [背景与目标](#背景与目标)
2. [需求总结](#需求总结)
3. [总体架构](#总体架构)
4. [数据库设计](#数据库设计)
5. [记忆系统设计](#记忆系统设计)
6. [数据流设计](#数据流设计)
7. [自动化流程](#自动化流程)
8. [查询接口](#查询接口)
9. [实施计划](#实施计划)
10. [未来扩展](#未来扩展)

---

## 背景与目标

### 当前状况

TrendRadar 已经实现了基础的数据存储功能：
- 新闻数据按日期存储在 SQLite 数据库（`output/news/YYYY-MM-DD.db`）
- 存储表包括：platforms, news_items, rank_history, crawl_records 等
- 支持本地和远程（S3）两种存储后端

### 问题

1. **AI 分析结果未持久化**：每次分析的结果（6个板块内容）未保存，无法回溯和趋势分析
2. **关键词统计未记录**：无法追踪关键词的热度变化趋势
3. **缺少记忆提炼机制**：没有将原始数据提炼为洞察的机制
4. **Agent 分析能力受限**：缺少结构化的历史数据查询接口

### 目标

1. **完整数据持久化**：保存 AI 分析结果、关键词统计、每日摘要
2. **分层记忆系统**：原始数据 → 日摘要 → 周提炼 → 主题洞察
3. **智能查询接口**：为未来的 Agent 提供强大的历史数据分析能力
4. **永久保留策略**：所有数据永久保留，作为长期数据资产

---

## 需求总结

### 功能需求

| 需求 | 描述 | 优先级 |
|------|------|--------|
| FR1 | 存储完整 AI 分析结果（6个板块） | P0 |
| FR2 | 存储关键词统计信息（双层：新闻级别 + 统计级别） | P0 |
| FR3 | 每天自动生成日摘要 | P0 |
| FR4 | 每周自动生成周提炼 | P0 |
| FR5 | 提供结构化查询 API | P1 |
| FR6 | 记忆验证机制 | P2 |
| FR7 | Markdown 洞察文档生成 | P2 |

### 非功能需求

| 需求 | 描述 |
|------|------|
| NFR1 | 数据永久保留，不自动删除 |
| NFR2 | 查询性能：单次查询 < 1秒 |
| NFR3 | 存储效率：合理使用索引和压缩 |
| NFR4 | 可扩展性：支持未来新增记忆类型 |

---

## 总体架构

### 系统分层

```
┌─────────────────────────────────────────────────────────┐
│                Agent 查询层（未来扩展）                    │
│  - 趋势查询：get_keyword_trend(keyword, days)           │
│  - 分析检索：search_analysis(板块, 时间范围)             │
│  - 洞察获取：search_insights(query, types)              │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────┐
│                 记忆引擎（Memory Engine）                 │
│  - 日摘要生成：DailySummaryGenerator                    │
│  - 周提炼生成：WeeklyDigestGenerator                    │
│  - 洞察提取：InsightExtractor                           │
│  - 查询引擎：MemoryQueryEngine                          │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────┐
│                    自动化层（Scheduler）                  │
│  - 每次分析后：保存 AI 结果 + 更新关键词统计              │
│  - 每天 23:00：生成日摘要                                │
│  - 每周日 23:30：生成周提炼                              │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │
┌──────────────────────┬──────────────────────────────────┐
│   日期数据库          │        memory.db                 │
│ YYYY-MM-DD.db        │                                  │
│ - news_items         │  - memories (统一记忆表)         │
│   + matched_keywords │  - memory_links (记忆关联)       │
│ - ai_analysis_results│  - memory_validations (验证)    │
│ - ai_analysis_sections│ - keyword_trends (趋势统计)     │
│ - rank_history       │                                  │
└──────────────────────┴──────────────────────────────────┘
```

### 数据库职责划分

#### 日期数据库（`output/news/YYYY-MM-DD.db`）

**职责**：存储当日的原始数据和分析详情

**新增表**：
- `ai_analysis_results`：AI 分析完整结果
- `ai_analysis_sections`：AI 分析分板块索引

**修改**：
- `news_items` 表新增 `matched_keywords` 字段（JSON）

#### 记忆数据库（`output/memory.db`）

**职责**：存储提炼后的记忆、统计和洞察

**表**：
- `memories`：统一记忆表（日摘要、周提炼、洞察等）
- `memory_links`：记忆之间的关联
- `memory_validations`：记忆验证记录
- `keyword_trends`：关键词热度统计

#### 洞察文档（`output/insights/`，可选）

**职责**：人类可读的 Markdown 洞察文档

**文件**：
- `INSIGHTS.md`：索引文件
- `<topic>_<id>.md`：具体洞察文档

---

## 数据库设计

### 日期数据库新增表

#### ai_analysis_results 表

存储每次 AI 分析的完整结果。

```sql
CREATE TABLE IF NOT EXISTS ai_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_time TEXT NOT NULL,           -- 分析时间（ISO 8601）
    report_mode TEXT NOT NULL,             -- 报告模式（当前榜单/增量模式等）
    news_count INTEGER DEFAULT 0,          -- 热榜新闻条数
    rss_count INTEGER DEFAULT 0,           -- RSS 新闻条数
    matched_keywords JSON,                 -- 匹配的关键词列表
    platforms JSON,                        -- 数据来源平台列表
    
    -- 完整 AI 分析结果（JSON）
    full_result JSON NOT NULL,             -- 包含所有6个板块的完整结果
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(analysis_time)
);

CREATE INDEX IF NOT EXISTS idx_ai_analysis_time 
    ON ai_analysis_results(analysis_time);
```

**full_result JSON 格式**：
```json
{
  "core_trends": "...",
  "sentiment_controversy": "...",
  "signals": "...",
  "rss_insights": "...",
  "outlook_strategy": "...",
  "standalone_summaries": {...}
}
```

#### ai_analysis_sections 表

分板块索引，便于按板块查询。

```sql
CREATE TABLE IF NOT EXISTS ai_analysis_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,         -- 引用 ai_analysis_results.id
    section_type TEXT NOT NULL,           -- 板块类型
    content TEXT NOT NULL,                -- 板块内容
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (analysis_id) REFERENCES ai_analysis_results(id),
    UNIQUE(analysis_id, section_type)
);

CREATE INDEX IF NOT EXISTS idx_ai_sections_type 
    ON ai_analysis_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_ai_sections_analysis 
    ON ai_analysis_sections(analysis_id);
```

**section_type 枚举值**：
- `core_trends`
- `sentiment_controversy`
- `signals`
- `rss_insights`
- `outlook_strategy`
- `standalone_summaries`

### news_items 表修改

新增 `matched_keywords` 字段。

```sql
ALTER TABLE news_items 
ADD COLUMN matched_keywords TEXT DEFAULT '[]';
```

**matched_keywords JSON 格式**：
```json
["DeepSeek", "华为", "AI"]
```

### 记忆数据库表结构

#### memories 表（核心）

统一存储所有类型的记忆。

```sql
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,                  -- 格式：<type>_YYYYMMDD_<seq>
    type TEXT NOT NULL,                   -- 记忆类型
    title TEXT NOT NULL,                  -- 标题
    description TEXT,                     -- 单行摘要（用于检索）
    content TEXT NOT NULL,                -- 完整内容（Markdown格式）
    
    metadata TEXT DEFAULT '{}',           -- JSON 元数据
    
    created_at TEXT NOT NULL,             -- ISO 8601
    updated_at TEXT NOT NULL,             -- ISO 8601
    
    CHECK (type IN (
        'daily_summary',
        'weekly_digest',
        'topic_insight',
        'pattern',
        'signal'
    ))
);

CREATE INDEX IF NOT EXISTS idx_memories_type 
    ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_created 
    ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_memories_type_date 
    ON memories(type, created_at);
```

**type 类型说明**：

| 类型 | 描述 | 生成频率 |
|------|------|----------|
| `daily_summary` | 每日摘要 | 每天 1 次 |
| `weekly_digest` | 每周提炼 | 每周 1 次 |
| `topic_insight` | 主题洞察 | 按需生成 |
| `pattern` | 模式识别 | 自动发现 |
| `signal` | 弱信号 | 自动发现 |

**metadata JSON 格式**：
```json
{
  "date": "2026-04-25",
  "date_range": ["2026-04-19", "2026-04-25"],
  "keywords": ["DeepSeek", "美股", "A股"],
  "platforms": ["微博", "知乎", "华尔街见闻"],
  "confidence": "high",
  "source_analyses": [1, 2, 3],  // 引用的 ai_analysis_results.id
  "source_summaries": ["daily_20260424", "daily_20260425"]
}
```

**content Markdown 格式**：
```markdown
## 核心洞察

...

## Why（为什么）

...

## How to apply（如何应用）

当 Agent 查询 XXX 时，返回此洞察。
```

#### memory_links 表

记忆之间的关联关系。

```sql
CREATE TABLE IF NOT EXISTS memory_links (
    from_memory_id TEXT NOT NULL,
    to_memory_id TEXT NOT NULL,
    link_type TEXT NOT NULL,              -- 关联类型
    notes TEXT,                            -- 关联说明
    
    created_at TEXT DEFAULT (datetime('now')),
    
    PRIMARY KEY (from_memory_id, to_memory_id),
    FOREIGN KEY (from_memory_id) REFERENCES memories(id),
    FOREIGN KEY (to_memory_id) REFERENCES memories(id),
    
    CHECK (link_type IN (
        'supports',       -- 支持
        'contradicts',    -- 矛盾
        'extends',        -- 扩展
        'derives_from'    -- 派生自
    ))
);

CREATE INDEX IF NOT EXISTS idx_memory_links_from 
    ON memory_links(from_memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_links_to 
    ON memory_links(to_memory_id);
```

#### memory_validations 表

追踪记忆是否仍然有效。

```sql
CREATE TABLE IF NOT EXISTS memory_validations (
    memory_id TEXT PRIMARY KEY,
    last_validated TEXT NOT NULL,         -- ISO 8601
    is_valid INTEGER NOT NULL,            -- 0/1
    validation_notes TEXT,                -- 验证说明
    
    FOREIGN KEY (memory_id) REFERENCES memories(id)
);
```

#### keyword_trends 表

关键词热度统计（时间序列数据）。

```sql
CREATE TABLE IF NOT EXISTS keyword_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                   -- YYYY-MM-DD
    keyword TEXT NOT NULL,                -- 关键词
    count INTEGER NOT NULL,               -- 出现次数
    platforms JSON,                       -- 出现的平台列表
    rank INTEGER,                         -- 当日排名
    
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

---

## 记忆系统设计

### 记忆类型详解

#### 1. daily_summary（日摘要）

**目的**：提炼当天的核心信息

**生成时机**：每天 23:00

**输入数据**：
- 当天所有 AI 分析结果
- 当天关键词统计

**输出内容**：
```markdown
## 2026-04-25 日摘要

### 核心热点
- DeepSeek V4 预览版发布，全网热议（知乎/微博/B站 跨平台共振）
- A股震荡，市场情绪谨慎

### 舆论风向
- 对 DeepSeek：技术乐观派 vs 商业化质疑派
- 对 A股：散户恐慌 vs 机构观望

### 异动与弱信号
- B站首次出现大量经济话题讨论（往常集中在娱乐/科技）

### 关键词热度 Top 5
1. DeepSeek (67条)
2. 美股 (32条)
3. A股 (28条)
...
```

**metadata**：
```json
{
  "date": "2026-04-25",
  "keywords": ["DeepSeek", "美股", "A股"],
  "platforms": ["微博", "知乎", "B站"],
  "source_analyses": [45, 46],
  "analysis_count": 2
}
```

#### 2. weekly_digest（周提炼）

**目的**：从 7 份日摘要中提取趋势和模式

**生成时机**：每周日 23:30

**输入数据**：
- 过去 7 天的 daily_summary
- 过去 7 天的关键词趋势

**输出内容**：
```markdown
## 2026-04-19 至 2026-04-25 周提炼

### 宏观趋势
- DeepSeek 热度从周一的技术圈讨论，演变为周五的全民话题
- A股情绪从周初的乐观转为周末的谨慎

### 平台温差
- 微博：情绪化讨论为主
- 知乎：深度分析增多
- B站：周四开始出现经济话题破圈

### 关键词演变
- DeepSeek：周初 15条/天 → 周末 67条/天（4.5倍增长）
- 美股：稳定在 30-35条/天

### 识别的模式
- 技术突破新闻的破圈路径：知乎(技术讨论) → 微博(情绪发酵) → B站/抖音(视觉传播)
```

**metadata**：
```json
{
  "date_range": ["2026-04-19", "2026-04-25"],
  "keywords": ["DeepSeek", "美股", "A股"],
  "source_summaries": [
    "daily_20260419",
    "daily_20260420",
    ...
  ]
}
```

#### 3. topic_insight（主题洞察）

**目的**：某个主题的长期演变分析

**生成时机**：Agent 发现模式时，或手动触发

**示例**：
```markdown
## DeepSeek 舆论演变洞察

### 核心发现
DeepSeek 从 3月初的"技术圈热点"演变为 4月的"全民话题"，跨平台共振显著。

### 时间线
- 2026-03-15: 知乎技术讨论开始升温（日均 5-10条）
- 2026-04-01: 微博开始出现大众讨论（日均 15条）
- 2026-04-20: B站/抖音破圈，视觉化传播爆发（日均 50+条）

### Why（为什么）
V4 预览版发布 + 性能碾压 Sonnet 4.5 → 媒体大量报道 → 民族情绪共振

### How to apply（如何应用）
当 Agent 查询"DeepSeek 舆论趋势"时，返回此洞察。
预测：类似的国产AI突破会引发相同的"技术圈→大众圈"破圈路径。
```

#### 4. pattern（模式识别）

**目的**：识别可复用的规律

**示例**：
```markdown
## 美联储加息前的舆论信号

### 模式描述
在美联储宣布加息的前 1-2 周，舆论会出现以下特征信号。

### 信号特征
1. 雪球平台"美债收益率"话题热度异常升高（+50%以上）
2. 微博情绪从"乐观"转为"谨慎观望"
3. 知乎出现"如何应对加息"类问题

### 历史验证
- 2025-12-15 加息前：符合（准确）
- 2026-03-20 加息前：符合（准确）
- 2026-04-10 加息前：符合（准确）

### How to apply
当检测到上述信号组合时，提醒用户"可能即将加息"。
```

#### 5. signal（弱信号）

**目的**：捕捉早期预警信号

**示例**：
```markdown
## B站经济话题异动（2026-04-20）

### 异常描述
2026-04-20，B站首次出现大量经济话题讨论（日均从 2条 → 15条）。

### Why 重要
B站用户以年轻人为主，通常关注娱乐/科技。
经济话题在 B站破圈，说明该话题已影响到年轻群体的生活。

### 后续追踪
- 2026-04-21: 持续（18条）
- 2026-04-22: 增长（23条）
- 建议：关注是否有重大经济政策即将出台
```

### 索引文件（INSIGHTS.md）

```markdown
# TrendRadar 洞察索引

> 最后更新：2026-04-25

## 日摘要（最近7天）
- [2026-04-25](daily_20260425.md) — DeepSeek 全网热议，B站经济话题异动
- [2026-04-24](daily_20260424.md) — A股震荡，市场情绪谨慎
...

## 周提炼
- [2026-W17](weekly_2026w17.md) — DeepSeek 破圈路径，技术圈→全民话题

## 主题洞察
- [DeepSeek 舆论演变](topic_deepseek_evolution.md) — 从技术圈到全民话题的完整轨迹
- [杭州滨江房价舆论](topic_hangzhou_housing.md) — 2026年Q1房价舆论波动

## 模式识别
- [美联储加息前信号](pattern_fed_rate_hike.md) — 加息前1-2周的舆论特征（准确率100%）

## 弱信号
- [B站经济话题异动](signal_bilibili_economic.md) — 2026-04-20 首次大量经济讨论
```

---

## 数据流设计

### 数据流向图

```
┌─────────────────────────────────────────────────────────────┐
│                      TrendRadar 主流程                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    爬取新闻 (Crawler)                         │
│  - 从各平台抓取热榜新闻                                        │
│  - 返回：CrawlResults                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  关键词匹配 (Frequency)                       │
│  - 匹配 frequency_words.txt 中的关键词                       │
│  - 为每条新闻标记 matched_keywords                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              存储新闻数据 (StorageManager)                    │
│  - 保存到 YYYY-MM-DD.db                                      │
│  - news_items 表（含 matched_keywords）                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  AI 分析 (AIAnalyzer)                         │
│  - 生成 6 个板块的分析结果                                     │
│  - 返回：AIAnalysisResult                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           存储 AI 分析结果（新增功能）                          │
│  - 保存到 ai_analysis_results 表                             │
│  - 保存到 ai_analysis_sections 表                            │
│  - 更新 keyword_trends 表                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   推送通知 (Notification)                     │
│  - 发送到配置的通知渠道                                        │
└─────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│                      定时任务流程                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              每天 23:00 - 生成日摘要                          │
│  1. 从 memory.db 获取当天所有 AI 分析结果                     │
│  2. 从 keyword_trends 获取当天关键词统计                      │
│  3. 用 AI 提炼生成 daily_summary                             │
│  4. 保存到 memories 表                                        │
│  5. 更新 INSIGHTS.md 索引                                    │
└─────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│            每周日 23:30 - 生成周提炼                          │
│  1. 从 memories 获取过去 7 天的 daily_summary                │
│  2. 从 keyword_trends 获取过去 7 天的趋势                     │
│  3. 用 AI 提炼生成 weekly_digest                             │
│  4. 保存到 memories 表                                        │
│  5. 创建 memory_links（周提炼 derives_from 日摘要）          │
│  6. 更新 INSIGHTS.md 索引                                    │
└─────────────────────────────────────────────────────────────┘
```

### 核心数据结构

#### AIAnalysisResultWithMeta

扩展现有的 `AIAnalysisResult`，增加元数据。

```python
@dataclass
class AIAnalysisResultWithMeta:
    # 原有字段
    core_trends: str
    sentiment_controversy: str
    signals: str
    rss_insights: str
    outlook_strategy: str
    standalone_summaries: Dict[str, str]
    
    # 新增元数据
    analysis_time: str  # ISO 8601
    report_mode: str
    news_count: int
    rss_count: int
    matched_keywords: List[str]
    platforms: List[str]
```

#### KeywordStat

关键词统计数据。

```python
@dataclass
class KeywordStat:
    date: str  # YYYY-MM-DD
    keyword: str
    count: int
    platforms: List[str]
    rank: Optional[int] = None
```

#### Memory

记忆对象。

```python
@dataclass
class Memory:
    id: str
    type: str  # daily_summary|weekly_digest|topic_insight|pattern|signal
    title: str
    description: str
    content: str  # Markdown
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
```

---

## 自动化流程

### 1. AI 分析结果自动保存

**触发时机**：每次 AI 分析完成后

**实现位置**：`trendradar/__main__.py`

**流程**：
```python
def save_ai_analysis_result(
    storage_manager: StorageManager,
    analysis_result: AIAnalysisResult,
    metadata: dict
):
    """保存 AI 分析结果"""
    # 1. 保存到日期数据库
    db_path = storage_manager.get_today_db_path()
    conn = sqlite3.connect(db_path)
    
    # 1.1 保存完整结果
    insert_ai_analysis_result(conn, analysis_result, metadata)
    
    # 1.2 保存分板块索引
    insert_ai_analysis_sections(conn, analysis_result)
    
    # 2. 更新关键词统计（memory.db）
    update_keyword_trends(
        storage_manager.memory_db_path,
        metadata['matched_keywords'],
        metadata['platforms']
    )
    
    conn.commit()
    conn.close()
```

### 2. 日摘要自动生成

**触发时机**：每天 23:00

**实现方式**：新增定时任务

**流程**：
```python
async def generate_daily_summary(date: str):
    """生成每日摘要"""
    memory_engine = MemoryEngine()
    
    # 1. 收集当天数据
    analyses = get_today_analyses(date)
    keyword_stats = get_today_keyword_stats(date)
    
    # 2. 用 AI 提炼摘要
    summary_content = await memory_engine.generate_summary(
        analyses=analyses,
        keyword_stats=keyword_stats,
        summary_type='daily'
    )
    
    # 3. 保存到 memories 表
    memory_id = f"daily_{date.replace('-', '')}"
    save_memory(
        id=memory_id,
        type='daily_summary',
        title=f"{date} 日摘要",
        content=summary_content,
        metadata={
            'date': date,
            'source_analyses': [a.id for a in analyses],
            'keywords': extract_top_keywords(keyword_stats)
        }
    )
    
    # 4. 更新 INSIGHTS.md
    update_insights_index()
```

### 3. 周提炼自动生成

**触发时机**：每周日 23:30

**流程**：
```python
async def generate_weekly_digest(week_start: str, week_end: str):
    """生成每周提炼"""
    memory_engine = MemoryEngine()
    
    # 1. 收集过去 7 天的日摘要
    daily_summaries = get_memories_by_date_range(
        type='daily_summary',
        start=week_start,
        end=week_end
    )
    
    # 2. 收集关键词趋势
    keyword_trends = get_keyword_trends(
        start=week_start,
        end=week_end
    )
    
    # 3. 用 AI 提炼周摘要
    digest_content = await memory_engine.generate_digest(
        summaries=daily_summaries,
        trends=keyword_trends
    )
    
    # 4. 保存到 memories 表
    week_id = f"weekly_{get_iso_week(week_start)}"
    save_memory(
        id=week_id,
        type='weekly_digest',
        title=f"{week_start} 至 {week_end} 周提炼",
        content=digest_content,
        metadata={
            'date_range': [week_start, week_end],
            'source_summaries': [s.id for s in daily_summaries]
        }
    )
    
    # 5. 创建记忆关联
    for summary in daily_summaries:
        create_memory_link(
            from_memory_id=week_id,
            to_memory_id=summary.id,
            link_type='derives_from'
        )
    
    # 6. 更新 INSIGHTS.md
    update_insights_index()
```

---

## 查询接口

### MemoryQueryEngine

提供结构化的查询接口。

```python
class MemoryQueryEngine:
    """记忆查询引擎"""
    
    def __init__(self, memory_db_path: str):
        self.db_path = memory_db_path
    
    def search_memories(
        self,
        query: Optional[str] = None,
        types: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        date_range: Optional[Tuple[str, str]] = None,
        limit: int = 10
    ) -> List[Memory]:
        """
        智能检索记忆
        
        Args:
            query: 自然语言查询（可选）
            types: 记忆类型过滤
            keywords: 关键词过滤
            date_range: 日期范围过滤 (start, end)
            limit: 返回数量限制
            
        Returns:
            匹配的记忆列表
        """
        pass
    
    def get_keyword_trend(
        self,
        keyword: str,
        days: int = 30
    ) -> List[KeywordStat]:
        """
        获取关键词的热度趋势
        
        Args:
            keyword: 关键词
            days: 过去多少天
            
        Returns:
            关键词统计列表（按日期排序）
        """
        pass
    
    def get_topic_timeline(
        self,
        topic: str
    ) -> List[Memory]:
        """
        获取某主题的演变时间线
        
        Returns:
            相关记忆列表（按时间排序）
        """
        pass
    
    def find_related_memories(
        self,
        memory_id: str,
        link_types: Optional[List[str]] = None
    ) -> List[Tuple[Memory, str]]:
        """
        查找相关记忆
        
        Returns:
            (Memory, link_type) 元组列表
        """
        pass
    
    def validate_memory(
        self,
        memory_id: str,
        force: bool = False
    ) -> bool:
        """
        验证记忆是否仍然有效
        
        Args:
            memory_id: 记忆 ID
            force: 强制重新验证
            
        Returns:
            是否有效
        """
        pass
```

### 使用示例

```python
# 初始化查询引擎
query_engine = MemoryQueryEngine('output/memory.db')

# 查询：过去一周 DeepSeek 的舆论趋势
memories = query_engine.search_memories(
    query="DeepSeek 舆论趋势",
    types=['daily_summary', 'weekly_digest'],
    date_range=('2026-04-18', '2026-04-25')
)

# 查询：某关键词的热度变化
trend = query_engine.get_keyword_trend(
    keyword='DeepSeek',
    days=30
)

# 绘制趋势图
dates = [t.date for t in trend]
counts = [t.count for t in trend]
```

---

## 实施计划

### Phase 1：核心存储功能（2天）

**目标**：实现 AI 分析结果和关键词统计的持久化

**任务**：
1. 创建数据库 schema
   - `ai_analysis_results` 表
   - `ai_analysis_sections` 表
   - `news_items` 表增加 `matched_keywords` 字段
   - `memory.db` 及其表结构

2. 实现存储函数
   - `save_ai_analysis_result()`
   - `update_keyword_trends()`

3. 集成到主流程
   - 在 `__main__.py` 中调用存储函数

4. 测试验证
   - 运行一次完整流程
   - 验证数据正确存储

**交付物**：
- 数据库 schema 文件
- 存储模块代码
- 单元测试

### Phase 2：记忆生成功能（2天）

**目标**：实现日摘要和周提炼的自动生成

**任务**：
1. 创建 MemoryEngine 类
   - `generate_daily_summary()`
   - `generate_weekly_digest()`

2. 实现定时任务
   - 日摘要：每天 23:00
   - 周提炼：每周日 23:30

3. 实现 INSIGHTS.md 更新
   - `update_insights_index()`

4. 测试验证
   - 手动触发生成
   - 验证内容质量

**交付物**：
- MemoryEngine 模块
- 定时任务配置
- 生成的摘要示例

### Phase 3：查询接口（1天）

**目标**：实现基础查询 API

**任务**：
1. 实现 MemoryQueryEngine
   - `search_memories()`
   - `get_keyword_trend()`
   - `get_topic_timeline()`

2. 提供 CLI 命令
   - `python -m trendradar.memory query "查询内容"`
   - `python -m trendradar.memory trend <keyword>`

3. 文档和示例

**交付物**：
- MemoryQueryEngine 代码
- CLI 命令
- 使用文档

### Phase 4：高级功能（可选，后续迭代）

**任务**：
1. 记忆验证机制
2. 主题洞察自动提取
3. 模式自动识别
4. Markdown 洞察文档生成

---

## 未来扩展

### 1. Agent 集成

基于记忆系统构建分析 Agent：

```python
class TrendAnalysisAgent:
    """趋势分析 Agent"""
    
    def analyze_topic_evolution(self, topic: str):
        """分析某主题的演变"""
        pass
    
    def predict_trend(self, keyword: str):
        """预测关键词趋势"""
        pass
    
    def find_correlations(self, keyword1: str, keyword2: str):
        """发现关键词之间的关联"""
        pass
    
    def detect_anomalies(self):
        """检测异常信号"""
        pass
```

### 2. 数据大盘

基于历史数据构建可视化大盘：

- 关键词热度图
- 平台温差分析
- 跨平台共振识别
- 舆论情绪曲线

### 3. 向量检索

使用向量数据库增强语义搜索：

- 为每条记忆生成 embedding
- 支持语义相似度检索
- 相关记忆自动推荐

### 4. 知识图谱

构建事件-主题-关键词的知识图谱：

- 实体识别和关系抽取
- 图数据库存储（Neo4j）
- 图查询和推理

---

## 附录

### A. 数据库迁移脚本

```python
# migration_001_add_ai_analysis.py

def upgrade(conn):
    """升级数据库 schema"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_analysis_results (
            ...
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_analysis_sections (
            ...
        )
    """)
    conn.execute("""
        ALTER TABLE news_items 
        ADD COLUMN matched_keywords TEXT DEFAULT '[]'
    """)

def downgrade(conn):
    """回滚 schema"""
    conn.execute("DROP TABLE IF EXISTS ai_analysis_results")
    conn.execute("DROP TABLE IF EXISTS ai_analysis_sections")
    # matched_keywords 字段无法删除（SQLite 限制）
```

### B. 配置选项

```yaml
# config/config.yaml

memory:
  enabled: true
  
  daily_summary:
    enabled: true
    schedule: "0 23 * * *"  # 每天 23:00
    
  weekly_digest:
    enabled: true
    schedule: "30 23 * * 0"  # 每周日 23:30
    
  insights_path: "output/insights/"
  memory_db_path: "output/memory.db"
  
  retention:
    raw_data_days: -1  # -1 表示永久保留
    summaries_days: -1
```

### C. API 参考

详见 `docs/api/memory_api.md`（待补充）

---

## 总结

本设计方案提供了一个完整的数据持久化和记忆系统架构，融合了 Claude Code 的记忆系统最佳实践：

1. **类型化记忆**：5 种明确定义的记忆类型
2. **分层架构**：原始数据 → 日摘要 → 周提炼 → 洞察
3. **智能检索**：结构化查询接口
4. **永久保留**：所有数据作为长期资产
5. **可扩展性**：为未来 Agent 和数据大盘打好基础

通过分 3 个 Phase 实施，可以在 5 天内完成核心功能，并为后续扩展预留充分的空间。
