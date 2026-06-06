import os
import glob as _glob
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

api_base_url = os.environ.get('API_BASE_URL')
api_key = os.environ.get('API_KEY')
model = os.environ.get('MODEL', 'deepseek-v4-flash')
max_tokens = int(os.environ.get('MAX_TOKENS', '65536'))

system_prompt = (
    '你是一个在命令行工作的 AI 编码助手。\n'
    '\n'
    '## 工作方式\n'
    '1. 先理解用户的需求，不清楚时主动提问\n'
    '2. 用 glob 了解项目文件结构\n'
    '3. 用 grep 搜索关键代码，用 read 阅读相关文件\n'
    '4. 根据需求修改代码（write）或执行命令（bash）\n'
    '\n'
    '## 代码风格\n'
    '- 遵循项目现有的代码风格，不要随意改变\n'
    '- 不引入不必要的抽象，YAGNI\n'
    '- 只在非显而易见的逻辑处写简短注释\n'
    '\n'
    '## 注意事项\n'
    '- 写文件前先读文件，确保理解准确再动笔\n'
    '- 不要无理由地改变与任务无关的代码\n'
    '- shell 命令无沙箱限制，注意安全性\n'
    '\n'
    '## 可用工具\n'
    '1. read — 读取文件内容，带行号\n'
    '   参数：file_path(必填), offset(可选，起始行号), limit(可选，最大行数)\n'
    '2. write — 写入文件，自动创建父目录\n'
    '   参数：file_path(必填), content(必填，完整内容)\n'
    '3. glob — 按 glob 模式匹配文件列表，支持 ** 递归\n'
    '   参数：pattern(必填), path(可选，默认当前目录)\n'
    '4. grep — 搜索文件内容，不区分大小写，最多返回 100 条\n'
    '   参数：pattern(必填), path(可选), include(可选，文件名过滤)\n'
    '5. bash — 执行 shell 命令，60 秒超时\n'
    '   参数：cmd(必填)\n'
    '\n'
    '## 输出格式（必须严格遵守）\n'
    '你每次只能输出一个 JSON 对象，格式如下：\n'
    '- 需要调工具时：{"action": "tool", "tool": "工具名", "args": {"参数": "值"}}\n'
    '- 直接回复用户时：{"action": "text", "content": "回复内容"}\n'
    '注意：一次只能调用一个工具，不要同时调用多个。'
)


def tool_read(file_path: str, offset: int = 0, limit: int = 0) -> str:
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
        except (Exception,):
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


def tool_write(file_path: str, content: str) -> str:
    """写入文件，自动创建父目录。"""
    p = Path(file_path).expanduser().resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return f'已写入 {len(content):,} 字节到 {p}'
    except OSError as e:
        return f'写入失败：{e}'


def tool_glob(pattern: str, path: str = '.') -> str:
    """匹配文件列表，按修改时间倒序排列。"""
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

    # 按修改时间降序
    def mtime(f):
        return (root / f).stat().st_mtime

    matches.sort(key=mtime, reverse=True)
    return '\n'.join(matches[:200])  # 最多 200 条


def tool_grep(pattern: str, path: str = '.', include: str = '') -> str:
    """纯 Python 递归搜索文件内容，不依赖外部 grep 命令。"""
    root = Path(path).expanduser().resolve()
    if not root.exists():
        return f'错误：路径不存在 — {root}'

    results = []
    pattern_lower = pattern.lower()

    for dirpath_str, _dirnames, filenames in os.walk(root):
        # 跳过常见的无关目录
        _dirnames[:] = [
            d for d in _dirnames
            if not d.startswith('.') and d not in ('__pycache__', 'node_modules', '.git')
        ]
        for fn in filenames:
            if include:
                # 简单的 glob 匹配
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


def tool_bash(cmd: str) -> str:
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


# LLM 结构化输出模型（替代原生 function calling）
class AgentAction(BaseModel):
    action: Literal['text', 'tool', 'bash', 'file_path']
    content: str | None = None      # action=text 时的回复内容
    tool: str | None = None          # action=tool 时的工具名
    args: dict | None = None         # action=tool 时的工具参数


# 工具注册表
tool_map = {
    'read': tool_read,
    'write': tool_write,
    'glob': tool_glob,
    'grep': tool_grep,
    'bash': tool_bash,
}


def _short(args: dict) -> str:
    """给终端显示的参数摘要"""
    items = []
    for k, v in args.items():
        s = str(v)
        if len(s) > 60:
            s = s[:57] + '...'
        items.append(f'{k}={s}')
    return ', '.join(items)


def _agent_loop(client: OpenAI, messages: list) -> None:
    """处理 LLM 的工具调用循环，最多 20 轮。"""
    for _round in range(20):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                response_format={'type': 'json_object'},  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=0.1,
            )
        except Exception as e:
            print(f'\n[API 调用失败] {e}')
            break

        raw = resp.choices[0].message.content or ''
        messages.append({'role': 'assistant', 'content': raw})

        # 解析结构化输出
        try:
            action = AgentAction.model_validate_json(raw)
        except Exception as e:
            print(f'\n[结构化输出解析失败] {e}')
            print(f'原始输出: {raw[:500]}')
            break

        if action.action == 'text':
            print(f'\n{action.content}\n')
            break

        # 执行工具
        fn_name = action.tool
        fn_args = action.args or {}
        handler = tool_map.get(fn_name or '')

        print(f'  [{fn_name}({_short(fn_args)})]', end=' ')
        if handler:
            try:
                tool_result = handler(**fn_args)
            except Exception as e:
                tool_result = f'工具执行异常：{e}'
        else:
            tool_result = f'未知工具：{fn_name}'
        print('')

        # 工具结果作为 user 消息返回（无原生 tool 角色）
        messages.append({
            'role': 'user',
            'content': (
                f'工具 [{fn_name}] 执行结果：\n'
                f'{tool_result[:8000]}'
            ),
        })
    else:
        print('(已达到最大工具调用轮数，停止)')


def _print_banner() -> None:
    print('Code CLI (type /help /clear /quit /exit for available commands)')
    print('-----------------------------------------------------------------------------')


def main() -> None:
    _print_banner()

    try:
        client = OpenAI(base_url=api_base_url, api_key=api_key)
    except Exception as e:
        print(f'初始化 OpenAI 客户端失败：{e}')
        return

    messages = [{'role': 'system', 'content': system_prompt}]

    while True:
        try:
            user_input = input('\nYou: ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\n再见。')
            break

        if not user_input:
            continue

        if user_input in ('/exit', '/q', '/quit'):
            print('再见。')
            break

        if user_input == '/c':
            messages = [{'role': 'system', 'content': system_prompt}]
            print('对话已重置。')
            continue

        if user_input == '/help':
            print(
                '命令说明：\n'
                '  /exit, /q, /quit — 退出程序\n'
                '  /c               — 重置对话历史\n'
                '  /help             — 显示此帮助\n'
                '\n'
                '使用方式：直接输入自然语言指令即可，例如：\n'
                '  >>> 帮我看看这个项目的目录结构\n'
                '  >>> 给 src/models.py 里的 User 类加个 phone 字段\n'
                '  >>> 用 pytest 跑一下 tests/ 目录下的测试\n'
            )
            continue

        messages.append({'role': 'user', 'content': user_input})
        _agent_loop(client, messages)


if __name__ == '__main__':
    main()
