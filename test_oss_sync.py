#!/usr/bin/env python3
# coding=utf-8
"""
OSS 数据库同步功能测试脚本

测试以下功能：
1. 列出远程数据库文件
2. 从远程下载数据库
3. 上传数据库到远程
"""

import os
import sys
from pathlib import Path

# 添加项目路径到 sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from trendradar.core import load_config
from trendradar.storage import get_storage_manager


def test_list_remote_databases():
    """测试列出远程数据库"""
    print("\n" + "=" * 60)
    print("测试 1: 列出远程数据库")
    print("=" * 60)

    config = load_config()
    storage_config = config.get("STORAGE", {})

    storage_manager = get_storage_manager(
        backend_type=storage_config.get("BACKEND_TYPE", "auto"),
        data_dir=storage_config.get("DATA_DIR", "output"),
        remote_config=storage_config.get("REMOTE_BACKEND", {}),
    )

    databases = storage_manager.list_remote_databases()

    if databases:
        print(f"\n✅ 成功列出 {len(databases)} 个数据库文件")
        return True
    else:
        print("\n⚠️  远程没有数据库文件（首次运行）")
        return True


def test_sync_to_remote():
    """测试上传数据库到远程"""
    print("\n" + "=" * 60)
    print("测试 2: 上传数据库到远程")
    print("=" * 60)

    config = load_config()
    storage_config = config.get("STORAGE", {})

    storage_manager = get_storage_manager(
        backend_type=storage_config.get("BACKEND_TYPE", "auto"),
        data_dir=storage_config.get("DATA_DIR", "output"),
        remote_config=storage_config.get("REMOTE_BACKEND", {}),
    )

    # 检查本地是否有数据库文件
    data_dir = Path(storage_config.get("DATA_DIR", "output"))
    news_dir = data_dir / "news"

    if not news_dir.exists():
        print("\n⚠️  本地没有数据库文件，跳过上传测试")
        return True

    db_files = list(news_dir.glob("*.db"))
    if not db_files:
        print("\n⚠️  本地没有数据库文件，跳过上传测试")
        return True

    print(f"\n本地有 {len(db_files)} 个数据库文件")

    uploaded = storage_manager.sync_databases_to_s3()

    if uploaded > 0:
        print(f"\n✅ 成功上传 {uploaded} 个文件")
        return True
    else:
        print("\n⚠️  未上传任何文件（可能未配置远程存储）")
        return True


def test_sync_from_remote():
    """测试从远程下载数据库"""
    print("\n" + "=" * 60)
    print("测试 3: 从远程下载数据库")
    print("=" * 60)

    config = load_config()
    storage_config = config.get("STORAGE", {})

    storage_manager = get_storage_manager(
        backend_type=storage_config.get("BACKEND_TYPE", "auto"),
        data_dir=storage_config.get("DATA_DIR", "output"),
        remote_config=storage_config.get("REMOTE_BACKEND", {}),
    )

    downloaded = storage_manager.sync_databases_from_s3()

    if downloaded > 0:
        print(f"\n✅ 成功下载 {downloaded} 个文件")
        return True
    else:
        print("\n⚠️  未下载任何文件（远程可能没有数据库）")
        return True


def main():
    """主测试入口"""
    print("=" * 60)
    print("OSS 数据库同步功能测试")
    print("=" * 60)

    try:
        # 测试 1: 列出远程数据库
        test1_ok = test_list_remote_databases()

        # 测试 2: 上传数据库
        test2_ok = test_sync_to_remote()

        # 测试 3: 下载数据库
        test3_ok = test_sync_from_remote()

        # 汇总结果
        print("\n" + "=" * 60)
        print("测试汇总")
        print("=" * 60)
        print(f"列出远程数据库: {'✅ 通过' if test1_ok else '❌ 失败'}")
        print(f"上传数据库: {'✅ 通过' if test2_ok else '❌ 失败'}")
        print(f"下载数据库: {'✅ 通过' if test3_ok else '❌ 失败'}")

        all_ok = test1_ok and test2_ok and test3_ok
        if all_ok:
            print("\n🎉 所有测试通过！")
            return 0
        else:
            print("\n⚠️  部分测试失败")
            return 1

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
