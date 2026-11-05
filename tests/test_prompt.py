from langchain_core.messages import AIMessage

from src import agent, settings
from src.core.memory import ShortTerm


class _FakeLLM:
    """记录收到的消息，直接返回最终回答"""

    def __init__(self):
        self.messages = []

    def invoke(self, messages):
        self.messages = messages
        return AIMessage(content='ok', tool_calls=[])


def test_system_message_follows_current_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'WORKSPACE', tmp_path)
    fake = _FakeLLM()
    monkeypatch.setattr(agent, 'llm_with_tools', fake)

    agent.run('hi', ShortTerm())

    assert str(tmp_path) in fake.messages[0].content
