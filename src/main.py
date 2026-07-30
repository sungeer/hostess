from src.logger import setup_logger
from src.agent import run_agent
from src.memory import ShortTerm


def main() -> None:
    setup_logger()

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
            print('Memory cleared. New conversation started.')
            continue

        result = run_agent(user_input, memory)

        print(f'Agent: {result}')
