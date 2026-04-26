# OSS 数据库同步 - 快速开始

## 5 分钟快速配置指南

### 步骤 1: 安装依赖

```bash
pip install boto3
```

### 步骤 2: 创建阿里云 OSS 存储桶

1. 登录阿里云控制台
2. 进入对象存储 OSS 服务
3. 创建新的存储桶（Bucket）
   - 选择区域（如：华东1-杭州）
   - 设置存储桶名称（如：`trendradar-data`）
   - 访问控制：私有

### 步骤 3: 创建 RAM 用户和 AccessKey

1. 进入 RAM 访问控制
2. 创建新用户
3. 授予权限：`AliyunOSSFullAccess`（或自定义更细粒度权限）
4. 创建 AccessKey
5. 保存 AccessKey ID 和 AccessKey Secret

### 步骤 4: 配置 TrendRadar

在 `config/config.yaml` 中添加：

```yaml
STORAGE:
  BACKEND_TYPE: auto
  DATA_DIR: output
  
  REMOTE_BACKEND:
    bucket_name: trendradar-data  # 替换为你的存储桶名称
    access_key_id: LTAI5tXXXXXXXXXXXXXX  # 替换为你的 AccessKey ID
    secret_access_key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # 替换为你的 AccessKey Secret
    endpoint_url: https://oss-cn-hangzhou.aliyuncs.com  # 替换为你的区域端点
    region: cn-hangzhou  # 替换为你的区域
```

或使用环境变量（更安全）：

```bash
export S3_BUCKET_NAME=trendradar-data
export S3_ACCESS_KEY_ID=LTAI5tXXXXXXXXXXXXXX
export S3_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export S3_ENDPOINT_URL=https://oss-cn-hangzhou.aliyuncs.com
export S3_REGION=cn-hangzhou
```

### 步骤 5: 测试配置

```bash
python test_oss_sync.py
```

预期输出：
```
============================================================
OSS 数据库同步功能测试
============================================================

============================================================
测试 1: 列出远程数据库
============================================================
[数据库同步] 远程没有数据库文件（首次运行），跳过下载
⚠️  远程没有数据库文件（首次运行）

============================================================
测试 2: 上传数据库到远程
============================================================
本地有 7 个数据库文件
[数据库同步] 上传: 2025-12-21.db (922.0 KB)
[数据库同步] 上传成功: databases/news/2025-12-21.db
...
✅ 成功上传 7 个文件

...
🎉 所有测试通过！
```

### 步骤 6: 正常运行

```bash
python -m trendradar
```

现在每次运行都会自动同步数据库！

## 常用命令

### 列出远程数据库
```python
from trendradar.storage import get_storage_manager
from trendradar.core import load_config

config = load_config()
storage = get_storage_manager(
    backend_type=config.get("STORAGE", {}).get("BACKEND_TYPE", "auto"),
    data_dir=config.get("STORAGE", {}).get("DATA_DIR", "output"),
    remote_config=config.get("STORAGE", {}).get("REMOTE_BACKEND", {}),
)

databases = storage.list_remote_databases()
```

### 手动上传
```python
uploaded = storage.sync_databases_to_s3()
print(f"上传了 {uploaded} 个文件")
```

### 手动下载
```python
downloaded = storage.sync_databases_from_s3()
print(f"下载了 {downloaded} 个文件")
```

## 故障排查

### 问题 1: 认证失败

```
[数据库同步] 访问被拒绝，请检查密钥权限
```

**解决**:
- 检查 AccessKey ID 和 Secret 是否正确
- 确保 RAM 用户有 OSS 读写权限
- 验证存储桶名称和区域是否正确

### 问题 2: 存储桶不存在

```
[数据库同步] 存储桶不存在: your-bucket-name
```

**解决**:
- 在阿里云 OSS 控制台创建存储桶
- 确保 bucket_name 拼写正确
- 检查区域是否匹配

### 问题 3: 未安装 boto3

```
[数据库同步] 未安装 boto3，跳过上传/下载
```

**解决**:
```bash
pip install boto3
```

## 安全提示

1. 不要将 AccessKey 提交到 Git
2. 使用环境变量而不是配置文件存储密钥
3. 定期轮换 AccessKey
4. 使用 RAM 子账号而非主账号
5. 设置最小权限（仅授予必要的 OSS 权限）

## 进一步阅读

- [完整使用文档](docs/OSS_SYNC.md)
- [功能实现摘要](OSS_SYNC_SUMMARY.md)
- [配置示例](config/config.yaml.oss.example)
