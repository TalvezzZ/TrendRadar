#!/usr/bin/env python3
# coding=utf-8
"""Generate custom memory records and sync them with OSS."""

import argparse
import os
from datetime import datetime
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from trendradar.core.loader import load_config
from trendradar_custom.memory.scheduler import (
    generate_daily_summary_sync,
    generate_weekly_digest_sync,
)
from trendradar_custom.scripts.upload_markdown_to_oss import upload_markdown_to_oss


DB_PATH = Path("output/ai_analysis.db")
MEMORY_DIR = Path("output/memory_markdown")
REMOTE_DB_KEY = "databases/ai_analysis.db"


def _build_s3_client():
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    endpoint_url = os.environ.get("S3_ENDPOINT_URL")
    access_key_id = os.environ.get("S3_ACCESS_KEY_ID")
    secret_access_key = os.environ.get("S3_SECRET_ACCESS_KEY")

    missing = [
        name
        for name, value in {
            "S3_BUCKET_NAME": bucket_name,
            "S3_ENDPOINT_URL": endpoint_url,
            "S3_ACCESS_KEY_ID": access_key_id,
            "S3_SECRET_ACCESS_KEY": secret_access_key,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing OSS environment variables: {', '.join(missing)}")

    s3_config = Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3",
    )
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=os.environ.get("S3_REGION", ""),
        config=s3_config,
    )
    return client, bucket_name


def _download_file(client, bucket_name: str, remote_key: str, local_path: Path) -> bool:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        client.download_file(bucket_name, remote_key, str(local_path))
        print(f"[memory] Downloaded {remote_key} -> {local_path}")
        return True
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchKey", "Not Found"):
            print(f"[memory] Remote file not found, will create locally: {remote_key}")
            return False
        raise


def _upload_file(client, bucket_name: str, local_path: Path, remote_key: str) -> None:
    if not local_path.exists():
        print(f"[memory] Local file missing, skip upload: {local_path}")
        return

    with open(local_path, "rb") as file_obj:
        client.put_object(
            Bucket=bucket_name,
            Key=remote_key,
            Body=file_obj.read(),
            ContentLength=local_path.stat().st_size,
            ContentType="application/x-sqlite3",
        )
    print(f"[memory] Uploaded {local_path} -> {remote_key}")


def _download_memory_markdown(client, bucket_name: str) -> None:
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix="memory_markdown/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            relative_path = key.removeprefix("memory_markdown/")
            _download_file(client, bucket_name, key, MEMORY_DIR / relative_path)


def run(mode: str) -> None:
    client, bucket_name = _build_s3_client()
    _download_file(client, bucket_name, REMOTE_DB_KEY, DB_PATH)
    _download_memory_markdown(client, bucket_name)

    config = load_config()
    ai_config = config.get("AI", {})

    if mode == "daily":
        memory = generate_daily_summary_sync(str(DB_PATH), ai_config)
    elif mode == "weekly":
        memory = generate_weekly_digest_sync(str(DB_PATH), ai_config)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    if memory is None:
        print(f"[memory] No {mode} memory generated")
    else:
        print(f"[memory] Generated {mode} memory: {memory.id}")

    _upload_file(client, bucket_name, DB_PATH, REMOTE_DB_KEY)
    if MEMORY_DIR.exists():
        upload_markdown_to_oss(str(MEMORY_DIR), "memory_markdown")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TrendRadar custom memory records")
    parser.add_argument("mode", choices=("daily", "weekly"))
    args = parser.parse_args()
    run(args.mode)


if __name__ == "__main__":
    main()
