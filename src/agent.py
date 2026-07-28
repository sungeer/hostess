import json
import logging
import textwrap

from src.llm import client, model_name, common_kwargs
from src.tools import TOOLS, TOOLS_MAP
from src.memory import ShortTerm

log = logging.getLogger(__name__)

system_prompt = textwrap.dedent('''
    # 角色
    你是一个在命令行工作的 AI 编码助手。
    
    # 工作方式
    1. 先理解用户的需求，不清楚时主动提问
    2. 用 glob 了解项目文件结构
    3. 用 grep 搜索关键代码，用 read 阅读相关文件
    4. 根据需求修改代码（write）或执行命令（bash）
    
    # 代码风格
    - 遵循项目现有的代码风格，不要随意改变
    - 不引入不必要的抽象，YAGNI
    - 只在非显而易见的逻辑处写简短注释
    
    # 注意事项
    - 行动前先简要说明当前的理解和下一步计划
    - 写文件前先读文件，确保理解准确再动笔
    - 不要无理由地改变与任务无关的代码
''').strip()


def run_agent(user_input: str, memory: ShortTerm, max_steps: int = 20) -> str:
    memory.add({'role': 'user', 'content': user_input})

    for step in range(max_steps):
        messages = [{'role': 'system', 'content': system_prompt}] + memory.get_messages()
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=TOOLS,
                **common_kwargs,
            )
        except Exception:
            log.exception('LLM 调用失败，第[%s]轮', step)
            return f'错误：LLM 调用失败（第{step}轮），请检查 API 配置或网络连接'
        response_msg = response.choices[0].message.to_dict()
        memory.add(response_msg)

        tool_calls = response_msg.get('tool_calls')
        if not tool_calls:
            log.info(f'无需工具调用，第[{step}]轮结束')
            return response_msg.get('content') or ''

        log.info(f'工具调用第[{step + 1}]轮')

        for tc in tool_calls:
            func_name = tc['function']['name']
            tool_func = TOOLS_MAP.get(func_name)
            if tool_func is None:
                log.warning(f'未知工具: {func_name}')
                continue

            try:
                func_args = json.loads(tc['function']['arguments'])
            except json.JSONDecodeError:
                log.warning(f'工具参数解析失败: {tc["function"]["arguments"]}')
                continue

            log.info(f'执行工具: {func_name}，参数: {func_args}')

            try:
                result = tool_func(**func_args)
            except Exception:
                log.exception(f'工具执行失败: {func_name}')
                result = f'工具执行失败: {func_name}'

            log.info(f'工具结果: {str(result)[:100]}')

            memory.add({
                'role': 'tool',
                'tool_call_id': tc['id'],
                'content': str(result),
            })

    log.warning(f'工具调用达到上限 {max_steps} 轮，强制总结')

    summary_prompt = (
        '你是一个在命令行工作的 AI 编码助手。'
        '根据已有信息回答用户，不要客套寒暄，采用最简洁明了的回答。'
    )
    final_messages = [{'role': 'system', 'content': summary_prompt}]
    for msg in memory.get_messages():
        if msg.get('role') in ('user', 'tool'):
            final_messages.append(msg)
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=final_messages,
            **common_kwargs,
        )
    except Exception:
        log.exception('LLM 总结调用失败')
        return '错误：LLM 调用失败，无法生成总结'
    response_msg = response.choices[0].message.to_dict()
    memory.add(response_msg)
    return response_msg.get('content') or ''
