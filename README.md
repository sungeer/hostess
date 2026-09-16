# hostess

A minimal AI coding agent that lives in your terminal.
You describe what you want; it reads files, searches the project, and edits code to get it done.
It is built on LangChain and talks to any OpenAI-compatible chat API (DeepSeek by default), logging each run to `logs/`.

## Requirements

- Python 3.10+

```bash
python -m pip install langchain-openai httpx2 python-dotenv loguru
```

## Quick Start

### 1. Configure environment variables

Create a `.env` file in the project root (see `.env.example`):

```bash
API_BASE_URL=https://api.deepseek.com
API_KEY=sk-no-key
MODEL=deepseek-v4-flash
```

### 2. Launch

```bash
python -m src
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `/clear` | Clear the conversation history and start over |
| `/exit` `/q` `/quit` | Quit |

## Available Tools

The agent has 6 tools; the LLM decides which ones to call:

| Tool | Function | Parameters |
|------|----------|------------|
| `read` | Read a file with line numbers, paginated via `offset`/`limit` | `path`, `offset`, `limit` |
| `write` | Create or overwrite a file (parent directories created automatically) | `path`, `content` |
| `edit` | Exact string replacement; every `oldText` must be unique and non-overlapping | `path`, `edits` |
| `grep` | Search file contents (regex or literal, glob filter, context lines) | `pattern`, `path`, `glob`, `ignore_case`, `literal`, `context`, `limit` |
| `find` | Find files by glob pattern, newest first | `pattern`, `path`, `limit` |
| `ls` | List directory contents | `path`, `limit` |

All three traversal tools — `grep`, `find`, `ls` — skip hidden directories and build directories such as `__pycache__` and `node_modules`.

## Workflow

1. **Understand the request** — Work out what the user wants; ask questions when it is unclear
2. **Explore** — Use `find` to learn the project's file structure
3. **Search** — Use `grep` to locate the key code
4. **Read** — Use `read` to go through the relevant files (paginating large ones)
5. **Edit** — Make precise changes with small-scope `edit`; use `write` for brand-new files or full rewrites

## Use Cases

- Quickly read and modify code from the command line
- Help troubleshoot bugs and locate the problematic code
- Explore unfamiliar projects and understand their code structure

## Notes

- There is no shell tool: hostess cannot run commands, tests, builds, or git. Run those yourself in your own terminal
- Files over 1 MB are flagged as large so the LLM pages through them with `offset`/`limit`, avoiding one oversized request
- A single request is capped at 100 tool-calling rounds to prevent runaway loops
- Short-term memory keeps at most 100 messages and drops the oldest ones automatically
- `/clear` resets the conversation, after which the LLM no longer remembers the files it read earlier
