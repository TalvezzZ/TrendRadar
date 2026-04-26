# OSS 数据库同步功能使用指南

## 功能概述

TrendRadar 支持将本地 SQLite 数据库自动同步到阿里云 OSS（对象存储服务），实现数据的云端备份和多环境共享。

### 核心功能

1. **自动下载**: 爬虫运行前自动从 OSS 下载数据库到本地
2. **自动上传**: 爬虫运行后自动上传数据库到 OSS
3. **数据备份**: 所有日期数据库 (`output/news/*.db`) 和 `memory.db` 都会同步
4. **首次运行友好**: 远程没有数据库时静默跳过，不影响使用

## 配置方法

### 1. 在 `config/config.yaml` 中添加 OSS 配置

```yaml
STORAGE:
  BACKEND_TYPE: auto  # auto / local / remote
  DATA_DIR: output
  
  # 远程存储配置（阿里云 OSS）
  REMOTE_BACKEND:
    bucket_name: your-bucket-name
    access_key_id: your-access-key-id
    secret_access_key: your-secret-access-key
    endpoint_url: https://oss-cn-hangzhou.aliyuncs.com  # OSS 区域端点
    region: cn-hangzhou  # OSS 区域
```

### 2. OSS 区域端点参考

| 区域 | endpoint_url |
|------|-------------|
| 华东1（杭州） | `https://oss-cn-hangzhou.aliyuncs.com` |
| 华东2（上海） | `https://oss-cn-shanghai.aliyuncs.com` |
| 华北1（青岛） | `https://oss-cn-qingdao.aliyuncs.com` |
| 华北2（北京） | `https://oss-cn-beijing.aliyuncs.com` |
| 华北3（张家口） | `https://oss-cn-zhangjiakou.aliyuncs.com` |
| 华南1（深圳） | `https://oss-cn-shenzhen.aliyuncs.com` |

完整列表请参考：https://help.aliyun.com/document_detail/31837.html

### 3. 环境变量配置（可选）

也可以使用环境变量配置（优先级高于配置文件）：

```bash
export S3_BUCKET_NAME=your-bucket-name
export S3_ACCESS_KEY_ID=your-access-key-id
export S3_SECRET_ACCESS_KEY=your-secret-access-key
export S3_ENDPOINT_URL=https://oss-cn-hangzhou.aliyuncs.com
export S3_REGION=cn-hangzhou
```

## 使用方法

### 自动同步（推荐）

配置完成后，TrendRadar 会在每次运行时自动同步：

```bash
python -m trendradar
```

流程：
1. 启动前：从 OSS 下载所有数据库到 `output/` 目录
2. 运行爬虫：正常抓取和分析数据
3. 结束后：上传所有数据库到 OSS

### 手动测试同步

使用测试脚本验证配置是否正确：

```bash
python test_oss_sync.py
```

测试内容：
- 列出远程数据库文件
- 上传本地数据库到 OSS
- 从 OSS 下载数据库到本地

### 使用 StorageManager API

在代码中手动调用同步方法：

```python
from trendradar.storage import get_storage_manager
from trendradar.core import load_config

config = load_config()
storage_config = config.get("STORAGE", {})

storage_manager = get_storage_manager(
    backend_type=storage_config.get("BACKEND_TYPE", "auto"),
    data_dir=storage_config.get("DATA_DIR", "output"),
    remote_config=storage_config.get("REMOTE_BACKEND", {}),
)

# 上传数据库到 OSS
uploaded = storage_manager.sync_databases_to_s3()
print(f"上传了 {uploaded} 个文件")

# 从 OSS 下载数据库
downloaded = storage_manager.sync_databases_from_s3()
print(f"下载了 {downloaded} 个文件")

# 列出远程数据库
databases = storage_manager.list_remote_databases()
for db in databases:
    print(f"{db['key']} - {db['size']} bytes")
```

## 远程存储路径结构

数据库在 OSS 中的存储路径：

```
your-bucket/
├── databases/
│   ├── news/
│   │   ├── 2025-12-21.db
│   │   ├── 2025-12-22.db
│   │   └── ...
│   └── memory.db
```

## 常见问题

### 1. 未安装 boto3

错误：`未安装 boto3，跳过上传/下载`

解决：
```bash
pip install boto3
```

### 2. 认证失败

错误：`访问被拒绝，请检查密钥权限`

解决：
- 检查 `access_key_id` 和 `secret_access_key` 是否正确
- 确保 RAM 用户有 OSS 读写权限
- 验证 bucket 名称是否正确

### 3. 存储桶不存在

错误：`存储桶不存在: your-bucket-name`

解决：
- 在阿里云 OSS 控制台创建存储桶
- 确保 bucket 名称拼写正确
- 检查区域是否匹配

### 4. 首次运行没有数据

这是正常现象！首次运行时：
- OSS 上还没有数据库文件
- 系统会静默跳过下载
- 运行后会自动上传新数据库

### 5. 网络连接失败

错误：`下载/上传异常: ...`

解决：
- 检查网络连接
- 验证 endpoint_url 是否正确
- 确认防火墙没有阻止 OSS 访问

## 安全建议

1. **不要将密钥提交到 Git**
   - 使用 `.gitignore` 忽略包含密钥的配置文件
   - 或使用环境变量配置

2. **使用 RAM 子账号**
   - 不要使用主账号的 AccessKey
   - 创建 RAM 用户并授予最小权限

3. **定期轮换密钥**
   - 定期更换 AccessKey
   - 删除不使用的旧密钥

4. **限制 Bucket 权限**
   - 设置适当的 Bucket 访问策略
   - 禁止公开访问

## 技术细节

- 使用 boto3 S3 兼容 API 访问 OSS
- 支持阿里云 OSS 的 SigV2 签名
- 使用 chunked transfer encoding 处理大文件
- 自动处理网络异常和重试
- 支持进度显示和验证

## 参考文档

- [阿里云 OSS 文档](https://help.aliyun.com/product/31815.html)
- [OSS SDK for Python](https://help.aliyun.com/document_detail/32026.html)
- [boto3 文档](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
