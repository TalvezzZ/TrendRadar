"""
批量为历史新闻数据生成 AI 分析

扫描历史数据库，为每个有新闻数据但缺少 AI 分析的日期生成 AI 分析结果。
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trendradar.core import load_config
from trendradar.ai.client import AIClient
from trendradar.persistence.ai_storage import AIAnalysisStorage
from trendradar.persistence.schema import initialize_ai_analysis_tables


def get_news_data(db_path: str, date_str: str) -> Optional[Dict[str, Any]]:
    """
    从数据库读取指定日期的新闻数据

    Args:
        db_path: 数据库文件路径
        date_str: 日期字符串 YYYY-MM-DD

    Returns:
        包含新闻数据的字典，如果没有数据则返回 None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 获取新闻数量
        cursor.execute("SELECT COUNT(*) FROM news_items")
        news_count = cursor.fetchone()[0]

        if news_count == 0:
            return None

        # 获取所有新闻
        cursor.execute("""
            SELECT ni.platform_id, ni.title, ni.url, ni.rank,
                   p.name as platform_name
            FROM news_items ni
            LEFT JOIN platforms p ON ni.platform_id = p.id
            ORDER BY ni.platform_id, ni.rank
        """)

        news_items = []
        for row in cursor.fetchall():
            news_items.append({
                'platform_id': row[0],
                'platform_name': row[4] or row[0],
                'title': row[1],
                'url': row[2] or '',
                'rank': row[3]
            })

        # 按平台分组
        platforms = {}
        for item in news_items:
            platform_id = item['platform_id']
            if platform_id not in platforms:
                platforms[platform_id] = {
                    'id': platform_id,
                    'name': item['platform_name'],
                    'items': []
                }
            platforms[platform_id]['items'].append({
                'title': item['title'],
                'url': item['url'],
                'rank': item['rank']
            })

        return {
            'date': date_str,
            'news_count': news_count,
            'rss_count': 0,  # 暂不处理 RSS
            'platforms': list(platforms.values()),
            'platform_ids': list(platforms.keys())
        }

    finally:
        conn.close()


def build_analysis_prompt(data: Dict[str, Any]) -> str:
    """
    构建 AI 分析提示词

    Args:
        data: 新闻数据字典

    Returns:
        提示词字符串
    """
    platform_summaries = []
    for platform in data['platforms']:
        titles = [f"- {item['title']}" for item in platform['items'][:20]]  # 每个平台最多20条
        platform_text = f"\n### {platform['name']}\n" + "\n".join(titles)
        platform_summaries.append(platform_text)

    prompt = f"""# 新闻热点分析任务

日期：{data['date']}
总计：{data['news_count']} 条新闻

## 各平台热点

{''.join(platform_summaries)}

## 分析要求

请对以上新闻热点进行深度分析，输出结构化内容：

### 1. 核心趋势（2-3个）
- 识别最重要的宏观趋势或主题
- 说明趋势的影响和意义
- 使用客观、洞察性的语言

### 2. 重要信号与变化
- 跨平台叙事差异
- 急升/急降信号
- 弱信号捕捉
- 用数据支撑观点

### 3. 关键词提取
列出最重要的5-7个关键词（如：地缘政治、AI大模型、金融市场等）

请以 Markdown 格式输出分析结果。"""

    return prompt


def generate_ai_analysis(data: Dict[str, Any], ai_client: AIClient) -> Optional[Dict[str, Any]]:
    """
    调用 AI 生成分析结果

    Args:
        data: 新闻数据字典
        ai_client: AI 客户端

    Returns:
        AI 分析结果字典
    """
    prompt = build_analysis_prompt(data)

    try:
        messages = [{"role": "user", "content": prompt}]
        response = ai_client.chat(messages)

        # 提取关键词（简单实现）
        keywords = []
        if '关键词' in response:
            # 尝试从响应中提取关键词
            lines = response.split('\n')
            for i, line in enumerate(lines):
                if '关键词' in line and i + 1 < len(lines):
                    next_lines = '\n'.join(lines[i+1:i+10])
                    # 提取列表项
                    for item_line in next_lines.split('\n'):
                        if item_line.strip().startswith('-'):
                            keyword = item_line.strip().lstrip('- ').strip()
                            if keyword and len(keyword) < 20:
                                keywords.append(keyword)
                    break

        # 构建结果 - 使用新闻日期作为分析时间
        analysis_time = f"{data['date']}T12:00:00"

        return {
            'analysis_time': analysis_time,
            'report_mode': 'daily',
            'news_count': data['news_count'],
            'rss_count': data['rss_count'],
            'matched_keywords': keywords[:7],  # 最多7个
            'platforms': data['platform_ids'],
            'full_result': {
                'summary': response,
                'date': data['date']
            },
            'content': response
        }

    except Exception as e:
        print(f"  ❌ AI 分析失败: {e}")
        return None


def save_analysis(analysis: Dict[str, Any], memory_db_path: str) -> bool:
    """
    保存 AI 分析结果到 memory.db

    Args:
        analysis: AI 分析结果
        memory_db_path: memory.db 路径

    Returns:
        是否保存成功
    """
    try:
        storage = AIAnalysisStorage(memory_db_path)

        # 保存主分析结果
        analysis_id = storage.save_analysis_result(analysis)

        # 保存板块内容
        sections = {
            'core_trends': analysis['content'],  # 完整内容作为核心趋势
        }
        storage.save_analysis_sections(analysis_id, sections)

        return True

    except Exception as e:
        print(f"  ❌ 保存失败: {e}")
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='批量生成历史 AI 分析')
    parser.add_argument('--news-dir', default='output/news', help='新闻数据库目录')
    parser.add_argument('--memory-db', default='output/memory.db', help='记忆数据库路径')
    parser.add_argument('--start-date', help='开始日期 YYYY-MM-DD（默认从2026-04-26开始）')
    parser.add_argument('--dry-run', action='store_true', help='仅扫描不生成')

    args = parser.parse_args()

    news_dir = Path(args.news_dir)
    memory_db = Path(args.memory_db)

    if not news_dir.exists():
        print(f"❌ 新闻目录不存在: {news_dir}")
        return 1

    # 确保 memory.db 的表结构存在
    conn = sqlite3.connect(str(memory_db))
    try:
        initialize_ai_analysis_tables(conn)
        print(f"✅ 已确保数据库表结构: {memory_db}")
    finally:
        conn.close()

    # 加载配置
    config = load_config()
    ai_config = config.get('AI', {})

    if not ai_config and not args.dry_run:
        print("❌ 未找到 AI 配置")
        return 1

    # 创建 AI 客户端
    ai_client = AIClient(ai_config) if not args.dry_run else None

    # 扫描所有数据库
    db_files = sorted(news_dir.glob('2026-*.db'))

    print(f"\n📊 扫描到 {len(db_files)} 个数据库文件\n")

    # 获取已有的 AI 分析日期
    conn = sqlite3.connect(str(memory_db))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT date(analysis_time) as date
        FROM ai_analysis_results
        ORDER BY date
    """)
    existing_dates = set(row[0] for row in cursor.fetchall())
    conn.close()

    print(f"已有 AI 分析的日期: {len(existing_dates)} 个")
    if existing_dates:
        print(f"  {', '.join(sorted(existing_dates))}\n")

    # 处理每个数据库
    to_process = []
    for db_file in db_files:
        date_str = db_file.stem  # YYYY-MM-DD

        # 过滤开始日期
        if args.start_date and date_str < args.start_date:
            continue

        # 检查是否已有分析
        if date_str in existing_dates:
            continue

        # 检查数据库是否有效（有news_items表）
        conn_test = sqlite3.connect(str(db_file))
        cursor_test = conn_test.cursor()
        try:
            cursor_test.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news_items'")
            has_news = cursor_test.fetchone() is not None
            conn_test.close()
            if not has_news:
                print(f"⚠️  {date_str}: 数据库结构错误，跳过")
                continue
        except:
            conn_test.close()
            continue

        to_process.append((date_str, db_file))

    print(f"需要生成 AI 分析的日期: {len(to_process)} 个\n")

    if not to_process:
        print("✅ 所有日期都已有 AI 分析")
        return 0

    if args.dry_run:
        print("以下日期需要生成 AI 分析:")
        for date_str, _ in to_process:
            print(f"  - {date_str}")
        return 0

    # 生成 AI 分析
    success_count = 0
    fail_count = 0

    for date_str, db_file in to_process:
        print(f"处理 {date_str} ...")

        # 读取新闻数据
        data = get_news_data(str(db_file), date_str)
        if not data:
            print(f"  ⚠️  无新闻数据，跳过")
            continue

        print(f"  📰 {data['news_count']} 条新闻，{len(data['platforms'])} 个平台")

        # 生成 AI 分析
        print(f"  🤖 调用 AI 分析...")
        analysis = generate_ai_analysis(data, ai_client)

        if not analysis:
            fail_count += 1
            continue

        print(f"  💾 保存分析结果...")
        if save_analysis(analysis, str(memory_db)):
            print(f"  ✅ 完成")
            success_count += 1
        else:
            fail_count += 1

    print(f"\n{'='*50}")
    print(f"总计: {len(to_process)} 个日期")
    print(f"成功: {success_count} 个")
    print(f"失败: {fail_count} 个")

    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
