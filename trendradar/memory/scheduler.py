"""
记忆生成调度器

提供异步任务函数和同步包装器，用于 CLI 手动触发每日/每周记忆生成。
不包含真正的定时调度，仅提供手动调用接口。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from trendradar.memory.generator import MemoryGenerator
from trendradar.memory.models import Memory


async def generate_daily_summary_task(
    db_path: str,
    ai_config: Dict[str, Any],
    date: Optional[datetime] = None
) -> Optional[Memory]:
    """
    异步生成每日摘要任务

    Args:
        db_path: 数据库文件路径
        ai_config: AI 客户端配置
        date: 目标日期（默认为昨天）

    Returns:
        生成的记忆对象，如果没有数据则返回 None

    Raises:
        Exception: 生成失败时抛出异常
    """
    if date is None:
        # 默认生成昨天的摘要
        date = datetime.now() - timedelta(days=1)

    # 在异步上下文中运行同步代码
    loop = asyncio.get_event_loop()
    generator = MemoryGenerator(db_path, ai_config)

    # 使用 run_in_executor 在线程池中运行同步函数
    memory = await loop.run_in_executor(
        None,
        generator.generate_daily_summary,
        date
    )

    return memory


async def generate_weekly_digest_task(
    db_path: str,
    ai_config: Dict[str, Any],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Optional[Memory]:
    """
    异步生成每周摘要任务

    Args:
        db_path: 数据库文件路径
        ai_config: AI 客户端配置
        start_date: 开始日期（默认为上周一）
        end_date: 结束日期（默认为上周日）

    Returns:
        生成的记忆对象，如果没有数据则返回 None

    Raises:
        Exception: 生成失败时抛出异常
    """
    if start_date is None or end_date is None:
        # 默认生成上周的摘要（上周一到上周日）
        today = datetime.now()
        days_since_monday = today.weekday()  # 0=Monday, 6=Sunday
        last_monday = today - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)

        start_date = start_date or last_monday
        end_date = end_date or last_sunday

    # 在异步上下文中运行同步代码
    loop = asyncio.get_event_loop()
    generator = MemoryGenerator(db_path, ai_config)

    # 使用 run_in_executor 在线程池中运行同步函数
    memory = await loop.run_in_executor(
        None,
        generator.generate_weekly_digest,
        start_date,
        end_date
    )

    return memory


def generate_daily_summary_sync(
    db_path: str,
    ai_config: Dict[str, Any],
    date: Optional[datetime] = None
) -> Optional[Memory]:
    """
    同步生成每日摘要（CLI 使用）

    Args:
        db_path: 数据库文件路径
        ai_config: AI 客户端配置
        date: 目标日期（默认为昨天）

    Returns:
        生成的记忆对象，如果没有数据则返回 None

    Raises:
        Exception: 生成失败时抛出异常
    """
    return asyncio.run(generate_daily_summary_task(db_path, ai_config, date))


def generate_weekly_digest_sync(
    db_path: str,
    ai_config: Dict[str, Any],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Optional[Memory]:
    """
    同步生成每周摘要（CLI 使用）

    Args:
        db_path: 数据库文件路径
        ai_config: AI 客户端配置
        start_date: 开始日期（默认为上周一）
        end_date: 结束日期（默认为上周日）

    Returns:
        生成的记忆对象，如果没有数据则返回 None

    Raises:
        Exception: 生成失败时抛出异常
    """
    return asyncio.run(generate_weekly_digest_task(db_path, ai_config, start_date, end_date))
