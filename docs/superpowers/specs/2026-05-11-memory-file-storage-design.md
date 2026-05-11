# 记忆系统文件存储重构设计

**日期**: 2026-05-11  
**状态**: 设计完成，待实施  
**作者**: Claude Code

## 1. 背景与目标

### 1.1 现状

TrendRadar 当前使用 SQLite 数据库存储记忆数据：
- 5 种记忆类型：daily_summary, weekly_digest, topic_insight, pattern, signal
- 记忆之间有链接关系（supports, contradicts, extends, derives_from）
- 关键词趋势数据存储在独立的 keyword_trends 表

### 1.2 问题

- 数据库文件不便于直接阅读和查看
- 无法直接编辑记忆内容
- 不方便进行版本控制和协作

### 1.3 目标

- **可读性**：使用 Markdown 格式，可直接阅读和编辑
- **可管理**：文件系统组织，便于浏览和管理
- **兼容性**：保持现有 API 不变，现有代码无需修改
- **灵活性**：支持数据库和文件两种存储方式，可配置切换
- **可迁移**：提供双向迁移工具

## 2. 整体架构

### 2.1 架构层次

```
调用层（现有代码不变）
    ├─ MemoryGenerator
    ├─ MemoryQueryEngine
    └─ MemoryScheduler
           ↓
业务逻辑层（接口保持不变，内部重构）
    └─ MemoryRepository
           ↓
存储抽象层（新增）
    └─ StorageBackend (抽象基类)
           ↓
存储实现层（可选择）
    ├─ DatabaseBackend（现有逻辑）
    └─ FileBackend（新增）
```

### 2.2 设计原则

1. **接口稳定**：MemoryRepository 的公开方法签名不变
2. **存储无关**：业务逻辑不关心底层存储
3. **渐进迁移**：可以先用数据库，测试通过后切换到文件
4. **双向兼容**：提供迁移工具支持两种格式互转

### 2.3 配置驱动

通过配置文件或环境变量选择存储方式：

```yaml
memory:
  storage_type: "file"  # 或 "database"
  
  file_storage:
    base_path: ./output/memory
    auto_index: true
    max_memories_per_file: 100
    
  database_storage:
    db_path: ./output/memory.db
```

## 3. 文件格式设计

### 3.1 Markdown 文件格式

每个记忆存储为一个 `.md` 文件，使用 YAML frontmatter：

```markdown
---
id: daily-summary-20260501-143022
type: daily_summary
title: 每日摘要 - 2026-05-01
description: 基于 42 条新闻和 18 条 RSS 的智能分析摘要
created_at: 2026-05-01T14:30:22
updated_at: 2026-05-01T14:30:22
metadata:
  date: "2026-05-01"
  news_count: 42
  rss_count: 18
  top_keywords: ["AI", "区块链", "新能源"]
  platforms: ["微信", "微博", "知乎"]
  keyword_trends:
    - keyword: "AI"
      count: 15
      platforms: ["微信", "微博"]
      rank: 1
    - keyword: "区块链"
      count: 12
      platforms: ["知乎"]
      rank: 2
---

# 每日摘要 - 2026-05-01

## 关键趋势

1. **AI 技术突破**：今日 AI 相关讨论激增...
2. **区块链应用落地**：多个项目宣布...
3. **新能源政策**：政府发布新政策...

## 重要信号

- 微信平台上 AI 话题热度上升 30%
- 知乎区块链讨论量创新高

## 相关记忆

本周摘要基于本记忆生成：[每周摘要 - 2026-W18](../weekly_digest/2026-05.md#week-18)
```

### 3.2 目录结构

```
output/memory/
├── MEMORY.md                          # 索引文件
├── daily_summary/
│   ├── 2026-04.md                    # 按月合并
│   ├── 2026-05.md
│   └── archive/                      # 历史归档
│       └── 2025-12.md
├── weekly_digest/
│   └── 2026-05.md
├── topic_insight/
│   └── ai-technology-2026-q2.md
├── pattern/
│   └── keyword-correlation-analysis.md
└── signal/
    └── market-sentiment-shift.md
```

**设计说明**：
- 按记忆类型分目录
- 按日期合并到月度文件（避免文件过多）
- 单个文件记忆数超过阈值时自动拆分

### 3.3 MEMORY.md 索引格式

```markdown
# TrendRadar 记忆索引

更新时间：2026-05-01 14:30:22

## 每日摘要 (daily_summary)

- [2026-05-01](daily_summary/2026-05.md#2026-05-01) — 基于 42 条新闻，关键词：AI、区块链
- [2026-04-30](daily_summary/2026-04.md#2026-04-30) — 基于 35 条新闻，关键词：新能源、芯片

## 每周摘要 (weekly_digest)

- [2026-W18](weekly_digest/2026-05.md#week-18) — 2026-04-28 至 2026-05-04，基于 7 天数据

## 主题洞察 (topic_insight)

- [AI 技术 Q2](topic_insight/ai-technology-2026-q2.md) — 2026 Q2 AI 技术发展趋势分析

## 模式识别 (pattern)

- [关键词关联分析](pattern/keyword-correlation-analysis.md) — AI 与区块链的关联模式

## 信号记录 (signal)

- [市场情绪转变](signal/market-sentiment-shift.md) — 2026-04 市场情绪从谨慎转向乐观
```

### 3.4 链接表示方式

在文件内容中使用 Markdown 链接表示记忆关联：

```markdown
## 相关记忆

### 派生自

- [每日摘要 2026-04-28](../daily_summary/2026-04.md#2026-04-28)
- [每日摘要 2026-04-29](../daily_summary/2026-04.md#2026-04-29)
- [每日摘要 2026-04-30](../daily_summary/2026-04.md#2026-04-30)

### 支持

- [AI 技术洞察 Q2](../topic_insight/ai-technology-2026-q2.md)
```

### 3.5 关键词趋势整合

将 `keyword_trends` 表的数据整合到每日摘要的 metadata 中：

```yaml
metadata:
  keyword_trends:
    - keyword: "AI"
      count: 15
      platforms: ["微信", "微博"]
      rank: 1
```

## 4. 组件设计

### 4.1 StorageBackend 抽象基类

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

class StorageBackend(ABC):
    """存储后端抽象基类"""
    
    @abstractmethod
    def create_memory(self, memory: Memory) -> None:
        """创建记忆"""
        pass
    
    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        pass
    
    @abstractmethod
    def update_memory(self, memory: Memory) -> None:
        """更新记忆"""
        pass
    
    @abstractmethod
    def delete_memory(self, memory_id: str) -> None:
        """删除记忆"""
        pass
    
    @abstractmethod
    def list_memories(
        self, 
        memory_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """列出记忆"""
        pass
    
    @abstractmethod
    def search_memories(self, keyword: str, limit: Optional[int] = None) -> List[Memory]:
        """搜索记忆"""
        pass
```

### 4.2 DatabaseBackend

将现有 MemoryRepository 的数据库逻辑迁移到此类：

```python
class DatabaseBackend(StorageBackend):
    """数据库存储后端"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()
    
    def create_memory(self, memory: Memory) -> None:
        """创建记忆 - 现有数据库插入逻辑"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO memories
                (id, type, title, description, content, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.id,
                    memory.type,
                    memory.title,
                    memory.description,
                    memory.content,
                    json.dumps(memory.metadata, ensure_ascii=False),
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat()
                )
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆 - 现有数据库查询逻辑"""
        # ... 实现略
    
    # ... 其他方法
```

### 4.3 FileBackend

新增的文件存储实现：

```python
class FileBackend(StorageBackend):
    """文件存储后端"""
    
    def __init__(self, base_path: str, auto_index: bool = True):
        self.base_path = Path(base_path)
        self.auto_index = auto_index
        self.index_manager = MemoryIndexManager(self.base_path)
        self._ensure_directories()
    
    def create_memory(self, memory: Memory) -> None:
        """创建记忆"""
        # 1. 确定文件路径
        file_path = self._get_file_path(memory)
        
        # 2. 生成 Markdown 内容
        content = self._memory_to_markdown(memory)
        
        # 3. 写入文件（追加或创建）
        self._write_or_append(file_path, memory, content)
        
        # 4. 更新索引
        if self.auto_index:
            self.index_manager.update_index()
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        # 1. 搜索所有文件查找匹配的 memory_id
        file_path = self._find_file_by_id(memory_id)
        if not file_path:
            return None
        
        # 2. 解析 Markdown 提取记忆
        content = file_path.read_text(encoding='utf-8')
        return self._extract_memory_from_markdown(content, memory_id)
    
    def list_memories(
        self,
        memory_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """列出记忆"""
        # 1. 确定扫描目录
        if memory_type:
            dirs = [self.base_path / memory_type]
        else:
            dirs = [d for d in self.base_path.iterdir() if d.is_dir() and d.name != 'archive']
        
        # 2. 扫描所有 .md 文件
        memories = []
        for dir_path in dirs:
            for md_file in dir_path.glob("**/*.md"):
                memories.extend(self._parse_markdown_file(md_file))
        
        # 3. 过滤日期范围
        if start_date:
            memories = [m for m in memories if m.created_at >= start_date]
        if end_date:
            memories = [m for m in memories if m.created_at <= end_date]
        
        # 4. 排序和限制
        memories.sort(key=lambda m: m.created_at, reverse=True)
        if limit:
            memories = memories[:limit]
        
        return memories
    
    def search_memories(self, keyword: str, limit: Optional[int] = None) -> List[Memory]:
        """搜索记忆"""
        all_memories = self.list_memories()
        
        # 简单文本匹配
        results = [
            m for m in all_memories
            if keyword in m.title or keyword in m.content
        ]
        
        if limit:
            results = results[:limit]
        
        return results
    
    def _get_file_path(self, memory: Memory) -> Path:
        """
        根据记忆类型和日期确定文件路径
        例如：daily_summary + 2026-05-01 -> daily_summary/2026-05.md
        """
        type_dir = self.base_path / memory.type
        
        # 提取日期（从 metadata 或 created_at）
        date_str = memory.metadata.get('date')
        if date_str:
            date = datetime.fromisoformat(date_str) if isinstance(date_str, str) else date_str
        else:
            date = memory.created_at
        
        # 月度文件名
        file_name = f"{date.year}-{date.month:02d}.md"
        return type_dir / file_name
    
    def _memory_to_markdown(self, memory: Memory) -> str:
        """将 Memory 对象转换为 Markdown 格式"""
        import yaml
        
        # Frontmatter
        frontmatter = {
            'id': memory.id,
            'type': memory.type,
            'title': memory.title,
            'description': memory.description,
            'created_at': memory.created_at.isoformat(),
            'updated_at': memory.updated_at.isoformat(),
            'metadata': memory.metadata
        }
        
        yaml_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
        
        # 组合 Markdown
        markdown = f"---\n{yaml_str}---\n\n{memory.content}\n"
        
        return markdown
    
    def _parse_markdown_file(self, file_path: Path) -> List[Memory]:
        """解析 Markdown 文件，提取所有记忆"""
        content = file_path.read_text(encoding='utf-8')
        
        # 按 frontmatter 分割（一个文件可能包含多个记忆）
        memories = []
        parts = content.split('---\n')
        
        i = 1  # 跳过第一个空部分
        while i < len(parts) - 1:
            yaml_content = parts[i]
            md_content = parts[i + 1] if i + 1 < len(parts) else ""
            
            memory = self._parse_single_memory(yaml_content, md_content)
            if memory:
                memories.append(memory)
            
            i += 2
        
        return memories
    
    def _parse_single_memory(self, yaml_content: str, md_content: str) -> Optional[Memory]:
        """解析单个记忆"""
        import yaml
        
        try:
            data = yaml.safe_load(yaml_content)
            
            return Memory(
                id=data['id'],
                type=data['type'],
                title=data['title'],
                description=data.get('description'),
                content=md_content.strip(),
                metadata=data.get('metadata', {}),
                created_at=datetime.fromisoformat(data['created_at']),
                updated_at=datetime.fromisoformat(data['updated_at'])
            )
        except Exception as e:
            print(f"Failed to parse memory: {e}")
            return None
    
    def _ensure_directories(self) -> None:
        """确保所有类型目录存在"""
        from trendradar.memory.models import MemoryType
        
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        for mem_type in [MemoryType.DAILY_SUMMARY, MemoryType.WEEKLY_DIGEST,
                         MemoryType.TOPIC_INSIGHT, MemoryType.PATTERN, MemoryType.SIGNAL]:
            (self.base_path / mem_type).mkdir(exist_ok=True)
```

### 4.4 MemoryRepository 重构

```python
class MemoryRepository:
    """记忆仓库（门面类）"""
    
    def __init__(self, backend: StorageBackend):
        """使用依赖注入传入存储后端"""
        self.backend = backend
    
    def create(self, memory: Memory) -> None:
        """创建记忆 - 接口不变"""
        self.backend.create_memory(memory)
    
    def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """获取记忆 - 接口不变"""
        return self.backend.get_memory(memory_id)
    
    def get_by_type(self, memory_type: str, limit: Optional[int] = None) -> List[Memory]:
        """根据类型获取记忆 - 接口不变"""
        return self.backend.list_memories(memory_type=memory_type, limit=limit)
    
    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        memory_type: Optional[str] = None
    ) -> List[Memory]:
        """根据日期范围获取记忆 - 接口不变"""
        return self.backend.list_memories(
            memory_type=memory_type,
            start_date=start_date,
            end_date=end_date
        )
    
    def update(self, memory: Memory) -> None:
        """更新记忆 - 接口不变"""
        self.backend.update_memory(memory)
    
    def delete(self, memory_id: str) -> None:
        """删除记忆 - 接口不变"""
        self.backend.delete_memory(memory_id)
    
    def search(self, keyword: str, limit: Optional[int] = None) -> List[Memory]:
        """搜索记忆 - 接口不变"""
        return self.backend.search_memories(keyword, limit)
    
    # 链接相关方法保持不变（对于 FileBackend，从内容中解析链接）
```

### 4.5 MemoryIndexManager

专门管理 MEMORY.md 索引：

```python
class MemoryIndexManager:
    """记忆索引管理器"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.index_file = base_path / "MEMORY.md"
    
    def update_index(self) -> None:
        """扫描所有记忆文件，重新生成索引"""
        from trendradar.memory.models import MemoryType
        
        # 扫描所有类型
        all_memories = {}
        for mem_type in [MemoryType.DAILY_SUMMARY, MemoryType.WEEKLY_DIGEST,
                         MemoryType.TOPIC_INSIGHT, MemoryType.PATTERN, MemoryType.SIGNAL]:
            type_dir = self.base_path / mem_type
            if not type_dir.exists():
                continue
            
            memories = []
            for md_file in type_dir.glob("**/*.md"):
                memories.extend(self._scan_file(md_file))
            
            all_memories[mem_type] = sorted(memories, key=lambda m: m['created_at'], reverse=True)
        
        # 生成索引内容
        content = self._generate_index_content(all_memories)
        
        # 写入文件
        self.index_file.write_text(content, encoding='utf-8')
    
    def _scan_file(self, file_path: Path) -> List[Dict]:
        """扫描文件提取索引信息"""
        import yaml
        
        content = file_path.read_text(encoding='utf-8')
        parts = content.split('---\n')
        
        entries = []
        i = 1
        while i < len(parts) - 1:
            try:
                data = yaml.safe_load(parts[i])
                
                # 提取关键信息
                entries.append({
                    'id': data['id'],
                    'title': data['title'],
                    'description': data.get('description', ''),
                    'created_at': datetime.fromisoformat(data['created_at']),
                    'file_path': file_path.relative_to(self.base_path),
                    'metadata': data.get('metadata', {})
                })
            except:
                pass
            
            i += 2
        
        return entries
    
    def _generate_index_content(self, all_memories: Dict[str, List]) -> str:
        """生成索引 Markdown 内容"""
        from datetime import datetime
        
        lines = [
            "# TrendRadar 记忆索引",
            "",
            f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        type_names = {
            'daily_summary': '每日摘要',
            'weekly_digest': '每周摘要',
            'topic_insight': '主题洞察',
            'pattern': '模式识别',
            'signal': '信号记录'
        }
        
        for mem_type, memories in all_memories.items():
            if not memories:
                continue
            
            lines.append(f"## {type_names.get(mem_type, mem_type)} ({mem_type})")
            lines.append("")
            
            for memory in memories[:20]:  # 每类最多显示 20 条
                # 提取简要信息
                date = memory['created_at'].strftime('%Y-%m-%d')
                desc = memory['description'][:50] + '...' if len(memory['description']) > 50 else memory['description']
                
                # 提取关键词
                keywords = memory['metadata'].get('top_keywords', [])
                keywords_str = '，'.join(keywords[:3]) if keywords else ''
                
                link = f"{memory['file_path']}#{memory['id']}"
                lines.append(f"- [{date}]({link}) — {desc}" + (f"，关键词：{keywords_str}" if keywords_str else ""))
            
            lines.append("")
        
        return '\n'.join(lines)
```

### 4.6 工厂函数

```python
def create_memory_repository(config: Dict[str, Any]) -> MemoryRepository:
    """根据配置创建 MemoryRepository"""
    storage_type = config.get("storage_type", "database")
    
    if storage_type == "database":
        db_config = config.get("database_storage", {})
        backend = DatabaseBackend(db_config["db_path"])
    elif storage_type == "file":
        file_config = config.get("file_storage", {})
        backend = FileBackend(
            base_path=file_config["base_path"],
            auto_index=file_config.get("auto_index", True)
        )
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
    
    return MemoryRepository(backend)
```

## 5. 数据流设计

### 5.1 创建记忆流程

```
MemoryGenerator.generate_daily_summary()
    ↓
调用 repository.create(memory)
    ↓
MemoryRepository.create(memory)
    ↓
backend.create_memory(memory)
    ↓
[FileBackend]
    ├─ 确定文件路径：daily_summary/2026-05.md
    ├─ 转换为 Markdown 格式
    ├─ 追加到月度文件（或创建新文件）
    ├─ 提取关键词趋势到 metadata
    └─ 更新 MEMORY.md 索引
```

### 5.2 查询记忆流程

```
repository.get_by_type("daily_summary", limit=10)
    ↓
MemoryRepository.get_by_type()
    ↓
backend.list_memories(memory_type="daily_summary", limit=10)
    ↓
[FileBackend]
    ├─ 扫描 daily_summary/ 目录
    ├─ 解析所有 .md 文件
    ├─ 提取 frontmatter 和内容
    ├─ 按 created_at 排序
    ├─ 应用 limit
    └─ 返回 Memory 对象列表
```

## 6. 迁移工具设计

### 6.1 MemoryMigrator 类

```python
class MemoryMigrator:
    """记忆数据迁移工具"""
    
    def __init__(self, db_path: str, file_base_path: str):
        self.db_backend = DatabaseBackend(db_path)
        self.file_backend = FileBackend(file_base_path)
    
    def migrate_db_to_file(self, dry_run: bool = False) -> Dict[str, int]:
        """
        从数据库迁移到文件
        
        Args:
            dry_run: 仅模拟，不实际执行
        
        Returns:
            统计信息：{"migrated": 10, "skipped": 2, "failed": 0}
        """
        stats = {"migrated": 0, "skipped": 0, "failed": 0}
        
        # 1. 获取所有记忆
        all_memories = self.db_backend.list_memories()
        
        print(f"找到 {len(all_memories)} 条记忆")
        
        # 2. 逐个迁移
        for memory in all_memories:
            try:
                # 检查文件中是否已存在
                existing = self.file_backend.get_memory(memory.id)
                if existing:
                    print(f"  跳过: {memory.id}（已存在）")
                    stats["skipped"] += 1
                    continue
                
                if not dry_run:
                    self.file_backend.create_memory(memory)
                
                print(f"  ✓ 迁移: {memory.id}")
                stats["migrated"] += 1
                
            except Exception as e:
                print(f"  ✗ 失败: {memory.id} - {e}")
                stats["failed"] += 1
        
        # 3. 迁移关键词趋势（合并到每日摘要）
        if not dry_run:
            print("\n合并关键词趋势...")
            self._merge_keyword_trends()
        
        return stats
    
    def migrate_file_to_db(self) -> Dict[str, int]:
        """从文件迁移到数据库（反向）"""
        stats = {"migrated": 0, "skipped": 0, "failed": 0}
        
        # 扫描所有文件并写入数据库
        all_memories = self.file_backend.list_memories()
        
        print(f"找到 {len(all_memories)} 条记忆")
        
        for memory in all_memories:
            try:
                existing = self.db_backend.get_memory(memory.id)
                if existing:
                    print(f"  跳过: {memory.id}（已存在）")
                    stats["skipped"] += 1
                    continue
                
                self.db_backend.create_memory(memory)
                print(f"  ✓ 迁移: {memory.id}")
                stats["migrated"] += 1
                
            except Exception as e:
                print(f"  ✗ 失败: {memory.id} - {e}")
                stats["failed"] += 1
        
        return stats
    
    def _merge_keyword_trends(self) -> None:
        """将 keyword_trends 表数据合并到每日摘要"""
        import sqlite3
        import json
        from collections import defaultdict
        
        # 1. 从数据库读取 keyword_trends
        conn = sqlite3.connect(self.db_backend.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT date, keyword, count, platforms, rank FROM keyword_trends ORDER BY date")
        rows = cursor.fetchall()
        conn.close()
        
        # 2. 按日期分组
        trends_by_date = defaultdict(list)
        for row in rows:
            date = row['date']
            trends_by_date[date].append({
                'keyword': row['keyword'],
                'count': row['count'],
                'platforms': json.loads(row['platforms']) if row['platforms'] else [],
                'rank': row['rank']
            })
        
        # 3. 更新每日摘要
        for date_str, trends in trends_by_date.items():
            # 查找对应的每日摘要
            date = datetime.strptime(date_str, '%Y-%m-%d')
            daily_memories = self.file_backend.list_memories(
                memory_type='daily_summary',
                start_date=date,
                end_date=date
            )
            
            for memory in daily_memories:
                # 更新 metadata
                if 'keyword_trends' not in memory.metadata:
                    memory.metadata['keyword_trends'] = trends
                    self.file_backend.update_memory(memory)
                    print(f"  ✓ 合并关键词趋势到: {memory.id}")
```

### 6.2 CLI 命令

```python
# trendradar/cli/memory_commands.py

import click
from trendradar.memory.migrator import MemoryMigrator

@click.group()
def memory():
    """记忆系统管理命令"""
    pass

@memory.command()
@click.option('--db-path', required=True, help='数据库文件路径')
@click.option('--file-path', required=True, help='文件存储目录路径')
@click.option('--dry-run', is_flag=True, help='仅模拟，不实际执行')
def migrate_to_file(db_path: str, file_path: str, dry_run: bool):
    """将数据库数据迁移到文件格式"""
    click.echo("=" * 60)
    click.echo("记忆数据迁移：数据库 → 文件")
    click.echo("=" * 60)
    click.echo(f"数据库路径: {db_path}")
    click.echo(f"文件路径: {file_path}")
    click.echo(f"模式: {'试运行（不写入）' if dry_run else '正式运行'}")
    click.echo()
    
    migrator = MemoryMigrator(db_path, file_path)
    
    click.echo("开始迁移...")
    stats = migrator.migrate_db_to_file(dry_run=dry_run)
    
    click.echo()
    click.echo("=" * 60)
    click.echo("迁移完成")
    click.echo("=" * 60)
    click.echo(f"  ✓ 成功迁移: {stats['migrated']}")
    click.echo(f"  ⊘ 跳过: {stats['skipped']}")
    click.echo(f"  ✗ 失败: {stats['failed']}")
    click.echo()

@memory.command()
@click.option('--db-path', required=True, help='数据库文件路径')
@click.option('--file-path', required=True, help='文件存储目录路径')
def migrate_to_db(db_path: str, file_path: str):
    """将文件格式数据迁移到数据库"""
    click.echo("=" * 60)
    click.echo("记忆数据迁移：文件 → 数据库")
    click.echo("=" * 60)
    click.echo(f"文件路径: {file_path}")
    click.echo(f"数据库路径: {db_path}")
    click.echo()
    
    migrator = MemoryMigrator(db_path, file_path)
    
    click.echo("开始迁移...")
    stats = migrator.migrate_file_to_db()
    
    click.echo()
    click.echo("=" * 60)
    click.echo("迁移完成")
    click.echo("=" * 60)
    click.echo(f"  ✓ 成功迁移: {stats['migrated']}")
    click.echo(f"  ⊘ 跳过: {stats['skipped']}")
    click.echo(f"  ✗ 失败: {stats['failed']}")
    click.echo()

# 使用示例：
# python -m trendradar memory migrate-to-file --db-path output/memory.db --file-path output/memory --dry-run
# python -m trendradar memory migrate-to-file --db-path output/memory.db --file-path output/memory
# python -m trendradar memory migrate-to-db --db-path output/memory.db --file-path output/memory
```

## 7. 错误处理

### 7.1 异常定义

```python
class MemoryStorageError(Exception):
    """存储层基础异常"""
    pass

class MemoryNotFoundError(MemoryStorageError):
    """记忆不存在"""
    pass

class MemoryAlreadyExistsError(MemoryStorageError):
    """记忆已存在"""
    pass

class MemoryParseError(MemoryStorageError):
    """Markdown 解析失败"""
    pass

class MemoryCorruptedError(MemoryStorageError):
    """记忆数据损坏"""
    pass
```

### 7.2 错误处理策略

```python
class FileBackend(StorageBackend):
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        try:
            # 查找文件
            file_path = self._find_file_by_id(memory_id)
            if not file_path:
                return None
            
            # 解析文件
            content = file_path.read_text(encoding='utf-8')
            return self._extract_memory_from_markdown(content, memory_id)
            
        except UnicodeDecodeError as e:
            raise MemoryParseError(f"Failed to decode file: {e}")
        except yaml.YAMLError as e:
            raise MemoryParseError(f"Failed to parse YAML frontmatter: {e}")
        except KeyError as e:
            raise MemoryCorruptedError(f"Missing required field in memory: {e}")
        except Exception as e:
            raise MemoryStorageError(f"Failed to get memory {memory_id}: {e}")
    
    def create_memory(self, memory: Memory) -> None:
        try:
            # ... 创建逻辑
            pass
        except PermissionError as e:
            raise MemoryStorageError(f"Permission denied: {e}")
        except OSError as e:
            raise MemoryStorageError(f"File system error: {e}")
```

## 8. 测试策略

### 8.1 单元测试

```python
# tests/memory/test_file_backend.py

import pytest
from datetime import datetime
from pathlib import Path
from trendradar.memory.models import Memory, MemoryType
from trendradar.memory.storage import FileBackend

@pytest.fixture
def temp_storage(tmp_path):
    """临时文件存储"""
    return FileBackend(str(tmp_path), auto_index=False)

def test_create_and_get_memory(temp_storage):
    """测试创建和获取记忆"""
    memory = Memory(
        id="test-001",
        type=MemoryType.DAILY_SUMMARY,
        title="测试摘要",
        content="测试内容",
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1)
    )
    
    temp_storage.create_memory(memory)
    retrieved = temp_storage.get_memory("test-001")
    
    assert retrieved is not None
    assert retrieved.id == "test-001"
    assert retrieved.title == "测试摘要"
    assert retrieved.content == "测试内容"

def test_list_memories_by_type(temp_storage):
    """测试按类型列出记忆"""
    # 创建多个记忆
    for i in range(3):
        memory = Memory(
            id=f"daily-{i}",
            type=MemoryType.DAILY_SUMMARY,
            title=f"摘要 {i}",
            content=f"内容 {i}",
            created_at=datetime(2026, 5, i+1),
            updated_at=datetime(2026, 5, i+1)
        )
        temp_storage.create_memory(memory)
    
    results = temp_storage.list_memories(memory_type=MemoryType.DAILY_SUMMARY)
    assert len(results) == 3
    assert all(m.type == MemoryType.DAILY_SUMMARY for m in results)

def test_search_memories(temp_storage):
    """测试搜索记忆"""
    memory = Memory(
        id="search-test",
        type=MemoryType.DAILY_SUMMARY,
        title="包含关键词AI的标题",
        content="内容中也包含AI技术",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    temp_storage.create_memory(memory)
    
    results = temp_storage.search_memories("AI")
    assert len(results) == 1
    assert results[0].id == "search-test"

def test_update_memory(temp_storage):
    """测试更新记忆"""
    memory = Memory(
        id="update-test",
        type=MemoryType.DAILY_SUMMARY,
        title="原标题",
        content="原内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    temp_storage.create_memory(memory)
    
    # 更新
    updated_memory = Memory(
        id="update-test",
        type=MemoryType.DAILY_SUMMARY,
        title="新标题",
        content="新内容",
        created_at=memory.created_at,
        updated_at=datetime.now()
    )
    temp_storage.update_memory(updated_memory)
    
    # 验证
    retrieved = temp_storage.get_memory("update-test")
    assert retrieved.title == "新标题"
    assert retrieved.content == "新内容"

def test_delete_memory(temp_storage):
    """测试删除记忆"""
    memory = Memory(
        id="delete-test",
        type=MemoryType.DAILY_SUMMARY,
        title="待删除",
        content="待删除内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    temp_storage.create_memory(memory)
    
    # 删除
    temp_storage.delete_memory("delete-test")
    
    # 验证
    assert temp_storage.get_memory("delete-test") is None

def test_markdown_format(temp_storage):
    """测试 Markdown 格式正确性"""
    memory = Memory(
        id="format-test",
        type=MemoryType.DAILY_SUMMARY,
        title="格式测试",
        content="# 标题\n\n内容",
        metadata={"key": "value"},
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1)
    )
    
    temp_storage.create_memory(memory)
    
    # 读取原始文件内容
    file_path = temp_storage.base_path / "daily_summary" / "2026-05.md"
    content = file_path.read_text(encoding='utf-8')
    
    # 验证格式
    assert content.startswith("---\n")
    assert "id: format-test" in content
    assert "type: daily_summary" in content
    assert "# 标题" in content
```

### 8.2 集成测试

```python
# tests/memory/test_repository_integration.py

def test_repository_with_file_backend(tmp_path):
    """测试 Repository 使用 FileBackend"""
    backend = FileBackend(str(tmp_path))
    repo = MemoryRepository(backend)
    
    memory = Memory(
        id="integration-test",
        type=MemoryType.DAILY_SUMMARY,
        title="集成测试",
        content="测试内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    repo.create(memory)
    retrieved = repo.get_by_id(memory.id)
    
    assert retrieved.id == memory.id
    assert retrieved.title == memory.title

def test_repository_with_database_backend(tmp_path):
    """测试 Repository 使用 DatabaseBackend"""
    db_path = str(tmp_path / "test.db")
    backend = DatabaseBackend(db_path)
    repo = MemoryRepository(backend)
    
    memory = Memory(
        id="db-integration-test",
        type=MemoryType.DAILY_SUMMARY,
        title="数据库集成测试",
        content="测试内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    repo.create(memory)
    retrieved = repo.get_by_id(memory.id)
    
    assert retrieved.id == memory.id
    assert retrieved.title == memory.title
```

### 8.3 迁移测试

```python
# tests/memory/test_migration.py

def test_migrate_db_to_file(tmp_path):
    """测试数据库到文件的迁移"""
    db_path = str(tmp_path / "test.db")
    file_path = str(tmp_path / "memory")
    
    # 1. 准备数据库数据
    db_backend = DatabaseBackend(db_path)
    memory = Memory(
        id="migrate-test-001",
        type=MemoryType.DAILY_SUMMARY,
        title="迁移测试",
        content="测试内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db_backend.create_memory(memory)
    
    # 2. 迁移
    migrator = MemoryMigrator(db_path, file_path)
    stats = migrator.migrate_db_to_file()
    
    assert stats["migrated"] == 1
    assert stats["failed"] == 0
    
    # 3. 验证文件存在
    file_backend = FileBackend(file_path)
    retrieved = file_backend.get_memory(memory.id)
    
    assert retrieved is not None
    assert retrieved.id == memory.id
    assert retrieved.title == memory.title

def test_migrate_file_to_db(tmp_path):
    """测试文件到数据库的迁移"""
    db_path = str(tmp_path / "test.db")
    file_path = str(tmp_path / "memory")
    
    # 1. 准备文件数据
    file_backend = FileBackend(file_path)
    memory = Memory(
        id="migrate-test-002",
        type=MemoryType.DAILY_SUMMARY,
        title="反向迁移测试",
        content="测试内容",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    file_backend.create_memory(memory)
    
    # 2. 迁移
    migrator = MemoryMigrator(db_path, file_path)
    stats = migrator.migrate_file_to_db()
    
    assert stats["migrated"] == 1
    assert stats["failed"] == 0
    
    # 3. 验证数据库记录
    db_backend = DatabaseBackend(db_path)
    retrieved = db_backend.get_memory(memory.id)
    
    assert retrieved is not None
    assert retrieved.id == memory.id
    assert retrieved.title == memory.title
```

## 9. 使用示例

### 9.1 现有代码继续工作

```python
# 以前的代码（继续工作，无需修改）
from trendradar.memory.generator import MemoryGenerator

generator = MemoryGenerator(db_path="output/memory.db", ai_config={...})
memory = generator.generate_daily_summary(date)
```

### 9.2 切换到文件存储

#### 方式 1：通过配置文件

```python
from trendradar.context import load_config
from trendradar.memory.factory import create_memory_repository
from trendradar.memory.generator import MemoryGenerator

# 加载配置
config = load_config("config.yaml")

# 创建 repository
repo = create_memory_repository(config["memory"])

# MemoryGenerator 使用新 repository
generator = MemoryGenerator(repository=repo, ai_config={...})
memory = generator.generate_daily_summary(date)
```

#### 方式 2：直接指定

```python
from trendradar.memory.storage import FileBackend
from trendradar.memory.models import MemoryRepository
from trendradar.memory.generator import MemoryGenerator

# 创建文件后端
backend = FileBackend(base_path="output/memory")

# 创建 repository
repo = MemoryRepository(backend)

# 使用
generator = MemoryGenerator(repository=repo, ai_config={...})
memory = generator.generate_daily_summary(date)
```

### 9.3 数据迁移

```bash
# 试运行（不实际写入）
python -m trendradar memory migrate-to-file \
    --db-path output/memory.db \
    --file-path output/memory \
    --dry-run

# 正式迁移
python -m trendradar memory migrate-to-file \
    --db-path output/memory.db \
    --file-path output/memory

# 反向迁移（文件 → 数据库）
python -m trendradar memory migrate-to-db \
    --db-path output/memory.db \
    --file-path output/memory
```

## 10. 实施计划

### Phase 1：基础架构（1-2天）
- [ ] 创建 StorageBackend 抽象基类
- [ ] 实现 DatabaseBackend（迁移现有逻辑）
- [ ] 重构 MemoryRepository 使用依赖注入
- [ ] 单元测试

### Phase 2：文件存储（2-3天）
- [ ] 实现 FileBackend 核心功能
  - [ ] create_memory
  - [ ] get_memory
  - [ ] list_memories
  - [ ] search_memories
  - [ ] update_memory
  - [ ] delete_memory
- [ ] 实现 Markdown 解析和生成
- [ ] 单元测试

### Phase 3：索引管理（1天）
- [ ] 实现 MemoryIndexManager
- [ ] 自动索引更新
- [ ] 测试

### Phase 4：迁移工具（1-2天）
- [ ] 实现 MemoryMigrator
- [ ] CLI 命令
- [ ] 关键词趋势合并逻辑
- [ ] 测试

### Phase 5：集成与测试（1-2天）
- [ ] 集成测试
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 文档更新

### Phase 6：部署与切换（1天）
- [ ] 配置文件更新
- [ ] 数据迁移
- [ ] 验证

**预计总工时**：7-11 天

## 11. 风险与缓解

### 风险 1：文件系统性能
**风险**：大量小文件可能影响性能  
**缓解**：
- 按月合并文件，减少文件数量
- 添加缓存层
- 监控性能指标

### 风险 2：并发写入
**风险**：多进程同时写入同一文件可能冲突  
**缓解**：
- 使用文件锁
- 或者每个记忆单独文件
- 记录写入日志

### 风险 3：数据完整性
**风险**：文件损坏或格式错误  
**缓解**：
- 写入前验证
- 写入时使用原子操作
- 定期备份
- 提供修复工具

### 风险 4：迁移失败
**风险**：迁移过程中数据丢失或损坏  
**缓解**：
- 先备份
- 使用 dry-run 模式测试
- 提供回滚机制
- 保留原数据库

## 12. 附录

### A. 配置示例

```yaml
# config.yaml

memory:
  # 存储类型：database 或 file
  storage_type: file
  
  # 文件存储配置
  file_storage:
    base_path: ./output/memory
    auto_index: true
    max_memories_per_file: 100
  
  # 数据库存储配置
  database_storage:
    db_path: ./output/memory.db
```

### B. 环境变量

```bash
# 存储类型
export MEMORY_STORAGE_TYPE=file

# 文件路径
export MEMORY_FILE_PATH=./output/memory

# 是否自动索引
export MEMORY_AUTO_INDEX=true

# 数据库路径
export MEMORY_DB_PATH=./output/memory.db
```

### C. 文件大小估算

假设：
- 每条记忆平均 2KB
- 每月 30 条每日摘要
- 每个月度文件约 60KB

一年数据：
- 12 个月度文件 × 60KB = 720KB
- 加上其他类型记忆，总计约 1-2MB

文件数量少，易于管理。

---

**设计文档结束**
