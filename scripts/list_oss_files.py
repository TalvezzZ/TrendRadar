#!/usr/bin/env python3
# coding=utf-8
"""列出 OSS 中的文件"""

import os
from pathlib import Path
from dotenv import load_dotenv
import boto3

# 加载 .env
load_dotenv()

# 创建 S3 客户端（阿里云 OSS 需要 virtual hosted style）
from botocore.config import Config

s3_config = Config(
    s3={'addressing_style': 'virtual'},
    signature_version='s3'  # 阿里云 OSS 使用 v2 签名
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

print(f"📦 Bucket: {bucket_name}")
print(f"🌐 Endpoint: {os.getenv('S3_ENDPOINT_URL')}")
print("\n📁 OSS 文件列表:\n")

try:
    # 列出所有对象
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket_name)

    count = 0
    db_files = []

    for page in page_iterator:
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                size = obj['Size']
                modified = obj['LastModified']

                # 检查是否是 .db 文件
                if key.endswith('.db'):
                    db_files.append(key)
                    print(f"💾 {key} ({size / 1024:.1f} KB) - {modified}")
                    count += 1
                elif count < 50:  # 只显示前 50 个非数据库文件
                    print(f"   {key} ({size / 1024:.1f} KB)")
                    count += 1

    if db_files:
        print(f"\n\n🎯 找到 {len(db_files)} 个数据库文件:")
        for db_file in db_files:
            print(f"   - {db_file}")
    else:
        print("\n⚠️  未找到 .db 文件")

    print(f"\n总计显示: {count} 个文件")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
