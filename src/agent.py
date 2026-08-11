import json
import textwrap

from loguru import logger

from src.llm import client, model_name, common_kwargs
from src.tools import TOOLS, TOOLS_MAP
from src.memory import ShortTerm

system_prompt = textwrap.dedent('''
    # 角色
    你是一个在 AI 编码代理中运行的专家级编码助手。你通过读取文件、执行命令、编辑代码和编写新文件来帮助用户。

    # 可用工具
    - read: 读取文件内容，支持分页
    - write: 创建或覆写文件
    - edit: 精确字符串替换（oldText 必须唯一、不重叠，所有编辑基于原始文件）
    - bash: 执行 shell 命令（ls、grep、find 等）
    - grep: 按模式搜索文件内容（支持正则、glob 过滤、上下文行）
    - find: 按 glob 模式查找文件（支持 ** 递归）
    - ls: 列出目录内容

    # 工作方式
    1. 先理解用户的需求，不清楚时主动提问
    2. 用 find 了解项目文件结构
    3. 用 grep 搜索关键代码，用 read 阅读相关文件
    4. 用小范围的 edit 做精确修改；全新文件或完整重写用 write
    5. 用 bash 执行测试、构建、git 等命令

    # 工具使用指南
    - 用 edit 做精确修改——edits[].oldText 必须精确匹配原文件
    - 修改同一文件多处不连续位置时，在一次 edit 调用中使用多个 edits[]，不要多次调用 edit
    - 不要包含重叠或嵌套的 edit；相邻修改请合并为一个 edit
    - 保持 edits[].oldText 尽可能短，同时确保在文件中唯一
    - 用 write 只用于创建新文件或完整重写
    - 读文件时检查文件大小，大文件用 offset/limit 分页

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
            logger.exception('LLM 调用失败，第[%s]轮', step)
            return f'错误：LLM 调用失败（第{step}轮），请检查 API 配置或网络连接'

        response_msg = response.choices[0].message.to_dict()

        memory.add(response_msg)

        tool_calls = response_msg.get('tool_calls')
        if not tool_calls:
            logger.info(f'无需工具调用，第[{step}]轮结束')
            return response_msg.get('content') or ''

        logger.info(f'工具调用第[{step + 1}]轮')

        for tc in tool_calls:
            func_name = tc['function']['name']
            tool_func = TOOLS_MAP.get(func_name)
            if tool_func is None:
                logger.warning(f'未知工具: {func_name}')
                continue

            try:
                func_args = json.loads(tc['function']['arguments'])
            except json.JSONDecodeError:
                logger.warning(f'工具参数解析失败: {tc["function"]["arguments"]}')
                continue

            logger.info(f'执行工具: {func_name}，参数: {func_args}')

            try:
                result = tool_func(**func_args)
            except Exception:
                logger.exception(f'工具执行失败: {func_name}')
                result = f'工具执行失败: {func_name}'

            logger.info(f'工具结果: {str(result)[:100]}')

            memory.add({
                'role': 'tool',
                'tool_call_id': tc['id'],
                'content': str(result),
            })

    logger.warning(f'工具调用达到上限 {max_steps} 轮，强制总结')

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
        logger.exception('LLM 总结调用失败')
        return '错误：LLM 调用失败，无法生成总结'

    response_msg = response.choices[0].message.to_dict()

    memory.add(response_msg)

    return response_msg.get('content') or ''
