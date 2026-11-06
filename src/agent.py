import logging

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src import prompt, settings
from src.llm import llm
from src.memory import Memory
from src.tools.bash import tool_bash
from src.tools.read import tool_read
from src.tools.write import tool_write

logger = logging.getLogger(__name__)

tools = [tool_bash, tool_read, tool_write]

llm_with_tools = llm.bind_tools(tools)

tools_map = {t.name: t for t in tools}


def run(user_input: str, memory: Memory, max_steps: int = 50) -> str:
    memory.add(HumanMessage(content=user_input))

    system_message = SystemMessage(content=prompt.build(settings.WORKSPACE))

    for step in range(1, max_steps + 1):
        messages = [system_message] + memory.get_messages()

        try:
            response = llm_with_tools.invoke(messages)
        except Exception:
            logger.exception('调用失败: 第 %d 轮', step)
            if step == 1:
                # 去除没有回复的提问
                memory.drop_last()
            return f'错误：LLM 调用失败（第 {step} 轮），请检查 API 配置或网络连接'

        memory.add(response)

        thought = response.content
        if thought:
            logger.info('思考过程: %s', thought[:200])

        if not response.tool_calls:
            logger.info('无需工具: 第 %d 轮结束', step)
            return response.content or ''

        logger.info('工具调用: 第 %d 轮', step)

        for tc in response.tool_calls:
            func_name = tc['name']
            tool_func = tools_map.get(func_name)
            if tool_func is None:
                logger.warning('未知工具: %s', func_name)
                memory.add(ToolMessage(
                    content=f'错误：未知工具 {func_name}，可用工具：{", ".join(tools_map)}',
                    tool_call_id=tc['id'],
                ))
                continue

            logger.info('执行工具: %s，参数: %s', func_name, tc['args'])

            try:
                result = tool_func.invoke(tc)
            except Exception as exc:
                logger.exception('执行失败: %s', func_name)
                result = ToolMessage(
                    content=f'工具执行失败（{type(exc).__name__}）: {exc}',
                    tool_call_id=tc['id'],
                )

            logger.info('工具结果: %s', str(result.content)[:100])

            memory.add(result)

    logger.warning('工具调用达到上限 %d 轮，本轮中断', max_steps)

    return f'已达工具调用上限（{max_steps} 轮），本轮中断。可以回复「继续」接着做。'
