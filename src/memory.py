class ShortTerm:

    def __init__(self) -> None:
        self._messages = []

    def add(self, message) -> None:
        """添加一条消息"""
        self._messages.append(message)

    def get_messages(self):
        """返回消息列表的副本"""
        messages = list(self._messages)
        return messages

    def drop_last(self) -> None:
        """撤掉最后一条消息
        请求失败时用来回收那条还没得到回复的用户提问
        """
        if self._messages:
            self._messages.pop()

    def clear(self) -> None:
        """清空全部历史
        开始新对话时使用
        """
        self._messages.clear()
