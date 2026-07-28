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

Agent 拥有 5 个工具，由 LLM 自动选择调用：

| 工具 | 功能 | 参数 |
|------|------|------|
| `read` | 读取文件内容（带行号） | `file_path`, `offset`, `limit` |
| `write` | 写入文件（自动建目录） | `file_path`, `content` |
| `glob` | 文件模式匹配 | `pattern`, `path` |
| `grep` | 递归搜索文件内容 | `pattern`, `path`, `include` |
| `bash` | 执行 shell 命令 | `cmd` |

### 工具示例

```
read('src/main.py', offset=10, limit=30)    → 从第10行开始读30行
write('docs/api.md', '# API 文档\n...')      → 写入文件
glob('src/**/*.py')                          → 递归匹配所有 .py 文件
grep('@route', include='*.py')              → 搜索路由定义
bash('git log --oneline -5')                 → 执行 git 命令
```

## 工作流程

1. **理解需求** — 先理解用户想做什么，不清楚时主动提问
2. **探索** — 用 `glob` 了解项目文件结构
3. **搜索** — 用 `grep` 查找关键代码
4. **阅读** — 用 `read` 仔细阅读相关文件（大文件分页读）
5. **执行** — 用 `write` 修改代码，或用 `bash` 执行命令

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
