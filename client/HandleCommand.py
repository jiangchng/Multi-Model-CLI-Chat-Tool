import datetime
import json

from config.Settings import Settings
from model.Conversation import Conversation
from tools import ToolRegistry


def print_help():
    """打印命令帮助"""
    print("""
    ──────────────────────────────────────────────────────
                     智能 CLI 助手 命令
    ──────────────────────────────────────────────────────
    /model <名称>      切换模型
    /system <提示词>    设置 System Prompt（AI 人设）
    /prompt <名称>     切换 Prompt 模板（代码审查/苏格拉底导师/...） 
    /clear             清空对话（保留 System Prompt）
    /save <名称>        保存当前对话到 JSON 文件
    /load <名称>        从 JSON 文件加载对话
    /export <名称>      导出对话为 Markdown 文件
    /history           查看当前对话的消息列表
    /tools             列出所有注册的工具
    /analyze <文本>     结构化分析文本
    /usage             查看当前会话 Token 用量和费用
    /help              显示本帮助
    /exit              退出程序
    ──────────────────────────────────────────────────────
    """, end="")


async def handle_command(cmd: str, conversation: Conversation, setting: Settings, tools: ToolRegistry) -> bool:
    """处理 / 开头的命令。

    Args:
        cmd: 用户输入的完整命令，如 "/model deepseek-reasoner"

    Returns:
        True  → 继续运行主循环
        False → 退出程序（/exit）
        :param tools:
        :param setting:
        :param cmd:
        :param conversation:
    """
    parts = cmd.split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else None

    match command:

        # ---- 基础命令 ----
        case "/exit":
            print("再见！")
            return False

        case "/help":
            print_help()

        case "/model":
            if arg:
                if arg.startswith("deepseek"):
                    conversation.model = setting.models_name[0]
                elif arg.startswith("glm"):
                    conversation.model = setting.models_name[1]
                else:
                    print("没有相关模型")
                print(f"已切换到模型: {arg}")
            else:
                print(f"当前模型: {conversation.model}")

        case "/system":
            if arg:
                conversation.system_prompt = arg
                print(f"System Prompt 已更新: {arg}")
            else:
                print(f"当前 System Prompt: {conversation.system_prompt}")

        case "/clear":
            conversation.clear()
            print("对话已清空。System Prompt 已保留。")

        # ---- 文件命令 ----
        case "/save":
            name = arg or f"chat_{datetime.now():%Y%m%d_%H%M%S}"
            path = setting.history_dir / f"{name}.json"
            path.write_text(
                conversation.model_dump_json(indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"已保存到: {path}")

        case "/load":
            if not arg:
                print("用法: /load <文件名>（不含 .json 后缀）")
                return True
            path = setting.history_dir / f"{arg}.json"
            if not path.exists():
                files = list(setting.history_dir.glob("*.json"))
                if files:
                    print(f"文件不存在。可用的文件: {[f.stem for f in files]}")
                else:
                    print(f"文件不存在: {path}")
                return True
            data = json.loads(path.read_text(encoding="utf-8"))
            conversation = Conversation(**data)
            print(f"已加载: {arg}（{len(conversation.messages)}条消息）")

        case "/export":
            name = arg or f"chat_{datetime.now():%Y%m%d_%H%M%S}"
            path = setting.history_dir / f"{name}.md"

            lines = [
                f"# 对话导出 — {datetime.now():%Y-%m-%d %H:%M}",
                f"模型: {conversation.model}",
                f"System Prompt: {conversation.system_prompt}",
                "",
                "---",
                "",
            ]
            for msg in conversation.messages:
                role_label = {"user": "🧑 你", "assistant": "🤖 AI", "system": "⚙️ 系统"}
                label = role_label.get(msg.role, msg.role)
                lines.append(f"### {label}")
                lines.append("")
                lines.append(msg.content)
                lines.append("")

            path.write_text("\n".join(lines), encoding="utf-8")
            print(f"已导出到: {path}")

        case "/history":
            count = len(conversation.messages)
            print(f"共 {count} 条消息 | 模型: {conversation.model}")
            for i, msg in enumerate(conversation.messages):
                preview = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content
                print(f"  [{i}] {msg.role:10} | {preview}")

        # ---- 第二阶段命令 ----
        case "/tools":
            print(f"🔧 已注册 {tools.count} 个工具:")
            for line in tools.list_tools():
                print(line)

        # case "/analyze":
        #     if not arg:
        #         print("用法: /analyze <需要分析的文本>")
        #         return True
        #
        #     print("📊 正在分析...")
        #     try:
        #         client = self._get_tool_client()
        #         result = await client.ask_structured(
        #             prompt=arg,
        #             output_model=ArticleAnalysis,
        #             system_prompt="你是一个文章/文本分析专家。从给定内容中提取关键信息。",
        #             model=self.conversation.model,
        #         )
        #         print("\n📊 结构化分析结果:")
        #         print(result.model_dump_json(indent=2, ensure_ascii=False))
        #     except Exception as e:
        #         print(f"\n❌ 分析失败: {e}")

        case "/prompt":
            if not arg:
                print("📝 可用 Prompt 模板:")
                for line in self.prompt_library.list_prompts():
                    print(line)
                print("\n用法: /prompt <模板名>")
                return True

            tpl = self.prompt_library.get_prompt(arg)
            if tpl:
                # 使用 safe_substitute：未提供的变量保留占位符，不会崩溃
                self.conversation.system_prompt = tpl.render(
                    language="Java",
                    focus_points="- 线程安全\n- 空指针防护",
                    severity="🔴 致命",
                    code="（待用户粘贴代码）",
                    role="Java 后端开发工程师",
                    topic="Java 并发编程",
                    question="（待用户提问）",
                    context="技术讨论",
                )
                print(f"已切换到模板: {tpl.name} — {tpl.description}")
                print(f"System Prompt 预览: {self.conversation.system_prompt[:100]}...")
            else:
                print(f"未知模板: {arg}")
                print("可用模板:")
                for line in self.prompt_library.list_prompts():
                    print(line)

        case "/usage":
            print(self.usage_tracker.summary(self.conversation.model))

        case _:
            print(f"未知命令: {command}，输入 /help 查看帮助")

    return True
