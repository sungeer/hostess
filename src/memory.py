from collections import deque

from langchain_core.messages import BaseMessage, ToolMessage


class ShortTerm:

    def __init__(self, max_messages: int = 100) -> None:
        self._messages: deque[BaseMessage] = deque(maxlen=max_messages)

    def add(self, message: BaseMessage) -> None:
        """添加一条消息
        超出上限时自动丢弃最旧的
        """
        self._messages.append(message)

    def get_messages(self) -> list[BaseMessage]:
        """返回消息列表的副本"""
        messages = list(self._messages)
        while messages and isinstance(messages[0], ToolMessage):
            messages.pop(0)
        return messages

    def clear(self) -> None:
        """清空全部历史
        开始新对话时使用
        """
        self._messages.clear()
