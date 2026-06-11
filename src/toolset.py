import os
import re
import subprocess
import glob as _glob
from pathlib import Path

from pydantic import BaseModel, Field
from langchain_core.tools import tool


class ReadInput(BaseModel):
    """read 工具参数"""
    file_path: str = Field(description='文件路径')
    offset: int = Field(default=0, description='起始行号，从1开始，0表示从头读取')
    limit: int = Field(default=0, description='最大行数，0表示读取全部')


@tool(args_schema=ReadInput)
def read(file_path: str, offset: int = 0, limit: int = 0) -> str:
    """读取文件内容，带行号。offset 和 limit 从 1 开始计数。"""
    p = Path(file_path).expanduser().resolve()
    if not p.exists():
        return f'错误：文件不存在 — {p}'
    if p.is_dir():
        return f'错误：路径是目录不是文件 — {p}'

    # 大文件提醒
    size = p.stat().st_size
    if size > 1_000_000:
        hint = f'注意：文件较大（{size:,} 字节），建议用 offset/limit 分页读取。\n'
    else:
        hint = ''

    try:
        text = p.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            text = p.read_text(encoding='latin-1')
            hint += '（已用 latin-1 编码读取）\n'
        except Exception:
            return '错误：无法读取该文件（可能为二进制文件）'

    lines = text.splitlines()
    total = len(lines)

    # 确定读取范围
    start = max(0, offset - 1) if offset > 0 else 0
    if limit > 0:
        end = min(start + limit, total)
    else:
        end = total

    # 格式化输出
    out_lines = []
    for i in range(start, end):
        out_lines.append(f'{i + 1:>6}\t{lines[i]}')

    result = '\n'.join(out_lines)
    header = f'{p}  (行 {start + 1}-{end} / 共 {total} 行)\n'
    return hint + header + result


class WriteInput(BaseModel):
    """write 工具参数"""
    file_path: str = Field(description='文件路径')
    content: str = Field(description='文件的完整内容')


@tool(args_schema=WriteInput)
def write(file_path: str, content: str) -> str:
    """写入文件，自动创建父目录。"""
    p = Path(file_path).expanduser().resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return f'已写入 {len(content):,} 字节到 {p}'
    except OSError as e:
        return f'写入失败：{e}'


class GlobInput(BaseModel):
    """glob 工具参数"""
    pattern: str = Field(description='glob 模式，例如 **/*.py，支持 ** 递归')
    path: str = Field(default='.', description='搜索目录，默认当前目录')


@tool(args_schema=GlobInput)
def glob(pattern: str, path: str = '.') -> str:
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


class GrepInput(BaseModel):
    """grep 工具参数"""
    pattern: str = Field(description='搜索关键词或正则，不区分大小写')
    path: str = Field(default='.', description='搜索目录，默认当前目录')
    include: str = Field(default='', description='文件名过滤，例如 .py')


@tool(args_schema=GrepInput)
def grep(pattern: str, path: str = '.', include: str = '') -> str:
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


class BashInput(BaseModel):
    """bash 工具参数"""
    cmd: str = Field(description='要执行的 shell 命令')


@tool(args_schema=BashInput)
def bash(cmd: str) -> str:
    """执行 shell 命令，60 秒超时。"""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=60, encoding='utf-8', errors='replace',
        )
        out = r.stdout.strip()
        err = r.stderr.strip()
        parts = [out] if out else []
        if err:
            parts.append(f'[stderr]\n{err}')
        return '\n'.join(parts) if parts else '(无输出)'
    except subprocess.TimeoutExpired:
        return '(命令超时，已等待 60 秒)'
    except OSError as e:
        return f'命令执行失败：{e}'


# ── 工具列表 ──────────────────────────────────────────

tools = [read, write, glob, grep, bash]
