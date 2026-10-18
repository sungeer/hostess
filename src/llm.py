import os

import httpx2 as httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.environ.get('MODEL', 'deepseek-v4-flash')

http_client = httpx.Client(
    timeout=httpx.Timeout(
        connect=10.0,
        read=180.0,
        write=10.0,
        pool=10.0
    ),
    limits=httpx.Limits(
        max_connections=1000,
        keepalive_expiry=0.0,
    ),
    verify=False,
)

client = OpenAI(
    base_url=os.environ.get('API_BASE_URL'),
    api_key=os.environ.get('API_KEY'),
    http_client=http_client,
)
