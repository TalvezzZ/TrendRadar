-- ============================================
-- 金融跟踪数据库表结构
-- ============================================

-- 金融标的跟踪表
CREATE TABLE IF NOT EXISTS finance_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                                                    -- YYYY-MM-DD
    symbol TEXT NOT NULL,                                                  -- 标的代码
    symbol_type TEXT NOT NULL CHECK(symbol_type IN ('stock', 'etf', 'fund')),  -- 标的类型
    market TEXT NOT NULL,                                                  -- A股 | 美股 | 港股
    name TEXT NOT NULL,                                                    -- 标的名称
    current_price REAL NOT NULL,                                           -- 当前价格
    change_pct REAL NOT NULL,                                              -- 涨跌幅
    volume REAL,                                                           -- 成交量/额
    keywords TEXT DEFAULT '[]',                                            -- 关联的热点关键词 JSON
    created_at TEXT NOT NULL,                                              -- 创建时间
    UNIQUE(date, symbol)
);

CREATE INDEX IF NOT EXISTS idx_finance_tracking_date
    ON finance_tracking(date);
CREATE INDEX IF NOT EXISTS idx_finance_tracking_symbol
    ON finance_tracking(symbol);
CREATE INDEX IF NOT EXISTS idx_finance_tracking_keyword
    ON finance_tracking(keywords);

-- 关键词-标的映射表
CREATE TABLE IF NOT EXISTS keyword_finance_mapping (
    keyword TEXT NOT NULL,                                                 -- 关键词
    symbol TEXT NOT NULL,                                                  -- 标的代码
    symbol_type TEXT NOT NULL,                                             -- 标的类型
    market TEXT NOT NULL,                                                  -- 市场
    name TEXT NOT NULL,                                                    -- 标的名称
    priority INTEGER DEFAULT 1,                                            -- 优先级（数字越小越高）
    is_active INTEGER DEFAULT 1,                                           -- 是否启用
    created_at TEXT DEFAULT (datetime('now')),                             -- 创建时间
    updated_at TEXT DEFAULT (datetime('now')),                             -- 更新时间
    PRIMARY KEY (keyword, symbol)
);

CREATE INDEX IF NOT EXISTS idx_kfm_keyword
    ON keyword_finance_mapping(keyword);
CREATE INDEX IF NOT EXISTS idx_kfm_symbol
    ON keyword_finance_mapping(symbol);
