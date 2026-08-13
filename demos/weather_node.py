import json

import httpx
import openai

LLM_BASE_URL = 'http://your-proxy-host/v1'
LLM_API_KEY = 'your-api-key'
LLM_MODEL = 'deepseek-v4-pro'

http_client = httpx.Client(verify=False)  # 禁用 SSL 证书验证

client = openai.OpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
    http_client=http_client,
    timeout=120,
)

GET_WEATHER_TOOL = {
    'type': 'function',
    'function': {
        'name': 'get_weather',
        'description': '查询指定城市的天气信息',
        'parameters': {
            'type': 'object',
            'properties': {
                'city': {
                    'type': 'string',
                    'description': '城市名称',
                },
            },
            'required': ['city'],
        },
    },
}

TOOLS = [GET_WEATHER_TOOL]


def get_weather(city: str) -> str:
    weather_data = {
        '北京': '晴，25°C，微风',
        '上海': '多云，28°C，东南风3级',
        '深圳': '阵雨，30°C，西南风2级',
    }
    return weather_data.get(city, f'未找到[{city}]的天气数据')


TOOLS_MAP = {
    'get_weather': get_weather,
}


def llm_chat(messages: list, tools: list | None = None) -> dict:
    kwargs = {
        'model': LLM_MODEL,
        'messages': messages,
        'extra_body': {'thinking': {'type': 'disabled'}},
        'temperature': 0.0,
    }
    if tools:
        kwargs['tools'] = tools

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.to_dict()


def weather_node(user_input: str) -> str:
    """天气咨询：内部 ReAct 循环，LLM 自主决定调工具，最多 3 轮。

    Args:
        user_input: 用户输入，如 "今天深圳天气怎么样"

    Returns:
        LLM 的最终回答文本
    """
    # 第一阶段：工具调用循环
    system_prompt = (
        '你是天气咨询专家，可以根据需要调用 get_weather 工具查询天气。'
    )
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_input},
    ]

    for i in range(3):
        response_msg = llm_chat(messages, tools=TOOLS)
        messages.append(response_msg)

        # 没有工具调用 → LLM 认为不需要查天气，直接退出循环
        tool_calls = response_msg.get('tool_calls')
        if not tool_calls:
            print(f'[ReAct] 无需工具调用，第 [{i}] 轮结束循环')
            break

        print(f'[ReAct] 工具调用第 [{i + 1}] 轮')
        for tc in tool_calls:
            func_name = tc['function']['name']
            try:
                func_args = json.loads(tc['function']['arguments'])
            except json.JSONDecodeError:
                print(f'[ReAct] 工具参数解析失败，跳过: {tc["function"]["arguments"]}')
                continue

            tool_func = TOOLS_MAP.get(func_name)
            if tool_func is None:
                print(f'[ReAct] 未知工具 [{func_name}]，跳过')
                continue

            result = tool_func(**func_args)
            print(f'[ReAct] {func_name}({func_args}) → {result}')

            # 将工具结果追加到消息历史
            messages.append({
                'role': 'tool',
                'tool_call_id': tc['id'],
                'content': result,
            })
    else:
        # for-else：达到上限 3 轮，强制让 LLM 基于已有信息回答
        print('[ReAct] 工具调用达到上限 [3] 轮，强制结束')
        response_msg = llm_chat(messages)
        messages.append(response_msg)

    # 第二阶段：总结归纳 —— 只保留用户问题和工具结果，过滤掉中间推理噪音
    print('[ReAct] 开始总结归纳...')
    summary_prompt = (
        '你是天气咨询专家，根据已有信息回答用户，'
        '不要客套寒暄，采用最简洁明了的回答。'
    )
    final_messages = [
        {'role': 'system', 'content': summary_prompt},
    ]
    for msg in messages:
        if msg.get('role') in ('user', 'tool'):
            final_messages.append(msg)

    final_msg = llm_chat(final_messages)
    return final_msg.get('content') or ''


if __name__ == '__main__':
    queries = [
        '今天深圳天气怎么样？',
        '北京呢？',
        '介绍一下你自己',
    ]

    for query in queries:
        print(f'\n{"=" * 60}')
        print(f'用户: {query}')
        print('-' * 60)
        answer = weather_node(query)
        print(f'助手: {answer}')
