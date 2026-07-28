class ShortTerm:

    def __init__(self, max_messages: int = 100) -> None:
        self.max_messages = max_messages
        self._messages: list[dict] = []

    def add(self, message: dict) -> None:
        """添加一条消息
        超出上限时自动丢弃最旧的
        """
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]

    def get_messages(self) -> list[dict]:
        """返回消息列表的副本"""
        return list(self._messages)

    def clear(self) -> None:
        """清空全部历史
        开始新对话时使用
        """
        self._messages = []
