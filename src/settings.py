import os
from pathlib import Path

from dotenv import load_dotenv

VERSION = '26.1105.0907'

BASE_DIR = Path(__file__).resolve().parent.parent

# 启动时所在目录，作为工具的默认工作目录
WORKSPACE = Path.cwd().resolve()


def resolve_path(p: str) -> Path:
    """相对路径以启动目录为基准解析"""
    q = Path(p).expanduser()
    return q.resolve() if q.is_absolute() else (WORKSPACE / q).resolve()

dotenv_path = BASE_DIR / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)

LLM_MODEL = os.environ.get('MODEL', 'deepseek-v4-flash')
LLM_URL = os.environ.get('API_BASE_URL')
LLM_KEY = os.environ.get('API_KEY')
