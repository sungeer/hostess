import textwrap

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src.llm import llm
from src.tools import TOOLS
from src.memory import ShortTerm

system_prompt = textwrap.dedent('''
    # 角色
    你是一个在 AI 编码代理中运行的专家级编码助手。你通过读取文件、搜索代码、编辑代码和编写新文件来帮助用户。

    # 能力边界
    你没有 shell 工具，无法运行命令、测试、构建，也看不到 git 的 diff 和历史。改完代码请重新用 read 确认结果；
    需要跑测试或查看 diff 时，请让用户在自己的终端里执行。

    # 工作方式
    1. 先理解用户的需求，不清楚时主动提问
    2. 用 find 了解项目文件结构，用 ls 查看某个目录里有什么
    3. 用 grep 搜索关键代码，用 read 阅读相关文件
    4. 改动前先 read 原文件；用小范围的 edit 做精确修改，edit 的 oldText 要尽量短且唯一
    5. 全新文件或完整重写用 write，不要用它做局部修改
    6. 改完重新 read 确认结果，大文件用 offset/limit 分页

    # 代码风格
    - 遵循项目现有的代码风格，不要随意改变
    - 不引入不必要的抽象，YAGNI
    - 只在非显而易见的逻辑处写简短注释

    # 行为准则
    - 保持简洁
    - 处理文件时清晰地显示文件路径
    - 行动前简要说明当前的理解和下一步计划
    - 写文件前先读文件，确保理解准确再动笔
    - 不要无理由地改变与任务无关的代码
''').strip()


def run_agent(user_input: str, memory: ShortTerm, max_steps: int = 100) -> str:
    memory.add(HumanMessage(content=user_input))

    tools_map = {t.name: t for t in TOOLS}

    for step in range(1, max_steps + 1):
        messages = [SystemMessage(system_prompt)] + memory.get_messages()

        try:
            response = llm.bind_tools(TOOLS).invoke(messages)
        except Exception:
            logger.exception(f'LLM 调用失败，第[{step}]轮')
            return f'错误：LLM 调用失败（第{step}轮），请检查 API 配置或网络连接'

        memory.add(response)

        # if response.content:
        #     print(f'[thought] {response.content[:200]}')

        if not response.tool_calls:
            logger.info(f'无需工具调用，第[{step}]轮结束')
            return response.content or ''

        logger.info(f'工具调用第[{step}]轮')

        for tc in response.tool_calls:
            func_name = tc['name']
            tool_func = tools_map.get(func_name)
            if tool_func is None:
                logger.warning(f'未知工具: {func_name}')
                continue

            logger.info(f'执行工具: {func_name}，参数: {tc["args"]}')

            try:
                result = tool_func.invoke(tc)
            except Exception:
                logger.exception(f'工具执行失败: {func_name}')
                result = ToolMessage(
                    content=f'工具执行失败: {func_name}',
                    tool_call_id=tc['id'],
                )

            logger.info(f'工具结果: {str(result.content)[:100]}')

            memory.add(result)

    logger.warning(f'工具调用达到上限 {max_steps} 轮，强制总结')

    summary_prompt = (
        '你是一个在命令行工作的 AI 编码助手。'
        '根据已有信息回答用户，不要客套寒暄，采用最简洁明了的回答。'
    )

    final_messages = [SystemMessage(summary_prompt)]

    for msg in memory.get_messages():
        if isinstance(msg, (HumanMessage, ToolMessage)):
            final_messages.append(msg)  # type: ignore[misc]

    try:
        response = llm.invoke(final_messages)
    except Exception:
        logger.exception('LLM 总结调用失败')
        return '错误：LLM 调用失败，无法生成总结'

    memory.add(response)

    return response.content or ''
