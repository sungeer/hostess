import os

import httpx2 as httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

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

llm = ChatOpenAI(
    model=os.environ.get('MODEL', 'deepseek-v4-flash'),
    base_url=os.environ.get('API_BASE_URL'),
    api_key=os.environ.get('API_KEY'),
    streaming=False,
    extra_body={
        'thinking': {
            'type': 'disabled'
        }
    },
    http_client=http_client,
    temperature=0.0,
    http_socket_options=(),  # 关闭 TCP Keep-Alive 的自定义配置
)
