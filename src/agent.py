import logging

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from src.llm import llm
from src.toolset import tools
from src.memory import ShortTerm

log = logging.getLogger(__name__)

system_prompt = (
    '你是一个在命令行工作的 AI 编码助手。\n'
    '\n'
    '## 工作方式\n'
    '1. 先理解用户的需求，不清楚时主动提问\n'
    '2. 用 glob 了解项目文件结构\n'
    '3. 用 grep 搜索关键代码，用 read 阅读相关文件\n'
    '4. 根据需求修改代码（write）或执行命令（bash）\n'
    '\n'
    '## 代码风格\n'
    '- 遵循项目现有的代码风格，不要随意改变\n'
    '- 不引入不必要的抽象，YAGNI\n'
    '- 只在非显而易见的逻辑处写简短注释\n'
    '\n'
    '## 注意事项\n'
    '- 行动前先简要说明当前的理解和下一步计划\n'
    '- 写文件前先读文件，确保理解准确再动笔\n'
    '- 不要无理由地改变与任务无关的代码\n'
    '- 不要用相同参数重复调用同一个工具\n'
)

tools_map = {t.name: t for t in tools}


def run_agent(user_input: str, memory: ShortTerm, max_steps: int = 20) -> str:
    """bind_tools 模式的 agent 循环，支持边说边调、并行工具调用。"""
    memory.add(HumanMessage(content=user_input))

    llm_with_tools = llm.bind_tools(tools)

    for step in range(max_steps):
        messages = [SystemMessage(content=system_prompt)] + memory.get_messages()
        response = llm_with_tools.invoke(messages)
        memory.add(response)

        if response.content:
            log.info(f'[thought] {response.content[:200]}')

        if not response.tool_calls:
            log.info(f'无需工具调用，第[{step}]轮结束')
            return response.content or ''

        log.info(f'工具调用第[{step + 1}]轮')

        for tc in response.tool_calls:
            tool_func = tools_map.get(tc['name'])
            if tool_func is None:
                log.warning(f'未知工具: {tc["name"]}')
                continue

            log.info(f'执行工具: {tc["name"]}，参数: {tc["args"]}')

            result = tool_func.invoke(tc)

            log.info(f'工具结果: {str(result)[:100]}')

            memory.add(ToolMessage(content=str(result), tool_call_id=tc['id']))

    log.warning(f'工具调用达到上限 {max_steps} 轮，强制总结')

    messages = [SystemMessage(content=system_prompt)] + memory.get_messages()
    messages.append(HumanMessage(content='请根据已有的工具返回信息，简洁地回答用户的问题。'))
    response = llm.invoke(messages)
    memory.add(response)
    return response.content or ''
