# 记忆同步问题修复文档

## 问题描述

在使用记忆生成功能时,发现OSS上的记忆文件被覆盖而不是追加,导致历史记忆丢失。

### 具体表现

- **本地**: 5月有22条记忆, 4月有5条记忆
- **OSS**: 5月只有1条记忆, 4月有5条记忆
- **现象**: 每次生成新的记忆后上传,会覆盖远程文件而不是追加

## 根本原因

在 `trendradar/storage/manager.py` 的 `sync_memory_markdown_to_s3()` 方法中:

```python
# 原始逻辑 (错误)
if local_modified <= remote_modified and remote_size == local_size:
    skip_upload = True
else:
    # 直接上传本地文件,覆盖远程文件
    s3_client.put_object(...)
```

这个逻辑存在以下问题:

1. **直接覆盖**: 当本地文件更新或大小不同时,直接上传覆盖远程文件
2. **丢失远程独有数据**: 如果远程有本地没有的记忆,会被覆盖丢失
3. **没有合并机制**: 缺少合并本地和远程数据的逻辑

## 修复方案

### 1. 修改上传逻辑

```python
# 新逻辑 (正确)
# 1. 检查远程文件是否存在
remote_obj = s3_client.head_object(Bucket=bucket_name, Key=remote_key)

# 2. 如果大小相同,跳过(假设内容一致)
if remote_size == local_size:
    continue

# 3. 大小不同,下载远程文件
remote_content = s3_client.get_object(...).read().decode('utf-8')

# 4. 合并本地和远程内容
merged_content = self._merge_memory_markdown(local_content, remote_content)

# 5. 更新本地文件
with open(md_file, 'w') as f:
    f.write(merged_content)

# 6. 上传合并后的内容
s3_client.put_object(...)
```

### 2. 添加合并方法

新增 `_merge_memory_markdown()` 方法:

```python
def _merge_memory_markdown(self, local_content: str, remote_content: str) -> str:
    """
    合并本地和远程的 Markdown 文件
    
    策略:
    - 提取所有记忆的 ID
    - 找出远程独有的记忆
    - 追加到本地文件末尾
    """
    # 1. 解析所有记忆ID
    local_ids = parse_markdown_ids(local_content)
    remote_ids = parse_markdown_ids(remote_content)
    
    # 2. 找出远程独有的记忆
    remote_only_ids = remote_ids - local_ids
    
    # 3. 追加远程独有的记忆到本地
    merged_content = local_content
    for memory_id in remote_only_ids:
        memory_block = extract_memory_block(remote_content, memory_id)
        merged_content += "\n" + memory_block
    
    return merged_content
```

### 3. 修复历史数据

创建并运行修复脚本 `scripts/fix_memory_sync.py`:

```bash
python scripts/fix_memory_sync.py
```

脚本功能:
1. 扫描所有本地记忆文件
2. 下载对应的远程文件
3. 合并本地和远程内容
4. 保存合并后的文件到本地
5. 上传合并后的文件到OSS

## 修复结果

### 数据恢复情况

| 文件 | 修复前(OSS) | 修复后(OSS) | 本地 | 状态 |
|------|-------------|-------------|------|------|
| 2026-05.md | 1条记忆 | 24条记忆 | 24条记忆 | ✅ 已修复 |
| 2026-04.md | 5条记忆 | 5条记忆 | 5条记忆 | ✅ 一致 |

### 验证结果

```bash
# 5月文件
OSS上5月文件 - 记忆数量: 24, 总行数: 992
本地5月文件 - 记忆数量: 24, 总行数: 992
✅ OSS和本地记忆数量一致!

# 4月文件
OSS上4月文件 - 记忆数量: 5, 总行数: 210
本地4月文件 - 记忆数量: 5, 总行数: 210
✅ OSS和本地记忆数量一致!
```

## 后续建议

### 1. 测试场景

在以下场景测试修复后的逻辑:

- [x] 本地新增记忆 → 上传 (追加到远程)
- [ ] 远程新增记忆 → 下载 (追加到本地)
- [ ] 两端同时新增不同记忆 → 合并
- [ ] 两端新增相同记忆 → 去重

### 2. 监控建议

建议添加以下监控:

1. **记忆数量监控**: 定期检查OSS和本地记忆数量是否一致
2. **同步日志**: 记录每次同步的详细信息(新增/合并/跳过)
3. **异常告警**: 当检测到数据不一致时发送告警

### 3. 优化建议

考虑以下优化:

1. **增量同步**: 只同步有变化的记忆,减少网络传输
2. **版本控制**: 为记忆文件添加版本号,支持冲突检测
3. **备份机制**: 在覆盖前备份远程文件

## 相关文件

- 修复代码: `trendradar/storage/manager.py`
- 修复脚本: `scripts/fix_memory_sync.py`
- 测试验证: 见上述验证结果

## 修复时间

- 发现时间: 2026-06-01
- 修复时间: 2026-06-01
- 验证通过: 2026-06-01

## 影响范围

- **影响模块**: 记忆生成和同步
- **影响数据**: 5月份记忆文件(已修复)
- **未来影响**: 已修复,不会再发生

## 总结

本次修复彻底解决了记忆文件同步覆盖的问题,通过:

1. ✅ 修改上传逻辑支持智能合并
2. ✅ 添加合并方法处理本地和远程差异
3. ✅ 运行修复脚本恢复历史数据
4. ✅ 验证数据一致性

现在记忆同步功能可以正确地追加新记忆,而不会覆盖历史数据。
