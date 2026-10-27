from pathlib import Path

from pydantic import BaseModel, Field
from langchain_core.tools import tool


class WriteInput(BaseModel):
    """write 工具参数"""
    file_path: str = Field(description='文件路径')
    content: str = Field(description='文件的完整内容')


@tool(args_schema=WriteInput)
def tool_write(file_path: str, content: str) -> str:
    """写入文件，自动创建父目录。"""
    p = Path(file_path).expanduser().resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return f'已写入 {len(content):,} 字节到 {p}'
    except OSError as e:
        return f'写入失败：{e}'
