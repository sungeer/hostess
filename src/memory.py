from langchain_core.messages import BaseMessage


class ShortTerm:
    """短期记忆，保存对话历史，控制上限，防止超过 token 限制。"""

    def __init__(self, max_messages: int = 20) -> None:
        self.max_messages = max_messages
        self._messages: list[BaseMessage] = []

    def add(self, message: BaseMessage) -> None:
        self._messages.append(message)
        self._trim()

    def _trim(self) -> None:
        """超过上限时，丢掉最旧的消息。"""
        if len(self._messages) <= self.max_messages:
            return
        self._messages.pop(0)

    def get_messages(self) -> list[BaseMessage]:
        return list(self._messages)

    def clear(self) -> None:
        """清空全部历史（开始新对话时使用）。"""
        self._messages = []
