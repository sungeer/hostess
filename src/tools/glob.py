import re
import glob as _glob
from pathlib import Path

from pydantic import BaseModel, Field
from langchain_core.tools import tool


class GlobInput(BaseModel):
    """tool_glob 工具参数"""
    pattern: str = Field(description='glob 模式，例如 **/*.py，支持 ** 递归')
    path: str = Field(default='.', description='搜索目录，默认当前目录')


@tool(args_schema=GlobInput)
def tool_glob(pattern: str, path: str = '.') -> str:
    """按 glob 模式匹配文件列表，支持 ** 递归，按修改时间倒序排列。"""
    root = Path(path).expanduser().resolve()
    if not root.exists():
        return f'错误：路径不存在 — {root}'
    if not root.is_dir():
        return f'错误：路径不是目录 — {root}'

    try:
        matches = list(_glob.glob(pattern, root_dir=root, recursive=True))
    except (OSError, re.error) as e:
        return f'glob 错误：{e}'

    if not matches:
        return '(无匹配文件)'

    def mtime(f):
        return (root / f).stat().st_mtime

    matches.sort(key=mtime, reverse=True)
    return '\n'.join(matches[:200])
