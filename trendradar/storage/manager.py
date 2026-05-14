# coding=utf-8
"""
存储管理器 - 统一管理存储后端

根据环境和配置自动选择合适的存储后端
"""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from trendradar.storage.base import StorageBackend, NewsData, RSSData
from trendradar.utils.time import DEFAULT_TIMEZONE


# 存储管理器单例
_storage_manager: Optional["StorageManager"] = None


class StorageManager:
    """
    存储管理器

    功能：
    - 自动检测运行环境（GitHub Actions / Docker / 本地）
    - 根据配置选择存储后端（local / remote / auto）
    - 提供统一的存储接口
    - 支持从远程拉取数据到本地
    """

    def __init__(
        self,
        backend_type: str = "auto",
        data_dir: str = "output",
        enable_txt: bool = True,
        enable_html: bool = True,
        remote_config: Optional[dict] = None,
        local_retention_days: int = 0,
        remote_retention_days: int = 0,
        pull_enabled: bool = False,
        pull_days: int = 0,
        timezone: str = DEFAULT_TIMEZONE,
    ):
        """
        初始化存储管理器

        Args:
            backend_type: 存储后端类型 (local / remote / auto)
            data_dir: 本地数据目录
            enable_txt: 是否启用 TXT 快照
            enable_html: 是否启用 HTML 报告
            remote_config: 远程存储配置（endpoint_url, bucket_name, access_key_id 等）
            local_retention_days: 本地数据保留天数（0 = 无限制）
            remote_retention_days: 远程数据保留天数（0 = 无限制）
            pull_enabled: 是否启用启动时自动拉取
            pull_days: 拉取最近 N 天的数据
            timezone: 时区配置
        """
        self.backend_type = backend_type
        self.data_dir = data_dir
        self.enable_txt = enable_txt
        self.enable_html = enable_html
        self.remote_config = remote_config or {}
        self.local_retention_days = local_retention_days
        self.remote_retention_days = remote_retention_days
        self.pull_enabled = pull_enabled
        self.pull_days = pull_days
        self.timezone = timezone

        self._backend: Optional[StorageBackend] = None
        self._remote_backend: Optional[StorageBackend] = None

    @staticmethod
    def is_github_actions() -> bool:
        """检测是否在 GitHub Actions 环境中运行"""
        return os.environ.get("GITHUB_ACTIONS") == "true"

    @staticmethod
    def is_docker() -> bool:
        """检测是否在 Docker 容器中运行"""
        # 方法1: 检查 /.dockerenv 文件
        if os.path.exists("/.dockerenv"):
            return True

        # 方法2: 检查 cgroup（Linux）
        try:
            with open("/proc/1/cgroup", "r") as f:
                return "docker" in f.read()
        except (FileNotFoundError, PermissionError):
            pass

        # 方法3: 检查环境变量
        return os.environ.get("DOCKER_CONTAINER") == "true"

    def _resolve_backend_type(self) -> str:
        """解析实际使用的后端类型"""
        if self.backend_type == "auto":
            if self.is_github_actions():
                # GitHub Actions 环境，检查是否配置了远程存储
                if self._has_remote_config():
                    return "remote"
                else:
                    print("[存储管理器] GitHub Actions 环境但未配置远程存储，使用本地存储")
                    return "local"
            else:
                return "local"
        return self.backend_type

    def _has_remote_config(self) -> bool:
        """检查是否有有效的远程存储配置"""
        # 检查配置或环境变量
        bucket_name = self.remote_config.get("bucket_name") or os.environ.get("S3_BUCKET_NAME")
        access_key = self.remote_config.get("access_key_id") or os.environ.get("S3_ACCESS_KEY_ID")
        secret_key = self.remote_config.get("secret_access_key") or os.environ.get("S3_SECRET_ACCESS_KEY")
        endpoint = self.remote_config.get("endpoint_url") or os.environ.get("S3_ENDPOINT_URL")

        # 调试日志
        has_config = bool(bucket_name and access_key and secret_key and endpoint)
        if not has_config:
            print(f"[存储管理器] 远程存储配置检查失败:")
            print(f"  - bucket_name: {'已配置' if bucket_name else '未配置'}")
            print(f"  - access_key_id: {'已配置' if access_key else '未配置'}")
            print(f"  - secret_access_key: {'已配置' if secret_key else '未配置'}")
            print(f"  - endpoint_url: {'已配置' if endpoint else '未配置'}")

        return has_config

    def _create_remote_backend(self) -> Optional[StorageBackend]:
        """创建远程存储后端"""
        try:
            from trendradar.storage.remote import RemoteStorageBackend

            return RemoteStorageBackend(
                bucket_name=self.remote_config.get("bucket_name") or os.environ.get("S3_BUCKET_NAME", ""),
                access_key_id=self.remote_config.get("access_key_id") or os.environ.get("S3_ACCESS_KEY_ID", ""),
                secret_access_key=self.remote_config.get("secret_access_key") or os.environ.get("S3_SECRET_ACCESS_KEY", ""),
                endpoint_url=self.remote_config.get("endpoint_url") or os.environ.get("S3_ENDPOINT_URL", ""),
                region=self.remote_config.get("region") or os.environ.get("S3_REGION", ""),
                enable_txt=self.enable_txt,
                enable_html=self.enable_html,
                timezone=self.timezone,
            )
        except ImportError as e:
            print(f"[存储管理器] 远程后端导入失败: {e}")
            print("[存储管理器] 请确保已安装 boto3: pip install boto3")
            return None
        except Exception as e:
            print(f"[存储管理器] 远程后端初始化失败: {e}")
            return None

    def get_backend(self) -> StorageBackend:
        """获取存储后端实例"""
        if self._backend is None:
            resolved_type = self._resolve_backend_type()

            if resolved_type == "remote":
                self._backend = self._create_remote_backend()
                if self._backend:
                    print(f"[存储管理器] 使用远程存储后端")
                else:
                    print("[存储管理器] 回退到本地存储")
                    resolved_type = "local"

            if resolved_type == "local" or self._backend is None:
                from trendradar.storage.local import LocalStorageBackend

                self._backend = LocalStorageBackend(
                    data_dir=self.data_dir,
                    enable_txt=self.enable_txt,
                    enable_html=self.enable_html,
                    timezone=self.timezone,
                )
                print(f"[存储管理器] 使用本地存储后端 (数据目录: {self.data_dir})")

        return self._backend

    def pull_from_remote(self) -> int:
        """
        从远程拉取数据到本地

        Returns:
            成功拉取的文件数量
        """
        if not self.pull_enabled or self.pull_days <= 0:
            return 0

        if not self._has_remote_config():
            print("[存储管理器] 未配置远程存储，无法拉取")
            return 0

        # 创建远程后端（如果还没有）
        if self._remote_backend is None:
            self._remote_backend = self._create_remote_backend()

        if self._remote_backend is None:
            print("[存储管理器] 无法创建远程后端，拉取失败")
            return 0

        # 调用拉取方法
        return self._remote_backend.pull_recent_days(self.pull_days, self.data_dir)

    def save_news_data(self, data: NewsData) -> bool:
        """保存新闻数据"""
        return self.get_backend().save_news_data(data)

    def save_rss_data(self, data: RSSData) -> bool:
        """保存 RSS 数据"""
        return self.get_backend().save_rss_data(data)

    def get_rss_data(self, date: Optional[str] = None) -> Optional[RSSData]:
        """获取指定日期的所有 RSS 数据（当日汇总模式）"""
        return self.get_backend().get_rss_data(date)

    def get_latest_rss_data(self, date: Optional[str] = None) -> Optional[RSSData]:
        """获取最新一次抓取的 RSS 数据（当前榜单模式）"""
        return self.get_backend().get_latest_rss_data(date)

    def detect_new_rss_items(self, current_data: RSSData) -> dict:
        """检测新增的 RSS 条目（增量模式）"""
        return self.get_backend().detect_new_rss_items(current_data)

    def get_today_all_data(self, date: Optional[str] = None) -> Optional[NewsData]:
        """获取当天所有数据"""
        return self.get_backend().get_today_all_data(date)

    def get_latest_crawl_data(self, date: Optional[str] = None) -> Optional[NewsData]:
        """获取最新抓取数据"""
        return self.get_backend().get_latest_crawl_data(date)

    def detect_new_titles(self, current_data: NewsData) -> dict:
        """检测新增标题"""
        return self.get_backend().detect_new_titles(current_data)

    def save_txt_snapshot(self, data: NewsData) -> Optional[str]:
        """保存 TXT 快照"""
        return self.get_backend().save_txt_snapshot(data)

    def save_html_report(self, html_content: str, filename: str) -> Optional[str]:
        """保存 HTML 报告"""
        return self.get_backend().save_html_report(html_content, filename)

    def is_first_crawl_today(self, date: Optional[str] = None) -> bool:
        """检查是否是当天第一次抓取"""
        return self.get_backend().is_first_crawl_today(date)

    def cleanup(self) -> None:
        """清理资源"""
        if self._backend:
            self._backend.cleanup()
        if self._remote_backend:
            self._remote_backend.cleanup()

    def cleanup_old_data(self) -> int:
        """
        清理过期数据

        Returns:
            删除的日期目录数量
        """
        total_deleted = 0

        # 清理本地数据
        if self.local_retention_days > 0:
            total_deleted += self.get_backend().cleanup_old_data(self.local_retention_days)

        # 清理远程数据（如果配置了）
        if self.remote_retention_days > 0 and self._has_remote_config():
            if self._remote_backend is None:
                self._remote_backend = self._create_remote_backend()
            if self._remote_backend:
                total_deleted += self._remote_backend.cleanup_old_data(self.remote_retention_days)

        return total_deleted

    @property
    def backend_name(self) -> str:
        """获取当前后端名称"""
        return self.get_backend().backend_name

    @property
    def supports_txt(self) -> bool:
        """是否支持 TXT 快照"""
        return self.get_backend().supports_txt

    def has_period_executed(self, date_str: str, period_key: str, action: str) -> bool:
        """检查指定时间段的某个 action 是否已执行"""
        return self.get_backend().has_period_executed(date_str, period_key, action)

    def record_period_execution(self, date_str: str, period_key: str, action: str) -> bool:
        """记录时间段的 action 执行"""
        return self.get_backend().record_period_execution(date_str, period_key, action)

    # === AI 智能筛选存储操作 ===

    def begin_batch(self):
        """开启批量模式（远程后端延迟上传）"""
        self.get_backend().begin_batch()

    def end_batch(self):
        """结束批量模式（统一上传脏数据库）"""
        self.get_backend().end_batch()

    def get_active_ai_filter_tags(self, date=None, interests_file="ai_interests.txt"):
        """获取指定兴趣文件的 active 标签"""
        return self.get_backend().get_active_ai_filter_tags(date, interests_file)

    def get_latest_prompt_hash(self, date=None, interests_file="ai_interests.txt"):
        """获取指定兴趣文件的最新 prompt_hash"""
        return self.get_backend().get_latest_prompt_hash(date, interests_file)

    def get_latest_ai_filter_tag_version(self, date=None):
        """获取最新标签版本号"""
        return self.get_backend().get_latest_ai_filter_tag_version(date)

    def deprecate_all_ai_filter_tags(self, date=None, interests_file="ai_interests.txt"):
        """废弃指定兴趣文件的 active 标签和分类结果"""
        return self.get_backend().deprecate_all_ai_filter_tags(date, interests_file)

    def save_ai_filter_tags(self, tags, version, prompt_hash, date=None, interests_file="ai_interests.txt"):
        """保存新提取的标签"""
        return self.get_backend().save_ai_filter_tags(tags, version, prompt_hash, date, interests_file)

    def save_ai_filter_results(self, results, date=None):
        """保存分类结果"""
        return self.get_backend().save_ai_filter_results(results, date)

    def get_active_ai_filter_results(self, date=None, interests_file="ai_interests.txt"):
        """获取指定兴趣文件的 active 分类结果"""
        return self.get_backend().get_active_ai_filter_results(date, interests_file)

    def deprecate_specific_ai_filter_tags(self, tag_ids, date=None):
        """废弃指定 ID 的标签及其关联分类结果"""
        return self.get_backend().deprecate_specific_ai_filter_tags(tag_ids, date)

    def update_ai_filter_tags_hash(self, interests_file, new_hash, date=None):
        """更新指定兴趣文件所有 active 标签的 prompt_hash"""
        return self.get_backend().update_ai_filter_tags_hash(interests_file, new_hash, date)

    def update_ai_filter_tag_descriptions(self, tag_updates, date=None, interests_file="ai_interests.txt"):
        """按 tag 名匹配，更新 active 标签的 description"""
        return self.get_backend().update_ai_filter_tag_descriptions(tag_updates, date, interests_file)

    def update_ai_filter_tag_priorities(self, tag_priorities, date=None, interests_file="ai_interests.txt"):
        """按 tag 名匹配，更新 active 标签的 priority"""
        return self.get_backend().update_ai_filter_tag_priorities(tag_priorities, date, interests_file)

    def save_analyzed_news(self, news_ids, source_type, interests_file, prompt_hash, matched_ids, date=None):
        """批量记录已分析的新闻（匹配与不匹配都记录）"""
        return self.get_backend().save_analyzed_news(news_ids, source_type, interests_file, prompt_hash, matched_ids, date)

    def get_analyzed_news_ids(self, source_type="hotlist", date=None, interests_file="ai_interests.txt"):
        """获取已分析过的新闻 ID 集合"""
        return self.get_backend().get_analyzed_news_ids(source_type, date, interests_file)

    def clear_analyzed_news(self, date=None, interests_file="ai_interests.txt"):
        """清除指定兴趣文件的所有已分析记录"""
        return self.get_backend().clear_analyzed_news(date, interests_file)

    def clear_unmatched_analyzed_news(self, date=None, interests_file="ai_interests.txt"):
        """清除不匹配的已分析记录"""
        return self.get_backend().clear_unmatched_analyzed_news(date, interests_file)

    def get_all_news_ids(self, date=None):
        """获取所有新闻 ID 和标题"""
        return self.get_backend().get_all_news_ids(date)

    def get_all_rss_ids(self, date=None):
        """获取所有 RSS ID 和标题"""
        return self.get_backend().get_all_rss_ids(date)

    # === 持久化模块集成方法 ===

    def get_memory_db_path(self) -> str:
        """获取 memory.db 路径"""
        if self.backend_type == 'local' or self._resolve_backend_type() == 'local':
            from trendradar.storage.local import LocalStorageBackend
            backend = self.get_backend()
            if isinstance(backend, LocalStorageBackend):
                output_dir = Path(backend.data_dir)
                # 确保目录存在
                output_dir.mkdir(parents=True, exist_ok=True)
                return str(output_dir / 'memory.db')
        # 远程模式暂不支持 memory.db
        raise NotImplementedError("Memory DB not supported in remote mode yet")

    def ensure_memory_db(self):
        """确保 memory.db 存在并返回连接"""
        import sqlite3
        from trendradar.persistence.schema import initialize_memory_db

        memory_db_path = self.get_memory_db_path()

        # 如果文件不存在，initialize_memory_db 会创建并初始化
        conn = initialize_memory_db(memory_db_path)

        return conn

    def get_today_db_connection(self):
        """获取今天的数据库连接"""
        import sqlite3
        from trendradar.storage.local import LocalStorageBackend

        if self.backend_type == 'local' or self._resolve_backend_type() == 'local':
            backend = self.get_backend()
            if isinstance(backend, LocalStorageBackend):
                from datetime import datetime
                today = datetime.now(backend._get_configured_time().tzinfo or __import__('pytz').timezone(DEFAULT_TIMEZONE)).strftime('%Y-%m-%d')
                db_path = backend._get_db_path(today)

                # 检查数据库是否存在，如果不存在需要先创建基础表
                db_exists = db_path.exists()

                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row

                # 如果是新数据库，先创建基础表
                if not db_exists:
                    from trendradar.storage.sqlite_mixin import SQLiteStorageMixin
                    # 创建基础的新闻表
                    conn.execute('''
                        CREATE TABLE IF NOT EXISTS news_items (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            source_id TEXT NOT NULL,
                            title TEXT NOT NULL,
                            url TEXT,
                            rank INTEGER,
                            heat_value TEXT,
                            timestamp TEXT NOT NULL
                        )
                    ''')
                    conn.commit()

                # 确保有 AI 分析表
                from trendradar.persistence.schema import (
                    initialize_ai_analysis_tables,
                    ensure_matched_keywords_column
                )
                initialize_ai_analysis_tables(conn)
                ensure_matched_keywords_column(conn)

                return conn
        raise NotImplementedError("Only local backend supported for now")

    # === OSS 数据库同步功能 ===

    def sync_databases_to_s3(self) -> int:
        """
        上传本地数据库到 OSS

        上传所有日期数据库和 memory.db 到远程存储

        Returns:
            成功上传的文件数量
        """
        # 检查是否配置了远程存储
        if not self._has_remote_config():
            print("[数据库同步] 未配置远程存储，跳过上传")
            return 0

        try:
            import boto3
            from botocore.config import Config as BotoConfig
            from botocore.exceptions import ClientError
        except ImportError:
            print("[数据库同步] 未安装 boto3，跳过上传")
            print("[数据库同步] 安装方法: pip install boto3")
            return 0

        print("[数据库同步] 开始上传数据库到 OSS...")

        # 创建 S3 客户端
        try:
            bucket_name = self.remote_config.get("bucket_name") or os.environ.get("S3_BUCKET_NAME")
            access_key = self.remote_config.get("access_key_id") or os.environ.get("S3_ACCESS_KEY_ID")
            secret_key = self.remote_config.get("secret_access_key") or os.environ.get("S3_SECRET_ACCESS_KEY")
            endpoint = self.remote_config.get("endpoint_url") or os.environ.get("S3_ENDPOINT_URL")
            region = self.remote_config.get("region") or os.environ.get("S3_REGION", "")

            # 根据服务商选择签名版本
            use_sigv2 = "aliyuncs.com" in endpoint.lower()
            signature_version = 's3' if use_sigv2 else 's3v4'

            s3_config = BotoConfig(
                s3={"addressing_style": "virtual"},
                signature_version=signature_version,
            )

            client_kwargs = {
                "endpoint_url": endpoint,
                "aws_access_key_id": access_key,
                "aws_secret_access_key": secret_key,
                "config": s3_config,
            }
            if region:
                client_kwargs["region_name"] = region

            s3_client = boto3.client("s3", **client_kwargs)

        except Exception as e:
            print(f"[数据库同步] 初始化 S3 客户端失败: {e}")
            return 0

        uploaded_count = 0
        data_dir = Path(self.data_dir)

        # 1. 上传日期数据库文件
        news_dir = data_dir / "news"
        if news_dir.exists():
            db_files = sorted(news_dir.glob("*.db"))
            print(f"[数据库同步] 找到 {len(db_files)} 个日期数据库")

            for db_file in db_files:
                try:
                    # 远程路径: databases/news/YYYY-MM-DD.db
                    remote_key = f"databases/news/{db_file.name}"
                    local_size = db_file.stat().st_size

                    # 检查远程文件是否存在且大小相同（增量同步）
                    skip_upload = False
                    try:
                        remote_obj = s3_client.head_object(Bucket=bucket_name, Key=remote_key)
                        remote_size = remote_obj['ContentLength']

                        if remote_size == local_size:
                            print(f"[数据库同步] 跳过: {db_file.name} (已存在，大小相同)")
                            skip_upload = True
                        else:
                            print(f"[数据库同步] 更新: {db_file.name} ({local_size / 1024:.1f} KB, 远程: {remote_size / 1024:.1f} KB)")
                    except ClientError as e:
                        if e.response['Error']['Code'] == '404':
                            print(f"[数据库同步] 上传: {db_file.name} ({local_size / 1024:.1f} KB)")
                        else:
                            raise

                    if skip_upload:
                        continue

                    # 读取文件内容并上传
                    with open(db_file, 'rb') as f:
                        file_content = f.read()

                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=remote_key,
                        Body=file_content,
                        ContentLength=local_size,
                        ContentType='application/x-sqlite3',
                    )

                    uploaded_count += 1
                    print(f"[数据库同步] 上传成功: {remote_key}")

                except Exception as e:
                    print(f"[数据库同步] 上传失败 ({db_file.name}): {e}")

        # 2. 上传 memory.db
        memory_db = data_dir / "memory.db"
        if memory_db.exists():
            try:
                remote_key = "databases/memory.db"
                local_size = memory_db.stat().st_size

                # 检查远程文件是否存在且需要更新（增量同步）
                skip_upload = False
                try:
                    remote_obj = s3_client.head_object(Bucket=bucket_name, Key=remote_key)
                    remote_size = remote_obj['ContentLength']
                    remote_modified = remote_obj['LastModified']
                    local_modified = datetime.fromtimestamp(memory_db.stat().st_mtime)

                    # 本地文件更新 且 大小不同 -> 需要上传
                    # 只检查大小可能导致内容变化但大小不变的情况被跳过
                    if local_modified <= remote_modified and remote_size == local_size:
                        print(f"[数据库同步] 跳过: memory.db (远程已是最新)")
                        skip_upload = True
                    else:
                        print(f"[数据库同步] 更新: memory.db ({local_size / 1024:.1f} KB, 本地修改: {local_modified.strftime('%Y-%m-%d %H:%M:%S')})")
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        print(f"[数据库同步] 上传: memory.db ({local_size / 1024:.1f} KB)")
                    else:
                        raise

                if not skip_upload:
                    with open(memory_db, 'rb') as f:
                        file_content = f.read()

                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=remote_key,
                        Body=file_content,
                        ContentLength=local_size,
                        ContentType='application/x-sqlite3',
                    )

                    uploaded_count += 1
                    print(f"[数据库同步] 上传成功: {remote_key}")

            except Exception as e:
                print(f"[数据库同步] 上传失败 (memory.db): {e}")

        print(f"[数据库同步] 上传完成，共上传 {uploaded_count} 个文件")
        return uploaded_count

    def sync_databases_from_s3(self) -> int:
        """
        从 OSS 下载数据库到本地

        下载所有数据库文件，自动创建本地目录
        如果远程没有数据库，静默跳过（第一次运行）

        Returns:
            成功下载的文件数量
        """
        # 检查是否配置了远程存储
        if not self._has_remote_config():
            print("[数据库同步] 未配置远程存储，跳过下载")
            return 0

        try:
            import boto3
            from botocore.config import Config as BotoConfig
            from botocore.exceptions import ClientError
        except ImportError:
            print("[数据库同步] 未安装 boto3，跳过下载")
            return 0

        print("[数据库同步] 开始从 OSS 下载数据库...")

        # 创建 S3 客户端
        try:
            bucket_name = self.remote_config.get("bucket_name") or os.environ.get("S3_BUCKET_NAME")
            access_key = self.remote_config.get("access_key_id") or os.environ.get("S3_ACCESS_KEY_ID")
            secret_key = self.remote_config.get("secret_access_key") or os.environ.get("S3_SECRET_ACCESS_KEY")
            endpoint = self.remote_config.get("endpoint_url") or os.environ.get("S3_ENDPOINT_URL")
            region = self.remote_config.get("region") or os.environ.get("S3_REGION", "")

            # 根据服务商选择签名版本
            use_sigv2 = "aliyuncs.com" in endpoint.lower()
            signature_version = 's3' if use_sigv2 else 's3v4'

            s3_config = BotoConfig(
                s3={"addressing_style": "virtual"},
                signature_version=signature_version,
            )

            client_kwargs = {
                "endpoint_url": endpoint,
                "aws_access_key_id": access_key,
                "aws_secret_access_key": secret_key,
                "config": s3_config,
            }
            if region:
                client_kwargs["region_name"] = region

            s3_client = boto3.client("s3", **client_kwargs)

        except Exception as e:
            print(f"[数据库同步] 初始化 S3 客户端失败: {e}")
            return 0

        downloaded_count = 0
        data_dir = Path(self.data_dir)

        try:
            # 列出 databases/ 前缀下的所有对象
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix="databases/"
            )

            if 'Contents' not in response:
                print("[数据库同步] 远程没有数据库文件（首次运行），跳过下载")
                return 0

            objects = response['Contents']
            print(f"[数据库同步] 找到 {len(objects)} 个远程数据库文件")

            for obj in objects:
                key = obj['Key']
                size = obj['Size']

                # 跳过目录对象
                if key.endswith('/'):
                    continue

                try:
                    # 解析本地路径
                    # databases/news/2025-12-21.db -> output/news/2025-12-21.db
                    # databases/memory.db -> output/memory.db
                    relative_path = key.replace('databases/', '', 1)
                    local_path = data_dir / relative_path

                    # 创建目录
                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    print(f"[数据库同步] 下载: {key} ({size / 1024:.1f} KB)")

                    # 使用 get_object 下载
                    response = s3_client.get_object(Bucket=bucket_name, Key=key)
                    with open(local_path, 'wb') as f:
                        for chunk in response['Body'].iter_chunks(chunk_size=1024*1024):
                            f.write(chunk)

                    downloaded_count += 1
                    print(f"[数据库同步] 下载成功: {local_path}")

                except Exception as e:
                    print(f"[数据库同步] 下载失败 ({key}): {e}")

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                print(f"[数据库同步] 存储桶不存在: {bucket_name}")
            elif error_code == "AccessDenied":
                print(f"[数据库同步] 访问被拒绝，请检查密钥权限")
            else:
                print(f"[数据库同步] 下载失败: {e}")
        except Exception as e:
            print(f"[数据库同步] 下载异常: {e}")

        print(f"[数据库同步] 下载完成，共下载 {downloaded_count} 个文件")
        return downloaded_count

    def list_remote_databases(self) -> list:
        """
        列出 OSS 上的所有数据库文件

        Returns:
            文件列表，每项包含 (key, size, last_modified)
        """
        # 检查是否配置了远程存储
        if not self._has_remote_config():
            print("[数据库同步] 未配置远程存储")
            return []

        try:
            import boto3
            from botocore.config import Config as BotoConfig
            from botocore.exceptions import ClientError
        except ImportError:
            print("[数据库同步] 未安装 boto3")
            return []

        try:
            bucket_name = self.remote_config.get("bucket_name") or os.environ.get("S3_BUCKET_NAME")
            access_key = self.remote_config.get("access_key_id") or os.environ.get("S3_ACCESS_KEY_ID")
            secret_key = self.remote_config.get("secret_access_key") or os.environ.get("S3_SECRET_ACCESS_KEY")
            endpoint = self.remote_config.get("endpoint_url") or os.environ.get("S3_ENDPOINT_URL")
            region = self.remote_config.get("region") or os.environ.get("S3_REGION", "")

            # 根据服务商选择签名版本
            use_sigv2 = "aliyuncs.com" in endpoint.lower()
            signature_version = 's3' if use_sigv2 else 's3v4'

            s3_config = BotoConfig(
                s3={"addressing_style": "virtual"},
                signature_version=signature_version,
            )

            client_kwargs = {
                "endpoint_url": endpoint,
                "aws_access_key_id": access_key,
                "aws_secret_access_key": secret_key,
                "config": s3_config,
            }
            if region:
                client_kwargs["region_name"] = region

            s3_client = boto3.client("s3", **client_kwargs)

            # 列出所有数据库文件
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix="databases/"
            )

            if 'Contents' not in response:
                print("[数据库同步] 远程没有数据库文件")
                return []

            databases = []
            for obj in response['Contents']:
                key = obj['Key']
                # 跳过目录对象
                if key.endswith('/'):
                    continue
                databases.append({
                    'key': key,
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })

            print(f"[数据库同步] 找到 {len(databases)} 个数据库文件:")
            for db in databases:
                print(f"  - {db['key']} ({db['size'] / 1024:.1f} KB, {db['last_modified']})")

            return databases

        except Exception as e:
            print(f"[数据库同步] 列出数据库失败: {e}")
            return []



def get_storage_manager(
    backend_type: str = "auto",
    data_dir: str = "output",
    enable_txt: bool = True,
    enable_html: bool = True,
    remote_config: Optional[dict] = None,
    local_retention_days: int = 0,
    remote_retention_days: int = 0,
    pull_enabled: bool = False,
    pull_days: int = 0,
    timezone: str = DEFAULT_TIMEZONE,
    force_new: bool = False,
) -> StorageManager:
    """
    获取存储管理器单例

    Args:
        backend_type: 存储后端类型
        data_dir: 本地数据目录
        enable_txt: 是否启用 TXT 快照
        enable_html: 是否启用 HTML 报告
        remote_config: 远程存储配置
        local_retention_days: 本地数据保留天数（0 = 无限制）
        remote_retention_days: 远程数据保留天数（0 = 无限制）
        pull_enabled: 是否启用启动时自动拉取
        pull_days: 拉取最近 N 天的数据
        timezone: 时区配置
        force_new: 是否强制创建新实例

    Returns:
        StorageManager 实例
    """
    global _storage_manager

    if _storage_manager is None or force_new:
        _storage_manager = StorageManager(
            backend_type=backend_type,
            data_dir=data_dir,
            enable_txt=enable_txt,
            enable_html=enable_html,
            remote_config=remote_config,
            local_retention_days=local_retention_days,
            remote_retention_days=remote_retention_days,
            pull_enabled=pull_enabled,
            pull_days=pull_days,
            timezone=timezone,
        )

    return _storage_manager
