import asyncio
import json
from datetime import datetime

from client.LLMClient import LLMClient
from config.Settings import Settings
from model.Conversation import Conversation


class ChatApp:
    def __init__(self):
        self.settings = Settings()
        self.llm = LLMClient(self.settings)
        self.conversation = Conversation(model=self.settings.default_model)
        self.settings.history_dir.mkdir(parents=True, exist_ok=True)

    def print_help(self):
        print("""
──────────────────────────────────────────────────────
                 DeepSeek Chat 命令                   
──────────────────────────────────────────────────────
/model <名称>      切换模型                           
    deepseek-chat         DeepSeek V4（快速对话）         
    OpenAI GPT-4o（需自行配置）  
/system <提示词>    设置 System Prompt（AI 人设）       
/clear             清空对话（保留 System Prompt）      
/save <名称>        保存当前对话到文件                  
/load <名称>        从文件加载对话                      
/history           查看当前对话的消息列表               
/help              显示本帮助                          
/exit              退出程序                            
──────────────────────────────────────────────────────
        """)

    async def handle_command(self, cmd: str) -> bool:
        """处理 / 开头的命令。返回 False 表示退出。"""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else None

        if command == "/exit":
            print("再见！")
            return False
        elif command == "/help":
            self.print_help()
        elif command == "/clear":
            self.conversation = Conversation(
                model=self.conversation.model,
                system_prompt=self.conversation.system_prompt,
            )
            print("对话已清空。System Prompt 已保留。")
        elif command == "/system":
            if arg:
                self.conversation.system_prompt = arg
                print(f"System Prompt 已更新: {arg}")
            else:
                print(f"当前 System Prompt: {self.conversation.system_prompt}")
        elif command == "/model":
            if arg:
                self.conversation.model = arg
                model_map = {
                    "deepseek-chat":     "DeepSeek V3 — 快速对话",
                    "deepseek-reasoner": "DeepSeek R1 — 深度推理",
                }
                desc = model_map.get(arg, "自定义模型（OpenAI 兼容）")
                print(f"已切换: {arg}（{desc}）")
            else:
                print(f"当前模型: {self.conversation.model}")
        elif command == "/save":
            name = arg or f"chat_{datetime.now():%Y%m%d_%H%M%S}"
            path = self.settings.history_dir / f"{name}.json"
            path.write_text(
                self.conversation.model_dump_json(indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"已保存到: {path}")
        elif command == "/load":
            if not arg:
                print("用法: /load <文件名>（不含 .json 后缀）")
                return True
            path = self.settings.history_dir / f"{arg}.json"
            if not path.exists():
                files = list(self.settings.history_dir.glob("*.json"))
                if files:
                    print(f"文件不存在。可用的文件: {[f.stem for f in files]}")
                else:
                    print(f"文件不存在: {path}")
                return True
            data = json.loads(path.read_text(encoding="utf-8"))
            self.conversation = Conversation(**data)
            print(f"已加载: {arg}（{len(self.conversation.messages)} 条消息）")
        elif command == "/history":
            count = len(self.conversation.messages)
            print(f"共 {count} 条消息 | 模型: {self.conversation.model}")
            for i, msg in enumerate(self.conversation.messages):
                preview = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content
                print(f"  [{i}] {msg.role:10} | {preview}")
        else:
            print(f"未知命令: {command}，输入 /help 查看帮助")

        return True

    async def run(self):
        print(f"🤖 DeepSeek Chat | 模型: {self.conversation.model} | /help 查看帮助")
        print("-" * 50)

        while True:
            try:
                user_input = input("\n你: ").strip()
                if not user_input:
                    continue

                if user_input.startswith("/"):
                    if not await self.handle_command(user_input):
                        break
                    continue

                self.conversation.add("user", user_input)
                print("AI: ", end="", flush=True)
                response = await self.llm.chat_stream(self.conversation)
                print()
                if response:
                    self.conversation.add("assistant", response)

            except KeyboardInterrupt:
                print("\n\n👋 再见！")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")

        await self.llm.close()


if __name__ == "__main__":
    app = ChatApp()
    asyncio.run(app.run())
