#!/usr/bin/env python3
# coding=utf-8
"""上传 Markdown 文件到 OSS"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.config import Config

# 加载 .env
load_dotenv()

def upload_markdown_to_oss(local_dir: str, oss_prefix: str = "memory_markdown"):
    """上传 Markdown 目录到 OSS"""

    print(f"📤 上传 Markdown 文件到 OSS...")
    print(f"   本地目录: {local_dir}")
    print(f"   OSS 前缀: {oss_prefix}")
    print()

    # 创建 S3 客户端（阿里云 OSS 配置）
    s3_config = Config(
        s3={'addressing_style': 'virtual'},
        signature_version='s3'
    )

    s3_client = boto3.client(
        's3',
        endpoint_url=os.getenv('S3_ENDPOINT_URL'),
        aws_access_key_id=os.getenv('S3_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('S3_SECRET_ACCESS_KEY'),
        region_name=os.getenv('S3_REGION', ''),
        config=s3_config
    )

    bucket_name = os.getenv('S3_BUCKET_NAME')

    # 收集所有文件
    local_path = Path(local_dir)
    all_files = list(local_path.rglob("*"))

    # 过滤出文件（不包括目录）
    files_to_upload = [f for f in all_files if f.is_file()]

    if not files_to_upload:
        print("⚠️  没有找到文件")
        return

    print(f"找到 {len(files_to_upload)} 个文件\n")

    success_count = 0
    failed_count = 0

    for file_path in files_to_upload:
        try:
            # 计算相对路径
            relative_path = file_path.relative_to(local_path)

            # 构建 OSS key
            oss_key = f"{oss_prefix}/{relative_path}".replace('\\', '/')

            # 上传文件
            s3_client.upload_file(str(file_path), bucket_name, oss_key)
            success_count += 1
            print(f"✅ {relative_path}")

        except Exception as e:
            failed_count += 1
            print(f"❌ {file_path.name}: {e}")

    print()
    print("=" * 60)
    print(f"上传完成: 成功 {success_count}, 失败 {failed_count}")

    if success_count > 0:
        print(f"\n📁 文件已上传到: {bucket_name}/{oss_prefix}/")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='上传 Markdown 文件到 OSS')
    parser.add_argument('local_dir', help='本地 Markdown 目录')
    parser.add_argument('--prefix', default='memory_markdown', help='OSS 前缀路径')

    args = parser.parse_args()

    if not Path(args.local_dir).exists():
        print(f"❌ 目录不存在: {args.local_dir}")
        sys.exit(1)

    try:
        upload_markdown_to_oss(args.local_dir, args.prefix)
    except Exception as e:
        print(f"❌ 上传失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
