# hostess

A minimal AI coding agent that lives in your terminal.
You describe what you want; it reads files, searches the project with bash, and writes new files.
It never modifies existing code — for changes it replies with a unified diff you apply yourself.
It talks to any OpenAI-compatible chat API (DeepSeek by default), logging each run to `logs/`.

## Requirements

- Python 3.10+
- Git Bash on Windows (`bash.exe`)

```bash
python -m pip install langchain-core langchain-openai httpx2 python-dotenv pydantic
```

## Quick Start

### 1. Configure environment variables

Create a `.env` file in the project root (see `.env.example`):

```bash
API_BASE_URL=https://api.deepseek.com
API_KEY=sk-no-key
MODEL=deepseek-flash
BASH_PATH=C:\Apps\Git\bin\bash.exe
```

### 2. Launch

```bash
python run.py
```

Or use `bin/hostess.bat` if the paths inside match your machine.

## Built-in Commands

| Command | Description |
|---------|-------------|
| `/clear` | Clear the conversation history and start over |
| `/exit` `/q` `/quit` | Quit |

## Available Tools

The agent has 3 tools; the LLM decides which ones to call:

| Tool | Function | Parameters |
|------|----------|------------|
| `bash` | Run a bash command with the project root as cwd; returns stdout, stderr and the exit code | `command`, `timeout` (seconds, default 30) |
| `read` | Read a file with line numbers, paginated via `offset`/`limit` | `file_path`, `offset`, `limit` |
| `write` | Create a new file (parent directories created automatically); existing files are refused | `file_path`, `content` |

`bash` is the only way to run commands, so listing and searching go through it: `ls`, `find`, `rg` (falling back to `grep -rn`).
Its output is truncated at 20,000 characters and the exit code is appended, so the model can tell success from failure.
