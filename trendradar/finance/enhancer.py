"""
金融增强模块

为新闻推送添加相关股票/基金的涨跌情况
"""

from pathlib import Path
from typing import Dict, List, Any, Optional

from .mapper import FinanceMapper
from .market import MarketDataFetcher
from .tracker import FinanceTracker


class FinanceEnhancer:
    """金融增强器 - 为新闻推送添加金融数据"""

    def __init__(self, data_dir: str = "output", config: Dict = None):
        """
        初始化增强器

        Args:
            data_dir: 数据目录路径
            config: 金融配置
        """
        self.data_dir = Path(data_dir)
        self.config = config or {}

        # 映射配置文件
        mapping_file = self.config.get("mapping_file", "finance_mapping.yaml")
        if not Path(mapping_file).is_absolute():
            mapping_file = Path("config") / mapping_file

        # 初始化组件
        self.mapper = FinanceMapper(str(mapping_file))
        self.fetcher = MarketDataFetcher(
            timeout=self.config.get("data_fetch", {}).get("timeout", 10),
            retry_times=self.config.get("data_fetch", {}).get("retry_times", 2),
        )
        self.tracker = FinanceTracker(data_dir=str(self.data_dir))

        # 显示配置
        self.display_config = self.config.get("display", {})
        self.max_items = self.display_config.get("max_items_per_keyword", 3)
        self.show_volume = self.display_config.get("show_volume", True)

        # 同步映射到数据库
        db_path = self.data_dir / "memory.db"
        if db_path.exists():
            self.mapper.sync_to_database(str(db_path))

    def enhance_news_push(self, matched_keywords: List[str]) -> Dict[str, Any]:
        """
        增强新闻推送内容

        Args:
            matched_keywords: 匹配的关键词列表

        Returns:
            增强后的金融数据
        """
        enhancement = {
            "finance_data": [],
            "stats": {
                "total_tracked": 0,
                "rising_count": 0,
                "falling_count": 0,
            },
        }

        # 为每个关键词获取金融数据
        for keyword in matched_keywords:
            finance_data = self._fetch_finance_data(keyword)
            if finance_data:
                enhancement["finance_data"].append(finance_data)

        # 统计数据
        total_tracked = 0
        rising_count = 0
        falling_count = 0

        for kw_data in enhancement["finance_data"]:
            for symbol in kw_data["symbols"]:
                total_tracked += 1
                if symbol.get("change_pct", 0) > 0:
                    rising_count += 1
                elif symbol.get("change_pct", 0) < 0:
                    falling_count += 1

        enhancement["stats"] = {
            "total_tracked": total_tracked,
            "rising_count": rising_count,
            "falling_count": falling_count,
        }

        return enhancement

    def _fetch_finance_data(self, keyword: str) -> Optional[Dict]:
        """
        获取关键词对应的金融数据

        Args:
            keyword: 关键词

        Returns:
            金融数据字典或 None
        """
        # 获取映射的标的
        symbols = self.mapper.get_symbols_for_keyword(keyword)

        if not symbols:
            return None

        # 限制数量
        symbols = symbols[: self.max_items]

        # 获取实时数据
        result_symbols = []

        for symbol_info in symbols:
            # 获取实时行情
            realtime_data = self.fetcher.get_realtime_data(
                symbol_info["symbol"],
                symbol_info["type"],
                symbol_info["market"],
            )

            if not realtime_data:
                continue

            # 获取历史趋势
            trend = self.tracker.get_trend_analysis(symbol_info["symbol"], days=7)

            # 保存跟踪数据
            self.tracker.save_tracking_data(realtime_data, keywords=[keyword])

            # 生成提醒
            alert = self._generate_alert(realtime_data, trend)

            # 组装数据
            symbol_data = {
                **realtime_data,
                "trend": trend,
                "alert": alert,
            }

            result_symbols.append(symbol_data)

        if not result_symbols:
            return None

        return {
            "keyword": keyword,
            "symbols": result_symbols,
        }

    def _generate_alert(
        self, realtime_data: Dict, trend: Optional[Dict]
    ) -> Optional[str]:
        """
        生成异常提醒

        Args:
            realtime_data: 实时数据
            trend: 趋势数据

        Returns:
            提醒信息或 None
        """
        change_pct = realtime_data.get("change_pct", 0)

        # 单日涨跌幅异常
        if change_pct > 5:
            return f"单日大涨 {change_pct:.1f}%"
        elif change_pct < -5:
            return f"单日大跌 {abs(change_pct):.1f}%"

        # 连续趋势
        if trend:
            if trend["rising_days"] >= 5:
                return f"连续 {trend['rising_days']} 天上涨"
            elif trend["falling_days"] >= 5:
                return f"连续 {trend['falling_days']} 天下跌"

            # 累计涨跌幅异常
            if trend["total_change_pct"] > 20:
                return f"近 {trend['days_count']} 日累计上涨 {trend['total_change_pct']:.1f}%"
            elif trend["total_change_pct"] < -20:
                return f"近 {trend['days_count']} 日累计下跌 {abs(trend['total_change_pct']):.1f}%"

        return None

    def format_enhanced_notification(
        self, original_content: str, finance_data: Dict[str, Any]
    ) -> str:
        """
        格式化增强后的通知内容

        Args:
            original_content: 原始通知内容
            finance_data: 金融数据

        Returns:
            格式化后的内容
        """
        if not finance_data.get("finance_data"):
            return original_content

        sections = [original_content, ""]

        # 添加金融数据
        sections.append("━━━━━━━━━━━━━━━━━━")
        sections.append("💹 相关标的表现")
        sections.append("")

        for kw_data in finance_data["finance_data"]:
            sections.append(f"【{kw_data['keyword']}】")

            for symbol in kw_data["symbols"]:
                # 涨跌符号
                if symbol["change_pct"] > 0:
                    direction = "⬆️"
                elif symbol["change_pct"] < 0:
                    direction = "⬇️"
                else:
                    direction = "➡️"

                # 基本信息
                line = f"• {symbol['name']} ({symbol['symbol']})     {symbol['change_pct']:+.1f}%  {direction}"
                sections.append(line)

                # 成交额（如果配置显示）
                if self.show_volume and symbol.get("volume"):
                    volume_str = self._format_volume(symbol["volume"])
                    sections.append(f"  成交额: {volume_str}")

                # 趋势信息
                if symbol.get("trend"):
                    trend = symbol["trend"]
                    if abs(trend["total_change_pct"]) > 5:
                        sections.append(
                            f"  📈 近{trend['days_count']}日累计: {trend['total_change_pct']:+.1f}%"
                        )

                # 异常提醒
                if symbol.get("alert"):
                    sections.append(f"  ⚠️  {symbol['alert']}")

                # 开放式基金标注 T-1
                if symbol["type"] == "fund" and symbol.get("data_date"):
                    sections.append(f"  净值: {symbol['current_price']:.3f} ({symbol['data_date']})")

                sections.append("")

        # 统计信息
        stats = finance_data.get("stats", {})
        if stats.get("total_tracked", 0) > 0:
            sections.append("━━━━━━━━━━━━━━━━━━")
            sections.append("📊 市场概览")
            sections.append(
                f"跟踪标的：{stats['total_tracked']} 个 | "
                f"上涨：{stats['rising_count']} 个 | "
                f"下跌：{stats['falling_count']} 个"
            )

        return "\n".join(sections)

    def _format_volume(self, volume: float) -> str:
        """
        格式化成交额

        Args:
            volume: 成交额

        Returns:
            格式化字符串
        """
        if volume >= 1_0000_0000:  # 亿
            return f"{volume / 1_0000_0000:.1f}亿"
        elif volume >= 1_0000:  # 万
            return f"{volume / 1_0000:.1f}万"
        else:
            return f"{volume:.0f}"
