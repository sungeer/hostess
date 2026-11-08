# hostess

A minimal AI coding agent that runs in your terminal. Built on the LangChain stack.

## Why this exists

Corporate intranets forbid installing third-party coding tools, and only a limited set of
packages is available. This project started from a ReAct loop script written on the LangChain
stack and grew into a working substitute.

It is meant to read project code, write documentation, write demos, find bugs, and produce
revised code modules.

Design constraints follow from that:

- **Three tools only.** `bash`, `read`, `write`. Nothing else.
- **No high-risk tools.** The agent never modifies existing files; it answers with a unified
  diff you apply yourself.
- **High user competence assumed.** This is not a one-click tool. You review what it does.

It talks to any OpenAI-compatible chat API (DeepSeek by default) and logs each run to `logs/`.

## Requirements

- Python 3.11+
- Git Bash on Windows (`bash.exe`)

```bash
python -m pip install python-dotenv langchain-openai
```

## Quick Start

Create a `.env` in the project root (see `.env.example`):

```bash
API_BASE_URL=https://api.deepseek.com
API_KEY=sk-no-key
MODEL=deepseek-flash
BASH_PATH=C:\Apps\Git\bin\bash.exe
```

Run:

```bash
python run.py
```

Or `bin/hostess.bat` if the paths inside match your machine.

## Commands

| Command | Description |
|---------|-------------|
| `/clear` | Clear conversation history |
| `/exit` `/q` `/quit` | Quit |

## Tools

| Tool | Function | Parameters |
|------|----------|------------|
| `bash` | Run a bash command with the project root as cwd; returns stdout, stderr and exit code | `command`, `timeout` (seconds, default 30) |
| `read` | Read a file with line numbers, paginated via `offset`/`limit` | `file_path`, `offset`, `limit` |
| `write` | Create a new file (parent directories created); existing files are refused | `file_path`, `content` |

All listing and searching go through `bash`: `ls`, `find`, `rg` (falling back to `grep -rn`).
Output is truncated at 20,000 characters with the exit code appended.
