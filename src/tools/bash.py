import subprocess

from pydantic import BaseModel, Field
from langchain_core.tools import tool

from src import settings

MAX_OUTPUT_CHARS = 20000
DEFAULT_TIMEOUT = 30


class BashInput(BaseModel):
    """tool_bash 工具参数"""
    command: str = Field(description='要执行的 bash 命令')
    timeout: int = Field(default=DEFAULT_TIMEOUT, description='超时秒数，默认 30')


@tool(args_schema=BashInput)
def tool_bash(command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """在 Git Bash 中执行命令，工作目录是项目根目录。
    返回标准输出、标准错误和退出码，输出过长会截断。
    """
    exe = settings.BASH_PATH
    if not exe:
        return '错误：未找到 bash，请把环境变量 BASH_PATH 设为 Git Bash 的 bash.exe 路径'
    if 'system32' in exe.lower():
        return f'错误：解析到的是 WSL 的 bash（{exe}），请把 BASH_PATH 设为 Git Bash 的 bash.exe'

    if timeout <= 0:
        return f'错误：timeout 必须大于 0 — timeout={timeout}'

    try:
        proc = subprocess.run(
            [exe, '-c', command],
            cwd=settings.WORKSPACE,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f'错误：命令超时（{timeout} 秒）— {command}'
    except OSError as e:
        return f'错误：无法启动 bash（{exe}）— {e}'

    out = (proc.stdout + proc.stderr).decode('utf-8', errors='replace').strip()
    if not out:
        return f'退出码 {proc.returncode}（无输出）'
    if len(out) > MAX_OUTPUT_CHARS:
        out = out[:MAX_OUTPUT_CHARS] + f'\n...（输出已截断，共 {len(out):,} 字符）'
    return f'{out}\n[退出码 {proc.returncode}]'
