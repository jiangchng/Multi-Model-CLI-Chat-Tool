from pydantic import BaseModel
from model.Message import Message

"""
聊天记忆
多次对话后发送量会累积，可设置读取记录位置
"""
class Conversation(BaseModel):

    # 一次完整的对话状态
    messages: list[Message] = []
    # 模型名称
    model: str = "deepseek-chat"
    # 提示词
    system_prompt: str = "你是一个有帮助的AI助手。"

    def add(self, role: str, content: str):

        # 添加一条新消息到历史
        self.messages.append(Message(role=role, content=content))

    def get_context(self, max_messages: int = 20) -> list[dict]:

        # 组装发送给 API 的消息列表，System Prompt 放最前
        api_messages = [{"role": "system", "content": self.system_prompt}]
        # 在记录中取最近的20条记录
        for m in self.messages[-max_messages:]:
            # 放到请求体中
            api_messages.append({"role": m.role, "content": m.content})
        return api_messages
