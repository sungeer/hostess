import os
from pathlib import Path

from dotenv import load_dotenv

VERSION = '26.1027.1533'

BASE_DIR = Path(__file__).resolve().parent.parent

dotenv_path = BASE_DIR / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)

LLM_MODEL = os.environ.get('MODEL', 'deepseek-v4-flash')
LLM_URL = os.environ.get('API_BASE_URL')
LLM_KEY = os.environ.get('API_KEY')
