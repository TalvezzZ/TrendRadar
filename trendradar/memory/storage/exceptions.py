"""
存储层异常定义
"""


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
