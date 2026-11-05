import pytest

from src import main as main_mod
from src.core.errors import ToolAbort


def test_tool_abort_exits_program(monkeypatch):
    calls = []

    def fake_input(_prompt):
        calls.append(1)
        return '读 big.txt'

    def fake_run(_user_input, _memory):
        raise ToolAbort('文件含超长单行，禁止读取')

    monkeypatch.setattr('builtins.input', fake_input)
    monkeypatch.setattr(main_mod.react_agent, 'run', fake_run)

    main_mod.main()

    assert len(calls) == 1
