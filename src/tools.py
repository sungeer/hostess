import os
import re
import subprocess
from pathlib import Path


def read(path: str, offset: int = 0, limit: int = 0) -> str:
    """读取文件内容。支持文本文件。用 offset/limit 分页读取大文件。"""
    p = Path(path).expanduser().resolve()
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


def write(path: str, content: str) -> str:
    """写入文件，自动创建父目录。创建或覆盖文件。"""
    p = Path(path).expanduser().resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return f'已写入 {len(content):,} 字节到 {p}'
    except OSError as e:
        return f'写入失败：{e}'


def edit(path: str, edits: list[dict]) -> str:
    """对单个文件进行精确字符串替换。
    每个 edits[].oldText 必须在原文件中唯一且不与其他 edit 重叠。
    所有 edit 都基于原始文件匹配（非增量应用）。
    """
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f'错误：文件不存在 — {p}'
    if p.is_dir():
        return f'错误：路径是目录不是文件 — {p}'

    try:
        original = p.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return '错误：无法读取该文件（编码不支持，可能为二进制文件）'

    # 验证 edits 参数
    if not isinstance(edits, list) or len(edits) == 0:
        return '错误：edits 必须是至少包含一个替换项的非空列表'

    parsed: list[dict] = []
    for i, item in enumerate(edits):
        if not isinstance(item, dict):
            return f'错误：edits[{i}] 不是对象'
        old_text = item.get('oldText', '')
        new_text = item.get('newText', '')
        if not isinstance(old_text, str) or not isinstance(new_text, str):
            return f'错误：edits[{i}] 的 oldText 和 newText 必须是字符串'
        parsed.append({'oldText': old_text, 'newText': new_text, 'index': i})

    # 在原始文件中定位每个 oldText，检查唯一性
    spans: list[dict] = []
    for item in parsed:
        old_text = item['oldText']
        # 查找所有匹配位置
        positions: list[int] = []
        start = 0
        while True:
            pos = original.find(old_text, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1

        if len(positions) == 0:
            return f'错误：edits[{item["index"]}] 的 oldText 在原文件中未找到'

        if len(positions) > 1:
            return (
                f'错误：edits[{item["index"]}] 的 oldText 在原文件中出现了 {len(positions)} 次，'
                f'必须唯一。请包含更多上下文使其唯一。'
            )

        spans.append({
            'index': item['index'],
            'start': positions[0],
            'end': positions[0] + len(old_text),
            'oldText': old_text,
            'newText': item['newText'],
        })

    # 检查重叠：按起始位置排序后检查相邻区间
    spans.sort(key=lambda s: s['start'])
    for i in range(len(spans) - 1):
        if spans[i]['end'] > spans[i + 1]['start']:
            return (
                f'错误：edits[{spans[i]["index"]}] 和 edits[{spans[i + 1]["index"]}] 存在重叠。'
                f'请合并为一个 edit。'
            )

    # 从后往前应用替换（保持位置不变）
    result = original
    for span in reversed(spans):
        result = result[:span['start']] + span['newText'] + result[span['end']:]

    try:
        p.write_text(result, encoding='utf-8')
        return f'已成功替换 {len(parsed)} 个代码块到 {p}'
    except OSError as e:
        return f'写入失败：{e}'


def bash(command: str, timeout: int = 0) -> str:
    """执行 shell 命令。可指定超时秒数（0 表示默认 120 秒）。"""
    timeout_sec = float(timeout) if timeout > 0 else 120.0
    try:
        r = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout_sec, encoding='utf-8', errors='replace',
        )
        out = r.stdout.strip()
        err = r.stderr.strip()
        parts = [out] if out else []
        if err:
            parts.append(f'[stderr]\n{err}')
        return '\n'.join(parts) if parts else '(无输出)'
    except subprocess.TimeoutExpired:
        return f'(命令超时，已等待 {timeout_sec:.0f} 秒)'
    except OSError as e:
        return f'命令执行失败：{e}'


def grep(
    pattern: str,
    path: str = '.',
    glob: str = '',
    ignoreCase: bool = False,
    literal: bool = False,
    context: int = 0,
    limit: int = 100,
) -> str:
    """搜索文件内容。返回带文件路径和行号的匹配行。每行长行截断至 200 字符。"""
    root = Path(path).expanduser().resolve()
    if not root.exists():
        return f'错误：路径不存在 — {root}'

    results: list[str] = []
    search_glob = glob.strip() if glob else ''

    # 构建搜索模式
    if literal:
        # 字面量搜索：不区分大小写时转小写对比
        pass
    else:
        try:
            flags = re.IGNORECASE if ignoreCase else 0
            compiled = re.compile(pattern, flags)
        except re.error as e:
            return f'正则错误：{e}'

    def match_line(line_text: str) -> bool:
        if literal:
            if ignoreCase:
                return pattern.lower() in line_text.lower()
            return pattern in line_text
        return bool(compiled.search(line_text))

    context_lines = max(0, int(context))
    effective_limit = max(1, int(limit))

    for dirpath_str, _dirnames, filenames in os.walk(root):
        _dirnames[:] = [
            d for d in _dirnames
            if not d.startswith('.') and d not in ('__pycache__', 'node_modules', '.git')
        ]
        for fn in filenames:
            if search_glob:
                if not Path(fn).match(search_glob):
                    continue
            fpath = os.path.join(dirpath_str, fn)
            try:
                with open(fpath, encoding='utf-8', errors='replace') as f:
                    file_lines = f.readlines()
            except OSError:
                continue

            if context_lines > 0:
                # 带上下文模式
                matched: set[int] = set()
                for i, line in enumerate(file_lines):
                    if match_line(line):
                        matched.add(i)
                if not matched:
                    continue
                for i, line in enumerate(file_lines):
                    in_range = any(abs(i - m) <= context_lines for m in matched)
                    if in_range:
                        prefix = ':' if i in matched else '-'
                        rel = os.path.relpath(fpath, root).replace('\\', '/')
                        line_text = line.rstrip('\n\r')[:200]
                        results.append(f'{rel}:{prefix}{i + 1}: {line_text}')
                        if len(results) >= effective_limit:
                            return '\n'.join(results) + '\n...（结果已截断，请缩小搜索范围）'
            else:
                # 无上下文模式
                for i, line in enumerate(file_lines):
                    if match_line(line):
                        rel = os.path.relpath(fpath, root).replace('\\', '/')
                        line_text = line.rstrip('\n\r')[:200]
                        results.append(f'{rel}:{i + 1}: {line_text}')
                        if len(results) >= effective_limit:
                            return '\n'.join(results) + '\n...（结果已截断，请缩小搜索范围）'

    return '\n'.join(results) if results else '(无匹配)'


def find(pattern: str, path: str = '.', limit: int = 1000) -> str:
    """按 glob 模式匹配文件，支持 ** 递归。返回相对于搜索目录的文件路径。"""
    root = Path(path).expanduser().resolve()
    if not root.exists():
        return f'错误：路径不存在 — {root}'
    if not root.is_dir():
        return f'错误：路径不是目录 — {root}'

    effective_limit = max(1, int(limit))

    try:
        import glob as _glob
        matches = list(_glob.glob(pattern, root_dir=root, recursive=True))
    except (OSError, re.error) as e:
        return f'find 错误：{e}'

    if not matches:
        return '没有找到匹配的文件'

    def mtime(f):
        return (root / f).stat().st_mtime

    matches.sort(key=mtime, reverse=True)
    truncated = matches[:effective_limit]

    out = '\n'.join(truncated)
    if len(matches) > effective_limit:
        out += f'\n\n[达到 {effective_limit} 条结果上限。请用更精确的 pattern 或增大 limit。]'
    return out


def ls(path: str = '.', limit: int = 500) -> str:
    """列出目录内容。按字母排序，目录带 '/' 后缀。包含隐藏文件。"""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f'错误：路径不存在 — {p}'
    if not p.is_dir():
        return f'错误：不是目录 — {p}'

    effective_limit = max(1, int(limit))

    try:
        entries = sorted(p.iterdir(), key=lambda e: e.name.lower())
    except OSError as e:
        return f'无法列出目录：{e}'

    if not entries:
        return '(空目录)'

    results: list[str] = []
    for entry in entries:
        if len(results) >= effective_limit:
            results.append(f'...（还有 {len(entries) - effective_limit} 个条目，请增大 limit 查看）')
            break
        suffix = '/' if entry.is_dir() else ''
        results.append(entry.name + suffix)

    return '\n'.join(results)


TOOLS_MAP = {
    'read': read,
    'write': write,
    'edit': edit,
    'bash': bash,
    'grep': grep,
    'find': find,
    'ls': ls,
}

TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'read',
            'description': '读取文件内容。支持文本文件。用 offset/limit 分页读取大文件。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': '要读取的文件路径（相对或绝对）',
                    },
                    'offset': {
                        'type': 'integer',
                        'description': '起始行号，从1开始，0表示从头读取',
                        'default': 0,
                    },
                    'limit': {
                        'type': 'integer',
                        'description': '最大读取行数，0表示读取全部',
                        'default': 0,
                    },
                },
                'required': ['path'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'write',
            'description': '写入文件。文件不存在则创建，存在则覆盖。自动创建父目录。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': '要写入的文件路径（相对或绝对）',
                    },
                    'content': {
                        'type': 'string',
                        'description': '要写入文件的完整内容',
                    },
                },
                'required': ['path', 'content'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'edit',
            'description': '对单个文件进行精确字符串替换。edits[].oldText 必须在原文件中唯一，且不能重叠。所有编辑基于原始文件匹配（非增量应用）。多个不连续的修改请放在一次 edit 调用的多个 edits[] 中。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': '要编辑的文件路径（相对或绝对）',
                    },
                    'edits': {
                        'type': 'array',
                        'description': '一个或多个精确替换。每个 edit 都有 oldText 和 newText。切勿包含重叠或嵌套的 edit。',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'oldText': {
                                    'type': 'string',
                                    'description': '要精确匹配的原文本，必须在文件中唯一',
                                },
                                'newText': {
                                    'type': 'string',
                                    'description': '替换后的新文本',
                                },
                            },
                            'required': ['oldText', 'newText'],
                        },
                    },
                },
                'required': ['path', 'edits'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'bash',
            'description': '在当前工作目录执行 shell 命令。返回 stdout 和 stderr。可指定超时秒数。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'command': {
                        'type': 'string',
                        'description': '要执行的 shell 命令',
                    },
                    'timeout': {
                        'type': 'integer',
                        'description': '超时秒数（可选，默认 120 秒）',
                        'default': 0,
                    },
                },
                'required': ['command'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'grep',
            'description': '搜索文件内容。返回带文件路径和行号的匹配行。尊重 .gitignore。默认最多返回 100 条匹配。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'pattern': {
                        'type': 'string',
                        'description': '搜索模式（正则或字面量字符串）',
                    },
                    'path': {
                        'type': 'string',
                        'description': '搜索目录或文件（默认当前目录）',
                    },
                    'glob': {
                        'type': 'string',
                        'description': '按 glob 过滤文件，例如 *.py 或 **/*.spec.ts',
                    },
                    'ignoreCase': {
                        'type': 'boolean',
                        'description': '不区分大小写搜索（默认 false）',
                    },
                    'literal': {
                        'type': 'boolean',
                        'description': '将 pattern 视为字面量字符串而非正则（默认 false）',
                    },
                    'context': {
                        'type': 'integer',
                        'description': '每条匹配前后显示的行数（默认 0）',
                    },
                    'limit': {
                        'type': 'integer',
                        'description': '最大返回匹配数（默认 100）',
                    },
                },
                'required': ['pattern'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'find',
            'description': '按 glob 模式搜索文件。返回相对于搜索目录的文件路径。尊重 .gitignore。默认最多返回 1000 条结果。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'pattern': {
                        'type': 'string',
                        'description': 'Glob 模式，例如 *.ts、**/*.json 或 src/**/*.spec.ts',
                    },
                    'path': {
                        'type': 'string',
                        'description': '搜索目录（默认当前目录）',
                    },
                    'limit': {
                        'type': 'integer',
                        'description': '最大返回结果数（默认 1000）',
                    },
                },
                'required': ['pattern'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'ls',
            'description': '列出目录内容。按字母排序，目录带 / 后缀。包含隐藏文件。默认最多返回 500 条。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': '要列出的目录（默认当前目录）',
                    },
                    'limit': {
                        'type': 'integer',
                        'description': '最大返回条目数（默认 500）',
                    },
                },
                'required': [],
            },
        },
    },
]
