import os
from pathlib import Path

from pydantic import BaseModel, Field
from langchain_core.tools import tool


class GrepInput(BaseModel):
    """grep 工具参数"""
    pattern: str = Field(description='搜索关键词或正则，不区分大小写')
    path: str = Field(default='.', description='搜索目录，默认当前目录')
    include: str = Field(default='', description='文件名过滤，例如 .py')


@tool(args_schema=GrepInput)
def tool_grep(pattern: str, path: str = '.', include: str = '') -> str:
    """纯 Python 递归搜索文件内容，不区分大小写，最多返回 100 条。"""
    root = Path(path).expanduser().resolve()
    if not root.exists():
        return f'错误：路径不存在 — {root}'

    results: list[str] = []
    pattern_lower = pattern.lower()

    for dirpath_str, _dirnames, filenames in os.walk(root):
        _dirnames[:] = [
            d for d in _dirnames
            if not d.startswith('.') and d not in ('__pycache__', 'node_modules', '.git')
        ]
        for fn in filenames:
            if include:
                if not fn.endswith(include.lstrip('*')):
                    continue
            fpath = os.path.join(dirpath_str, fn)
            try:
                with open(fpath, encoding='utf-8', errors='replace') as f:
                    for lineno, line in enumerate(f, 1):
                        if pattern_lower in line.lower():
                            results.append(f'{fpath}:{lineno}: {line.rstrip()[:200]}')
                            if len(results) >= 100:
                                return '\n'.join(results) + '\n...（结果已截断，请缩小搜索范围）'
            except OSError:
                continue

    return '\n'.join(results) if results else '(无匹配)'
