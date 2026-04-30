"""
数据跟踪模块

管理金融数据的存储和历史查询
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class FinanceTracker:
    """金融数据跟踪器"""

    def __init__(self, data_dir: str = "output"):
        """
        初始化

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "memory.db"

    def save_tracking_data(self, symbol_data: Dict, keywords: List[str] = None) -> bool:
        """
        保存跟踪数据

        Args:
            symbol_data: 标的数据
            keywords: 关联的关键词列表

        Returns:
            是否保存成功
        """
        if not self.db_path.exists():
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            today = datetime.now().strftime("%Y-%m-%d")

            cursor.execute(
                """
                INSERT OR REPLACE INTO finance_tracking
                (date, symbol, symbol_type, market, name, current_price, change_pct, volume, keywords, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    today,
                    symbol_data["symbol"],
                    symbol_data["type"],
                    symbol_data["market"],
                    symbol_data["name"],
                    symbol_data["current_price"],
                    symbol_data["change_pct"],
                    symbol_data.get("volume"),
                    json.dumps(keywords or [], ensure_ascii=False),
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            return True

        except Exception as e:
            return False

        finally:
            conn.close()

    def get_historical_data(self, symbol: str, days: int = 7) -> List[Dict]:
        """
        获取历史数据

        Args:
            symbol: 标的代码
            days: 查询天数

        Returns:
            历史数据列表
        """
        if not self.db_path.exists():
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            cursor.execute(
                """
                SELECT date, current_price, change_pct, volume, keywords
                FROM finance_tracking
                WHERE symbol = ? AND date >= ?
                ORDER BY date DESC
                """,
                (symbol, start_date),
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    "date": row[0],
                    "current_price": row[1],
                    "change_pct": row[2],
                    "volume": row[3],
                    "keywords": json.loads(row[4]) if row[4] else [],
                })

            return results

        finally:
            conn.close()

    def get_trend_analysis(self, symbol: str, days: int = 7) -> Optional[Dict]:
        """
        分析趋势

        Args:
            symbol: 标的代码
            days: 分析天数

        Returns:
            趋势分析结果
        """
        historical = self.get_historical_data(symbol, days)

        if len(historical) < 2:
            return None

        # 计算累计涨跌幅
        total_change = sum(h["change_pct"] for h in historical)

        # 统计涨跌天数
        rising_days = sum(1 for h in historical if h["change_pct"] > 0)
        falling_days = sum(1 for h in historical if h["change_pct"] < 0)

        # 判断趋势
        if total_change > 5:
            trend_direction = "上涨"
        elif total_change < -5:
            trend_direction = "下跌"
        else:
            trend_direction = "震荡"

        return {
            "days_count": len(historical),
            "total_change_pct": round(total_change, 2),
            "rising_days": rising_days,
            "falling_days": falling_days,
            "trend_direction": trend_direction,
            "latest_change_pct": historical[0]["change_pct"],
        }

    def associate_keyword(self, symbol: str, keyword: str) -> bool:
        """
        关联关键词到最新的跟踪数据

        Args:
            symbol: 标的代码
            keyword: 关键词

        Returns:
            是否关联成功
        """
        if not self.db_path.exists():
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            today = datetime.now().strftime("%Y-%m-%d")

            # 获取当前关键词列表
            cursor.execute(
                """
                SELECT keywords FROM finance_tracking
                WHERE symbol = ? AND date = ?
                """,
                (symbol, today),
            )

            row = cursor.fetchone()
            if not row:
                return False

            keywords = json.loads(row[0]) if row[0] else []

            # 添加新关键词（去重）
            if keyword not in keywords:
                keywords.append(keyword)

                cursor.execute(
                    """
                    UPDATE finance_tracking
                    SET keywords = ?
                    WHERE symbol = ? AND date = ?
                    """,
                    (json.dumps(keywords, ensure_ascii=False), symbol, today),
                )

                conn.commit()

            return True

        except Exception:
            return False

        finally:
            conn.close()

    def get_all_tracked_symbols(self, date: str = None) -> List[Dict]:
        """
        获取所有跟踪的标的

        Args:
            date: 日期（YYYY-MM-DD），默认今天

        Returns:
            标的列表
        """
        if not self.db_path.exists():
            return []

        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT symbol, symbol_type, market, name, current_price, change_pct, volume, keywords
                FROM finance_tracking
                WHERE date = ?
                ORDER BY change_pct DESC
                """,
                (date,),
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    "symbol": row[0],
                    "type": row[1],
                    "market": row[2],
                    "name": row[3],
                    "current_price": row[4],
                    "change_pct": row[5],
                    "volume": row[6],
                    "keywords": json.loads(row[7]) if row[7] else [],
                })

            return results

        finally:
            conn.close()
