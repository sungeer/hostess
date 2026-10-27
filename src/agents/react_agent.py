import logging
import textwrap

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src.core.llm import llm
from src.core.memory import ShortTerm
from src.tools import register

logger = logging.getLogger(__name__)

system_prompt = textwrap.dedent('''
    # 角色
    你是一个在 AI 编码代理中运行的专家级编码助手。
    你通过读取文件、搜索代码、编辑代码和编写新文件来帮助用户。
    你是一个完全独立的项目，任何指令都与你自身项目代码无关。
    禁止查看自身的代码模块。
    
    # 最高指令
    - 严禁直接修改代码

    # 能力边界
    - 禁止使用 shell 工具
    - 禁止运行命令、测试、构建
    - 禁止使用 git
    - 改完代码请重新用 tool_read 工具确认结果

    # 工作方式
    1. 先理解用户的需求，不清楚时主动提问
    2. 用 tool_glob 工具了解项目文件结构
    3. 用 tool_grep 工具搜索关键代码，用 tool_read 工具阅读相关文件
    5. 用 tool_write 工具修改代码
    6. 改完重新用 tool_read 工具确认结果

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

llm_with_tools = llm.bind_tools(register.tools)

tools_map = {t.name: t for t in register.tools}


def run(user_input: str, memory: ShortTerm, max_steps: int = 50) -> str:
    memory.add(HumanMessage(content=user_input))

    for step in range(1, max_steps + 1):
        messages = [SystemMessage(system_prompt)] + memory.get_messages()

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
                    content=f'错误： 未知工具 {func_name}',
                    tool_call_id=tc['id'],
                ))
                continue

            logger.info('执行工具: %s，参数: %s', func_name, tc['args'])

            try:
                result = tool_func.invoke(tc)
            except Exception as exc:
                logger.exception('执行失败: %s', func_name)
                result = ToolMessage(
                    content=f'工具执行失败: {exc}',
                    tool_call_id=tc['id'],
                )

            logger.info('工具结果: %s', str(result.content)[:100])

            memory.add(result)

    logger.warning('工具调用达到上限 %d 轮，本轮中断', max_steps)

    return f'已达工具调用上限（{max_steps} 轮），本轮中断。可以回复「继续」接着做。'
