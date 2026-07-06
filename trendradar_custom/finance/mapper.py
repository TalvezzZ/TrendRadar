"""
映射管理模块

管理热点关键词到股票/基金的映射关系
"""

import yaml
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class FinanceMapper:
    """金融映射管理器"""

    def __init__(self, config_file: str):
        """
        初始化

        Args:
            config_file: 映射配置文件路径
        """
        self.config_file = Path(config_file)
        self.mappings: Dict[str, List[Dict]] = {}
        self._load_mappings()

    def _load_mappings(self) -> None:
        """从配置文件加载映射"""
        if not self.config_file.exists():
            return

        with open(self.config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self.mappings = data.get("mappings", {})

    def get_symbols_for_keyword(self, keyword: str) -> List[Dict]:
        """
        根据关键词获取标的列表

        Args:
            keyword: 关键词

        Returns:
            标的列表，按 priority 排序
        """
        symbols = self.mappings.get(keyword, [])

        # 按 priority 排序
        symbols_sorted = sorted(symbols, key=lambda x: x.get("priority", 999))

        return symbols_sorted

    def get_all_keywords(self) -> List[str]:
        """
        获取所有已配置的关键词

        Returns:
            关键词列表
        """
        return list(self.mappings.keys())

    def sync_to_database(self, db_path: str) -> None:
        """
        同步映射到数据库

        Args:
            db_path: 数据库路径
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # 清空现有映射（可选，如果想保留手动添加的映射，可以注释掉）
            # cursor.execute("DELETE FROM keyword_finance_mapping")

            # 插入新映射
            current_time = datetime.now().isoformat()

            for keyword, symbols in self.mappings.items():
                for symbol_info in symbols:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO keyword_finance_mapping
                        (keyword, symbol, symbol_type, market, name, priority, is_active, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                        """,
                        (
                            keyword,
                            symbol_info["symbol"],
                            symbol_info["type"],
                            symbol_info["market"],
                            symbol_info["name"],
                            symbol_info.get("priority", 1),
                            current_time,
                        ),
                    )

            conn.commit()

        finally:
            conn.close()

    def get_symbols_from_database(
        self, db_path: str, keyword: str
    ) -> List[Dict]:
        """
        从数据库读取关键词映射

        Args:
            db_path: 数据库路径
            keyword: 关键词

        Returns:
            标的列表
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT symbol, symbol_type, market, name, priority
                FROM keyword_finance_mapping
                WHERE keyword = ? AND is_active = 1
                ORDER BY priority ASC
                """,
                (keyword,),
            )

            symbols = []
            for row in cursor.fetchall():
                symbols.append({
                    "symbol": row[0],
                    "type": row[1],
                    "market": row[2],
                    "name": row[3],
                    "priority": row[4],
                })

            return symbols

        finally:
            conn.close()

    def add_mapping(
        self,
        keyword: str,
        symbol: str,
        symbol_type: str,
        market: str,
        name: str,
        priority: int = 1,
    ) -> None:
        """
        添加新映射（仅内存）

        Args:
            keyword: 关键词
            symbol: 标的代码
            symbol_type: 标的类型
            market: 市场
            name: 名称
            priority: 优先级
        """
        if keyword not in self.mappings:
            self.mappings[keyword] = []

        self.mappings[keyword].append({
            "symbol": symbol,
            "type": symbol_type,
            "market": market,
            "name": name,
            "priority": priority,
        })

    def remove_mapping(self, keyword: str, symbol: str) -> bool:
        """
        删除映射（仅内存）

        Args:
            keyword: 关键词
            symbol: 标的代码

        Returns:
            是否删除成功
        """
        if keyword not in self.mappings:
            return False

        original_length = len(self.mappings[keyword])
        self.mappings[keyword] = [
            s for s in self.mappings[keyword] if s["symbol"] != symbol
        ]

        return len(self.mappings[keyword]) < original_length
