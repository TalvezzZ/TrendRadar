#!/usr/bin/env python3
# coding=utf-8
"""
批量补全历史记忆

扫描已有数据库，为缺失记忆的日期生成记忆
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trendradar.core import load_config
from trendradar.memory.scheduler import generate_daily_summary_sync

# 加载 .env
load_dotenv()


def get_existing_dates(databases_dir: str) -> list[str]:
    """获取所有有数据的日期"""
    db_dir = Path(databases_dir)
    if not db_dir.exists():
        return []

    dates = []
    for db_file in sorted(db_dir.glob("*.db")):
        date_str = db_file.stem  # 2026-04-26
        if date_str.startswith("2026"):  # 只处理 2026 年的数据
            dates.append(date_str)

    return dates


def get_existing_memories(db_path: str) -> set[str]:
    """获取已有的记忆日期"""
    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 从 id 中提取日期（格式：daily_summary_YYYYMMDD）
        cursor.execute("""
            SELECT DISTINCT
                substr(id, 16, 4) || '-' || substr(id, 20, 2) || '-' || substr(id, 22, 2) as date
            FROM memories
            WHERE type = 'daily_summary'
        """)

        dates = {row[0] for row in cursor.fetchall()}
        conn.close()

        return dates

    except Exception as e:
        print(f"⚠️  读取记忆数据库失败: {e}")
        return set()


def backfill_memories(
    databases_dir: str,
    memory_db_path: str,
    start_date: str = "2026-01-01"
):
    """批量生成缺失的记忆"""

    print("🔍 扫描数据库文件...")

    # 获取所有有数据的日期
    available_dates = get_existing_dates(databases_dir)
    print(f"   找到 {len(available_dates)} 个日期的数据")

    # 过滤出需要的日期（>= start_date）
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    filtered_dates = [
        date for date in available_dates
        if datetime.strptime(date, "%Y-%m-%d") >= start_dt
    ]
    print(f"   过滤后剩余 {len(filtered_dates)} 个日期（>= {start_date}）")

    # 获取已有的记忆
    existing_memories = get_existing_memories(memory_db_path)
    print(f"   已有 {len(existing_memories)} 条记忆")

    # 找出缺失的日期
    missing_dates = [date for date in filtered_dates if date not in existing_memories]

    if not missing_dates:
        print("\n✅ 所有日期的记忆都已存在，无需补全")
        return

    print(f"\n📝 需要补全 {len(missing_dates)} 个日期的记忆:")
    for date in missing_dates:
        print(f"   - {date}")

    # 加载配置
    print("\n🔧 加载配置...")
    config = load_config()
    ai_config = config.get("AI", {})

    if not ai_config:
        print("❌ 未找到 AI 配置")
        sys.exit(1)

    # 批量生成记忆
    print("\n🚀 开始生成记忆...\n")

    success_count = 0
    failed_count = 0

    for i, date_str in enumerate(missing_dates, 1):
        print(f"[{i}/{len(missing_dates)}] 生成 {date_str} 的记忆...")

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            memory = generate_daily_summary_sync(memory_db_path, ai_config, date_obj)

            if memory:
                success_count += 1
                print(f"         ✅ 成功: {memory.title}")
            else:
                print(f"         ⚠️  无数据")

        except Exception as e:
            failed_count += 1
            print(f"         ❌ 失败: {e}")

    # 统计
    print("\n" + "=" * 70)
    print("📊 补全统计:\n")
    print(f"   需要补全: {len(missing_dates)}")
    print(f"   成功: {success_count}")
    print(f"   失败: {failed_count}")
    print(f"\n💾 记忆数据库: {memory_db_path}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='批量补全历史记忆')
    parser.add_argument(
        '--databases-dir',
        default='output/oss_sync/databases/news',
        help='数据库目录（默认: output/oss_sync/databases/news）'
    )
    parser.add_argument(
        '--memory-db',
        default='output/memory.db',
        help='记忆数据库路径（默认: output/memory.db）'
    )
    parser.add_argument(
        '--start-date',
        default='2026-01-01',
        help='开始日期（默认: 2026-01-01）'
    )

    args = parser.parse_args()

    try:
        backfill_memories(
            databases_dir=args.databases_dir,
            memory_db_path=args.memory_db,
            start_date=args.start_date
        )
        print("\n✅ 补全完成！")

    except Exception as e:
        print(f"\n❌ 补全失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
