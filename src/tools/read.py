from pathlib import Path

from pydantic import BaseModel, Field
from langchain_core.tools import tool


class ReadInput(BaseModel):
    """tool_read 工具参数"""
    file_path: str = Field(description='文件路径')
    offset: int = Field(default=0, description='起始行号，从1开始，0表示从头读取')
    limit: int = Field(default=0, description='最大行数，0表示读取全部')


@tool(args_schema=ReadInput)
def tool_read(file_path: str, offset: int = 0, limit: int = 0) -> str:
    """读取文件内容，带行号。
    支持文本文件。
    offset 和 limit 分页读取大文件。
    """
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
