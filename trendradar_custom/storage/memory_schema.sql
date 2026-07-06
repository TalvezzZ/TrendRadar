-- ============================================
-- 记忆表（统一存储所有类型的记忆）
-- ============================================
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK(type IN (
        'daily_summary',
        'weekly_digest',
        'topic_insight',
        'pattern',
        'signal'
    )),
    title TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',              -- JSON
    created_at TEXT NOT NULL,                -- ISO 8601
    updated_at TEXT NOT NULL                 -- ISO 8601
);

CREATE INDEX IF NOT EXISTS idx_memories_type
    ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_created
    ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_memories_type_date
    ON memories(type, created_at);

-- ============================================
-- 记忆关联表
-- ============================================
CREATE TABLE IF NOT EXISTS memory_links (
    from_memory_id TEXT NOT NULL,
    to_memory_id TEXT NOT NULL,
    link_type TEXT NOT NULL CHECK(link_type IN (
        'supports',
        'contradicts',
        'extends',
        'derives_from'
    )),
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (from_memory_id, to_memory_id),
    FOREIGN KEY (from_memory_id) REFERENCES memories(id),
    FOREIGN KEY (to_memory_id) REFERENCES memories(id)
);

CREATE INDEX IF NOT EXISTS idx_memory_links_from
    ON memory_links(from_memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_links_to
    ON memory_links(to_memory_id);

-- ============================================
-- 记忆验证表
-- ============================================
CREATE TABLE IF NOT EXISTS memory_validations (
    memory_id TEXT PRIMARY KEY,
    last_validated TEXT NOT NULL,
    is_valid INTEGER NOT NULL,
    validation_notes TEXT,
    FOREIGN KEY (memory_id) REFERENCES memories(id)
);

-- ============================================
-- 关键词趋势表
-- ============================================
CREATE TABLE IF NOT EXISTS keyword_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    keyword TEXT NOT NULL,
    count INTEGER NOT NULL,
    platforms TEXT DEFAULT '[]',             -- JSON array
    rank INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(date, keyword)
);

CREATE INDEX IF NOT EXISTS idx_keyword_trends_date
    ON keyword_trends(date);
CREATE INDEX IF NOT EXISTS idx_keyword_trends_keyword
    ON keyword_trends(keyword);
CREATE INDEX IF NOT EXISTS idx_keyword_trends_keyword_date
    ON keyword_trends(keyword, date);
