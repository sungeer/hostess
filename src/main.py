import logging

from src.logger import setup_logger
from src.memory import Memory
from src import agent

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logger()

    print('* An agentic tool that lives in your terminal.')
    print('* Press /exit to quit, /clear to clear memory')

    memory = Memory()

    while True:
        try:
            user_input = input('\n> ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\n* Bye！')
            break

        if not user_input:
            continue

        if user_input.lower() in ('/exit', '/q', '/quit'):
            print('\n* Bye！')
            break

        if user_input.lower() == '/clear':
            memory.clear()
            print('* 记忆已清空，开始新对话')
            continue

        try:
            result = agent.run(user_input, memory)
        except Exception:
            logger.exception('本次请求失败')
            print('· 本次请求失败，详情见日志记录')
            continue

        print(f'· {result}')
