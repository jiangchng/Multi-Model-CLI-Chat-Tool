from datetime import datetime

from pydantic import Field

from pydantic import BaseModel

"""
       一次聊天消息。
       发送方和内容
       role 的取值（OpenAI/DeepSeek 标准）：
         - "system"    : 系统指令，定义 AI 的行为
         - "user"      : 用户说的话
         - "assistant" : AI 的回复
       """
class Message(BaseModel):

    # 角色
    role: str
    # 内容
    content: str
    # 对话时间
    timestamp: datetime = Field(default_factory=datetime.now)
    # default_factory=datetime.now 而不是 default=datetime.now
    # 区别：
    #   default=datetime.now     → 所有 Message 共用一个时间（定义时求值一次）
    #   default_factory=datetime.now → 每条 Message 创建时重新求值 ✅