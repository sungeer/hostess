import logging

from pydantic import BaseModel, Field, model_validator

from src.llm import llm
from src.logger import setup_logger

logger = logging.getLogger(__name__)

# 单次结构化输出的最大尝试次数：首次失败后带错误原因重试一次
MAX_ATTEMPTS = 2


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

    @model_validator(mode='after')
    def check_total_amount(self) -> 'OrderInfo':
        """业务校验：明细合计必须与总金额一致（容忍 1 分钱浮点误差）"""
        items_sum = sum(item.quantity * item.unit_price for item in self.items)
        if abs(items_sum - self.total_amount) > 0.01:
            raise ValueError(
                f'明细合计 {items_sum} 与总金额 {self.total_amount} 不一致'
            )
        return self


def llm_parse(messages: list, response_format):
    """调用 LLM 并返回按 response_format 解析后的结构化对象。

    Args:
        messages: 对话消息列表
        response_format: Pydantic 模型类（不是实例）

    Returns:
        解析后的 Pydantic 模型实例；重试用尽仍失败时返回 None
    """
    structured_llm = llm.with_structured_output(
        response_format,            # OrderInfo
        method='function_calling',  # 当前代理不支持 json_schema
        include_raw=True,           # 解析失败不抛异常，便于按 None 处理
    )
    current_messages = messages
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = structured_llm.invoke(current_messages)
        except Exception:
            # 调用层失败（超时、503 过载等）：原样重试，错误原因对模型没有意义
            logger.exception('第 %s 次调用 LLM 失败', attempt)
            continue

        parsed = result['parsed']  # OrderInfo | None
        if parsed is not None:
            return parsed

        error = result['parsing_error']
        logger.warning('第 %s 次结构化解析失败: %s', attempt, error)
        # 模型的 tool_call 必须逐条用 tool 消息应答，否则接口返回 400；
        # 校验错误就放在 tool 的返回内容里，模型据此自我修正，而不是原样重试
        corrections = [
            {
                'role': 'tool',
                'content': f'校验失败：{error}。请修正后重新输出。',
                'tool_call_id': call['id'],
            }
            for call in result['raw'].tool_calls
        ]
        current_messages = [*current_messages, result['raw'], *corrections]

    return None


def extract_order(user_input: str):
    """从自然语言文本中抽取订单结构化信息。

    Args:
        user_input: 用户自由输入的订单描述

    Returns:
        解析后的 OrderInfo 对象；重试用尽仍失败时返回 None
    """
    messages = [
        {
            'role': 'system',
            'content': '你是订单信息提取助手。从用户输入中提取订单信息。缺失的字段根据上下文合理推断。',
        },
        {
            'role': 'user',
            'content': user_input
        },
    ]
    return llm_parse(messages, OrderInfo)


if __name__ == '__main__':
    setup_logger()

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
    else:
        print('提取失败，详情见日志记录')
