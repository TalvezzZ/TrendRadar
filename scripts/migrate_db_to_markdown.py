#!/usr/bin/env python3
# coding=utf-8
"""
数据库到 Markdown 迁移脚本

将 SQLite 数据库中的记忆数据迁移到 Markdown 文件格式
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trendradar.memory.storage import DatabaseBackend, FileBackend
from trendradar.memory.models import Memory


def migrate_database_to_markdown(
    db_path: str,
    output_path: str,
    auto_index: bool = True
) -> dict:
    """
    将数据库中的记忆迁移到 Markdown 文件

    Args:
        db_path: 源数据库文件路径
        output_path: 目标 Markdown 文件目录
        auto_index: 是否自动生成索引文件

    Returns:
        迁移统计信息
    """
    print(f"🚀 开始迁移数据...")
    print(f"   源数据库: {db_path}")
    print(f"   目标目录: {output_path}")
    print()

    # 初始化后端
    db_backend = DatabaseBackend(db_path)
    file_backend = FileBackend(output_path, auto_index=auto_index)

    # 统计信息
    stats = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'by_type': {}
    }

    # 获取所有记忆
    print("📖 读取数据库中的所有记忆...")
    all_memories = db_backend.list_memories()
    stats['total'] = len(all_memories)
    print(f"   找到 {stats['total']} 条记忆")
    print()

    if stats['total'] == 0:
        print("⚠️  数据库中没有记忆数据，跳过迁移")
        return stats

    # 按类型分组显示
    from collections import defaultdict
    type_counts = defaultdict(int)
    for memory in all_memories:
        type_counts[memory.type] += 1

    print("📊 记忆类型分布:")
    for mem_type, count in sorted(type_counts.items()):
        print(f"   - {mem_type}: {count} 条")
    print()

    # 迁移每条记忆
    print("✍️  开始写入 Markdown 文件...")
    for i, memory in enumerate(all_memories, 1):
        try:
            # 确保 metadata 中有 date 字段（用于文件路径生成）
            if 'date' not in memory.metadata:
                memory = Memory(
                    id=memory.id,
                    type=memory.type,
                    title=memory.title,
                    description=memory.description,
                    content=memory.content,
                    metadata={**memory.metadata, 'date': memory.created_at.isoformat()},
                    created_at=memory.created_at,
                    updated_at=memory.updated_at
                )

            file_backend.create_memory(memory)
            stats['success'] += 1
            stats['by_type'][memory.type] = stats['by_type'].get(memory.type, 0) + 1

            if i % 10 == 0 or i == stats['total']:
                print(f"   进度: {i}/{stats['total']} ({i*100//stats['total']}%)")

        except Exception as e:
            stats['failed'] += 1
            print(f"   ❌ 失败: {memory.id} - {e}")

    print()
    print("=" * 60)
    print("✅ 迁移完成！")
    print()
    print(f"📈 统计信息:")
    print(f"   - 总计: {stats['total']} 条")
    print(f"   - 成功: {stats['success']} 条")
    print(f"   - 失败: {stats['failed']} 条")
    print()

    if stats['by_type']:
        print("📂 按类型统计:")
        for mem_type, count in sorted(stats['by_type'].items()):
            print(f"   - {mem_type}: {count} 条")
        print()

    if auto_index:
        index_file = Path(output_path) / "MEMORY.md"
        if index_file.exists():
            print(f"📑 索引文件已生成: {index_file}")
            print()

    return stats


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='将 SQLite 数据库中的记忆迁移到 Markdown 文件格式'
    )
    parser.add_argument(
        '--db-path',
        default='output/memory.db',
        help='源数据库文件路径（默认: output/memory.db）'
    )
    parser.add_argument(
        '--output-path',
        default='output/memory_markdown',
        help='目标 Markdown 文件目录（默认: output/memory_markdown）'
    )
    parser.add_argument(
        '--no-index',
        action='store_true',
        help='不生成索引文件'
    )

    args = parser.parse_args()

    # 检查源文件是否存在
    db_file = Path(args.db_path)
    if not db_file.exists():
        print(f"❌ 错误: 数据库文件不存在: {args.db_path}")
        sys.exit(1)

    # 执行迁移
    try:
        stats = migrate_database_to_markdown(
            db_path=args.db_path,
            output_path=args.output_path,
            auto_index=not args.no_index
        )

        # 根据结果返回退出码
        if stats['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
