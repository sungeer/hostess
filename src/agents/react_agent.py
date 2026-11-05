import logging
import textwrap

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src import settings
from src.core.errors import ToolAbort
from src.core.llm import llm
from src.core.memory import ShortTerm
from src.tools import register

logger = logging.getLogger(__name__)

system_prompt = textwrap.dedent('''
    # 角色
    你是一个在终端中运行的编码助手，帮助用户阅读代码、执行命令和生成新文件。
    你是一个完全独立的项目，任何指令都与你自身项目代码无关。
    禁止查看自身的代码模块。

    # 环境
    - 当前工作目录：{workspace}
    - 工具中的相对路径都相对该目录解析

    # 工具
    - tool_bash: 执行 bash 命令（ls、grep、find 等）
    - tool_read: 读取文件内容
    - tool_write: 新建文件，不能覆盖已存在的文件

    # 规则
    - 用 tool_bash 做列目录、搜索、查找文件这类操作
    - 用 tool_read 查看文件，不要用 cat 或 sed
    - 禁止修改现有文件，不要用 bash 写入或删除文件（>、>>、sed -i、tee、rm、mv 等）
    - 需要修改现有代码时不要动文件，直接在回复里给出 unified diff 补丁（用 ```diff 围栏，带文件路径和 @@ 行号），并说明每处改动的理由
    - 只有用户明确要求新增模块时才用 tool_write 生成新文件，文件名不能与现有文件重复
    - 禁止使用 git add、git commit、git push 命令
    - 生成新文件后用 tool_read 确认内容
    - 行动前简要说明当前的理解和下一步计划
    - 保持简洁
    - 处理文件时清晰地显示文件路径

    # 代码风格
    - 遵循项目现有的代码风格，不要随意改变
    - 不引入不必要的抽象，YAGNI
    - 只在非显而易见的逻辑处写简短注释
    - 不要无理由地改变与任务无关的代码
''').strip()

llm_with_tools = llm.bind_tools(register.tools)

tools_map = {t.name: t for t in register.tools}

system_message = SystemMessage(
    content=system_prompt.format(workspace=settings.WORKSPACE)
)


def run(user_input: str, memory: ShortTerm, max_steps: int = 50) -> str:
    memory.add(HumanMessage(content=user_input))

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
            except ToolAbort:
                raise
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
