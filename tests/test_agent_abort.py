import pytest
from langchain_core.messages import AIMessage

from src import settings
from src.agents import react_agent
from src.core.errors import ToolAbort
from src.core.memory import ShortTerm


@pytest.fixture(autouse=True)
def _workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'WORKSPACE', tmp_path)


class _FakeLLM:
    """只返回一次 tool_calls，模拟大模型要求读取超长单行文件"""

    def __init__(self, tool_calls):
        self._tool_calls = tool_calls

    def invoke(self, _messages):
        return AIMessage(content='', tool_calls=self._tool_calls)


def test_tool_abort_breaks_out(tmp_path, monkeypatch):
    big = tmp_path / 'big.txt'
    big.write_text('x' * 2001, encoding='utf-8')

    tool_calls = [
        {'name': 'tool_read', 'args': {'file_path': str(big)}, 'id': 'c1'},
        {'name': 'tool_read', 'args': {'file_path': str(big)}, 'id': 'c2'},
    ]
    monkeypatch.setattr(react_agent, 'llm_with_tools', _FakeLLM(tool_calls))

    memory = ShortTerm()
    with pytest.raises(ToolAbort):
        react_agent.run('读一下 big.txt', memory)
