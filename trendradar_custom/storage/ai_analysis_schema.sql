-- AI 分析结果表
CREATE TABLE IF NOT EXISTS ai_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_time TEXT NOT NULL UNIQUE,    -- ISO 8601 格式
    report_mode TEXT NOT NULL,              -- 报告模式
    news_count INTEGER DEFAULT 0,
    rss_count INTEGER DEFAULT 0,
    matched_keywords TEXT DEFAULT '[]',     -- JSON array
    platforms TEXT DEFAULT '[]',            -- JSON array
    full_result TEXT NOT NULL,              -- JSON 对象
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_analysis_time
    ON ai_analysis_results(analysis_time);

-- AI 分析板块表
CREATE TABLE IF NOT EXISTS ai_analysis_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    section_type TEXT NOT NULL CHECK(section_type IN (
        'core_trends',
        'sentiment_controversy',
        'signals',
        'rss_insights',
        'outlook_strategy',
        'standalone_summaries'
    )),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES ai_analysis_results(id),
    UNIQUE(analysis_id, section_type)
);

CREATE INDEX IF NOT EXISTS idx_ai_sections_type
    ON ai_analysis_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_ai_sections_analysis
    ON ai_analysis_sections(analysis_id);
