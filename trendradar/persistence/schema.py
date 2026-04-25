"""
数据库 Schema 管理模块

负责初始化和管理所有持久化数据的表结构。
"""

import sqlite3
from pathlib import Path


def load_schema_file(schema_path: str) -> str:
    """
    加载 SQL schema 文件

    Args:
        schema_path: schema 文件路径

    Returns:
        SQL 内容

    Raises:
        FileNotFoundError: 如果文件不存在
    """
    path = Path(schema_path)
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    return path.read_text(encoding='utf-8')


def initialize_ai_analysis_tables(conn: sqlite3.Connection) -> None:
    """
    初始化 AI 分析相关表

    Args:
        conn: 数据库连接
    """
    storage_dir = Path(__file__).parent.parent / 'storage'
    schema_path = storage_dir / 'ai_analysis_schema.sql'
    sql = load_schema_file(str(schema_path))

    conn.executescript(sql)
    conn.commit()


def initialize_memory_db(db_path: str) -> sqlite3.Connection:
    """
    初始化 memory.db 数据库

    创建数据库连接并初始化所有必要的表结构。

    Args:
        db_path: 数据库文件路径

    Returns:
        数据库连接对象
    """
    conn = sqlite3.connect(db_path)

    storage_dir = Path(__file__).parent.parent / 'storage'

    # 初始化记忆相关表
    memory_schema_path = storage_dir / 'memory_schema.sql'
    sql = load_schema_file(str(memory_schema_path))
    conn.executescript(sql)
    conn.commit()

    return conn


def ensure_matched_keywords_column(conn: sqlite3.Connection) -> None:
    """
    确保 news_items 表有 matched_keywords 字段

    如果字段不存在则添加。

    Args:
        conn: 数据库连接
    """
    cursor = conn.cursor()

    # 检查字段是否存在
    cursor.execute("PRAGMA table_info(news_items)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'matched_keywords' not in columns:
        cursor.execute(
            "ALTER TABLE news_items ADD COLUMN matched_keywords TEXT DEFAULT '[]'"
        )
        conn.commit()
