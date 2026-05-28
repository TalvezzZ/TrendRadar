# Phase 4: 投资建议设计文档

## 概述

**功能定位**：基于历史关联模式和异常检测数据，提供智能投资建议和风险评估。

**核心价值**：
- 数据驱动的投资决策支持
- 基于历史模式的概率预测
- 风险收益量化评估
- 投资组合优化建议

**依赖关系**：
- **必需**：Phase 1（基础数据）+ Phase 2（关联分析）
- **增强**：Phase 3（异常检测，可选）
- **定位**：Phase 4 是整个系统的"智能大脑"

---

## 设计原则

### 1. 概率思维，而非确定性预测

**不承诺收益，只提供概率和风险分析**

```
❌ 错误："宁德时代将上涨 10%，建议买入"
✅ 正确："历史上'新能源'热点出现时，宁德时代有 65% 概率上涨，
         平均涨幅 3.2%，但存在 35% 下跌风险（平均 -1.8%）"
```

### 2. 数据充分性检验

建议质量取决于数据质量：
- **最低样本要求**：至少 20 次历史关联事件
- **置信度标注**：样本数越多，置信度越高
- **数据新鲜度**：优先使用近 6 个月数据

### 3. 风险优先

所有建议必须包含风险评估：
- 最大回撤（历史最差表现）
- 失败概率（下跌概率）
- 止损建议（基于历史波动率）

### 4. 多维度综合评分

单一因素不足以决策，需要综合：
- **关联强度**（Phase 2 数据）：热点-价格的历史相关性
- **情绪分数**（Phase 2 数据）：当前新闻情绪
- **异常检测**（Phase 3 数据）：是否存在异常信号
- **市场环境**：大盘趋势、板块轮动
- **估值水平**：PE、PB 等基本面指标（可选）

### 5. 组合思维

推荐投资组合而非单一标的：
- 分散风险：不同行业、不同市场
- 关联组合：热点 + 相关标的组合
- 动态调整：根据新数据更新建议

---

## 数据库设计

### 4.1 投资建议表

```sql
-- 投资建议表（记录每次生成的建议）
CREATE TABLE IF NOT EXISTS investment_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    trigger_type TEXT NOT NULL,           -- keyword | anomaly | manual
    trigger_value TEXT NOT NULL,          -- 触发值（如关键词、标的代码）
    
    -- 建议内容
    symbol TEXT NOT NULL,
    symbol_type TEXT NOT NULL,
    market TEXT NOT NULL,
    name TEXT NOT NULL,
    
    action TEXT NOT NULL,                 -- buy | sell | hold | watch
    confidence REAL NOT NULL,             -- 置信度 0-1
    
    -- 预期收益风险
    expected_return REAL,                 -- 预期收益率（%）
    win_probability REAL,                 -- 盈利概率（%）
    max_drawdown REAL,                    -- 最大回撤（%）
    suggested_stop_loss REAL,             -- 建议止损点（%）
    
    -- 时间窗口
    holding_period TEXT DEFAULT '7-14d',  -- 建议持仓周期
    valid_until TEXT,                     -- 建议有效期
    
    -- 依据数据
    correlation_score REAL,               -- 关联分数（来自 Phase 2）
    sentiment_score REAL,                 -- 情绪分数（来自 Phase 2）
    anomaly_score REAL,                   -- 异常分数（来自 Phase 3）
    sample_count INTEGER,                 -- 历史样本数
    
    -- 建议理由
    reason TEXT,                          -- 建议理由（JSON）
    risk_warning TEXT,                    -- 风险提示
    
    -- 执行跟踪
    is_executed INTEGER DEFAULT 0,        -- 是否被用户采纳
    executed_price REAL,                  -- 执行价格
    executed_at TEXT,
    
    created_at TEXT NOT NULL,
    
    UNIQUE(date, trigger_type, trigger_value, symbol)
);

CREATE INDEX IF NOT EXISTS idx_investment_recommendations_date
    ON investment_recommendations(date);
CREATE INDEX IF NOT EXISTS idx_investment_recommendations_symbol
    ON investment_recommendations(symbol);
CREATE INDEX IF NOT EXISTS idx_investment_recommendations_action
    ON investment_recommendations(action);
```

### 4.2 建议跟踪表

```sql
-- 建议跟踪表（跟踪建议的实际表现）
CREATE TABLE IF NOT EXISTS recommendation_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id INTEGER NOT NULL,
    
    -- 执行信息
    entry_date TEXT NOT NULL,             -- 入场日期
    entry_price REAL NOT NULL,            -- 入场价格
    exit_date TEXT,                       -- 出场日期
    exit_price REAL,                      -- 出场价格
    
    -- 收益计算
    actual_return REAL,                   -- 实际收益率（%）
    holding_days INTEGER,                 -- 实际持仓天数
    max_gain REAL,                        -- 期间最高收益（%）
    max_loss REAL,                        -- 期间最大亏损（%）
    
    -- 表现评估
    is_successful INTEGER,                -- 是否成功（1=盈利，0=亏损）
    hit_stop_loss INTEGER DEFAULT 0,      -- 是否触发止损
    
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    
    FOREIGN KEY (recommendation_id) REFERENCES investment_recommendations(id)
);

CREATE INDEX IF NOT EXISTS idx_recommendation_tracking_recommendation
    ON recommendation_tracking(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_tracking_dates
    ON recommendation_tracking(entry_date, exit_date);
```

### 4.3 策略表现表

```sql
-- 策略表现表（统计不同策略的历史胜率）
CREATE TABLE IF NOT EXISTS strategy_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,          -- 策略名称
    strategy_params TEXT,                 -- 策略参数（JSON）
    
    -- 统计周期
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    
    -- 表现指标
    total_recommendations INTEGER DEFAULT 0,
    executed_recommendations INTEGER DEFAULT 0,
    successful_trades INTEGER DEFAULT 0,
    failed_trades INTEGER DEFAULT 0,
    
    win_rate REAL,                        -- 胜率（%）
    avg_return REAL,                      -- 平均收益率（%）
    avg_holding_days REAL,                -- 平均持仓天数
    max_consecutive_wins INTEGER,         -- 最大连胜
    max_consecutive_losses INTEGER,       -- 最大连亏
    
    -- 风险指标
    sharpe_ratio REAL,                    -- 夏普比率
    max_drawdown REAL,                    -- 最大回撤
    
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    
    UNIQUE(strategy_name, period_start, period_end)
);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_name
    ON strategy_performance(strategy_name);
```

---

## 模块设计

### 架构图

```
InvestmentAdvisor (主入口)
├── DataAggregator (数据聚合器)
│   ├── get_correlation_data()      # Phase 2 数据
│   ├── get_anomaly_data()          # Phase 3 数据
│   ├── get_market_context()        # 市场环境
│   └── aggregate_signals()         # 信号聚合
│
├── SignalEvaluator (信号评估器)
│   ├── evaluate_correlation()      # 评估关联强度
│   ├── evaluate_sentiment()        # 评估情绪分数
│   ├── evaluate_anomaly()          # 评估异常信号
│   ├── calculate_confidence()      # 计算置信度
│   └── check_data_sufficiency()    # 检查数据充分性
│
├── RiskCalculator (风险计算器)
│   ├── calculate_expected_return() # 计算预期收益
│   ├── calculate_win_probability() # 计算盈利概率
│   ├── calculate_max_drawdown()    # 计算最大回撤
│   ├── suggest_stop_loss()         # 建议止损点
│   └── assess_risk_level()         # 风险等级评估
│
├── RecommendationGenerator (建议生成器)
│   ├── generate_recommendation()   # 生成单一建议
│   ├── generate_portfolio()        # 生成组合建议
│   ├── format_recommendation()     # 格式化建议
│   └── add_disclaimer()            # 添加免责声明
│
└── PerformanceTracker (表现跟踪器)
    ├── track_recommendation()      # 跟踪建议执行
    ├── update_performance()        # 更新表现数据
    ├── calculate_strategy_metrics() # 计算策略指标
    └── generate_report()           # 生成表现报告
```

---

## 核心实现

### 文件：`trendradar/finance/advisor.py`

```python
"""
投资建议模块

职责：
1. 聚合多源数据（关联、异常、市场环境）
2. 综合评估信号强度和置信度
3. 计算风险收益指标
4. 生成投资建议和组合
5. 跟踪建议表现
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import math


class DataAggregator:
    """数据聚合器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_correlation_data(self, keyword: str, symbol: str) -> Optional[Dict]:
        """获取关联分析数据（Phase 2）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT win_rate, avg_price_change, total_events,
                   positive_events, negative_events, avg_sentiment
            FROM correlation_patterns
            WHERE keyword = ? AND symbol = ?
        """, (keyword, symbol))
        
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        return {
            'win_rate': row[0],
            'avg_price_change': row[1],
            'total_events': row[2],
            'positive_events': row[3],
            'negative_events': row[4],
            'avg_sentiment': row[5]
        }
    
    def get_anomaly_data(self, symbol: str, days: int = 7) -> List[Dict]:
        """获取异常检测数据（Phase 3）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT date, anomaly_type, severity, direction, 
                   change_pct, volume_ratio, z_score
            FROM anomaly_events
            WHERE symbol = ? AND date >= date('now', '-' || ? || ' days')
            ORDER BY date DESC
        """, (symbol, days))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'date': row[0],
                'anomaly_type': row[1],
                'severity': row[2],
                'direction': row[3],
                'change_pct': row[4],
                'volume_ratio': row[5],
                'z_score': row[6]
            }
            for row in rows
        ]
    
    def get_market_context(self) -> Dict:
        """获取市场环境（可选功能）"""
        # TODO: 集成大盘指数数据（沪深300、上证指数等）
        # 简化版：返回默认中性环境
        return {
            'market_trend': 'neutral',    # bullish | bearish | neutral
            'volatility': 'medium'        # low | medium | high
        }
    
    def aggregate_signals(
        self,
        keyword: str,
        symbol: str,
        symbol_data: Dict
    ) -> Dict:
        """聚合所有信号"""
        correlation = self.get_correlation_data(keyword, symbol)
        anomalies = self.get_anomaly_data(symbol, days=7)
        market = self.get_market_context()
        
        return {
            'correlation': correlation,
            'anomalies': anomalies,
            'market': market,
            'current_data': symbol_data
        }


class SignalEvaluator:
    """信号评估器"""
    
    def evaluate_correlation(self, correlation: Dict) -> Tuple[float, str]:
        """
        评估关联强度
        
        Returns:
            (分数 0-1, 评级文本)
        """
        if correlation is None:
            return 0.0, '无数据'
        
        # 综合考虑胜率和样本量
        win_rate = correlation['win_rate']
        sample_count = correlation['total_events']
        
        # 样本量权重（样本越多，权重越高）
        sample_weight = min(sample_count / 50, 1.0)  # 50 个样本视为充分
        
        # 胜率归一化（50% 为中性）
        win_rate_normalized = (win_rate - 50) / 50  # [-1, 1]
        
        # 综合分数
        score = (win_rate_normalized * 0.7 + 0.3) * sample_weight
        score = max(0, min(1, score))  # 限制在 [0, 1]
        
        # 评级
        if score >= 0.7:
            rating = '强相关'
        elif score >= 0.5:
            rating = '中等相关'
        elif score >= 0.3:
            rating = '弱相关'
        else:
            rating = '无明显相关'
        
        return score, rating
    
    def evaluate_sentiment(self, correlation: Dict) -> Tuple[float, str]:
        """
        评估情绪分数
        
        Returns:
            (分数 0-1, 情绪文本)
        """
        if correlation is None or correlation.get('avg_sentiment') is None:
            return 0.5, '中性'
        
        sentiment = correlation['avg_sentiment']  # -1 到 1
        
        # 归一化到 [0, 1]
        score = (sentiment + 1) / 2
        
        # 情绪标签
        if sentiment > 0.5:
            label = '非常积极'
        elif sentiment > 0.2:
            label = '积极'
        elif sentiment > -0.2:
            label = '中性'
        elif sentiment > -0.5:
            label = '消极'
        else:
            label = '非常消极'
        
        return score, label
    
    def evaluate_anomaly(self, anomalies: List[Dict]) -> Tuple[float, str]:
        """
        评估异常信号
        
        Returns:
            (分数 0-1, 信号描述)
        """
        if not anomalies:
            return 0.5, '无异常信号'
        
        # 统计异常方向和严重程度
        scores = []
        for anomaly in anomalies:
            severity_weight = {'high': 1.0, 'medium': 0.6, 'low': 0.3}[anomaly['severity']]
            direction_score = 1.0 if anomaly['direction'] == 'up' else 0.0
            scores.append(direction_score * severity_weight)
        
        # 加权平均（近期权重更高）
        weighted_score = sum(s * (0.5 ** i) for i, s in enumerate(scores))
        weight_sum = sum(0.5 ** i for i in range(len(scores)))
        final_score = weighted_score / weight_sum if weight_sum > 0 else 0.5
        
        # 描述
        if final_score > 0.7:
            desc = '强烈上涨信号'
        elif final_score > 0.6:
            desc = '上涨信号'
        elif final_score > 0.4:
            desc = '震荡信号'
        elif final_score > 0.3:
            desc = '下跌信号'
        else:
            desc = '强烈下跌信号'
        
        return final_score, desc
    
    def calculate_confidence(
        self,
        correlation_score: float,
        sentiment_score: float,
        anomaly_score: float,
        sample_count: int
    ) -> float:
        """
        计算综合置信度
        
        权重分配：
        - 关联强度：50%（最重要）
        - 情绪分数：20%
        - 异常信号：20%
        - 样本充分性：10%
        """
        # 样本充分性权重
        sample_weight = min(sample_count / 30, 1.0)  # 30 个样本为充分
        
        # 加权求和
        confidence = (
            correlation_score * 0.5 +
            sentiment_score * 0.2 +
            anomaly_score * 0.2 +
            sample_weight * 0.1
        )
        
        return confidence
    
    def check_data_sufficiency(self, sample_count: int) -> Tuple[bool, str]:
        """检查数据充分性"""
        if sample_count >= 30:
            return True, '数据充分'
        elif sample_count >= 20:
            return True, '数据基本充分'
        elif sample_count >= 10:
            return False, '数据不足，建议谨慎'
        else:
            return False, '数据严重不足，不建议参考'


class RiskCalculator:
    """风险计算器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def calculate_expected_return(
        self,
        keyword: str,
        symbol: str,
        correlation: Dict
    ) -> Tuple[float, float, float]:
        """
        计算预期收益
        
        Returns:
            (期望值, 最好情况, 最坏情况)
        """
        if correlation is None:
            return 0.0, 0.0, 0.0
        
        # 从历史事件计算
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT change_pct
            FROM hotspot_price_events
            WHERE keyword = ? AND symbol = ?
            ORDER BY date DESC
            LIMIT 30
        """, (keyword, symbol))
        
        changes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not changes:
            return 0.0, 0.0, 0.0
        
        expected = sum(changes) / len(changes)
        best_case = max(changes)
        worst_case = min(changes)
        
        return expected, best_case, worst_case
    
    def calculate_win_probability(self, correlation: Dict) -> float:
        """计算盈利概率"""
        if correlation is None:
            return 0.5
        
        return correlation['win_rate'] / 100.0
    
    def calculate_max_drawdown(
        self,
        keyword: str,
        symbol: str
    ) -> float:
        """计算历史最大回撤"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT change_pct
            FROM hotspot_price_events
            WHERE keyword = ? AND symbol = ?
            ORDER BY change_pct ASC
            LIMIT 5
        """, (keyword, symbol))
        
        worst_changes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not worst_changes:
            return 0.0
        
        # 平均最差 5 次
        return sum(worst_changes) / len(worst_changes)
    
    def suggest_stop_loss(
        self,
        current_price: float,
        max_drawdown: float,
        volatility: float = None
    ) -> float:
        """
        建议止损点
        
        策略：
        - 基于历史最大回撤 * 1.2（留出缓冲）
        - 或基于波动率的 2σ
        """
        # 方法1：基于历史回撤
        stop_loss_pct = abs(max_drawdown) * 1.2
        
        # 方法2：基于波动率（如果有）
        if volatility:
            stop_loss_pct = max(stop_loss_pct, volatility * 2)
        
        # 限制范围（最小 2%，最大 15%）
        stop_loss_pct = max(2.0, min(15.0, stop_loss_pct))
        
        stop_loss_price = current_price * (1 - stop_loss_pct / 100)
        
        return stop_loss_price
    
    def assess_risk_level(
        self,
        max_drawdown: float,
        volatility: float,
        win_probability: float
    ) -> str:
        """
        风险等级评估
        
        Returns:
            'low' | 'medium' | 'high' | 'very_high'
        """
        risk_score = 0
        
        # 回撤风险
        if abs(max_drawdown) > 10:
            risk_score += 3
        elif abs(max_drawdown) > 5:
            risk_score += 2
        else:
            risk_score += 1
        
        # 波动性风险
        if volatility > 0.5:
            risk_score += 3
        elif volatility > 0.3:
            risk_score += 2
        else:
            risk_score += 1
        
        # 胜率风险
        if win_probability < 0.4:
            risk_score += 3
        elif win_probability < 0.5:
            risk_score += 2
        else:
            risk_score += 1
        
        # 综合评级
        if risk_score >= 7:
            return 'very_high'
        elif risk_score >= 5:
            return 'high'
        elif risk_score >= 3:
            return 'medium'
        else:
            return 'low'


class RecommendationGenerator:
    """建议生成器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.aggregator = DataAggregator(db_path)
        self.evaluator = SignalEvaluator()
        self.risk_calc = RiskCalculator(db_path)
    
    def generate_recommendation(
        self,
        date: str,
        keyword: str,
        symbol: str,
        symbol_data: Dict
    ) -> Optional[Dict]:
        """
        生成单一投资建议
        
        Args:
            date: 日期
            keyword: 触发关键词
            symbol: 标的代码
            symbol_data: 标的数据 {
                'type': 'stock',
                'market': 'A股',
                'name': '宁德时代',
                'current_price': 245.60,
                'change_pct': 3.2,
                'volume': 8560000000
            }
        
        Returns:
            建议字典（如果生成成功）
        """
        # 1. 聚合数据
        signals = self.aggregator.aggregate_signals(keyword, symbol, symbol_data)
        correlation = signals['correlation']
        anomalies = signals['anomalies']
        
        # 数据充分性检查
        if correlation is None or correlation['total_events'] < 10:
            return None  # 数据不足，不生成建议
        
        # 2. 评估信号
        corr_score, corr_rating = self.evaluator.evaluate_correlation(correlation)
        sent_score, sent_label = self.evaluator.evaluate_sentiment(correlation)
        anom_score, anom_desc = self.evaluator.evaluate_anomaly(anomalies)
        
        # 3. 计算置信度
        confidence = self.evaluator.calculate_confidence(
            corr_score, sent_score, anom_score, correlation['total_events']
        )
        
        # 置信度过低，不生成建议
        if confidence < 0.4:
            return None
        
        # 4. 计算风险收益
        expected, best, worst = self.risk_calc.calculate_expected_return(
            keyword, symbol, correlation
        )
        win_prob = self.risk_calc.calculate_win_probability(correlation)
        max_dd = self.risk_calc.calculate_max_drawdown(keyword, symbol)
        
        # 从 price_statistics 获取波动率
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT volatility FROM price_statistics
            WHERE symbol = ? ORDER BY stat_date DESC LIMIT 1
        """, (symbol,))
        row = cursor.fetchone()
        volatility = row[0] if row else 0.3  # 默认 0.3
        conn.close()
        
        stop_loss = self.risk_calc.suggest_stop_loss(
            symbol_data['current_price'], max_dd, volatility
        )
        risk_level = self.risk_calc.assess_risk_level(max_dd, volatility, win_prob)
        
        # 5. 决定操作建议
        if confidence >= 0.7 and win_prob >= 0.6:
            action = 'buy'
        elif confidence >= 0.5 and win_prob >= 0.55:
            action = 'watch'  # 观望
        elif confidence < 0.4 or win_prob < 0.4:
            action = 'avoid'
        else:
            action = 'hold'
        
        # 6. 构建建议
        recommendation = {
            'date': date,
            'trigger_type': 'keyword',
            'trigger_value': keyword,
            'symbol': symbol,
            'symbol_type': symbol_data['type'],
            'market': symbol_data['market'],
            'name': symbol_data['name'],
            'action': action,
            'confidence': confidence,
            'expected_return': expected,
            'win_probability': win_prob * 100,
            'max_drawdown': max_dd,
            'suggested_stop_loss': stop_loss,
            'holding_period': '7-14d',
            'valid_until': (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=3)).strftime('%Y-%m-%d'),
            'correlation_score': corr_score,
            'sentiment_score': sent_score,
            'anomaly_score': anom_score,
            'sample_count': correlation['total_events'],
            'reason': json.dumps({
                'correlation': corr_rating,
                'sentiment': sent_label,
                'anomaly': anom_desc,
                'best_case': f'+{best:.1f}%',
                'worst_case': f'{worst:.1f}%'
            }, ensure_ascii=False),
            'risk_level': risk_level,
            'risk_warning': self._generate_risk_warning(risk_level, max_dd, win_prob)
        }
        
        return recommendation
    
    def _generate_risk_warning(
        self,
        risk_level: str,
        max_drawdown: float,
        win_probability: float
    ) -> str:
        """生成风险提示"""
        warnings = []
        
        if risk_level in ['high', 'very_high']:
            warnings.append(f"⚠️ {risk_level.upper()} 风险等级")
        
        if abs(max_drawdown) > 8:
            warnings.append(f"历史最大回撤 {max_drawdown:.1f}%")
        
        if win_probability < 0.5:
            warnings.append(f"盈利概率仅 {win_probability*100:.0f}%")
        
        if not warnings:
            return "风险可控，但请注意市场变化"
        
        return " | ".join(warnings)
    
    def generate_portfolio(
        self,
        date: str,
        keywords: List[str],
        max_items: int = 5
    ) -> List[Dict]:
        """
        生成投资组合建议
        
        策略：
        1. 为每个关键词生成候选建议
        2. 按置信度排序
        3. 分散化选择（避免同一行业过多）
        """
        all_recommendations = []
        
        # 1. 为每个关键词生成建议
        for keyword in keywords:
            symbols = self._get_symbols_for_keyword(keyword)
            for symbol_info in symbols:
                symbol_data = self._fetch_symbol_data(symbol_info)
                if symbol_data:
                    rec = self.generate_recommendation(
                        date, keyword, symbol_info['symbol'], symbol_data
                    )
                    if rec and rec['action'] in ['buy', 'watch']:
                        all_recommendations.append(rec)
        
        # 2. 按置信度排序
        all_recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 3. 分散化选择
        portfolio = []
        used_markets = set()
        
        for rec in all_recommendations:
            if len(portfolio) >= max_items:
                break
            
            market = rec['market']
            # 每个市场最多 2 个
            if used_markets.count(market) < 2:
                portfolio.append(rec)
                used_markets.add(market)
        
        return portfolio
    
    def _get_symbols_for_keyword(self, keyword: str) -> List[Dict]:
        """获取关键词对应的标的列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, symbol_type, market, name, priority
            FROM keyword_finance_mapping
            WHERE keyword = ? AND is_active = 1
            ORDER BY priority ASC
        """, (keyword,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'symbol': row[0],
                'type': row[1],
                'market': row[2],
                'name': row[3],
                'priority': row[4]
            }
            for row in rows
        ]
    
    def _fetch_symbol_data(self, symbol_info: Dict) -> Optional[Dict]:
        """获取标的最新数据"""
        # TODO: 调用 MarketDataFetcher
        # 这里简化为从 finance_tracking 读取最新数据
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT current_price, change_pct, volume
            FROM finance_tracking
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 1
        """, (symbol_info['symbol'],))
        
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        return {
            'symbol': symbol_info['symbol'],
            'type': symbol_info['type'],
            'market': symbol_info['market'],
            'name': symbol_info['name'],
            'current_price': row[0],
            'change_pct': row[1],
            'volume': row[2]
        }
    
    def format_recommendation(self, rec: Dict) -> str:
        """格式化建议为可读文本"""
        action_emoji = {
            'buy': '✅',
            'watch': '👀',
            'hold': '⏸️',
            'avoid': '❌'
        }
        
        action_text = {
            'buy': '建议买入',
            'watch': '建议观望',
            'hold': '建议持有',
            'avoid': '建议规避'
        }
        
        msg = f"{action_emoji[rec['action']]} {action_text[rec['action']]}\n"
        msg += f"{rec['name']} ({rec['symbol']})\n"
        msg += f"置信度: {rec['confidence']*100:.0f}%\n"
        msg += f"\n📊 预期表现:\n"
        msg += f"  期望收益: {rec['expected_return']:+.1f}%\n"
        msg += f"  盈利概率: {rec['win_probability']:.0f}%\n"
        msg += f"  最大回撤: {rec['max_drawdown']:.1f}%\n"
        msg += f"\n💡 建议:\n"
        msg += f"  止损价: {rec['suggested_stop_loss']:.2f}\n"
        msg += f"  持仓周期: {rec['holding_period']}\n"
        msg += f"  有效期至: {rec['valid_until']}\n"
        
        reason = json.loads(rec['reason'])
        msg += f"\n📝 理由:\n"
        msg += f"  关联性: {reason['correlation']}\n"
        msg += f"  情绪: {reason['sentiment']}\n"
        msg += f"  异常信号: {reason['anomaly']}\n"
        msg += f"  历史最好: {reason['best_case']}\n"
        msg += f"  历史最差: {reason['worst_case']}\n"
        
        msg += f"\n⚠️ 风险提示:\n"
        msg += f"  {rec['risk_warning']}\n"
        
        return msg
    
    def add_disclaimer(self, message: str) -> str:
        """添加免责声明"""
        disclaimer = "\n" + "="*40 + "\n"
        disclaimer += "⚠️ 免责声明:\n"
        disclaimer += "本建议基于历史数据统计，不构成投资建议。\n"
        disclaimer += "投资有风险，入市需谨慎。请根据自身情况决策。\n"
        disclaimer += "="*40
        
        return message + disclaimer


class InvestmentAdvisor:
    """投资顾问（主入口）"""
    
    def __init__(self, db_path: str, config: Dict = None):
        self.db_path = db_path
        self.config = config or {}
        self.generator = RecommendationGenerator(db_path)
    
    def advise(
        self,
        date: str,
        keywords: List[str],
        mode: str = 'single'
    ) -> Dict:
        """
        生成投资建议
        
        Args:
            date: 日期
            keywords: 触发关键词
            mode: 'single' | 'portfolio'
        
        Returns:
            {
                'recommendations': [...],
                'summary': {...}
            }
        """
        if mode == 'portfolio':
            recommendations = self.generator.generate_portfolio(date, keywords)
        else:
            recommendations = []
            for keyword in keywords:
                symbols = self.generator._get_symbols_for_keyword(keyword)
                for symbol_info in symbols[:3]:  # 每个关键词最多 3 个标的
                    symbol_data = self.generator._fetch_symbol_data(symbol_info)
                    if symbol_data:
                        rec = self.generator.generate_recommendation(
                            date, keyword, symbol_info['symbol'], symbol_data
                        )
                        if rec:
                            recommendations.append(rec)
        
        # 保存到数据库
        for rec in recommendations:
            self._save_recommendation(rec)
        
        # 生成摘要
        summary = self._generate_summary(recommendations)
        
        return {
            'recommendations': recommendations,
            'summary': summary
        }
    
    def _save_recommendation(self, rec: Dict):
        """保存建议到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO investment_recommendations
            (date, trigger_type, trigger_value, symbol, symbol_type, market, name,
             action, confidence, expected_return, win_probability, max_drawdown,
             suggested_stop_loss, holding_period, valid_until, correlation_score,
             sentiment_score, anomaly_score, sample_count, reason, risk_warning, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec['date'], rec['trigger_type'], rec['trigger_value'],
            rec['symbol'], rec['symbol_type'], rec['market'], rec['name'],
            rec['action'], rec['confidence'], rec['expected_return'],
            rec['win_probability'], rec['max_drawdown'], rec['suggested_stop_loss'],
            rec['holding_period'], rec['valid_until'], rec['correlation_score'],
            rec['sentiment_score'], rec['anomaly_score'], rec['sample_count'],
            rec['reason'], rec['risk_warning'], datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _generate_summary(self, recommendations: List[Dict]) -> Dict:
        """生成建议摘要"""
        if not recommendations:
            return {
                'total': 0,
                'message': '当前无符合条件的投资建议'
            }
        
        buy_count = sum(1 for r in recommendations if r['action'] == 'buy')
        watch_count = sum(1 for r in recommendations if r['action'] == 'watch')
        
        avg_confidence = sum(r['confidence'] for r in recommendations) / len(recommendations)
        avg_expected = sum(r['expected_return'] for r in recommendations) / len(recommendations)
        
        return {
            'total': len(recommendations),
            'buy_count': buy_count,
            'watch_count': watch_count,
            'avg_confidence': avg_confidence,
            'avg_expected_return': avg_expected,
            'message': f"生成 {len(recommendations)} 条建议，其中 {buy_count} 条买入，{watch_count} 条观望"
        }
    
    def format_output(self, result: Dict) -> str:
        """格式化输出"""
        output = "💼 投资建议报告\n"
        output += "=" * 40 + "\n\n"
        
        # 摘要
        summary = result['summary']
        output += f"📊 摘要: {summary['message']}\n"
        if summary['total'] > 0:
            output += f"   平均置信度: {summary['avg_confidence']*100:.0f}%\n"
            output += f"   平均预期收益: {summary['avg_expected_return']:+.1f}%\n"
        output += "\n"
        
        # 详细建议
        for i, rec in enumerate(result['recommendations'], 1):
            output += f"【建议 {i}】\n"
            output += self.generator.format_recommendation(rec)
            output += "\n" + "-" * 40 + "\n\n"
        
        # 免责声明
        output = self.generator.add_disclaimer(output)
        
        return output
```

---

## 集成方案

### 集成到 FinanceEnhancer

在 `trendradar/finance/enhancer.py` 中：

```python
class FinanceEnhancer:
    def __init__(self, data_dir: str, config: Dict):
        # ... 现有代码
        
        # Phase 4: 投资顾问
        self.advisor = None
        if config.get('investment_advisor', {}).get('enabled', False):
            from trendradar.finance.advisor import InvestmentAdvisor
            self.advisor = InvestmentAdvisor(
                db_path=self.db_path,
                config=config.get('investment_advisor', {})
            )
    
    def enhance_news_push(self, matched_keywords: List[str]) -> Dict:
        """为推送添加金融增强"""
        result = {
            'finance_data': ...,  # Phase 1
            'anomalies': ...,     # Phase 3
            'recommendations': None  # Phase 4
        }
        
        # Phase 4: 生成投资建议
        if self.advisor and len(matched_keywords) > 0:
            date = datetime.now().strftime('%Y-%m-%d')
            advice = self.advisor.advise(date, matched_keywords, mode='single')
            
            # 只推送高置信度建议
            high_conf_recs = [
                r for r in advice['recommendations']
                if r['confidence'] >= 0.6 and r['action'] in ['buy', 'watch']
            ]
            
            if high_conf_recs:
                result['recommendations'] = {
                    'items': high_conf_recs,
                    'summary': advice['summary']
                }
        
        return result
```

---

## 配置规范

在 `config/config.yaml` 中添加：

```yaml
finance:
  # ... Phase 1-3 配置
  
  # Phase 4: 投资建议
  investment_advisor:
    enabled: false                    # 默认关闭，需要用户主动开启
    
    # 数据要求
    min_samples: 20                   # 最少样本数
    min_confidence: 0.4               # 最低置信度阈值
    
    # 建议模式
    mode: 'single'                    # single | portfolio
    max_recommendations: 5            # 最多建议数
    
    # 推送配置
    notification:
      enabled: true
      min_confidence_for_push: 0.6   # 推送最低置信度
      actions_to_push: ['buy', 'watch']  # 推送的操作类型
      
    # 免责声明
    disclaimer:
      enabled: true
      custom_text: null               # 自定义免责声明（可选）
```

---

## 推送内容示例

```
━━━━━━━━━━━━━━━━━━
💼 智能投资建议

基于历史关联分析，为您推荐:

✅ 建议买入
宁德时代 (300750)
置信度: 72%

📊 预期表现:
  期望收益: +3.8%
  盈利概率: 68%
  最大回撤: -4.2%

💡 建议:
  止损价: 236.50
  持仓周期: 7-14d
  有效期至: 2026-05-03

📝 理由:
  关联性: 强相关（30次历史事件）
  情绪: 积极
  异常信号: 上涨信号
  历史最好: +12.3%
  历史最差: -6.8%

⚠️ 风险提示:
  风险可控，但请注意市场变化

━━━━━━━━━━━━━━━━━━
⚠️ 免责声明:
本建议基于历史数据统计，不构成投资建议。
投资有风险，入市需谨慎。请根据自身情况决策。
━━━━━━━━━━━━━━━━━━
```

---

## 测试计划

### 单元测试

```python
class TestSignalEvaluator(unittest.TestCase):
    def test_evaluate_correlation(self):
        """测试关联评估"""
        evaluator = SignalEvaluator()
        correlation = {
            'win_rate': 68.0,
            'total_events': 30,
            'avg_price_change': 3.2
        }
        score, rating = evaluator.evaluate_correlation(correlation)
        self.assertGreater(score, 0.6)
        self.assertEqual(rating, '强相关')

class TestRiskCalculator(unittest.TestCase):
    def test_calculate_expected_return(self):
        """测试收益计算"""
        calc = RiskCalculator('test.db')
        expected, best, worst = calc.calculate_expected_return(
            '新能源', '300750', {...}
        )
        self.assertGreater(best, expected)
        self.assertLess(worst, expected)

class TestRecommendationGenerator(unittest.TestCase):
    def test_generate_recommendation(self):
        """测试建议生成"""
        gen = RecommendationGenerator('test.db')
        rec = gen.generate_recommendation(
            '2026-04-30', '新能源', '300750', {...}
        )
        self.assertIsNotNone(rec)
        self.assertIn('action', rec)
        self.assertIn('confidence', rec)
        self.assertIn('risk_warning', rec)
```

---

## 实施检查清单

### 准备阶段
- [ ] 确保 Phase 2 已运行至少 30 天（数据积累）
- [ ] 数据库 schema 准备
- [ ] 配置文件扩展
- [ ] 法律合规审查（免责声明）

### 开发阶段
- [ ] 实现 `DataAggregator`（数据聚合）
- [ ] 实现 `SignalEvaluator`（信号评估）
- [ ] 实现 `RiskCalculator`（风险计算）
- [ ] 实现 `RecommendationGenerator`（建议生成）
- [ ] 实现 `InvestmentAdvisor`（主入口）
- [ ] 集成到 `FinanceEnhancer`
- [ ] 推送格式化

### 测试阶段
- [ ] 单元测试（评估、计算、生成）
- [ ] 集成测试（端到端建议生成）
- [ ] 回测验证（历史数据回测胜率）
- [ ] 边界测试（数据不足、极端情况）

### 部署阶段
- [ ] 功能开关验证
- [ ] 小范围试运行（监控建议质量）
- [ ] 用户反馈收集
- [ ] 正式上线

### 监控阶段
- [ ] 跟踪建议表现（胜率、收益率）
- [ ] 用户采纳率统计
- [ ] 误导率监控（避免误导用户）
- [ ] 策略优化（调整权重、阈值）

---

## 实施时间线

**前提条件**：Phase 2 已运行至少 30 天

| 阶段 | 时间 | 工作内容 |
|------|------|----------|
| Week 1 | 准备 | 法律审查、数据库 schema、配置准备 |
| Week 2-3 | 核心开发 | 实现所有核心类 |
| Week 4 | 集成测试 | 集成到系统、端到端测试 |
| Week 5 | 回测验证 | 历史数据回测、策略调优 |
| Week 6 | 试运行 | 小范围部署、收集反馈 |
| Week 7-8 | 优化上线 | 根据反馈优化、正式上线 |

---

## 成功标准

- [ ] 回测胜率 > 55%（至少跑赢随机）
- [ ] 高置信度建议（>70%）的胜率 > 65%
- [ ] 实际最大回撤不超过预测 * 1.5
- [ ] 用户采纳率 > 20%
- [ ] 无误导性建议投诉
- [ ] 法律合规（免责声明、风险提示）
- [ ] 与 Phase 1-3 协同无冲突

---

## 风险与限制

### 法律风险
- **投资建议资质**：需要确认是否需要投顾牌照
- **免责声明**：必须明确告知用户风险
- **误导风险**：避免"保证收益"等误导性表述

### 技术限制
- **数据依赖**：建议质量完全依赖历史数据质量
- **黑天鹅事件**：历史模式无法预测突发事件
- **市场环境变化**：牛熊转换时模式失效

### 道德考量
- **用户亏损**：即使有免责声明，也应尽量避免误导
- **推送频率**：避免过度推送导致用户冲动交易
- **透明度**：建议依据和风险必须透明

---

## 后续扩展

1. **强化学习策略优化**（Phase 4.5）
   - 根据实际执行结果调整策略参数
   - 自动学习最佳持仓周期、止损点
   
2. **用户画像**（Phase 4.5）
   - 风险偏好评估
   - 个性化建议（保守/激进）
   
3. **实盘追踪**（Phase 4.5）
   - 用户绑定券商账户
   - 自动追踪建议执行情况
   - 生成个人投资报告

4. **社区功能**（Phase 5）
   - 用户分享建议执行结果
   - 策略排行榜
   - 群体智慧聚合
