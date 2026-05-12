#!/usr/bin/env python3
# coding=utf-8
"""
OSS 数据库到 Markdown 迁移脚本

1. 从 OSS 下载 memory.db
2. 转换为 Markdown 格式
3. 可选上传 Markdown 文件到 OSS
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trendradar.memory.storage import DatabaseBackend, FileBackend
from trendradar.memory.models import Memory


def download_db_from_oss(config: dict, local_path: str) -> bool:
    """
    从 OSS 下载 memory.db 文件

    Args:
        config: 配置字典
        local_path: 本地保存路径

    Returns:
        是否成功
    """
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    print("📥 从 OSS 下载 memory.db...")

    remote_config = config['storage']['remote']

    # 创建 S3 客户端（阿里云 OSS 需要特殊配置）
    try:
        # 阿里云 OSS 需要 virtual hosted style 和 v2 签名
        s3_config = Config(
            s3={'addressing_style': 'virtual'},
            signature_version='s3'  # v2 签名
        )

        s3_client = boto3.client(
            's3',
            endpoint_url=remote_config['endpoint_url'],
            aws_access_key_id=remote_config['access_key_id'],
            aws_secret_access_key=remote_config['secret_access_key'],
            region_name=remote_config.get('region', ''),
            config=s3_config
        )
    except Exception as e:
        print(f"❌ 创建 S3 客户端失败: {e}")
        return False

    # 下载 memory.db 文件
    try:
        # memory.db 在 databases/ 目录下
        remote_key = "databases/memory.db"
        bucket_name = remote_config['bucket_name']

        print(f"   从 OSS 下载: {remote_key}")
        s3_client.download_file(bucket_name, remote_key, local_path)

        if Path(local_path).exists():
            file_size = Path(local_path).stat().st_size
            print(f"✅ 下载成功: {local_path} ({file_size / 1024:.1f} KB)")
            return True
        else:
            print(f"❌ 下载失败或文件不存在")
            return False

    except ClientError as e:
        if e.response['Error']['Code'] == '404' or e.response['Error']['Code'] == 'NoSuchKey':
            print(f"❌ OSS 上不存在 databases/memory.db 文件")
        else:
            print(f"❌ 下载失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def upload_markdown_to_oss(config: dict, local_dir: str) -> bool:
    """
    上传 Markdown 文件到 OSS

    Args:
        config: 配置字典
        local_dir: 本地 Markdown 目录

    Returns:
        是否成功
    """
    import boto3
    from botocore.config import Config

    print("\n📤 上传 Markdown 文件到 OSS...")

    remote_config = config['storage']['remote']

    # 创建 S3 客户端（阿里云 OSS 需要特殊配置）
    try:
        s3_config = Config(
            s3={'addressing_style': 'virtual'},
            signature_version='s3'
        )

        s3_client = boto3.client(
            's3',
            endpoint_url=remote_config['endpoint_url'],
            aws_access_key_id=remote_config['access_key_id'],
            aws_secret_access_key=remote_config['secret_access_key'],
            region_name=remote_config.get('region', ''),
            config=s3_config
        )
    except Exception as e:
        print(f"❌ 创建 S3 客户端失败: {e}")
        return False

    # 收集所有 Markdown 文件
    local_path = Path(local_dir)
    markdown_files = list(local_path.rglob("*.md"))

    if not markdown_files:
        print("⚠️  没有找到 Markdown 文件")
        return False

    print(f"   找到 {len(markdown_files)} 个文件")

    success_count = 0
    failed_count = 0
    bucket_name = remote_config['bucket_name']

    for md_file in markdown_files:
        try:
            # 计算相对路径作为 OSS key
            relative_path = md_file.relative_to(local_path)
            remote_key = f"memory_markdown/{relative_path}".replace('\\', '/')  # Windows 路径兼容

            # 上传文件
            s3_client.upload_file(str(md_file), bucket_name, remote_key)
            success_count += 1
            print(f"   ✅ {relative_path}")

        except Exception as e:
            failed_count += 1
            print(f"   ❌ {md_file.name}: {e}")

    print(f"\n上传完成: 成功 {success_count}, 失败 {failed_count}")
    return failed_count == 0


def migrate_oss_to_markdown(
    config_path: str = "config/config.yaml",
    output_dir: str = "output/memory_markdown",
    upload_to_oss: bool = False,
    keep_temp: bool = False
) -> dict:
    """
    从 OSS 迁移数据库到 Markdown

    Args:
        config_path: 配置文件路径
        output_dir: 输出目录
        upload_to_oss: 是否上传到 OSS
        keep_temp: 是否保留临时下载的数据库文件

    Returns:
        迁移统计信息
    """
    # 加载 .env 文件
    print("🔧 加载配置...")
    env_file = Path(".env")
    if env_file.exists():
        print("   加载 .env 文件...")
        from dotenv import load_dotenv
        load_dotenv()

    import yaml

    config_file = Path(config_path)
    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 确保有 storage.remote 配置
    if 'storage' not in config:
        config['storage'] = {}
    if 'remote' not in config['storage']:
        config['storage']['remote'] = {}

    # 从环境变量获取 OSS 配置（优先级高于配置文件）
    remote_config = config['storage']['remote']
    remote_config['endpoint_url'] = os.getenv('S3_ENDPOINT_URL', remote_config.get('endpoint_url', ''))
    remote_config['bucket_name'] = os.getenv('S3_BUCKET_NAME', remote_config.get('bucket_name', ''))
    remote_config['access_key_id'] = os.getenv('S3_ACCESS_KEY_ID', remote_config.get('access_key_id', ''))
    remote_config['secret_access_key'] = os.getenv('S3_SECRET_ACCESS_KEY', remote_config.get('secret_access_key', ''))
    remote_config['region'] = os.getenv('S3_REGION', remote_config.get('region', ''))

    # 检查是否配置了凭证
    if not remote_config.get('endpoint_url') or not remote_config.get('bucket_name'):
        print("❌ 远程存储配置不完整")
        print("   需要在 .env 文件或环境变量中配置:")
        print("   - S3_ENDPOINT_URL")
        print("   - S3_BUCKET_NAME")
        print("   - S3_ACCESS_KEY_ID")
        print("   - S3_SECRET_ACCESS_KEY")
        sys.exit(1)

    print(f"   OSS Endpoint: {remote_config['endpoint_url']}")
    print(f"   Bucket: {remote_config['bucket_name']}")

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="trendradar_oss_")
    temp_db_path = os.path.join(temp_dir, "memory.db")

    try:
        # 1. 从 OSS 下载数据库
        if not download_db_from_oss(config, temp_db_path):
            print("\n❌ 从 OSS 下载失败")
            return {"total": 0, "success": 0, "failed": 0}

        # 2. 转换为 Markdown
        print(f"\n🔄 转换数据库到 Markdown 格式...")
        print(f"   目标目录: {output_dir}\n")

        db_backend = DatabaseBackend(temp_db_path)
        file_backend = FileBackend(output_dir, auto_index=True)

        # 统计信息
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'by_type': {}
        }

        # 获取所有记忆
        all_memories = db_backend.list_memories()
        stats['total'] = len(all_memories)

        if stats['total'] == 0:
            print("⚠️  OSS 数据库中没有记忆数据")
            return stats

        print(f"📊 找到 {stats['total']} 条记忆")

        # 按类型统计
        from collections import defaultdict
        type_counts = defaultdict(int)
        for memory in all_memories:
            type_counts[memory.type] += 1

        print("\n记忆类型分布:")
        for mem_type, count in sorted(type_counts.items()):
            print(f"   - {mem_type}: {count} 条")
        print()

        # 转换每条记忆
        print("✍️  写入 Markdown 文件...")
        for i, memory in enumerate(all_memories, 1):
            try:
                # 确保 metadata 中有 date 字段
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

        print("\n" + "=" * 60)
        print("✅ 转换完成！")
        print(f"\n📈 统计信息:")
        print(f"   - 总计: {stats['total']} 条")
        print(f"   - 成功: {stats['success']} 条")
        print(f"   - 失败: {stats['failed']} 条")

        if stats['by_type']:
            print("\n📂 按类型统计:")
            for mem_type, count in sorted(stats['by_type'].items()):
                print(f"   - {mem_type}: {count} 条")

        index_file = Path(output_dir) / "MEMORY.md"
        if index_file.exists():
            print(f"\n📑 索引文件已生成: {index_file}")

        # 3. 可选：上传到 OSS
        if upload_to_oss:
            if not upload_markdown_to_oss(config, output_dir):
                print("\n⚠️  上传到 OSS 失败（但本地文件已生成）")

        return stats

    finally:
        # 清理临时文件
        if not keep_temp and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"\n🧹 已清理临时文件: {temp_dir}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='从 OSS 下载数据库并转换为 Markdown 格式'
    )
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='配置文件路径（默认: config/config.yaml）'
    )
    parser.add_argument(
        '--output-dir',
        default='output/memory_markdown',
        help='输出目录（默认: output/memory_markdown）'
    )
    parser.add_argument(
        '--upload',
        action='store_true',
        help='转换后上传 Markdown 文件到 OSS'
    )
    parser.add_argument(
        '--keep-temp',
        action='store_true',
        help='保留临时下载的数据库文件'
    )

    args = parser.parse_args()

    try:
        stats = migrate_oss_to_markdown(
            config_path=args.config,
            output_dir=args.output_dir,
            upload_to_oss=args.upload,
            keep_temp=args.keep_temp
        )

        if stats['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
