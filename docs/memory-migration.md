# 记忆系统数据迁移指南

本文档说明如何在数据库和 Markdown 文件格式之间迁移记忆数据。

## 数据库到 Markdown 迁移

### 基本用法

将 SQLite 数据库中的记忆转换为 Markdown 格式：

```bash
python scripts/migrate_db_to_markdown.py
```

默认参数：
- 源数据库：`output/memory.db`
- 目标目录：`output/memory_markdown`
- 自动生成索引：是

### 自定义参数

```bash
python scripts/migrate_db_to_markdown.py \
    --db-path /path/to/memory.db \
    --output-path /path/to/output \
    --no-index  # 不生成 MEMORY.md 索引文件
```

### 输出格式

迁移后的目录结构：

```
output/memory_markdown/
├── MEMORY.md                    # 自动生成的索引文件
├── daily_summary/
│   └── 2026-05.md              # 按月合并的记忆文件
├── weekly_digest/
│   └── 2026-05.md
├── topic_insight/
├── pattern/
└── signal/
```

### Markdown 文件格式

每个记忆以 YAML frontmatter + Markdown 正文的格式存储：

```markdown
---
id: daily_summary_20260511
type: daily_summary
title: 2026年05月11日 科技热点摘要
description: 这是 2026-05-11 的每日摘要
created_at: '2026-05-11T10:38:44.312149'
updated_at: '2026-05-11T10:38:44.312149'
metadata:
  news_count: 15
  keywords:
  - AI
  - 科技
  - 新能源
  summary_type: daily
  date: '2026-05-11T10:38:44.312149'
---

今日科技领域主要关注点：

1. AI技术发展
   - GPT-5模型发布，性能提升显著
   - 多家科技公司加速AI布局

2. 市场动态
   - 科技股整体表现良好
   - 新能源板块持续受到关注
```

### MEMORY.md 索引文件

自动生成的索引文件提供快速导航：

```markdown
# TrendRadar 记忆索引

更新时间：2026-05-12 11:03:07

## 每日摘要 (daily_summary)

- [2026-05-11](daily_summary/2026-05.md#daily_summary_20260511) — 这是 2026-05-11 的每日摘要，关键词：AI、科技、新能源
- [2026-05-10](daily_summary/2026-05.md#daily_summary_20260510) — 这是 2026-05-10 的每日摘要，关键词：AI、科技、新能源
```

## Markdown 到数据库迁移

如果需要将 Markdown 文件转换回数据库格式，可以使用以下代码：

```python
from trendradar.memory.storage import DatabaseBackend, FileBackend
from trendradar.memory.models import MemoryRepository

# 源：Markdown 文件
file_backend = FileBackend("output/memory_markdown", auto_index=False)

# 目标：数据库
db_backend = DatabaseBackend("output/memory_new.db")

# 读取所有记忆并写入数据库
file_repo = MemoryRepository(file_backend)
db_repo = MemoryRepository(db_backend)

all_memories = file_repo.list_memories()
for memory in all_memories:
    db_repo.create(memory)

print(f"已迁移 {len(all_memories)} 条记忆")
```

## 配置记忆系统使用 Markdown 存储

修改配置以使用 Markdown 文件而非数据库：

```python
from trendradar.memory import create_memory_repository

# 使用文件存储
config = {
    "storage_type": "file",
    "file_storage": {
        "base_path": "output/memory_markdown",
        "auto_index": True  # 自动维护 MEMORY.md 索引
    }
}

repo = create_memory_repository(config)

# 之后的操作与数据库后端完全相同
repo.create(memory)
repo.get_by_id(memory_id)
# ...
```

## 优势对比

### 数据库存储
- ✅ 查询速度快
- ✅ 支持复杂查询
- ✅ 事务支持
- ❌ 不可直接阅读
- ❌ 需要工具查看

### Markdown 存储
- ✅ 人类可读
- ✅ 易于编辑和管理
- ✅ Git 友好（可追踪变更）
- ✅ 自动索引导航
- ❌ 查询速度较慢
- ❌ 不支持复杂查询

## 最佳实践

1. **本地开发**：使用 Markdown 格式，方便查看和调试
2. **生产环境**：使用数据库格式，性能更好
3. **备份归档**：定期将数据库导出为 Markdown 格式作为备份
4. **版本控制**：将 Markdown 文件纳入 Git 管理

## 故障排除

### 迁移失败

如果迁移过程中出现错误，检查：
1. 数据库文件是否存在且可读
2. 目标目录是否有写入权限
3. 磁盘空间是否充足

### 格式问题

如果 Markdown 文件格式有问题：
1. 检查 YAML frontmatter 是否正确闭合（`---` 分隔符）
2. 确保 metadata 字段是有效的 YAML 格式
3. 检查特殊字符是否正确转义

### 性能问题

如果处理大量数据时性能慢：
1. 迁移时禁用自动索引（`--no-index`）
2. 迁移完成后手动生成索引
3. 考虑分批迁移

```python
# 分批迁移示例
from trendradar.memory.storage import DatabaseBackend, FileBackend

db_backend = DatabaseBackend("output/memory.db")
file_backend = FileBackend("output/memory_markdown", auto_index=False)

# 按类型分批迁移
for memory_type in ['daily_summary', 'weekly_digest', ...]:
    memories = db_backend.list_memories(memory_type=memory_type)
    for memory in memories:
        file_backend.create_memory(memory)
    print(f"已迁移 {memory_type}: {len(memories)} 条")

# 最后生成索引
from trendradar.memory.index_manager import MemoryIndexManager
index_manager = MemoryIndexManager("output/memory_markdown")
index_manager.update_index()
```

## 相关文档

- [记忆系统设计文档](superpowers/specs/2026-05-11-memory-file-storage-design.md)
- [实施计划](superpowers/plans/2026-05-11-memory-file-storage.md)
