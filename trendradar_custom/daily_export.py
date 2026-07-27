"""Export one daily crawl result as a JSON object and optionally upload it."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import boto3
from botocore.config import Config

from trendradar.ai.formatter import render_ai_analysis_markdown


def _build_items(results: Dict, id_to_name: Dict) -> List[Dict]:
    items = []
    for source_id, titles in results.items():
        for title, data in titles.items():
            ranks = data.get("ranks", [])
            items.append({
                "platform_id": source_id,
                "platform": id_to_name.get(source_id, source_id),
                "title": title,
                "url": data.get("url", ""),
                "mobile_url": data.get("mobileUrl", ""),
                "rank": ranks[0] if ranks else 0,
                "ranks": ranks,
            })
    return items


def _build_rss_items(rss_items: Optional[List[Dict]]) -> List[Dict]:
    return [
        {
            "feed_id": item.get("feed_id", ""),
            "feed": item.get("feed_name", item.get("feed_id", "")),
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "published_at": item.get("published_at", ""),
            "summary": item.get("summary", ""),
            "author": item.get("author", ""),
        }
        for item in (rss_items or [])
    ]


def build_daily_payload(
    date: str,
    fetched_at: str,
    results: Dict,
    id_to_name: Dict,
    ai_result=None,
    rss_items: Optional[List[Dict]] = None,
) -> Dict:
    """Build the stable JSON contract consumed by downstream projects."""
    summary = ""
    if ai_result is not None and ai_result.success:
        summary = render_ai_analysis_markdown(ai_result)

    return {
        "date": date,
        "fetched_at": fetched_at,
        "hotspots": _build_items(results, id_to_name),
        "rss": _build_rss_items(rss_items),
        "ai_summary": summary,
    }


def export_daily_json(
    payload: Dict,
    output_dir: str = "output/daily",
    upload: bool = True,
) -> Path:
    """Write and optionally upload ``daily/YYYY-MM-DD.json``."""
    date = payload["date"]
    local_path = Path(output_dir) / f"{date}.json"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if upload and all(os.environ.get(key) for key in (
        "S3_BUCKET_NAME",
        "S3_ENDPOINT_URL",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    )):
        client = boto3.client(
            "s3",
            endpoint_url=os.environ["S3_ENDPOINT_URL"],
            aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
            region_name=os.environ.get("S3_REGION", ""),
            config=Config(s3={"addressing_style": "virtual"}, signature_version="s3"),
        )
        remote_key = f"daily/{date}.json"
        client.put_object(
            Bucket=os.environ["S3_BUCKET_NAME"],
            Key=remote_key,
            Body=local_path.read_bytes(),
            ContentType="application/json; charset=utf-8",
        )
        print(f"[daily export] uploaded: {remote_key}")
    else:
        print("[daily export] OSS credentials unavailable, local file only")

    print(f"[daily export] saved: {local_path}")
    return local_path
