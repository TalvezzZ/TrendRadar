"""
数据回填模块

从历史爬虫数据补运行 AI 分析，用于修复缺失的分析记录。
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import sqlite3


def backfill_ai_analysis(
    target_date: datetime,
    config: Dict[str, Any],
    ctx,  # AppContext
    storage_manager,
    ai_analysis_db_path: str
) -> bool:
    """
    从历史爬虫数据补运行 AI 分析

    Args:
        target_date: 目标日期
        config: 配置字典
        ctx: AppContext 实例
        storage_manager: StorageManager 实例
        ai_analysis_db_path: ai_analysis.db 的路径

    Returns:
        是否成功
    """
    date_str = target_date.strftime("%Y-%m-%d")

    print(f"\n📥 步骤 1/4: 加载 {date_str} 的爬虫数据...")

    # 1. 检查数据库是否存在
    data_dir = Path(config.get("STORAGE", {}).get("DATA_DIR", "output"))
    news_db_path = data_dir / "news" / f"{date_str}.db"

    if not news_db_path.exists():
        print(f"❌ 未找到该日期的数据库: {news_db_path}")
        return False

    # 2. 从数据库读取新闻数据
    try:
        all_results, id_to_name, title_info = _load_news_from_db(news_db_path, ctx)
        if not all_results:
            print(f"❌ 数据库中没有新闻数据")
            return False

        total_news = sum(len(titles) for titles in all_results.values())
        print(f"✅ 加载了 {total_news} 条新闻，来自 {len(all_results)} 个平台")

    except Exception as e:
        print(f"❌ 读取数据库失败: {e}")
        if config.get("DEBUG", False):
            import traceback
            traceback.print_exc()
        return False

    print(f"\n🔍 步骤 2/4: 加载关键词配置...")

    # 3. 加载关键词配置
    try:
        word_groups, filter_words, global_filters = ctx.load_frequency_words()
        print(f"✅ 加载了 {len(word_groups)} 个关键词组")
    except Exception as e:
        print(f"❌ 加载关键词配置失败: {e}")
        return False

    print(f"\n📊 步骤 3/4: 统计关键词匹配...")

    # 4. 统计关键词匹配
    try:
        # 使用 daily 模式统计（当天所有数据）
        stats, total_titles = ctx.count_frequency(
            all_results,
            word_groups,
            filter_words,
            id_to_name,
            title_info,
            new_titles={},  # 历史回填不需要新增标记
            mode="daily",
            global_filters=global_filters,
            quiet=False
        )

        matched_count = sum(len(stat.get("titles", [])) for stat in stats)
        print(f"✅ 匹配到 {matched_count} 条新闻，{len(stats)} 个关键词")

    except Exception as e:
        print(f"❌ 关键词统计失败: {e}")
        if config.get("DEBUG", False):
            import traceback
            traceback.print_exc()
        return False

    print(f"\n🤖 步骤 4/4: 运行 AI 分析...")

    # 5. 运行 AI 分析
    try:
        ai_config = config.get("AI", {})
        analysis_config = config.get("AI_ANALYSIS", {})

        if not analysis_config.get("ENABLED", False):
            print("⚠️  AI 分析功能未启用，跳过分析")
            print("💡 如需启用，请在 config.yaml 中设置 ai_analysis.enabled: true")
            return False

        from trendradar.ai import AIAnalyzer

        analyzer = AIAnalyzer(
            ai_config,
            analysis_config,
            ctx.get_time,
            debug=config.get("DEBUG", False)
        )

        # 提取平台和关键词列表
        platforms = list(id_to_name.values())
        keywords = [s.get("word", "") for s in stats if s.get("word")]

        # 运行分析
        result = analyzer.analyze(
            stats=stats,
            rss_stats=None,  # 暂不支持 RSS 回填
            report_mode="daily",
            report_type="当日汇总（回填）",
            platforms=platforms,
            keywords=keywords,
            standalone_data=None
        )

        if not result.success:
            print(f"❌ AI 分析失败: {result.error}")
            return False

        print(f"✅ AI 分析完成")

    except Exception as e:
        print(f"❌ AI 分析出错: {e}")
        if config.get("DEBUG", False):
            import traceback
            traceback.print_exc()
        return False

    print(f"\n💾 保存分析结果...")

    # 6. 保存分析结果
    try:
        from trendradar_custom.persistence.ai_storage import AIAnalysisStorage
        import json

        ai_storage = AIAnalysisStorage(ai_analysis_db_path)

        # 构建分析数据（与正常流程保持一致）
        analysis_time = f"{date_str}T23:59:00"  # 使用当天结束时间

        analysis_data = {
            'analysis_time': analysis_time,
            'report_mode': 'daily',
            'news_count': total_news,
            'rss_count': 0,
            'matched_keywords': keywords,
            'platforms': platforms,
            'full_result': {
                'core_trends': result.core_trends,
                'sentiment_controversy': result.sentiment_controversy,
                'signals': result.signals,
                'rss_insights': result.rss_insights,
                'outlook_strategy': result.outlook_strategy,
                'standalone_summaries': result.standalone_summaries
            }
        }

        analysis_id = ai_storage.save_analysis_result(analysis_data)

        # 保存各个板块
        sections_data = {
            'core_trends': result.core_trends,
            'sentiment_controversy': result.sentiment_controversy,
            'signals': result.signals,
            'rss_insights': result.rss_insights,
            'outlook_strategy': result.outlook_strategy,
            'standalone_summaries': json.dumps(result.standalone_summaries, ensure_ascii=False)
        }
        ai_storage.save_analysis_sections(analysis_id, sections_data)

        print(f"✅ 分析结果已保存（ID: {analysis_id}）")

        # 7. 同时保存关键词统计
        from trendradar_custom.persistence.keyword_stats import KeywordStatsManager

        memory_conn = storage_manager.ensure_memory_db()
        keyword_manager = KeywordStatsManager(memory_conn)

        keywords_data = []
        for rank, stat in enumerate(stats, 1):
            keyword = stat.get("word", "")
            count = len(stat.get("titles", []))

            if keyword and count > 0:
                # 提取该关键词出现的平台
                keyword_platforms = []
                for platform_id, titles in all_results.items():
                    for title in titles:
                        if keyword in title:
                            platform_name = id_to_name.get(platform_id, platform_id)
                            if platform_name not in keyword_platforms:
                                keyword_platforms.append(platform_name)

                keywords_data.append({
                    'date': date_str,
                    'keyword': keyword,
                    'count': count,
                    'platforms': keyword_platforms,
                    'rank': rank
                })

        if keywords_data:
            keyword_manager.batch_update_keywords(keywords_data)
            print(f"✅ 关键词统计已更新（{len(keywords_data)} 个关键词）")

        memory_conn.close()

        return True

    except Exception as e:
        print(f"❌ 保存分析结果失败: {e}")
        if config.get("DEBUG", False):
            import traceback
            traceback.print_exc()
        return False


def _load_news_from_db(db_path: Path, ctx) -> tuple:
    """
    从数据库加载新闻数据

    Returns:
        (all_results, id_to_name, title_info)
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 读取平台信息
    cursor.execute("SELECT id, name FROM platforms")
    id_to_name = {row['id']: row['name'] for row in cursor.fetchall()}

    # 读取新闻数据
    cursor.execute("""
        SELECT
            title,
            platform_id,
            rank,
            url,
            mobile_url,
            first_crawl_time,
            last_crawl_time,
            crawl_count
        FROM news_items
        ORDER BY platform_id, rank
    """)

    all_results = {}
    title_info = {}

    for row in cursor.fetchall():
        platform_id = row['platform_id']
        title = row['title']

        # 初始化平台
        if platform_id not in all_results:
            all_results[platform_id] = {}
            title_info[platform_id] = {}

        # 构建标题数据（与 read_today_titles 格式一致）
        all_results[platform_id][title] = {
            "ranks": [row['rank']],
            "url": row['url'] or "",
            "mobileUrl": row['mobile_url'] or ""
        }

        # 构建标题信息
        title_info[platform_id][title] = {
            "first_time": row['first_crawl_time'],
            "last_time": row['last_crawl_time'],
            "count": row['crawl_count'],
            "ranks": [row['rank']],
            "url": row['url'] or "",
            "mobileUrl": row['mobile_url'] or ""
        }

    conn.close()

    return all_results, id_to_name, title_info
