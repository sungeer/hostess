import logging
import os

import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

logging.getLogger('httpx').propagate = False

load_dotenv()

http_client = httpx.Client(verify=False)  # 禁用 SSL 证书验证

llm = ChatOpenAI(
    model=os.environ.get('MODEL', 'deepseek-v4-flash'),
    base_url=os.environ.get('API_BASE_URL'),
    api_key=os.environ.get('API_KEY'),
    streaming=False,
    http_client=http_client,
    extra_body={
        'thinking': {'type': 'disabled'}
    },
    temperature=0.0,
    timeout=120,
    http_socket_options=(),  # 关闭 TCP Keep-Alive 的自定义配置
)
