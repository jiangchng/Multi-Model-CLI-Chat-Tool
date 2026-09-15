"""
消息和对话的数据模型 —— 项目的"领域层"。

Message  → 单条聊天消息（谁说的、说了什么、什么时候说的）
Conversation → 一次完整对话（消息列表 + System Prompt + 模型名）
"""

from datetime import datetime
from pydantic import BaseModel, Field


class Message(BaseModel):
    """单条聊天消息。

    对应 OpenAI/DeepSeek API 中 messages 数组的一项。

    role 的取值（OpenAI 标准）：
        - "system"    : 系统指令，定义 AI 的行为边界
        - "user"      : 用户说的话
        - "assistant" : AI 的回复
    """

    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    # default_factory=datetime.now  → 每条消息创建时重新求值
    # default=datetime.now          → 所有消息共用一个时间（定义时求值一次）❌
