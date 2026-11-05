from pydantic import BaseModel, Field
from langchain_core.tools import tool

from src import settings


class WriteInput(BaseModel):
    """tool_write 工具参数"""
    file_path: str = Field(description='新文件路径，不能与已存在的文件重复')
    content: str = Field(description='文件的完整内容')


@tool(args_schema=WriteInput)
def tool_write(file_path: str, content: str) -> str:
    """新建文件，写入完整内容。
    只用于创建新文件，已存在的文件一律拒绝覆盖。
    自动创建父目录。
    """
    p = settings.resolve_path(file_path)
    if p.exists():
        return f'错误：文件已存在，禁止覆盖 — {p}，请换一个新文件名'

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return f'已写入 {len(content):,} 字节到 {p}'
    except OSError as e:
        return f'写入失败：{e}'
