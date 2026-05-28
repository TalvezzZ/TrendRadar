# Phase 2: 热点-价格关联分析设计文档

> 📅 设计日期：2026-04-30  
> 🎯 实施时机：数据积累 5-7 天后  
> 📊 数据需求：至少 5 个关联事件才显示规律

---

## 一、功能概述

### 1.1 核心目标

分析"热点新闻出现"与"股价变化"的历史关联模式，回答：
- ✅ 某个热点出现时，相关标的通常如何反应？
- ✅ 该热点的历史平均涨跌幅是多少？
- ✅ 这次的反应是否符合历史规律？
- ✅ 新闻情绪（正面/负面）与价格变化的关系

### 1.2 价值主张

- **用户价值**：了解热点与价格的因果关系，辅助投资决策
- **数据价值**：建立热点知识图谱，为 Phase 4 提供基础
- **AI 价值**：训练情绪分析能力，提升预测准确度

---

## 二、数据库设计

### 2.1 热点-价格关联事件表

```sql
-- 记录每次"热点出现 + 价格变化"的事件
CREATE TABLE IF NOT EXISTS hotspot_price_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                      -- 事件日期 YYYY-MM-DD
    keyword TEXT NOT NULL,                   -- 热点关键词
    symbol TEXT NOT NULL,                    -- 标的代码
    
    -- 新闻维度
    news_count INTEGER DEFAULT 1,            -- 当天相关新闻数
    news_titles TEXT,                        -- JSON 数组，新闻标题列表（最多10条）
    sentiment TEXT,                          -- 情绪：positive/negative/neutral
    sentiment_score REAL,                    -- 情绪分数 -1 到 +1
    
    -- 价格维度
    price_before REAL,                       -- 前一日收盘价
    price_after REAL,                        -- 当日收盘价
    change_pct REAL,                         -- 当日涨跌幅
    volume REAL,                             -- 成交量/额
    volume_ratio REAL,                       -- 成交量相对20日均量的倍数
    
    -- 元数据
    created_at TEXT NOT NULL,
    
    UNIQUE(date, keyword, symbol)
);

CREATE INDEX IF NOT EXISTS idx_hpe_keyword ON hotspot_price_events(keyword);
CREATE INDEX IF NOT EXISTS idx_hpe_symbol ON hotspot_price_events(symbol);
CREATE INDEX IF NOT EXISTS idx_hpe_date ON hotspot_price_events(date);
CREATE INDEX IF NOT EXISTS idx_hpe_kw_sym ON hotspot_price_events(keyword, symbol);
```

### 2.2 关联模式统计表

```sql
-- 聚合统计的关联规律
CREATE TABLE IF NOT EXISTS correlation_patterns (
    keyword TEXT NOT NULL,
    symbol TEXT NOT NULL,
    
    -- 统计指标
    event_count INTEGER DEFAULT 0,           -- 历史事件总次数
    
    -- 价格统计
    avg_change_pct REAL DEFAULT 0,           -- 平均涨跌幅
    median_change_pct REAL DEFAULT 0,        -- 中位数涨跌幅
    std_change_pct REAL DEFAULT 0,           -- 涨跌幅标准差
    rising_count INTEGER DEFAULT 0,          -- 上涨次数
    falling_count INTEGER DEFAULT 0,         -- 下跌次数
    rising_probability REAL DEFAULT 0,       -- 上涨概率
    
    -- 极值
    max_change_pct REAL DEFAULT 0,           -- 最大涨幅
    max_change_date TEXT,                    -- 最大涨幅日期
    min_change_pct REAL DEFAULT 0,           -- 最大跌幅
    min_change_date TEXT,                    -- 最大跌幅日期
    
    -- 情绪统计
    positive_count INTEGER DEFAULT 0,        -- 正面情绪次数
    negative_count INTEGER DEFAULT 0,        -- 负面情绪次数
    neutral_count INTEGER DEFAULT 0,         -- 中性情绪次数
    
    -- 情绪-价格关联
    positive_avg_change REAL,                -- 正面情绪下的平均涨幅
    negative_avg_change REAL,                -- 负面情绪下的平均涨幅
    
    -- 元数据
    first_event_date TEXT,                   -- 首次事件日期
    last_event_date TEXT,                    -- 最新事件日期
    last_updated TEXT,
    
    PRIMARY KEY (keyword, symbol)
);

CREATE INDEX IF NOT EXISTS idx_cp_keyword ON correlation_patterns(keyword);
CREATE INDEX IF NOT EXISTS idx_cp_event_count ON correlation_patterns(event_count);
```

---

## 三、核心模块设计

### 3.1 文件结构

```
trendradar/finance/
├── __init__.py
├── correlation.py          # 关联分析器（新增）
├── enhancer.py            # 金融增强器（扩展）
├── mapper.py              # 映射管理器
├── market.py              # 市场数据获取
└── tracker.py             # 数据跟踪器
```

### 3.2 关联分析器 (correlation.py)

```python
"""
热点-价格关联分析模块

功能：
1. 记录每次热点出现时的价格变化
2. 分析历史关联模式
3. 生成关联洞察
4. AI 情绪分析（可选）
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class CorrelationAnalyzer:
    """关联分析器"""
    
    def __init__(self, data_dir: str = "output", use_ai: bool = False):
        """
        初始化
        
        Args:
            data_dir: 数据目录
            use_ai: 是否使用 AI 分析情绪
        """
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "memory.db"
        self.use_ai = use_ai
        self.ai_client = None
        
        if use_ai:
            self._init_ai_client()
    
    def _init_ai_client(self):
        """初始化 AI 客户端（复用现有配置）"""
        try:
            from trendradar.ai.client import get_ai_client
            self.ai_client = get_ai_client()
        except Exception as e:
            print(f"[关联分析] AI 初始化失败: {e}")
            self.use_ai = False
    
    def record_event(
        self,
        date: str,
        keyword: str,
        symbol: str,
        symbol_data: Dict,
        news_titles: List[str] = None
    ) -> bool:
        """
        记录热点-价格关联事件
        
        Args:
            date: 日期 YYYY-MM-DD
            keyword: 热点关键词
            symbol: 标的代码
            symbol_data: 标的数据（包含价格、涨跌幅、成交量等）
            news_titles: 相关新闻标题列表
        
        Returns:
            是否记录成功
        """
        if not self.db_path.exists():
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 分析情绪
            sentiment = "neutral"
            sentiment_score = 0.0
            
            if news_titles and self.use_ai:
                sentiment, sentiment_score = self.analyze_sentiment(keyword, news_titles)
            
            # 插入事件记录
            cursor.execute(
                """
                INSERT OR REPLACE INTO hotspot_price_events
                (date, keyword, symbol, news_count, news_titles, sentiment, sentiment_score,
                 price_after, change_pct, volume, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    date,
                    keyword,
                    symbol,
                    len(news_titles) if news_titles else 1,
                    json.dumps(news_titles[:10] if news_titles else [], ensure_ascii=False),
                    sentiment,
                    sentiment_score,
                    symbol_data.get("current_price"),
                    symbol_data.get("change_pct"),
                    symbol_data.get("volume"),
                    datetime.now().isoformat()
                )
            )
            
            conn.commit()
            
            # 更新统计模式
            self.update_pattern(keyword, symbol)
            
            return True
            
        except Exception as e:
            print(f"[关联分析] 记录事件失败: {e}")
            return False
        finally:
            conn.close()
    
    def analyze_sentiment(self, keyword: str, news_titles: List[str]) -> tuple[str, float]:
        """
        使用 AI 分析新闻情绪
        
        Args:
            keyword: 热点关键词
            news_titles: 新闻标题列表
        
        Returns:
            (sentiment, score) - 情绪类型和分数
        """
        if not self.ai_client:
            return "neutral", 0.0
        
        try:
            prompt = f"""分析以下关于"{keyword}"的新闻标题的整体情绪倾向。

新闻标题：
{chr(10).join(f"{i+1}. {title}" for i, title in enumerate(news_titles[:10]))}

请按以下格式回答：
情绪类型：positive（正面）、negative（负面）或 neutral（中性）
情绪分数：-1.0（极度负面）到 +1.0（极度正面）

示例输出：
positive
0.65"""
            
            response = self.ai_client.complete(prompt, max_tokens=50)
            lines = response.strip().split("\n")
            
            sentiment = lines[0].strip().lower()
            score = float(lines[1].strip()) if len(lines) > 1 else 0.0
            
            # 验证
            if sentiment not in ["positive", "negative", "neutral"]:
                sentiment = "neutral"
            score = max(-1.0, min(1.0, score))
            
            return sentiment, score
            
        except Exception as e:
            print(f"[关联分析] 情绪分析失败: {e}")
            return "neutral", 0.0
    
    def update_pattern(self, keyword: str, symbol: str) -> None:
        """
        更新关联模式统计
        
        Args:
            keyword: 关键词
            symbol: 标的代码
        """
        if not self.db_path.exists():
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查询所有事件
            cursor.execute(
                """
                SELECT change_pct, sentiment, date
                FROM hotspot_price_events
                WHERE keyword = ? AND symbol = ?
                ORDER BY date ASC
                """,
                (keyword, symbol)
            )
            
            events = cursor.fetchall()
            
            if not events:
                return
            
            # 计算统计指标
            changes = [e[0] for e in events if e[0] is not None]
            
            if not changes:
                return
            
            import statistics
            
            event_count = len(changes)
            avg_change = statistics.mean(changes)
            median_change = statistics.median(changes)
            std_change = statistics.stdev(changes) if len(changes) > 1 else 0
            rising_count = sum(1 for c in changes if c > 0)
            falling_count = sum(1 for c in changes if c < 0)
            rising_probability = rising_count / event_count if event_count > 0 else 0
            
            max_change = max(changes)
            min_change = min(changes)
            max_idx = changes.index(max_change)
            min_idx = changes.index(min_change)
            max_date = events[max_idx][2]
            min_date = events[min_idx][2]
            
            # 情绪统计
            positive_count = sum(1 for e in events if e[1] == "positive")
            negative_count = sum(1 for e in events if e[1] == "negative")
            neutral_count = sum(1 for e in events if e[1] == "neutral")
            
            positive_changes = [e[0] for e in events if e[1] == "positive" and e[0] is not None]
            negative_changes = [e[0] for e in events if e[1] == "negative" and e[0] is not None]
            
            positive_avg = statistics.mean(positive_changes) if positive_changes else None
            negative_avg = statistics.mean(negative_changes) if negative_changes else None
            
            # 插入或更新
            cursor.execute(
                """
                INSERT OR REPLACE INTO correlation_patterns
                (keyword, symbol, event_count, avg_change_pct, median_change_pct, std_change_pct,
                 rising_count, falling_count, rising_probability,
                 max_change_pct, max_change_date, min_change_pct, min_change_date,
                 positive_count, negative_count, neutral_count,
                 positive_avg_change, negative_avg_change,
                 first_event_date, last_event_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    keyword, symbol, event_count, avg_change, median_change, std_change,
                    rising_count, falling_count, rising_probability,
                    max_change, max_date, min_change, min_date,
                    positive_count, negative_count, neutral_count,
                    positive_avg, negative_avg,
                    events[0][2], events[-1][2], datetime.now().isoformat()
                )
            )
            
            conn.commit()
            
        except Exception as e:
            print(f"[关联分析] 更新模式失败: {e}")
        finally:
            conn.close()
    
    def get_pattern(self, keyword: str, symbol: str) -> Optional[Dict]:
        """
        获取关联模式
        
        Args:
            keyword: 关键词
            symbol: 标的代码
        
        Returns:
            关联模式数据，如果不存在返回 None
        """
        if not self.db_path.exists():
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT event_count, avg_change_pct, median_change_pct, rising_probability,
                       max_change_pct, min_change_pct,
                       positive_count, negative_count,
                       positive_avg_change, negative_avg_change
                FROM correlation_patterns
                WHERE keyword = ? AND symbol = ?
                """,
                (keyword, symbol)
            )
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                "event_count": row[0],
                "avg_change_pct": row[1],
                "median_change_pct": row[2],
                "rising_probability": row[3],
                "max_change_pct": row[4],
                "min_change_pct": row[5],
                "positive_count": row[6],
                "negative_count": row[7],
                "positive_avg_change": row[8],
                "negative_avg_change": row[9]
            }
            
        finally:
            conn.close()
    
    def generate_insight(
        self,
        keyword: str,
        symbol: str,
        current_change_pct: float,
        min_events: int = 5
    ) -> Optional[str]:
        """
        生成关联洞察
        
        Args:
            keyword: 关键词
            symbol: 标的代码
            current_change_pct: 当前涨跌幅
            min_events: 最少事件数（少于此数不生成洞察）
        
        Returns:
            洞察文本，如果数据不足返回 None
        """
        pattern = self.get_pattern(keyword, symbol)
        
        if not pattern or pattern["event_count"] < min_events:
            return None
        
        insights = []
        
        # 1. 历史规律
        event_count = pattern["event_count"]
        rising_prob = pattern["rising_probability"]
        
        if rising_prob > 0.7:
            rising_times = int(event_count * rising_prob)
            insights.append(f"历史上该热点通常利好（{event_count}次中{rising_times}次上涨）")
        elif rising_prob < 0.3:
            falling_times = int(event_count * (1 - rising_prob))
            insights.append(f"历史上该热点通常利空（{event_count}次中{falling_times}次下跌）")
        else:
            insights.append(f"历史上该热点影响不确定（{event_count}次事件）")
        
        # 2. 当前表现对比
        avg_change = pattern["avg_change_pct"]
        
        if abs(current_change_pct - avg_change) > 2:
            if current_change_pct > avg_change:
                insights.append(f"本次反应强于历史平均（{current_change_pct:+.1f}% vs 平均{avg_change:+.1f}%）")
            else:
                insights.append(f"本次反应弱于历史平均（{current_change_pct:+.1f}% vs 平均{avg_change:+.1f}%）")
        else:
            insights.append(f"本次反应符合历史平均（{current_change_pct:+.1f}% vs 平均{avg_change:+.1f}%）")
        
        # 3. 情绪关联（如果有足够数据）
        if pattern["positive_count"] >= 3 and pattern["negative_count"] >= 3:
            pos_avg = pattern["positive_avg_change"]
            neg_avg = pattern["negative_avg_change"]
            
            if pos_avg and neg_avg and abs(pos_avg - neg_avg) > 2:
                insights.append(f"情绪影响明显：正面新闻平均{pos_avg:+.1f}%，负面新闻平均{neg_avg:+.1f}%")
        
        return "；".join(insights) if insights else None
```

---

## 四、集成方案

### 4.1 扩展 FinanceEnhancer

在 `trendradar/finance/enhancer.py` 中添加：

```python
class FinanceEnhancer:
    def __init__(self, data_dir: str = "output", config: Dict = None):
        # ... 现有代码 ...
        
        # Phase 2: 关联分析器
        correlation_config = config.get("correlation_analysis", {})
        if correlation_config.get("enabled", False):
            from .correlation import CorrelationAnalyzer
            self.correlation_analyzer = CorrelationAnalyzer(
                data_dir=data_dir,
                use_ai=correlation_config.get("use_ai_sentiment", False)
            )
        else:
            self.correlation_analyzer = None
    
    def _fetch_finance_data(self, keyword: str) -> Optional[Dict]:
        # ... 现有获取数据代码 ...
        
        # 收集新闻标题（用于情绪分析）
        news_titles = self._collect_news_titles(keyword)
        
        for symbol_data in result_symbols:
            # === Phase 2: 记录关联事件 ===
            if self.correlation_analyzer:
                today = datetime.now().strftime("%Y-%m-%d")
                self.correlation_analyzer.record_event(
                    date=today,
                    keyword=keyword,
                    symbol=symbol_data["symbol"],
                    symbol_data=symbol_data,
                    news_titles=news_titles
                )
                
                # 生成关联洞察
                min_events = self.config.get("correlation_analysis", {}).get("min_events_for_pattern", 5)
                insight = self.correlation_analyzer.generate_insight(
                    keyword=keyword,
                    symbol=symbol_data["symbol"],
                    current_change_pct=symbol_data["change_pct"],
                    min_events=min_events
                )
                
                if insight:
                    symbol_data["correlation_insight"] = insight
        
        return {"keyword": keyword, "symbols": result_symbols}
    
    def _collect_news_titles(self, keyword: str) -> List[str]:
        """收集当前关键词相关的新闻标题"""
        # TODO: 从当前推送的新闻中提取标题
        # 可以从 matched_news 或其他来源获取
        return []
```

### 4.2 修改推送格式

在 `format_enhanced_notification()` 中添加关联洞察显示：

```python
def format_enhanced_notification(self, original_content: str, finance_data: Dict) -> str:
    # ... 现有代码 ...
    
    for symbol in kw_data["symbols"]:
        # ... 基本信息 ...
        
        # 关联洞察（Phase 2）
        if symbol.get("correlation_insight"):
            sections.append(f"  🧬 关联洞察：")
            sections.append(f"  {symbol['correlation_insight']}")
        
        sections.append("")
```

---

## 五、配置规范

### 5.1 配置文件

```yaml
# config/config.yaml

finance:
  enabled: true
  
  # Phase 2: 关联分析
  correlation_analysis:
    enabled: false                     # 初期设为 false，积累数据
    min_events_for_pattern: 5          # 至少 N 次事件才显示规律
    use_ai_sentiment: true             # 是否使用 AI 分析情绪（可选）
```

### 5.2 启用时机

**自动检查数据就绪度**：

```python
# 在 FinanceEnhancer.__init__ 中添加

def _check_data_readiness(self) -> Dict:
    """检查数据积累情况"""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    # 检查最早和最新的数据日期
    cursor.execute("""
        SELECT MIN(date), MAX(date), COUNT(DISTINCT date)
        FROM finance_tracking
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return {"days_count": 0, "first_date": None, "last_date": None}
    
    return {
        "days_count": row[2],
        "first_date": row[0],
        "last_date": row[1]
    }

# 启用检查
if correlation_config.get("enabled"):
    readiness = self._check_data_readiness()
    
    if readiness["days_count"] < 5:
        print(f"[金融] ℹ️  关联分析需要至少5天数据，当前已积累 {readiness['days_count']} 天")
        self.correlation_analyzer = None
    else:
        print(f"[金融] ✅ 关联分析已启用（已积累 {readiness['days_count']} 天数据）")
```

---

## 六、数据积累策略

### 6.1 无声积累模式

**第1-5天**：只记录事件，不显示洞察

```python
# correlation_analysis.enabled = false
# 但在代码中仍然调用 record_event()

if self.config.get("FINANCE", {}).get("enabled"):
    # 即使未启用 correlation_analysis，也记录事件
    correlation_analyzer = CorrelationAnalyzer(data_dir)
    correlation_analyzer.record_event(...)  # 无声积累
```

**第6天起**：启用显示

```yaml
correlation_analysis:
  enabled: true  # 改为 true
```

### 6.2 数据质量监控

添加监控命令：

```bash
# 查看数据积累情况
uv run python -m trendradar --finance-stats

# 输出示例：
# 金融数据统计
# ━━━━━━━━━━━━━━━━━━
# 数据积累天数：7 天
# 首次记录：2026-04-23
# 最新记录：2026-04-30
# 
# 事件统计：
# - 总事件数：45
# - 关键词数：8
# - 标的数：15
# 
# 关联模式：
# - 已建立规律：3 个（事件数 ≥ 5）
# - 待积累：12 个（事件数 < 5）
# 
# 建议：再积累 2-3 天可启用关联分析
```

---

## 七、测试计划

### 7.1 单元测试

```python
# tests/finance/test_correlation.py

def test_record_event():
    """测试事件记录"""
    analyzer = CorrelationAnalyzer(data_dir="test_output")
    
    result = analyzer.record_event(
        date="2026-04-30",
        keyword="新能源",
        symbol="300750",
        symbol_data={"current_price": 245.6, "change_pct": 3.2, "volume": 85600000000},
        news_titles=["宁德时代发布新电池技术", "新能源车销量创新高"]
    )
    
    assert result == True

def test_update_pattern():
    """测试模式更新"""
    # ... 测试聚合统计逻辑 ...

def test_generate_insight():
    """测试洞察生成"""
    # ... 测试不同场景下的洞察文本 ...
```

### 7.2 集成测试

```python
# tests/finance/test_correlation_integration.py

def test_end_to_end():
    """测试端到端流程"""
    # 1. 启用关联分析
    # 2. 运行爬虫
    # 3. 检查事件是否记录
    # 4. 检查模式是否更新
    # 5. 检查推送中是否包含洞察
```

---

## 八、实施检查清单

### 准备阶段
- [ ] 阅读本设计文档
- [ ] 确认 Phase 1 运行稳定
- [ ] 检查数据积累情况（至少5天）

### 开发阶段
- [ ] 添加数据库表（hotspot_price_events, correlation_patterns）
- [ ] 实现 CorrelationAnalyzer 类
- [ ] 扩展 FinanceEnhancer 集成关联分析
- [ ] 添加推送格式化逻辑
- [ ] 实现数据就绪度检查
- [ ] 编写单元测试
- [ ] 编写集成测试

### 测试阶段
- [ ] 本地测试：记录事件
- [ ] 本地测试：更新模式
- [ ] 本地测试：生成洞察
- [ ] 端到端测试：完整流程
- [ ] AI 情绪分析测试（可选）

### 部署阶段
- [ ] 更新 config.yaml 添加配置项
- [ ] 部署到生产环境
- [ ] 观察前3天数据积累
- [ ] 第4-5天启用显示
- [ ] 收集用户反馈

### 优化阶段
- [ ] 调整 min_events_for_pattern 阈值
- [ ] 优化洞察文本表达
- [ ] 评估 AI 情绪分析准确度
- [ ] 准备 Phase 3 设计

---

## 九、常见问题

### Q1: 数据积累不足怎么办？
**A**: 初期显示"数据积累中，N 天后可用"提示，用户无需操作。

### Q2: AI 情绪分析是否必需？
**A**: 非必需，without AI 也能提供基础的关联分析。AI 主要增强情绪维度。

### Q3: 如何验证关联规律的准确性？
**A**: Phase 4 会实现回测功能，评估历史规律的预测准确度。

### Q4: 如果某个关键词事件数始终 < 5 怎么办？
**A**: 不显示洞察，或者降低 min_events_for_pattern 阈值到 3。

---

## 十、后续展望

Phase 2 完成后，将为 Phase 3 和 Phase 4 提供：
- ✅ 丰富的历史事件数据
- ✅ 统计基线（用于异常检测）
- ✅ 情绪标签（用于 AI 训练）
- ✅ 关联规律（用于投资建议）

**预计时间线**：
- Week 1-2: 数据积累
- Week 3: 实施开发
- Week 4: 测试和优化
- Week 5: 准备 Phase 3

---

**文档版本**: v1.0  
**最后更新**: 2026-04-30  
**负责人**: AI Assistant  
**状态**: 待实施
