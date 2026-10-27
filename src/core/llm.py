import httpx2 as httpx
from langchain_openai import ChatOpenAI

from src import settings

http_client = httpx.Client(
    timeout=httpx.Timeout(
        connect=5.0,
        read=180.0,
        write=5.0,
        pool=5.0
    ),
    limits=httpx.Limits(
        max_connections=900,
        keepalive_expiry=0.0,
    ),
    verify=False,
)

llm = ChatOpenAI(
    model=settings.LLM_MODEL,
    base_url=settings.LLM_URL,
    api_key=settings.LLM_KEY,
    streaming=False,
    extra_body={
        'thinking': {
            'type': 'disabled'
        }
    },
    http_client=http_client,
    temperature=0.0,
    http_socket_options=(),
)
