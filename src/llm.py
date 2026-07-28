import logging
import os

import httpx
from dotenv import load_dotenv
from openai import OpenAI

logging.getLogger('httpx').propagate = False

load_dotenv()

model_name = os.environ.get('MODEL', 'deepseek-v4-flash')

http_client = httpx.Client(verify=False)  # 禁用 SSL 证书验证

client = OpenAI(
    base_url=os.environ.get('API_BASE_URL'),
    api_key=os.environ.get('API_KEY'),
    http_client=http_client,
    timeout=120,
)

common_kwargs = {
    'temperature': 0.0,
    'extra_body': {'thinking': {'type': 'disabled'}},
}
