import logging

from src.core.errors import ToolAbort
from src.core.logger import setup_logger
from src.core.memory import ShortTerm
from src import agent

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logger()

    print('* An agentic tool that lives in your terminal.')
    print('* Press /exit to quit, /clear to clear memory')

    memory = ShortTerm()

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
            print('* Memory cleared. New conversation started.')
            continue

        try:
            result = agent.run(user_input, memory)
        except ToolAbort as e:
            print(f'● {e}')
            print('\n* Bye！')
            break
        except Exception:
            logger.exception('this request failed')
            print('● 本次请求失败，详情见日志记录')
            continue

        print(f'● {result}')
