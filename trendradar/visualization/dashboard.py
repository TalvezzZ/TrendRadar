"""
可视化仪表板生成器

从数据库读取记忆和分析数据，生成交互式可视化仪表板
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional


class DashboardGenerator:
    """仪表板生成器"""

    def __init__(self, data_dir: str = "output"):
        """
        初始化仪表板生成器

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
        self.memory_db = self.data_dir / "memory.db"
        self.news_dir = self.data_dir / "news"

    def generate(self, output_path: Optional[str] = None) -> str:
        """
        生成仪表板

        Args:
            output_path: 输出路径，默认为 output/html/dashboard.html

        Returns:
            生成的文件路径
        """
        if output_path is None:
            output_path = self.data_dir / "html" / "dashboard.html"
        else:
            output_path = Path(output_path)

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 收集数据
        data = {
            "overview": self._get_overview_stats(),
            "timeline": self._get_memory_timeline(),
            "keywords": self._get_keyword_trends(),
            "relations": self._get_memory_relations(),
            "analysis": self._get_analysis_stats(),
        }

        # 生成 HTML
        html_content = self._generate_html(data)

        # 写入文件
        output_path.write_text(html_content, encoding="utf-8")

        return str(output_path)

    def _get_overview_stats(self) -> Dict[str, Any]:
        """获取概览统计"""
        if not self.memory_db.exists():
            return {
                "total_memories": 0,
                "daily_summaries": 0,
                "weekly_digests": 0,
                "last_update": None,
            }

        conn = sqlite3.connect(self.memory_db)
        cursor = conn.cursor()

        try:
            # 总记忆数
            cursor.execute("SELECT COUNT(*) FROM memories")
            total = cursor.fetchone()[0]

            # 每日摘要数
            cursor.execute("SELECT COUNT(*) FROM memories WHERE type = 'daily_summary'")
            daily = cursor.fetchone()[0]

            # 每周汇总数
            cursor.execute("SELECT COUNT(*) FROM memories WHERE type = 'weekly_digest'")
            weekly = cursor.fetchone()[0]

            # 最新更新时间
            cursor.execute("SELECT MAX(created_at) FROM memories")
            last_update = cursor.fetchone()[0]

            return {
                "total_memories": total,
                "daily_summaries": daily,
                "weekly_digests": weekly,
                "last_update": last_update,
            }
        finally:
            conn.close()

    def _get_memory_timeline(self) -> List[Dict[str, Any]]:
        """获取记忆时间线数据"""
        if not self.memory_db.exists():
            return []

        conn = sqlite3.connect(self.memory_db)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    id,
                    type,
                    title,
                    created_at,
                    metadata
                FROM memories
                ORDER BY created_at DESC
                LIMIT 100
            """)

            timeline = []
            for row in cursor.fetchall():
                metadata = json.loads(row[4]) if row[4] else {}
                # 从 metadata 中提取日期，或使用 created_at
                date = metadata.get('date', row[3][:10])  # 取 created_at 的日期部分

                timeline.append({
                    "id": row[0],
                    "type": row[1],
                    "title": row[2],
                    "date": date,
                    "created_at": row[3],
                    "metadata": metadata,
                })

            return timeline
        finally:
            conn.close()

    def _get_keyword_trends(self, days: int = 30) -> Dict[str, Any]:
        """获取关键词趋势数据"""
        trends = {}
        start_date = datetime.now() - timedelta(days=days)

        if not self.news_dir.exists():
            return trends

        # 遍历所有日期数据库
        for db_file in sorted(self.news_dir.glob("*.db")):
            try:
                # 解析日期
                date_str = db_file.stem  # YYYY-MM-DD
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")

                if date_obj < start_date:
                    continue

                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()

                try:
                    # 检查表是否存在
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='keyword_trends'"
                    )
                    if not cursor.fetchone():
                        continue

                    # 获取关键词统计
                    cursor.execute("""
                        SELECT keyword, frequency
                        FROM keyword_trends
                        WHERE date = ?
                        ORDER BY frequency DESC
                        LIMIT 20
                    """, (date_str,))

                    for keyword, freq in cursor.fetchall():
                        if keyword not in trends:
                            trends[keyword] = []
                        trends[keyword].append({
                            "date": date_str,
                            "frequency": freq,
                        })
                finally:
                    conn.close()

            except Exception as e:
                print(f"读取 {db_file.name} 失败: {e}")
                continue

        return trends

    def _get_memory_relations(self) -> List[Dict[str, Any]]:
        """获取记忆关系图谱数据"""
        if not self.memory_db.exists():
            return []

        conn = sqlite3.connect(self.memory_db)
        cursor = conn.cursor()

        try:
            # 获取记忆节点
            cursor.execute("""
                SELECT id, type, title
                FROM memories
                ORDER BY created_at DESC
                LIMIT 50
            """)

            nodes = []
            for row in cursor.fetchall():
                nodes.append({
                    "id": row[0],
                    "type": row[1],
                    "name": row[2],
                })

            # 获取记忆关联
            cursor.execute("""
                SELECT from_memory_id, to_memory_id, link_type
                FROM memory_links
                WHERE from_memory_id IN (SELECT id FROM memories ORDER BY created_at DESC LIMIT 50)
            """)

            links = []
            for row in cursor.fetchall():
                links.append({
                    "source": row[0],
                    "target": row[1],
                    "type": row[2],
                })

            return {
                "nodes": nodes,
                "links": links,
            }
        finally:
            conn.close()

    def _get_analysis_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取 AI 分析统计"""
        stats = {
            "daily_matched": [],
            "tag_distribution": {},
            "platform_distribution": {},
        }

        start_date = datetime.now() - timedelta(days=days)

        if not self.news_dir.exists():
            return stats

        # 遍历最近几天的数据库
        for db_file in sorted(self.news_dir.glob("*.db"), reverse=True)[:days]:
            try:
                date_str = db_file.stem
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")

                if date_obj < start_date:
                    continue

                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()

                try:
                    # 检查表是否存在
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_analysis_results'"
                    )
                    if not cursor.fetchone():
                        continue

                    # 获取每日匹配数
                    cursor.execute("""
                        SELECT news_count, rss_count, matched_keywords
                        FROM ai_analysis_results
                        ORDER BY created_at DESC
                        LIMIT 1
                    """)

                    row = cursor.fetchone()
                    if row:
                        matched_keywords = json.loads(row[2]) if row[2] else []
                        stats["daily_matched"].append({
                            "date": date_str,
                            "news": row[0],
                            "rss": row[1],
                            "matched": len(matched_keywords),
                        })

                        # 统计标签分布
                        for keyword in matched_keywords:
                            stats["tag_distribution"][keyword] = stats["tag_distribution"].get(keyword, 0) + 1

                finally:
                    conn.close()

            except Exception as e:
                print(f"读取 {db_file.name} 失败: {e}")
                continue

        return stats

    def _generate_html(self, data: Dict[str, Any]) -> str:
        """生成 HTML 内容"""
        # 转换为 JSON 字符串
        data_json = json.dumps(data, ensure_ascii=False, indent=2)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrendRadar 记忆可视化仪表板</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        .stat-card h3 {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
        }}

        .stat-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}

        .chart-container {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        .chart-container h2 {{
            font-size: 1.3em;
            margin-bottom: 15px;
            color: #333;
        }}

        .chart {{
            width: 100%;
            height: 400px;
        }}

        .timeline {{
            height: 500px;
        }}

        .relations {{
            height: 600px;
        }}

        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 TrendRadar 记忆可视化仪表板</h1>
            <p>智能记忆系统 · 数据分析 · 趋势洞察</p>
        </div>

        <div class="stats-grid" id="statsGrid"></div>

        <div class="chart-container">
            <h2>📈 记忆时间线</h2>
            <div id="timelineChart" class="chart timeline"></div>
        </div>

        <div class="chart-container">
            <h2>🔥 关键词趋势（近30天）</h2>
            <div id="keywordChart" class="chart"></div>
        </div>

        <div class="chart-container">
            <h2>🕸️ 话题关系图谱</h2>
            <div id="relationsChart" class="chart relations"></div>
        </div>

        <div class="chart-container">
            <h2>📊 AI 分析统计（近7天）</h2>
            <div id="analysisChart" class="chart"></div>
        </div>

        <div class="footer">
            <p>生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | TrendRadar v6.6.1</p>
        </div>
    </div>

    <script>
        // 数据
        const data = {data_json};

        // 渲染概览统计
        function renderStats() {{
            const statsGrid = document.getElementById('statsGrid');
            const overview = data.overview;

            const stats = [
                {{ label: '总记忆数', value: overview.total_memories, icon: '📚' }},
                {{ label: '每日摘要', value: overview.daily_summaries, icon: '📝' }},
                {{ label: '每周汇总', value: overview.weekly_digests, icon: '📊' }},
                {{ label: '最新更新', value: overview.last_update ? new Date(overview.last_update).toLocaleDateString('zh-CN') : '暂无', icon: '🕐' }}
            ];

            statsGrid.innerHTML = stats.map(stat => `
                <div class="stat-card">
                    <h3>${{stat.icon}} ${{stat.label}}</h3>
                    <div class="value">${{stat.value}}</div>
                </div>
            `).join('');
        }}

        // 记忆时间线
        function renderTimeline() {{
            const chart = echarts.init(document.getElementById('timelineChart'));
            const timeline = data.timeline;

            const option = {{
                tooltip: {{
                    trigger: 'item',
                    formatter: function(params) {{
                        const item = params.data;
                        return `
                            <strong>${{item.title}}</strong><br/>
                            类型: ${{item.type}}<br/>
                            日期: ${{item.date}}<br/>
                            创建: ${{new Date(item.created_at).toLocaleString('zh-CN')}}
                        `;
                    }}
                }},
                xAxis: {{
                    type: 'time',
                    boundaryGap: false
                }},
                yAxis: {{
                    type: 'category',
                    data: ['每日摘要', '每周汇总', '其他']
                }},
                series: [{{
                    type: 'scatter',
                    symbolSize: 20,
                    data: timeline.map(item => {{
                        let yIndex = item.type === 'daily_summary' ? 0 : item.type === 'weekly_digest' ? 1 : 2;
                        return {{
                            value: [item.date, yIndex],
                            title: item.title,
                            type: item.type,
                            created_at: item.created_at,
                            start_date: item.date
                        }};
                    }}),
                    itemStyle: {{
                        color: function(params) {{
                            const type = params.data.type;
                            return type === 'daily_summary' ? '#667eea' :
                                   type === 'weekly_digest' ? '#764ba2' : '#999';
                        }}
                    }}
                }}]
            }};

            chart.setOption(option);
            window.addEventListener('resize', () => chart.resize());
        }}

        // 关键词趋势
        function renderKeywords() {{
            const chart = echarts.init(document.getElementById('keywordChart'));
            const keywords = data.keywords;

            // 取前10个关键词
            const topKeywords = Object.entries(keywords)
                .sort((a, b) => b[1].length - a[1].length)
                .slice(0, 10);

            const series = topKeywords.map(([keyword, dataPoints]) => ({{
                name: keyword,
                type: 'line',
                smooth: true,
                data: dataPoints.map(point => [point.date, point.frequency])
            }}));

            const option = {{
                tooltip: {{
                    trigger: 'axis'
                }},
                legend: {{
                    data: topKeywords.map(([keyword]) => keyword),
                    bottom: 0
                }},
                xAxis: {{
                    type: 'time'
                }},
                yAxis: {{
                    type: 'value',
                    name: '频次'
                }},
                series: series
            }};

            chart.setOption(option);
            window.addEventListener('resize', () => chart.resize());
        }}

        // 话题关系图谱
        function renderRelations() {{
            const chart = echarts.init(document.getElementById('relationsChart'));
            const relations = data.relations;

            if (!relations || !relations.nodes || relations.nodes.length === 0) {{
                document.getElementById('relationsChart').innerHTML = '<p style="text-align:center;padding:50px;color:#999;">暂无关系数据</p>';
                return;
            }}

            const option = {{
                tooltip: {{}},
                series: [{{
                    type: 'graph',
                    layout: 'force',
                    data: relations.nodes.map(node => ({{
                        id: node.id,
                        name: node.name,
                        symbolSize: 50,
                        itemStyle: {{
                            color: node.type === 'daily_summary' ? '#667eea' :
                                   node.type === 'weekly_digest' ? '#764ba2' : '#999'
                        }}
                    }})),
                    links: relations.links.map(link => ({{
                        source: link.source,
                        target: link.target
                    }})),
                    roam: true,
                    label: {{
                        show: true,
                        position: 'right',
                        formatter: '{{b}}'
                    }},
                    force: {{
                        repulsion: 100
                    }}
                }}]
            }};

            chart.setOption(option);
            window.addEventListener('resize', () => chart.resize());
        }}

        // AI 分析统计
        function renderAnalysis() {{
            const chart = echarts.init(document.getElementById('analysisChart'));
            const analysis = data.analysis;

            const option = {{
                tooltip: {{
                    trigger: 'axis'
                }},
                legend: {{
                    data: ['新闻数', 'RSS数', '匹配数']
                }},
                xAxis: {{
                    type: 'category',
                    data: analysis.daily_matched.map(item => item.date)
                }},
                yAxis: {{
                    type: 'value'
                }},
                series: [
                    {{
                        name: '新闻数',
                        type: 'bar',
                        data: analysis.daily_matched.map(item => item.news)
                    }},
                    {{
                        name: 'RSS数',
                        type: 'bar',
                        data: analysis.daily_matched.map(item => item.rss)
                    }},
                    {{
                        name: '匹配数',
                        type: 'line',
                        data: analysis.daily_matched.map(item => item.matched)
                    }}
                ]
            }};

            chart.setOption(option);
            window.addEventListener('resize', () => chart.resize());
        }}

        // 初始化
        renderStats();
        renderTimeline();
        renderKeywords();
        renderRelations();
        renderAnalysis();
    </script>
</body>
</html>
"""
        return html
