import os
import glob as _glob
import json
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

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
    '- shell 命令无沙箱限制，注意安全性'
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


tools_schema = [
    {
        'type': 'function',
        'function': {
            'name': 'read',
            'description': (
                '读取文件内容，带行号。'
                'offset 和 limit 都从 1 开始计数。'
                '读取大文件时务必用 offset/limit 分页。'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'file_path': {
                        'type': 'string',
                        'description': '文件路径（绝对或相对）',
                    },
                    'offset': {
                        'type': 'integer',
                        'description': '起始行号（从1开始），不传则从第1行开始',
                    },
                    'limit': {
                        'type': 'integer',
                        'description': '最多读取的行数，不传则读到文件末尾',
                    },
                },
                'required': ['file_path'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'write',
            'description': '将内容写入文件。会自动创建父目录。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'file_path': {
                        'type': 'string',
                        'description': '目标文件路径',
                    },
                    'content': {
                        'type': 'string',
                        'description': '要写入的完整内容',
                    },
                },
                'required': ['file_path', 'content'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'glob',
            'description': (
                '按 glob 模式匹配文件列表，按修改时间降序排列。'
                '支持 ** 递归匹配。常用模式：**/*.py、src/**/*.ts'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'pattern': {
                        'type': 'string',
                        'description': 'glob 模式，如 **/*.py',
                    },
                    'path': {
                        'type': 'string',
                        'description': '搜索根目录，默认当前目录',
                    },
                },
                'required': ['pattern'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'grep',
            'description': (
                '在文件中搜索匹配的文本行（不区分大小写），返回 文件:行号:内容。'
                '大量匹配时自动截断到前 100 条。'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'pattern': {
                        'type': 'string',
                        'description': '搜索关键词或正则',
                    },
                    'path': {
                        'type': 'string',
                        'description': '搜索根目录，默认当前目录',
                    },
                    'include': {
                        'type': 'string',
                        'description': '文件名过滤，如 *.py 或 .py',
                    },
                },
                'required': ['pattern'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'bash',
            'description': '执行 shell 命令并返回输出。60 秒超时。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'cmd': {
                        'type': 'string',
                        'description': '要执行的命令',
                    },
                },
                'required': ['cmd'],
            },
        },
    },
]


def _agent_loop(client: OpenAI, messages: list) -> None:
    """处理 LLM 的工具调用循环，最多 20 轮。"""
    for _round in range(20):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                tools=tools_schema,  # type: ignore[arg-type]
                tool_choice='auto',
                max_tokens=max_tokens,
                temperature=0.1,
            )
        except Exception as e:
            print(f'\n[API 调用失败] {e}')
            break

        msg = resp.choices[0].message

        # 打印文本内容
        if msg.content:
            print(f'\n{msg.content}\n')

        # 将 assistant 消息加入历史
        assistant_msg: dict = {'role': 'assistant', 'content': msg.content or None}
        if msg.tool_calls:
            tool_calls = []
            for tc in msg.tool_calls:
                tool_call = {
                    'id': tc.id, 'type': 'function',
                    'function': {
                        'name': tc.function.name,
                        'arguments': tc.function.arguments,
                    }
                }
                tool_calls.append(tool_call)
            assistant_msg['tool_calls'] = tool_calls
        messages.append(assistant_msg)

        # 无工具调用 → 本轮结束
        if not msg.tool_calls:
            break

        # 执行每个工具调用
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            handler = tool_map.get(fn_name)

            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                tool_result = f'参数解析失败：{tc.function.arguments[:200]}'
            else:
                print(f'  [{fn_name}({_short(fn_args)})]', end=' ')
                if handler:
                    try:
                        tool_result = handler(**fn_args)
                    except Exception as e:
                        tool_result = f'工具执行异常：{e}'
                else:
                    tool_result = f'未知工具：{fn_name}'
                print('')

            messages.append({
                'role': 'tool',
                'tool_call_id': tc.id,
                'content': tool_result[:8000],  # 单次工具结果上限
            })
    else:
        print('(已达到最大工具调用轮数，停止)')


def _print_banner() -> None:
    print(f'╔══════════════════════════════════════════════╗')
    print(f'║         hostess — 极简 AI 编码助手           ║')
    print(f'╠══════════════════════════════════════════════╣')
    print(f'║  API: {api_base_url:<38}║')
    print(f'║  模型: {model:<37}║')
    print(f'║  命令: /help /clear /quit /exit             ║')
    print(f'╚══════════════════════════════════════════════╝')
    print()


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
            user_input = input('>>> ').strip()
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
