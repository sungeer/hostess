import httpx

from openai import OpenAI
from pydantic import BaseModel, Field

LLM_BASE_URL = 'http://your-proxy-host/v1'
LLM_API_KEY = 'your-api-key'
LLM_MODEL = 'deepseek-v4-pro'

http_client = httpx.Client(verify=False)  # 禁用 SSL 证书验证

client = OpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
    http_client=http_client,
    timeout=120,
)


class OrderItem(BaseModel):
    """订单明细中的单行商品"""
    product_name: str = Field(..., description='商品名称')  # 必填
    quantity: int = Field(..., description='购买数量')
    unit_price: float = Field(..., description='单价（元）')


class OrderInfo(BaseModel):
    """一笔完整的订单信息（含嵌套模型）"""
    customer_name: str = Field(..., description='客户姓名')
    phone: str = Field(..., description='联系电话')
    items: list[OrderItem] = Field(..., description='订单商品明细')
    total_amount: float = Field(..., description='订单总金额（元）')
    is_urgent: bool = Field(..., description='客户是否要求加急')


def llm_parse(messages: list, response_format):
    """调用 LLM 并返回按 response_format 解析后的结构化对象。

    Args:
        messages: 对话消息列表
        response_format: Pydantic 模型类（不是实例）

    Returns:
        解析后的 Pydantic 模型实例；解析失败时返回 None
    """
    response = client.beta.chat.completions.parse(
        model=LLM_MODEL,
        messages=messages,
        response_format=response_format,  # OrderInfo
        temperature=0.0,
        extra_body={'thinking': {'type': 'disabled'}},
    )
    parsed = response.choices[0].message.parsed  # OrderInfo | None
    if parsed is None:
        print(f'[警告] 结构化解析失败，原始内容: {response.choices[0].message.content}')
    return parsed


def extract_order(user_input: str):
    """从自然语言文本中抽取订单结构化信息。

    Args:
        user_input: 用户自由输入的订单描述

    Returns:
        解析后的 OrderInfo 对象
    """
    messages = [
        {
            'role': 'system',
            'content': '你是订单信息提取助手。从用户输入中提取订单信息。缺失的字段根据上下文合理推断。',
        },
        {'role': 'user', 'content': user_input},
    ]
    return llm_parse(messages, OrderInfo)


if __name__ == '__main__':
    # ----- 场景一：订单抽取 -----
    print('=' * 60)
    print('【场景一】订单信息抽取')
    print('=' * 60)

    order_text = (
        '你好，我叫张三，电话是13800138000。'
        '我要订2台iPhone 15 Pro Max，单价8999元；'
        '再加1个AirPods Pro，单价1899元。'
        '总共应该是19897元吧？急用，麻烦快点发货！'
    )
    print(f'输入: {order_text}')

    order = extract_order(order_text)
    if order:
        print(f'\n提取结果:')
        print(f'  客户姓名: {order.customer_name}')
        print(f'  联系电话: {order.phone}')
        print(f'  是否加急: {order.is_urgent}')
        print(f'  总金额:   ¥{order.total_amount}')
        print(f'  商品明细:')
        for item in order.items:
            print(f'    - {item.product_name} × {item.quantity}, '
                  f'单价 ¥{item.unit_price}')
        print(f'\nJSON 序列化:\n{order.model_dump_json(indent=2)}')
