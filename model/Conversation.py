"""
对话管理 —— 维护消息历史 + 上下文窗口截断。

核心认知：LLM 是无状态的，每次请求需要把全部历史一起发送。
对话越长 → 每次消耗的 Token 越多 → 费用越高、响应越慢。
因此需要 get_context() 截断历史消息。
"""

from pydantic import BaseModel
from model.Message import Message


class Conversation(BaseModel):
    """一次完整的对话状态。

    Attributes:
        messages:      历史消息列表（user 和 assistant 交替）
        model:         当前使用的模型名
        system_prompt: System Prompt，定义 AI 的角色和行为
    """

    messages: list[Message] = []
    model: str = "deepseek"
    system_prompt: str = ""

    # ================================================================
    # 消息管理
    # ================================================================

    def add(self, role: str, content: str):
        """追加一条消息到历史。

        Args:
            role:    "user" / "assistant" / "system"
            content: 消息正文
        """
        self.messages.append(Message(role=role, content=content))

    # ================================================================
    # 上下文组装
    # ================================================================

    def get_context(self, max_messages: int = 20) -> list[dict]:
        """组装发送给 API 的消息列表。

        做两件事：
            1. System Prompt 放在数组最前面（API 规范要求）
            2. 只取最近 max_messages 条历史（防止上下文超出窗口）

        Args:
            max_messages: 最多携带的历史消息条数，默认 20

        Returns:
            API 格式的消息列表，可直接放入请求体的 messages 字段
        """
        api_messages = [{"role": "system", "content": self.system_prompt}]
        for m in self.messages[-max_messages:]:   # 只取最近的 N 条
            api_messages.append({"role": m.role, "content": m.content})
        return api_messages

    def clear(self):
        self.messages = []
