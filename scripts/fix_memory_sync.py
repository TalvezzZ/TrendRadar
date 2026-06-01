#!/usr/bin/env python3
"""
修复记忆文件同步问题

问题: 上传时直接覆盖远程文件,导致记忆丢失
解决: 先下载远程文件,合并到本地,然后再上传
"""

import os
import sys
from pathlib import Path
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from datetime import timezone, datetime

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def parse_markdown_file(content: str) -> list:
    """解析 Markdown 文件,返回所有记忆的 ID"""
    import re
    # 匹配 id: xxx 格式
    return re.findall(r'^id:\s+(.+?)\s*$', content, re.MULTILINE)


def merge_markdown_files(local_content: str, remote_content: str) -> str:
    """
    合并本地和远程的 Markdown 文件

    策略:
    - 提取所有记忆的 ID
    - 保留远程独有的记忆
    - 追加到本地文件末尾
    """
    local_ids = set(parse_markdown_file(local_content))
    remote_ids = set(parse_markdown_file(remote_content))

    # 找出远程独有的记忆
    remote_only_ids = remote_ids - local_ids

    if not remote_only_ids:
        print(f"  没有发现远程独有的记忆,无需合并")
        return local_content

    print(f"  发现远程独有的记忆: {len(remote_only_ids)} 条")

    # 分割远程内容为多个记忆
    sections = remote_content.split("\n---\n")
    merged_content = local_content.rstrip()

    i = 0
    while i < len(sections):
        # YAML frontmatter
        if i == 0 and sections[i].startswith("---\n"):
            yaml_section = sections[i][4:]  # 跳过开头的 "---\n"
        else:
            yaml_section = sections[i]

        # Markdown 内容
        if i + 1 < len(sections):
            md_section = sections[i + 1].strip()
        else:
            md_section = ""

        # 检查这个记忆的 ID 是否是远程独有的
        import re
        id_match = re.search(r'^id:\s+(.+?)\s*$', yaml_section, re.MULTILINE)
        if id_match:
            memory_id = id_match.group(1)
            if memory_id in remote_only_ids:
                # 追加到本地内容
                memory_block = f"---\n{yaml_section}---\n\n{md_section}\n"
                merged_content += "\n" + memory_block
                print(f"    追加记忆: {memory_id}")

        i += 2  # 每个记忆占两个 section

    return merged_content


def fix_memory_sync():
    """修复记忆文件同步"""
    print("=" * 60)
    print("修复记忆文件同步")
    print("=" * 60)

    # 读取配置
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    access_key = os.environ.get('S3_ACCESS_KEY_ID')
    secret_key = os.environ.get('S3_SECRET_ACCESS_KEY')
    endpoint = os.environ.get('S3_ENDPOINT_URL', '')
    region = os.environ.get('S3_REGION', '')

    if not all([bucket_name, access_key, secret_key, endpoint]):
        print("❌ 缺少S3配置,请检查环境变量")
        return False

    # 创建 S3 客户端
    use_sigv2 = 'aliyuncs.com' in endpoint.lower()
    signature_version = 's3' if use_sigv2 else 's3v4'

    s3_config = BotoConfig(
        s3={'addressing_style': 'virtual'},
        signature_version=signature_version,
    )

    client_kwargs = {
        'endpoint_url': endpoint,
        'aws_access_key_id': access_key,
        'aws_secret_access_key': secret_key,
        'config': s3_config,
    }
    if region:
        client_kwargs['region_name'] = region

    s3_client = boto3.client('s3', **client_kwargs)

    # 本地记忆目录
    memory_dir = project_root / "output" / "memory_markdown"

    if not memory_dir.exists():
        print(f"❌ 记忆目录不存在: {memory_dir}")
        return False

    # 查找所有本地记忆文件
    md_files = list(memory_dir.rglob("*.md"))
    print(f"\n找到 {len(md_files)} 个本地记忆文件")

    fixed_count = 0

    for md_file in md_files:
        if md_file.name == "MEMORY.md":
            continue

        try:
            # 计算远程路径
            relative_path = md_file.relative_to(memory_dir)
            remote_key = f"memory_markdown/{relative_path}"

            print(f"\n处理文件: {relative_path}")

            # 读取本地文件
            local_content = md_file.read_text(encoding='utf-8')
            local_ids = parse_markdown_file(local_content)
            print(f"  本地记忆数: {len(local_ids)}")

            # 尝试下载远程文件
            try:
                response = s3_client.get_object(Bucket=bucket_name, Key=remote_key)
                remote_content = response['Body'].read().decode('utf-8')
                remote_ids = parse_markdown_file(remote_content)
                print(f"  远程记忆数: {len(remote_ids)}")

                # 合并本地和远程
                merged_content = merge_markdown_files(local_content, remote_content)
                merged_ids = parse_markdown_file(merged_content)

                if len(merged_ids) > len(local_ids):
                    print(f"  合并后记忆数: {len(merged_ids)} (增加了 {len(merged_ids) - len(local_ids)} 条)")

                    # 保存合并后的内容到本地
                    md_file.write_text(merged_content, encoding='utf-8')
                    print(f"  ✓ 已保存合并后的文件到本地")

                    # 上传到远程
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=remote_key,
                        Body=merged_content.encode('utf-8'),
                        ContentType='text/markdown; charset=utf-8',
                    )
                    print(f"  ✓ 已上传合并后的文件到OSS")
                    fixed_count += 1
                else:
                    print(f"  合并后记忆数: {len(merged_ids)} (无变化)")

            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    print(f"  远程文件不存在,将上传本地文件")
                    # 上传本地文件
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=remote_key,
                        Body=local_content.encode('utf-8'),
                        ContentType='text/markdown; charset=utf-8',
                    )
                    print(f"  ✓ 已上传到OSS")
                    fixed_count += 1
                else:
                    raise

        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"修复完成! 共处理 {fixed_count} 个文件")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = fix_memory_sync()
    sys.exit(0 if success else 1)
