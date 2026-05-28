# Phase 3: 价格异常检测设计文档

## 概述

**功能定位**：实时监测金融标的的异常价格波动，在检测到突然大涨/大跌时主动推送提醒。

**核心价值**：
- 捕捉异常交易机会（突破/暴跌）
- 风险预警（持仓标的异常下跌）
- 市场情绪指标（恐慌/狂热信号）

**依赖关系**：
- **基础设施**：Phase 1（finance_tracking 表）
- **增强数据**：Phase 2（correlation_patterns 表，可选）
- **独立性**：可独立运行，不强依赖 Phase 2

---

## 设计原则

### 1. 统计基线检测

使用**动态基线**而非固定阈值：
- 基线 = 过去 N 天的均值 ± 标准差
- 自适应：牛市/熊市有不同基线
- 避免误报：波动大的标的用更宽阈值

### 2. 多维度检测

单一指标不足以判断异常，需要综合：
- **价格维度**：涨跌幅超出正常区间
- **成交量维度**：放量/缩量异常
- **时间维度**：连续多日异常（趋势确认）
- **情绪维度**：配合 Phase 2 的情绪数据（可选）

### 3. 分级预警

不同异常程度触发不同响应：
- **一级预警（严重）**：单日涨跌超 5%，成交量翻倍
- **二级预警（中等）**：单日涨跌超 3%，成交量显著放大
- **三级预警（轻微）**：连续 3 日同向波动超 5%

### 4. 智能推送

避免推送疲劳：
- 同一标的同一方向，24 小时内最多推送 1 次
- 用户可配置关注列表（只推送感兴趣的标的）
- 用户可配置预警级别（只推送一级/一二级/全部）

---

## 数据库设计

### 3.1 统计基线表

```sql
-- 统计基线表（存储每个标的的历史统计特征）
CREATE TABLE IF NOT EXISTS price_statistics (
    symbol TEXT NOT NULL,
    stat_date TEXT NOT NULL,              -- 统计日期（基线更新日期）
    window_days INTEGER DEFAULT 30,       -- 统计窗口（天）
    
    -- 价格统计
    avg_change_pct REAL NOT NULL,         -- 平均涨跌幅
    std_change_pct REAL NOT NULL,         -- 涨跌幅标准差
    max_change_pct REAL,                  -- 最大涨幅
    min_change_pct REAL,                  -- 最大跌幅
    
    -- 成交量统计
    avg_volume REAL,                      -- 平均成交量/额
    std_volume REAL,                      -- 成交量标准差
    max_volume REAL,                      -- 最大成交量
    
    -- 波动性指标
    volatility REAL,                      -- 波动率（年化标准差）
    
    -- 元数据
    sample_count INTEGER DEFAULT 0,       -- 样本数量
    last_updated TEXT NOT NULL,
    
    PRIMARY KEY (symbol, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_price_statistics_symbol 
    ON price_statistics(symbol);
CREATE INDEX IF NOT EXISTS idx_price_statistics_date 
    ON price_statistics(stat_date);
```

### 3.2 异常事件表

```sql
-- 异常事件表（记录检测到的所有异常）
CREATE TABLE IF NOT EXISTS anomaly_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                   -- 事件日期
    symbol TEXT NOT NULL,
    symbol_type TEXT NOT NULL,
    market TEXT NOT NULL,
    name TEXT NOT NULL,
    
    -- 异常指标
    current_price REAL NOT NULL,
    change_pct REAL NOT NULL,
    volume REAL,
    volume_ratio REAL,                    -- 成交量倍数（vs 均值）
    
    -- 基线对比
    baseline_mean REAL,                   -- 基线均值
    baseline_std REAL,                    -- 基线标准差
    z_score REAL,                         -- Z-score（标准分数）
    
    -- 异常分类
    anomaly_type TEXT NOT NULL,           -- surge | crash | volume_spike | consecutive
    severity TEXT NOT NULL,               -- high | medium | low
    direction TEXT NOT NULL,              -- up | down | neutral
    
    -- 上下文信息
    consecutive_days INTEGER DEFAULT 1,   -- 连续异常天数
    related_keywords TEXT DEFAULT '[]',   -- 关联热点（JSON）
    news_sentiment TEXT,                  -- 新闻情绪（来自 Phase 2）
    
    -- 推送状态
    is_notified INTEGER DEFAULT 0,        -- 是否已推送
    notified_at TEXT,
    
    created_at TEXT NOT NULL,
    
    UNIQUE(date, symbol, anomaly_type)
);

CREATE INDEX IF NOT EXISTS idx_anomaly_events_date 
    ON anomaly_events(date);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_symbol 
    ON anomaly_events(symbol);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_severity 
    ON anomaly_events(severity);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_notified 
    ON anomaly_events(is_notified);
```

### 3.3 用户配置表

```sql
-- 用户配置表（多用户支持的扩展点）
CREATE TABLE IF NOT EXISTS user_watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',       -- 用户标识（预留多用户）
    symbol TEXT NOT NULL,
    symbol_type TEXT NOT NULL,
    name TEXT NOT NULL,
    
    -- 配置参数
    min_severity TEXT DEFAULT 'medium',   -- 最低预警级别
    enable_surge INTEGER DEFAULT 1,       -- 启用大涨提醒
    enable_crash INTEGER DEFAULT 1,       -- 启用大跌提醒
    enable_volume INTEGER DEFAULT 1,      -- 启用放量提醒
    
    added_at TEXT NOT NULL,
    
    UNIQUE(user_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_user_watchlist_user 
    ON user_watchlist(user_id);
```

---

## 模块设计

### 架构图

```
AnomalyDetector (主检测器)
├── StatisticsCalculator (统计计算器)
│   ├── calculate_baseline()
│   ├── update_statistics()
│   └── get_statistics()
├── AnomalyChecker (异常检查器)
│   ├── check_price_anomaly()
│   ├── check_volume_anomaly()
│   ├── check_consecutive_anomaly()
│   └── calculate_severity()
├── EventRecorder (事件记录器)
│   ├── record_anomaly()
│   ├── get_recent_anomalies()
│   └── mark_notified()
└── Notifier (推送器)
    ├── should_notify()
    ├── format_alert_message()
    └── send_alert()
```

---

## 核心实现

### 文件：`trendradar/finance/anomaly.py`

```python
"""
价格异常检测模块

职责：
1. 计算统计基线（均值、标准差、波动率）
2. 检测多维度异常（价格、成交量、趋势）
3. 分级预警（高/中/低）
4. 智能推送（去重、频控）
"""

import sqlite3
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
import math


class StatisticsCalculator:
    """统计基线计算器"""
    
    def __init__(self, db_path: str, window_days: int = 30):
        self.db_path = db_path
        self.window_days = window_days
    
    def calculate_baseline(self, symbol: str, end_date: str = None) -> Dict:
        """
        计算统计基线
        
        Args:
            symbol: 标的代码
            end_date: 截止日期（默认今天）
        
        Returns:
            {
                'avg_change_pct': 0.5,
                'std_change_pct': 2.3,
                'avg_volume': 1500000000,
                'std_volume': 500000000,
                'volatility': 0.35,
                'sample_count': 30
            }
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - 
                      timedelta(days=self.window_days)).strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取历史数据
        cursor.execute("""
            SELECT change_pct, volume
            FROM finance_tracking
            WHERE symbol = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC
        """, (symbol, start_date, end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) < 5:  # 样本过少，无法计算
            return None
        
        # 计算价格统计
        changes = [row[0] for row in rows if row[0] is not None]
        volumes = [row[1] for row in rows if row[1] is not None]
        
        avg_change = sum(changes) / len(changes)
        std_change = math.sqrt(sum((x - avg_change) ** 2 for x in changes) / len(changes))
        
        # 年化波动率（假设 252 个交易日）
        volatility = std_change * math.sqrt(252)
        
        result = {
            'avg_change_pct': avg_change,
            'std_change_pct': std_change,
            'max_change_pct': max(changes) if changes else 0,
            'min_change_pct': min(changes) if changes else 0,
            'volatility': volatility,
            'sample_count': len(rows)
        }
        
        # 成交量统计
        if volumes:
            avg_volume = sum(volumes) / len(volumes)
            std_volume = math.sqrt(sum((x - avg_volume) ** 2 for x in volumes) / len(volumes))
            result['avg_volume'] = avg_volume
            result['std_volume'] = std_volume
            result['max_volume'] = max(volumes)
        
        return result
    
    def update_statistics(self, symbol: str) -> bool:
        """更新统计基线到数据库"""
        stats = self.calculate_baseline(symbol)
        if stats is None:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stat_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("""
            INSERT OR REPLACE INTO price_statistics
            (symbol, stat_date, window_days, avg_change_pct, std_change_pct,
             max_change_pct, min_change_pct, avg_volume, std_volume, 
             max_volume, volatility, sample_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, stat_date, self.window_days,
            stats['avg_change_pct'], stats['std_change_pct'],
            stats['max_change_pct'], stats['min_change_pct'],
            stats.get('avg_volume'), stats.get('std_volume'),
            stats.get('max_volume'), stats['volatility'],
            stats['sample_count'], datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return True
    
    def get_statistics(self, symbol: str, max_age_days: int = 1) -> Optional[Dict]:
        """获取最新的统计基线"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT stat_date, avg_change_pct, std_change_pct, 
                   avg_volume, std_volume, volatility
            FROM price_statistics
            WHERE symbol = ?
            ORDER BY stat_date DESC
            LIMIT 1
        """, (symbol,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        # 检查数据新鲜度
        stat_date = datetime.strptime(row[0], '%Y-%m-%d')
        if (datetime.now() - stat_date).days > max_age_days:
            return None  # 过期，需要重新计算
        
        return {
            'avg_change_pct': row[1],
            'std_change_pct': row[2],
            'avg_volume': row[3],
            'std_volume': row[4],
            'volatility': row[5]
        }


class AnomalyChecker:
    """异常检查器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.calculator = StatisticsCalculator(db_path)
    
    def check_price_anomaly(
        self,
        symbol: str,
        current_change: float,
        baseline: Dict
    ) -> Tuple[bool, str, float]:
        """
        检查价格异常
        
        Returns:
            (是否异常, 异常类型, Z-score)
        """
        if baseline is None:
            return False, None, 0.0
        
        avg = baseline['avg_change_pct']
        std = baseline['std_change_pct']
        
        # 计算 Z-score（标准分数）
        z_score = (current_change - avg) / std if std > 0 else 0
        
        # 判断异常
        if z_score > 2.5:  # 超过 2.5 倍标准差
            return True, 'surge', z_score
        elif z_score < -2.5:
            return True, 'crash', z_score
        
        return False, None, z_score
    
    def check_volume_anomaly(
        self,
        current_volume: float,
        baseline: Dict
    ) -> Tuple[bool, float]:
        """
        检查成交量异常
        
        Returns:
            (是否异常, 成交量倍数)
        """
        if baseline is None or current_volume is None:
            return False, 1.0
        
        avg_volume = baseline.get('avg_volume')
        if avg_volume is None or avg_volume == 0:
            return False, 1.0
        
        volume_ratio = current_volume / avg_volume
        
        # 成交量超过均值 2 倍视为异常放量
        if volume_ratio > 2.0:
            return True, volume_ratio
        
        return False, volume_ratio
    
    def check_consecutive_anomaly(self, symbol: str, days: int = 3) -> Tuple[bool, int, str]:
        """
        检查连续异常（趋势确认）
        
        Returns:
            (是否连续异常, 连续天数, 方向)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取最近 N 天数据
        cursor.execute("""
            SELECT date, change_pct
            FROM finance_tracking
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
        """, (symbol, days))
        
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) < days:
            return False, 0, 'neutral'
        
        changes = [row[1] for row in rows]
        
        # 检查是否连续同向且幅度显著
        if all(c > 1.5 for c in changes):  # 连续上涨
            total_change = sum(changes)
            if total_change > 5.0:
                return True, days, 'up'
        elif all(c < -1.5 for c in changes):  # 连续下跌
            total_change = sum(changes)
            if total_change < -5.0:
                return True, days, 'down'
        
        return False, 0, 'neutral'
    
    def calculate_severity(
        self,
        z_score: float,
        volume_ratio: float,
        consecutive_days: int
    ) -> str:
        """
        计算异常严重程度
        
        Returns:
            'high' | 'medium' | 'low'
        """
        score = 0
        
        # 价格偏离度
        if abs(z_score) > 3.0:
            score += 3
        elif abs(z_score) > 2.5:
            score += 2
        else:
            score += 1
        
        # 成交量放大
        if volume_ratio > 3.0:
            score += 2
        elif volume_ratio > 2.0:
            score += 1
        
        # 连续性
        if consecutive_days >= 3:
            score += 2
        elif consecutive_days >= 2:
            score += 1
        
        # 分级
        if score >= 5:
            return 'high'
        elif score >= 3:
            return 'medium'
        else:
            return 'low'


class EventRecorder:
    """事件记录器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def record_anomaly(
        self,
        date: str,
        symbol: str,
        symbol_data: Dict,
        anomaly_type: str,
        severity: str,
        direction: str,
        z_score: float,
        volume_ratio: float,
        baseline: Dict,
        consecutive_days: int = 1,
        related_keywords: List[str] = None
    ) -> int:
        """记录异常事件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO anomaly_events
            (date, symbol, symbol_type, market, name, current_price, change_pct,
             volume, volume_ratio, baseline_mean, baseline_std, z_score,
             anomaly_type, severity, direction, consecutive_days, 
             related_keywords, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date, symbol, symbol_data['type'], symbol_data['market'],
            symbol_data['name'], symbol_data['current_price'],
            symbol_data['change_pct'], symbol_data.get('volume'),
            volume_ratio, baseline.get('avg_change_pct') if baseline else None,
            baseline.get('std_change_pct') if baseline else None, z_score,
            anomaly_type, severity, direction, consecutive_days,
            json.dumps(related_keywords or [], ensure_ascii=False),
            datetime.now().isoformat()
        ))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return event_id
    
    def get_recent_anomalies(
        self,
        days: int = 7,
        min_severity: str = 'low'
    ) -> List[Dict]:
        """获取最近的异常事件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        severity_order = {'high': 3, 'medium': 2, 'low': 1}
        min_severity_value = severity_order[min_severity]
        
        cursor.execute("""
            SELECT id, date, symbol, name, anomaly_type, severity,
                   change_pct, volume_ratio, z_score
            FROM anomaly_events
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date DESC, severity DESC
        """, (days,))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            severity = row[5]
            if severity_order[severity] >= min_severity_value:
                results.append({
                    'id': row[0],
                    'date': row[1],
                    'symbol': row[2],
                    'name': row[3],
                    'anomaly_type': row[4],
                    'severity': severity,
                    'change_pct': row[6],
                    'volume_ratio': row[7],
                    'z_score': row[8]
                })
        
        return results
    
    def mark_notified(self, event_id: int):
        """标记事件已推送"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE anomaly_events
            SET is_notified = 1, notified_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), event_id))
        
        conn.commit()
        conn.close()


class AnomalyDetector:
    """价格异常检测器（主入口）"""
    
    def __init__(self, db_path: str, config: Dict = None):
        self.db_path = db_path
        self.config = config or {}
        
        self.calculator = StatisticsCalculator(db_path)
        self.checker = AnomalyChecker(db_path)
        self.recorder = EventRecorder(db_path)
    
    def detect(
        self,
        date: str,
        symbol: str,
        symbol_data: Dict,
        related_keywords: List[str] = None
    ) -> Optional[Dict]:
        """
        执行异常检测
        
        Args:
            date: 日期
            symbol: 标的代码
            symbol_data: 标的数据 {
                'type': 'stock',
                'market': 'A股',
                'name': '宁德时代',
                'current_price': 245.60,
                'change_pct': 8.5,
                'volume': 15000000000
            }
            related_keywords: 关联热点关键词
        
        Returns:
            异常事件字典（如果检测到异常）
        """
        # 1. 获取或更新统计基线
        baseline = self.calculator.get_statistics(symbol, max_age_days=1)
        if baseline is None:
            self.calculator.update_statistics(symbol)
            baseline = self.calculator.get_statistics(symbol)
        
        if baseline is None:
            return None  # 数据不足，无法检测
        
        # 2. 检查价格异常
        is_price_anomaly, anomaly_type, z_score = self.checker.check_price_anomaly(
            symbol, symbol_data['change_pct'], baseline
        )
        
        # 3. 检查成交量异常
        is_volume_anomaly, volume_ratio = self.checker.check_volume_anomaly(
            symbol_data.get('volume'), baseline
        )
        
        # 4. 检查连续异常
        is_consecutive, consecutive_days, direction = self.checker.check_consecutive_anomaly(symbol)
        
        # 综合判断
        if not (is_price_anomaly or is_volume_anomaly or is_consecutive):
            return None  # 无异常
        
        # 确定异常类型
        if not anomaly_type:
            if is_volume_anomaly:
                anomaly_type = 'volume_spike'
            elif is_consecutive:
                anomaly_type = 'consecutive'
            else:
                return None
        
        # 确定方向
        if direction == 'neutral':
            direction = 'up' if symbol_data['change_pct'] > 0 else 'down'
        
        # 5. 计算严重程度
        severity = self.checker.calculate_severity(z_score, volume_ratio, consecutive_days)
        
        # 6. 记录事件
        event_id = self.recorder.record_anomaly(
            date, symbol, symbol_data, anomaly_type, severity, direction,
            z_score, volume_ratio, baseline, consecutive_days, related_keywords
        )
        
        # 7. 返回事件
        return {
            'event_id': event_id,
            'date': date,
            'symbol': symbol,
            'name': symbol_data['name'],
            'type': symbol_data['type'],
            'market': symbol_data['market'],
            'anomaly_type': anomaly_type,
            'severity': severity,
            'direction': direction,
            'current_price': symbol_data['current_price'],
            'change_pct': symbol_data['change_pct'],
            'volume': symbol_data.get('volume'),
            'volume_ratio': volume_ratio,
            'z_score': z_score,
            'consecutive_days': consecutive_days,
            'baseline': baseline,
            'related_keywords': related_keywords or []
        }
    
    def batch_detect(
        self,
        date: str,
        symbols_data: List[Dict],
        related_keywords: List[str] = None
    ) -> List[Dict]:
        """批量检测多个标的"""
        anomalies = []
        
        for symbol_data in symbols_data:
            anomaly = self.detect(date, symbol_data['symbol'], symbol_data, related_keywords)
            if anomaly:
                anomalies.append(anomaly)
        
        return anomalies
    
    def get_alert_message(self, anomaly: Dict) -> str:
        """生成预警消息"""
        emoji_map = {
            'surge': '🚀',
            'crash': '⚠️',
            'volume_spike': '📊',
            'consecutive': '📈' if anomaly['direction'] == 'up' else '📉'
        }
        
        severity_text = {
            'high': '【严重异常】',
            'medium': '【中等异常】',
            'low': '【轻微异常】'
        }
        
        type_text = {
            'surge': '突然大涨',
            'crash': '突然大跌',
            'volume_spike': '成交量异常',
            'consecutive': f"连续{anomaly['consecutive_days']}日{'上涨' if anomaly['direction'] == 'up' else '下跌'}"
        }
        
        message = f"{emoji_map[anomaly['anomaly_type']]} {severity_text[anomaly['severity']]}\n"
        message += f"{anomaly['name']} ({anomaly['symbol']})\n"
        message += f"类型: {type_text[anomaly['anomaly_type']]}\n"
        message += f"当前价格: {anomaly['current_price']:.2f}\n"
        message += f"涨跌幅: {anomaly['change_pct']:+.2f}%\n"
        
        if anomaly['volume'] and anomaly['volume_ratio'] > 1.5:
            message += f"成交放大: {anomaly['volume_ratio']:.1f}倍\n"
        
        if anomaly.get('related_keywords'):
            message += f"关联热点: {', '.join(anomaly['related_keywords'])}\n"
        
        # 统计对比
        baseline = anomaly.get('baseline', {})
        if baseline:
            message += f"\n📊 统计对比:\n"
            message += f"  正常涨跌幅: {baseline['avg_change_pct']:.2f}% ± {baseline['std_change_pct']:.2f}%\n"
            message += f"  偏离程度: {abs(anomaly['z_score']):.1f}σ\n"
        
        return message
```

---

## 集成方案

### 集成点 1：FinanceEnhancer

在 `trendradar/finance/enhancer.py` 中集成异常检测：

```python
class FinanceEnhancer:
    def __init__(self, data_dir: str, config: Dict):
        # ... 现有代码
        
        # Phase 3: 异常检测器
        self.anomaly_detector = None
        if config.get('anomaly_detection', {}).get('enabled', False):
            from trendradar.finance.anomaly import AnomalyDetector
            self.anomaly_detector = AnomalyDetector(
                db_path=self.db_path,
                config=config.get('anomaly_detection', {})
            )
    
    def enhance_news_push(self, matched_keywords: List[str]) -> Dict:
        """为推送添加金融增强"""
        # ... 现有逻辑
        
        # Phase 3: 检测异常
        anomalies = []
        if self.anomaly_detector:
            date = datetime.now().strftime('%Y-%m-%d')
            for keyword in matched_keywords:
                symbols = self.mapper.get_symbols_for_keyword(keyword)
                for symbol_info in symbols:
                    symbol_data = self._fetch_symbol_data(symbol_info)
                    if symbol_data:
                        anomaly = self.anomaly_detector.detect(
                            date, symbol_info['symbol'], symbol_data, [keyword]
                        )
                        if anomaly:
                            anomalies.append(anomaly)
        
        return {
            'finance_data': ...,
            'anomalies': anomalies,  # 新增
            'stats': ...
        }
```

### 集成点 2：独立推送任务

创建 **定时任务**，每日盘后/盘中实时检测所有配置的标的：

**文件**: `trendradar/tasks/anomaly_monitor.py`

```python
"""
异常监测定时任务

执行时机：
- 盘中：每 30 分钟检测一次
- 盘后：收盘后执行一次全面检测
"""

import schedule
from trendradar.finance.anomaly import AnomalyDetector
from trendradar.notification.dispatcher import NotificationDispatcher

def run_anomaly_monitor():
    """执行异常监测"""
    detector = AnomalyDetector(db_path='output/memory.db')
    
    # 获取所有需要监测的标的
    watchlist = get_watchlist()  # 从 user_watchlist 表读取
    
    date = datetime.now().strftime('%Y-%m-%d')
    anomalies = []
    
    for symbol_info in watchlist:
        # 获取最新数据
        symbol_data = fetch_latest_data(symbol_info['symbol'])
        
        # 检测异常
        anomaly = detector.detect(date, symbol_info['symbol'], symbol_data)
        if anomaly:
            # 检查是否需要推送
            if should_notify(anomaly, symbol_info):
                anomalies.append(anomaly)
    
    # 批量推送
    if anomalies:
        send_anomaly_alerts(anomalies)

# 调度设置
schedule.every(30).minutes.do(run_anomaly_monitor)  # 盘中每 30 分钟
schedule.every().day.at("15:30").do(run_anomaly_monitor)  # 收盘后
```

---

## 配置规范

在 `config/config.yaml` 中添加：

```yaml
finance:
  # ... Phase 1 & 2 配置
  
  # Phase 3: 异常检测
  anomaly_detection:
    enabled: true
    
    # 统计配置
    baseline_window: 30              # 统计窗口（天）
    min_samples: 10                  # 最少样本数
    update_frequency: 'daily'        # 更新频率：daily | realtime
    
    # 检测阈值
    thresholds:
      price_z_score: 2.5             # 价格 Z-score 阈值
      volume_ratio: 2.0              # 成交量倍数阈值
      consecutive_days: 3            # 连续天数
      consecutive_total: 5.0         # 连续涨跌幅总和
    
    # 推送配置
    notification:
      enabled: true
      min_severity: 'medium'         # 最低推送级别：high | medium | low
      cooldown_hours: 24             # 同标的同向冷却时间（小时）
      batch_mode: true               # 批量推送（避免刷屏）
      
    # 监控配置
    monitor:
      enabled: true
      realtime_interval: 30          # 实时检测间隔（分钟）
      market_hours: ['09:30-11:30', '13:00-15:00']  # 交易时段
```

---

## 推送内容示例

### 示例 1：严重异常（单一标的）

```
🚀 【严重异常】价格异常提醒

宁德时代 (300750)
类型: 突然大涨
当前价格: 268.50
涨跌幅: +8.5%
成交放大: 3.2倍

📊 统计对比:
  正常涨跌幅: +0.5% ± 2.1%
  偏离程度: 3.8σ

关联热点: 新能源, 电池技术

━━━━━━━━━━━━━━━━━━
💡 建议: 异常放量大涨，建议关注是否有重大利好消息
```

### 示例 2：批量异常（多个标的）

```
📊 异常监测日报 (2026-04-30)

检测到 5 个异常标的:

🚀 【严重】宁德时代 (300750)
   +8.5%，成交放大 3.2倍

⚠️ 【严重】中芯国际 (688981)
   -6.2%，成交放大 2.8倍

📈 【中等】新能源车ETF (159915)
   连续3日上涨，累计 +7.8%

📊 【轻微】半导体50ETF (512480)
   成交放大 2.1倍

📉 【中等】某基金 (005827)
   连续3日下跌，累计 -5.3%

━━━━━━━━━━━━━━━━━━
查看详情: /anomaly recent
```

---

## 测试计划

### 单元测试

**文件**: `tests/finance/test_anomaly.py`

```python
import unittest
from trendradar.finance.anomaly import (
    StatisticsCalculator, AnomalyChecker, AnomalyDetector
)

class TestStatisticsCalculator(unittest.TestCase):
    def test_calculate_baseline(self):
        """测试基线计算"""
        calc = StatisticsCalculator('test.db', window_days=30)
        baseline = calc.calculate_baseline('300750')
        
        self.assertIsNotNone(baseline)
        self.assertIn('avg_change_pct', baseline)
        self.assertIn('std_change_pct', baseline)
        self.assertIn('volatility', baseline)

class TestAnomalyChecker(unittest.TestCase):
    def test_check_price_anomaly(self):
        """测试价格异常检测"""
        checker = AnomalyChecker('test.db')
        baseline = {
            'avg_change_pct': 0.5,
            'std_change_pct': 2.0
        }
        
        # 测试大涨
        is_anomaly, type_, z_score = checker.check_price_anomaly(
            '300750', 8.5, baseline
        )
        self.assertTrue(is_anomaly)
        self.assertEqual(type_, 'surge')
        self.assertGreater(z_score, 2.5)
        
        # 测试正常波动
        is_anomaly, type_, z_score = checker.check_price_anomaly(
            '300750', 1.5, baseline
        )
        self.assertFalse(is_anomaly)

class TestAnomalyDetector(unittest.TestCase):
    def test_detect_surge(self):
        """测试大涨检测"""
        detector = AnomalyDetector('test.db')
        
        symbol_data = {
            'symbol': '300750',
            'type': 'stock',
            'market': 'A股',
            'name': '宁德时代',
            'current_price': 268.50,
            'change_pct': 8.5,
            'volume': 15000000000
        }
        
        anomaly = detector.detect(
            '2026-04-30', '300750', symbol_data, ['新能源']
        )
        
        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly['anomaly_type'], 'surge')
        self.assertEqual(anomaly['severity'], 'high')
```

### 集成测试

```python
def test_full_detection_workflow(self):
    """测试完整检测流程"""
    # 1. 准备历史数据
    setup_historical_data()
    
    # 2. 更新统计基线
    calc = StatisticsCalculator('test.db')
    calc.update_statistics('300750')
    
    # 3. 模拟异常数据
    symbol_data = simulate_surge_data()
    
    # 4. 执行检测
    detector = AnomalyDetector('test.db')
    anomaly = detector.detect('2026-04-30', '300750', symbol_data)
    
    # 5. 验证结果
    assert anomaly is not None
    assert anomaly['severity'] in ['high', 'medium', 'low']
    
    # 6. 验证数据库记录
    events = detector.recorder.get_recent_anomalies(days=1)
    assert len(events) > 0
```

---

## 实施检查清单

### 准备阶段
- [ ] 数据库 schema 准备（`price_statistics`, `anomaly_events`, `user_watchlist`）
- [ ] 配置文件扩展（`config.yaml` 中的 `anomaly_detection` 段）
- [ ] 历史数据验证（finance_tracking 表至少有 30 天数据）

### 开发阶段
- [ ] 实现 `StatisticsCalculator`（统计基线计算）
- [ ] 实现 `AnomalyChecker`（异常检测逻辑）
- [ ] 实现 `EventRecorder`（事件存储）
- [ ] 实现 `AnomalyDetector`（主入口）
- [ ] 集成到 `FinanceEnhancer`
- [ ] 创建独立监测任务 `anomaly_monitor.py`
- [ ] 推送格式化（`get_alert_message`）

### 测试阶段
- [ ] 单元测试（基线计算、异常检测、严重程度评估）
- [ ] 集成测试（完整检测流程）
- [ ] 边界测试（数据不足、极端波动、重复检测）
- [ ] 推送测试（消息格式、去重逻辑、冷却时间）

### 部署阶段
- [ ] 配置开关验证（`anomaly_detection.enabled`）
- [ ] 定时任务部署（cron / schedule）
- [ ] 监控告警（检测失败、推送失败）
- [ ] 性能优化（批量检测、数据库索引）

### 优化阶段
- [ ] 用户反馈收集（误报率、漏报率）
- [ ] 阈值调优（Z-score、成交量倍数）
- [ ] 推送策略优化（分级推送、用户自定义）
- [ ] 与 Phase 2 联动（情绪数据、关联分析）

---

## 实施时间线

**前提条件**：Phase 1 已运行至少 30 天，积累足够历史数据

| 阶段 | 时间 | 工作内容 |
|------|------|----------|
| Week 1 | 准备 | 数据库 schema、配置文件、单元测试准备 |
| Week 2 | 核心开发 | 实现统计计算器、异常检查器、事件记录器 |
| Week 3 | 集成开发 | 集成到 FinanceEnhancer、创建定时任务 |
| Week 4 | 测试调优 | 功能测试、阈值调优、推送测试 |
| Week 5 | 试运行 | 小范围部署，收集反馈 |
| Week 6 | 正式上线 | 全量部署，监控运行 |

---

## 依赖关系

- **必需**：Phase 1（finance_tracking 表，至少 30 天历史数据）
- **可选增强**：Phase 2（情绪数据、关联分析）
- **未来扩展**：Phase 4 将使用异常事件数据作为风险评估输入

---

## 注意事项

### 数据质量
- 统计基线依赖历史数据质量，缺失数据会影响准确性
- 需要定期清理异常数据点（如停牌、ST 股票）

### 推送策略
- 避免推送疲劳：同一标的 24 小时内最多推送 1 次
- 批量推送优于单条推送（盘后汇总）

### 误报控制
- 初期阈值可能需要调整，建议先试运行观察
- 小市值股票波动大，建议单独配置阈值

### 性能考虑
- 批量检测时注意数据库查询性能
- 考虑使用缓存减少重复计算

---

## 成功标准

- [ ] 能准确检测到真实的价格异常（涨跌幅 > 5% 且放量）
- [ ] 误报率 < 10%（不误报正常波动）
- [ ] 推送及时性 < 10 分钟（实时检测模式）
- [ ] 数据库存储完整（所有异常事件被记录）
- [ ] 用户可配置关注列表和预警级别
- [ ] 与 Phase 1、Phase 2 协同工作无冲突
- [ ] 关闭功能开关时不影响现有系统

---

## 后续扩展

1. **机器学习增强**（Phase 3.5）
   - 使用历史异常事件训练模型
   - 自动学习最佳阈值
   - 预测异常概率而非简单判断

2. **多因子异常**（Phase 3.5）
   - 结合市场指数（如沪深300）判断异常
   - 行业板块联动分析
   - 大盘环境校正

3. **用户个性化**（Phase 3.5）
   - 每个用户独立的关注列表
   - 自定义预警级别和推送方式
   - 历史推送效果反馈学习
