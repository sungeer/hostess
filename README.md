# hostess

一个运行在命令行里的极简 AI 编码助手，可以帮你读代码、写代码、搜文件和执行命令。

## 依赖

- Python 3.11+

```bash
pip install python-dotenv openai loguru
```

其余全部使用 Python 标准库。

## 快速开始

### 1. 配置环境变量

```bash
API_BASE_URL=https://api.deepseek.com
API_KEY=sk-no-key
MODEL=deepseek-v4-flash
MAX_TOKENS=65536
```

### 2. 启动

```bash
python src
```

### 3. 使用

直接输入自然语言指令：

```
>>> 帮我看看这个项目的目录结构
>>> 给 src/models.py 里的 User 类加个 phone 字段
>>> 用 pytest 跑一下 tests/ 目录下的测试
>>> 帮我分析这个 bug，定位出问题的代码
```

## 环境变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_BASE_URL` | `http://localhost:8000/v1` | LLM API 地址（OpenAI 兼容格式） |
| `API_KEY` | `sk-no-key` | API 密钥 |
| `MODEL` | `deepseek-chat` | 模型名称 |
| `MAX_TOKENS` | `16384` | 最大输出 token |
| `SYSTEM_PROMPT` | 内置默认 | 自定义系统提示 |

## 内置命令

| 命令 | 作用 |
|------|------|
| `/help` | 显示帮助 |
| `/c` | 重置对话历史 |
| `/exit` `/q` `/quit` | 退出程序 |

## 可用工具

Agent 拥有 7 个工具（完全对齐 pi-agent），由 LLM 自动选择调用：

| 工具 | 功能 | 参数 |
|------|------|------|
| `read` | 读取文件内容（带行号，可分页） | `path`, `offset`, `limit` |
| `write` | 创建或覆写文件（自动建目录） | `path`, `content` |
| `edit` | 精确字符串替换（支持多 edit） | `path`, `edits` |
| `bash` | 执行 shell 命令 | `command`, `timeout` |
| `grep` | 搜索文件内容（正则/字面量） | `pattern`, `path`, `glob`, `ignoreCase`, `literal`, `context`, `limit` |
| `find` | 按 glob 模式查找文件 | `pattern`, `path`, `limit` |
| `ls` | 列出目录内容 | `path`, `limit` |

### 工具示例

```
read('src/main.py', offset=10, limit=30)         → 从第10行开始读30行
write('docs/api.md', '# API 文档\n...')           → 写入文件
edit('src/app.py', [{'oldText': 'foo', 'newText': 'bar'}])  → 精确替换
bash('git log --oneline -5', timeout=30)          → 执行 git 命令，30秒超时
grep('@route', glob='*.py', context=2)            → 搜索路由定义，带2行上下文
find('src/**/*.py')                                → 递归匹配所有 .py 文件
ls('src/', limit=100)                              → 列出 src 目录前100条
```

## 工作流程

1. **理解需求** — 先理解用户想做什么，不清楚时主动提问
2. **探索** — 用 `find` 了解项目文件结构
3. **搜索** — 用 `grep` 查找关键代码
4. **阅读** — 用 `read` 仔细阅读相关文件（大文件分页读）
5. **编辑** — 用小范围 `edit` 做精确修改；全新文件用 `write`
6. **执行** — 用 `bash` 执行测试、构建、git 等命令

## 适用场景

- 在命令行中快速阅读、修改代码
- 辅助排查 bug，定位问题代码
- 执行 git 操作、跑测试等日常命令
- 探索陌生项目，理解代码结构

## 注意事项

- Agent 在执行 `bash` 命令时无沙箱限制，请在可信环境中使用
- 读取超大文件时 LLM 会自动使用分页，避免单次 token 溢出
- 工具调用最多 20 轮，防止意外死循环
- 使用 `/c` 可随时重置对话，LLM 会忘记此前读过的文件
