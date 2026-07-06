"""
迁移 OSS 文件结构

将 news/ 和 rss/ 顶层目录的文件迁移到 databases/news/ 和 databases/rss/
这是为了统一路径结构，使上传和下载使用相同的路径格式
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


def migrate_files(s3_client, bucket_name, dry_run=True):
    """
    迁移文件从旧结构到新结构

    旧结构:
      - news/YYYY-MM-DD.db
      - rss/YYYY-MM-DD.db

    新结构:
      - databases/news/YYYY-MM-DD.db
      - databases/rss/YYYY-MM-DD.db

    Args:
        s3_client: S3 客户端
        bucket_name: 存储桶名称
        dry_run: 是否只是预览，不执行实际操作
    """
    prefixes = ['news/', 'rss/']
    total_migrated = 0

    for prefix in prefixes:
        print(f"\n{'='*60}")
        print(f"处理 {prefix} 目录")
        print(f"{'='*60}")

        try:
            # 列出所有对象
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

            files_to_migrate = []

            for page in pages:
                if 'Contents' not in page:
                    print(f"✓ {prefix} 目录为空，跳过")
                    continue

                for obj in page['Contents']:
                    key = obj['Key']
                    size = obj['Size']
                    modified = obj['LastModified']

                    # 跳过目录对象
                    if key.endswith('/'):
                        continue

                    # 跳过非 .db 文件
                    if not key.endswith('.db'):
                        continue

                    # 构造新路径: news/2026-04-26.db -> databases/news/2026-04-26.db
                    new_key = f"databases/{key}"

                    files_to_migrate.append({
                        'old_key': key,
                        'new_key': new_key,
                        'size': size,
                        'modified': modified
                    })

            if not files_to_migrate:
                print(f"✓ 没有需要迁移的文件")
                continue

            print(f"\n找到 {len(files_to_migrate)} 个文件需要迁移:")
            for f in files_to_migrate:
                print(f"  {f['old_key']:<30} -> {f['new_key']:<35} ({f['size']/1024:.1f} KB)")

            if dry_run:
                print(f"\n[预览模式] 将迁移 {len(files_to_migrate)} 个文件")
                continue

            # 执行迁移
            print(f"\n开始迁移...")
            migrated = 0
            failed = 0

            for f in files_to_migrate:
                old_key = f['old_key']
                new_key = f['new_key']

                try:
                    # 检查新位置是否已存在
                    try:
                        new_obj = s3_client.head_object(Bucket=bucket_name, Key=new_key)
                        new_size = new_obj['ContentLength']

                        # 如果新文件已存在且大小相同，跳过
                        if new_size == f['size']:
                            print(f"  ⊙ 跳过: {old_key} (目标已存在)")
                            continue
                        else:
                            print(f"  ⚠ 覆盖: {old_key} (目标存在但大小不同: {new_size/1024:.1f} KB vs {f['size']/1024:.1f} KB)")
                    except ClientError as e:
                        if e.response['Error']['Code'] != '404':
                            raise

                    # 复制文件（服务端复制，不需要下载）
                    copy_source = {'Bucket': bucket_name, 'Key': old_key}
                    s3_client.copy_object(
                        CopySource=copy_source,
                        Bucket=bucket_name,
                        Key=new_key
                    )

                    migrated += 1
                    print(f"  ✓ 迁移成功: {old_key}")

                except Exception as e:
                    failed += 1
                    print(f"  ✗ 迁移失败: {old_key} - {e}")

            print(f"\n{prefix} 迁移完成: 成功 {migrated}, 失败 {failed}")
            total_migrated += migrated

        except Exception as e:
            print(f"✗ 处理 {prefix} 时出错: {e}")
            import traceback
            traceback.print_exc()

    return total_migrated


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='迁移 OSS 文件结构')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认，不询问')
    args = parser.parse_args()

    print("=" * 60)
    print("OSS 文件结构迁移工具")
    print("=" * 60)

    # 检查环境变量
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    access_key_id = os.environ.get("S3_ACCESS_KEY_ID")
    secret_access_key = os.environ.get("S3_SECRET_ACCESS_KEY")
    endpoint_url = os.environ.get("S3_ENDPOINT_URL")

    if not all([bucket_name, access_key_id, secret_access_key, endpoint_url]):
        print("❌ 错误：缺少必要的环境变量")
        print("需要设置: S3_BUCKET_NAME, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL")
        return False

    try:
        # 创建 S3 客户端
        s3_config = Config(
            s3={"addressing_style": "virtual"},
            signature_version='s3'
        )

        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=s3_config
        )

        # 先预览
        print("\n[预览模式] 检查需要迁移的文件...")
        migrate_files(s3_client, bucket_name, dry_run=True)

        # 询问确认
        print("\n" + "=" * 60)
        if not args.yes:
            response = input("确认执行迁移？(yes/no): ").strip().lower()
            if response != 'yes':
                print("取消迁移")
                return False
        else:
            print("自动确认模式，开始迁移...")

        # 执行迁移
        print("\n" + "=" * 60)
        print("开始执行迁移...")
        print("=" * 60)
        total = migrate_files(s3_client, bucket_name, dry_run=False)

        print("\n" + "=" * 60)
        print(f"✅ 迁移完成，共迁移 {total} 个文件")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
