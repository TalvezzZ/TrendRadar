"""
市场数据获取模块

使用 AKShare 获取股票、ETF、开放式基金的实时行情数据
"""

import time
from typing import Dict, Optional
from datetime import datetime


class MarketDataFetcher:
    """市场数据获取器"""

    def __init__(self, timeout: int = 10, retry_times: int = 2):
        """
        初始化

        Args:
            timeout: 请求超时时间（秒）
            retry_times: 失败重试次数
        """
        self.timeout = timeout
        self.retry_times = retry_times

    def get_realtime_data(
        self, symbol: str, symbol_type: str, market: str
    ) -> Optional[Dict]:
        """
        获取实时行情数据（统一入口）

        Args:
            symbol: 标的代码
            symbol_type: 标的类型（stock | etf | fund）
            market: 市场（A股 | 美股 | 港股）

        Returns:
            行情数据字典或 None
        """
        if symbol_type == "stock":
            return self.get_stock_realtime(symbol, market)
        elif symbol_type == "etf":
            return self.get_etf_realtime(symbol)
        elif symbol_type == "fund":
            return self.get_fund_nav(symbol)
        return None

    def get_stock_realtime(self, symbol: str, market: str) -> Optional[Dict]:
        """
        获取股票实时行情

        Args:
            symbol: 股票代码
            market: 市场（A股 | 美股 | 港股）

        Returns:
            行情数据字典或 None
        """
        if market == "A股":
            return self._fetch_a_stock(symbol)
        elif market == "美股":
            return self._fetch_us_stock(symbol)
        elif market == "港股":
            return self._fetch_hk_stock(symbol)
        return None

    def get_etf_realtime(self, symbol: str) -> Optional[Dict]:
        """
        获取 ETF 实时行情

        Args:
            symbol: ETF 代码

        Returns:
            行情数据字典或 None
        """
        return self._fetch_etf(symbol)

    def get_fund_nav(self, symbol: str) -> Optional[Dict]:
        """
        获取开放式基金净值（T-1 数据）

        Args:
            symbol: 基金代码

        Returns:
            净值数据字典或 None
        """
        return self._fetch_fund(symbol)

    def _fetch_a_stock(self, symbol: str) -> Optional[Dict]:
        """
        获取 A 股实时数据

        Args:
            symbol: 股票代码

        Returns:
            行情数据或 None
        """
        for attempt in range(self.retry_times + 1):
            try:
                import akshare as ak

                # 获取 A 股实时数据
                df = ak.stock_zh_a_spot_em()

                # 查找对应股票
                row = df[df["代码"] == symbol]
                if row.empty:
                    return None

                return {
                    "symbol": symbol,
                    "name": row["名称"].values[0],
                    "current_price": float(row["最新价"].values[0]),
                    "change_pct": float(row["涨跌幅"].values[0]),
                    "volume": float(row["成交额"].values[0]) if "成交额" in row.columns else None,
                    "type": "stock",
                    "market": "A股",
                    "fetch_time": datetime.now().isoformat(),
                }

            except Exception as e:
                if attempt < self.retry_times:
                    time.sleep(1)
                    continue
                return None

        return None

    def _fetch_us_stock(self, symbol: str) -> Optional[Dict]:
        """
        获取美股实时数据

        Args:
            symbol: 股票代码

        Returns:
            行情数据或 None
        """
        for attempt in range(self.retry_times + 1):
            try:
                import akshare as ak

                # 获取美股实时数据
                df = ak.stock_us_spot_em()

                # 查找对应股票
                row = df[df["代码"] == symbol]
                if row.empty:
                    return None

                return {
                    "symbol": symbol,
                    "name": row["名称"].values[0],
                    "current_price": float(row["最新价"].values[0]),
                    "change_pct": float(row["涨跌幅"].values[0]),
                    "volume": float(row["成交额"].values[0]) if "成交额" in row.columns else None,
                    "type": "stock",
                    "market": "美股",
                    "fetch_time": datetime.now().isoformat(),
                }

            except Exception as e:
                if attempt < self.retry_times:
                    time.sleep(1)
                    continue
                return None

        return None

    def _fetch_hk_stock(self, symbol: str) -> Optional[Dict]:
        """
        获取港股实时数据

        Args:
            symbol: 股票代码

        Returns:
            行情数据或 None
        """
        for attempt in range(self.retry_times + 1):
            try:
                import akshare as ak

                # 获取港股实时数据
                df = ak.stock_hk_spot_em()

                # 查找对应股票
                row = df[df["代码"] == symbol]
                if row.empty:
                    return None

                return {
                    "symbol": symbol,
                    "name": row["名称"].values[0],
                    "current_price": float(row["最新价"].values[0]),
                    "change_pct": float(row["涨跌幅"].values[0]),
                    "volume": float(row["成交额"].values[0]) if "成交额" in row.columns else None,
                    "type": "stock",
                    "market": "港股",
                    "fetch_time": datetime.now().isoformat(),
                }

            except Exception as e:
                if attempt < self.retry_times:
                    time.sleep(1)
                    continue
                return None

        return None

    def _fetch_etf(self, symbol: str) -> Optional[Dict]:
        """
        获取 ETF 实时数据

        Args:
            symbol: ETF 代码

        Returns:
            行情数据或 None
        """
        for attempt in range(self.retry_times + 1):
            try:
                import akshare as ak

                # 获取 ETF 实时行情
                df = ak.fund_etf_spot_em()

                # 查找对应 ETF
                row = df[df["代码"] == symbol]
                if row.empty:
                    return None

                return {
                    "symbol": symbol,
                    "name": row["名称"].values[0],
                    "current_price": float(row["最新价"].values[0]),
                    "change_pct": float(row["涨跌幅"].values[0]),
                    "volume": float(row["成交额"].values[0]) if "成交额" in row.columns else None,
                    "type": "etf",
                    "market": "A股",
                    "fetch_time": datetime.now().isoformat(),
                }

            except Exception as e:
                if attempt < self.retry_times:
                    time.sleep(1)
                    continue
                return None

        return None

    def _fetch_fund(self, symbol: str) -> Optional[Dict]:
        """
        获取开放式基金净值（T-1 数据）

        Args:
            symbol: 基金代码

        Returns:
            净值数据或 None
        """
        for attempt in range(self.retry_times + 1):
            try:
                import akshare as ak

                # 获取基金净值数据
                df = ak.fund_em_open_fund_info(fund=symbol, indicator="单位净值走势")

                if df.empty:
                    return None

                # 获取最新净值
                latest = df.iloc[-1]

                # 计算涨跌幅
                change_pct = 0.0
                if "日增长率" in latest.index:
                    try:
                        change_pct = float(latest["日增长率"])
                    except:
                        pass

                # 获取基金名称
                try:
                    info = ak.fund_individual_basic_info_xq(symbol=symbol)
                    name = info.get("基金简称", symbol)
                except:
                    name = symbol

                return {
                    "symbol": symbol,
                    "name": name,
                    "current_price": float(latest["单位净值"]),
                    "change_pct": change_pct,
                    "volume": None,  # 开放式基金没有成交额
                    "type": "fund",
                    "market": "A股",
                    "fetch_time": datetime.now().isoformat(),
                    "data_date": latest["净值日期"],  # 标注数据日期（T-1）
                }

            except Exception as e:
                if attempt < self.retry_times:
                    time.sleep(1)
                    continue
                return None

        return None
