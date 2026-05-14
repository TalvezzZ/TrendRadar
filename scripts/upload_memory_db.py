#!/usr/bin/env python3
# coding=utf-8
"""上传 memory.db 到 OSS"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.config import Config

# 加载 .env
env_file = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_file)


def upload_memory_db(local_file='output/memory.db', remote_key='databases/memory.db'):
    """上传 memory.db 到 OSS"""

    if not Path(local_file).exists():
        print(f"❌ 文件不存在: {local_file}")
        sys.exit(1)

    print(f"📤 上传 {local_file} 到 OSS...\n")

    # 创建 S3 客户端
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
    local_size = Path(local_file).stat().st_size

    print(f"   Bucket: {bucket_name}")
    print(f"   远程路径: {remote_key}")
    print(f"   文件大小: {local_size / 1024:.1f} KB\n")

    # 上传文件
    try:
        with open(local_file, 'rb') as f:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=remote_key,
                Body=f,
                ContentType='application/x-sqlite3'
            )

        print(f"✅ 上传成功！")

    except Exception as e:
        print(f"❌ 上传失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    upload_memory_db()
