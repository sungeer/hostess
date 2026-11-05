from pydantic import BaseModel, Field
from langchain_core.tools import tool

from src import settings


class EditBlock(BaseModel):
    """单处替换"""
    oldText: str = Field(description='原文片段，必须与文件中内容完全一致，且在文件中唯一')
    newText: str = Field(description='替换后的文本')


class EditInput(BaseModel):
    """tool_edit 工具参数"""
    path: str = Field(description='文件路径')
    edits: list[EditBlock] = Field(
        description='一处或多处替换。所有 oldText 都对原始文件匹配，不按顺序累加，彼此不能重叠'
    )


def _to_lf(text: str) -> str:
    return text.replace('\r\n', '\n').replace('\r', '\n')


@tool(args_schema=EditInput)
def tool_edit(path: str, edits: list[EditBlock]) -> str:
    """按精确文本替换修改文件，
    一次调用可以包含多处互不重叠的替换。
    每处 oldText 都对原始内容匹配且必须唯一。
    """
    p = settings.resolve_path(path)
    if not p.exists():
        return f'错误：文件不存在 — {p}'
    if p.is_dir():
        return f'错误：路径是目录不是文件 — {p}'
    if not edits:
        return '错误：edits 不能为空，至少需要一处替换'

    try:
        with open(p, encoding='utf-8', newline='') as f:
            raw = f.read()
    except UnicodeDecodeError:
        return f'错误：文件不是 UTF-8 编码 — {p}'

    bom = raw.startswith('\ufeff')
    if bom:
        raw = raw[1:]
    crlf = '\r\n' in raw
    content = _to_lf(raw)

    matched: list[tuple[int, int, str, int]] = []
    for i, block in enumerate(edits):
        old = _to_lf(block.oldText)
        new = _to_lf(block.newText)
        if not old:
            return f'错误：edits[{i}].oldText 不能为空'
        count = content.count(old)
        if count == 0:
            return f'错误：{p} 中找不到 edits[{i}] 的 oldText，必须与文件内容完全一致（含空白和换行）'
        if count > 1:
            return f'错误：edits[{i}] 的 oldText 在 {p} 中出现 {count} 次，必须唯一，请补上更多上下文'
        matched.append((content.index(old), len(old), new, i))

    matched.sort()
    for (start, length, _new, i), (next_start, _l, _n, next_i) in zip(matched, matched[1:]):
        if start + length > next_start:
            return (
                f'错误：edits[{i}] 和 edits[{next_i}] 在 {p} 中重叠，'
                '请合并成一处，或改成互不重叠的区域'
            )

    new_content = content
    for start, length, new, _i in reversed(matched):
        new_content = new_content[:start] + new + new_content[start + length:]

    if new_content == content:
        return f'错误：替换后内容没有变化 — {p}'

    if crlf:
        new_content = new_content.replace('\n', '\r\n')

    try:
        with open(p, 'w', encoding='utf-8', newline='') as f:
            f.write(('\ufeff' if bom else '') + new_content)
    except OSError as e:
        return f'写入失败：{e}'

    first_line = content.count('\n', 0, matched[0][0]) + 1
    return f'已替换 {len(matched)} 处 — {p}（首处改动在第 {first_line} 行）'
