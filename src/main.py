import logging

from src.agent import run_agent
from src.memory import ShortTerm


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print('* An agentic tool that lives in your terminal.')
    print('* Press /exit to quit, /clear to clear memory')

    memory = ShortTerm()

    while True:
        try:
            user_input = input('\nYou: ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nBye！')
            break

        if not user_input:
            continue

        if user_input.lower() in ('/exit', '/q', '/quit'):
            print('\nBye！')
            break

        if user_input.lower() == '/clear':
            memory.clear()
            print('记忆已清除，开始新对话。')
            continue

        result = run_agent(user_input, memory)

        print(f'Agent: {result}')
