"""最小化测试 LLM 是否支持 bind_tools / function calling"""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

llm = ChatOpenAI(
    model=os.environ.get('MODEL', 'deepseek-v4-flash'),
    base_url=os.environ.get('API_BASE_URL'),
    api_key=os.environ.get('API_KEY'),
    extra_body={'thinking': {'type': 'disabled'}},
    temperature=0,
    timeout=30,
)


@tool
def add(a: int, b: int) -> int:
    """把两个整数相加"""
    return a + b


llm_with_tools = llm.bind_tools([add])

messages = [
    SystemMessage(content='你是一个助手，可以调用工具。'),
    HumanMessage(content='帮我算一下 123 + 456 等于多少'),
]

response = llm_with_tools.invoke(messages)

print(f'content: {response.content!r}')
print(f'tool_calls: {response.tool_calls}')

if response.tool_calls:
    tc = response.tool_calls[0]
    result = add.invoke(tc)
    print(f'\n工具执行结果: {result}')
    print('\n✅ LLM 支持 bind_tools / function calling')
else:
    print('\n❌ LLM 未返回 tool_calls，可能不支持 function calling')
