class ToolAbort(Exception):
    """工具主动中止本轮，消息直接展示给用户，不回传给大模型"""

    pass
