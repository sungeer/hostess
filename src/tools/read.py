from pydantic import BaseModel, Field
from langchain_core.tools import tool

from src import settings
from src.core.errors import ToolAbort

MAX_LINE_CHARS = 2000


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
    p = settings.resolve_path(file_path)
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

    lines = text.splitlines()  # list
    total = len(lines)

    for i, line in enumerate(lines):
        if len(line) > MAX_LINE_CHARS:
            raise ToolAbort(
                f'文件含超长单行，禁止读取 — {p} 第 {i + 1} 行 {len(line)} 字符'
                f'（上限 {MAX_LINE_CHARS}），请改用 bash 工具 grep -n 定位内容'
            )

    if limit < 0:
        return f'错误：limit 不能为负数 — limit={limit}'
    if offset > total:
        return f'错误：offset 超出文件范围 — offset={offset}，共 {total} 行'

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
