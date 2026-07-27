from pathlib import Path

from trendradar.ai.analyzer import AIAnalysisResult
from trendradar_custom.daily_export import build_daily_payload, export_daily_json


def test_build_daily_payload_includes_links_and_summary():
    result = AIAnalysisResult(success=True, core_trends="今天的核心趋势")

    payload = build_daily_payload(
        date="2026-07-10",
        fetched_at="2026-07-10T23:20:00+08:00",
        results={
            "zhihu": {
                "热点标题": {
                    "url": "https://example.com/news",
                    "mobileUrl": "https://m.example.com/news",
                    "ranks": [1, 3],
                }
            }
        },
        id_to_name={"zhihu": "知乎"},
        ai_result=result,
        rss_items=[{
            "feed_id": "hacker-news",
            "feed_name": "Hacker News",
            "title": "RSS 标题",
            "url": "https://example.com/rss",
        }],
    )

    assert payload["date"] == "2026-07-10"
    assert payload["hotspots"][0]["url"] == "https://example.com/news"
    assert payload["rss"][0]["url"] == "https://example.com/rss"
    assert "今天的核心趋势" in payload["ai_summary"]


def test_export_daily_json_writes_one_file(tmp_path: Path):
    payload = {
        "date": "2026-07-10",
        "fetched_at": "2026-07-10T23:20:00+08:00",
        "hotspots": [],
        "rss": [],
        "ai_summary": "总结",
    }

    path = export_daily_json(payload, str(tmp_path), upload=False)

    assert path == tmp_path / "2026-07-10.json"
    assert path.exists()
    assert path.read_text(encoding="utf-8").find('"ai_summary": "总结"') >= 0
