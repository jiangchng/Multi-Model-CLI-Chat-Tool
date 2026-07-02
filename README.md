# DeepSeek Chat

命令行 AI 聊天工具 —— 支持多轮对话、流式输出、多模型切换、对话持久化。

基于 DeepSeek API（OpenAI 兼容格式），纯 Python 实现，适合新手学习 LLM 应用开发。

## 功能

- **多轮对话** — 保持上下文，AI 记住之前说了什么
- **流式输出** — 逐字打印，即时反馈（SSE 协议）
- **多模型切换** — DeepSeek V3（快速）/ R1（深度推理）/ OpenAI 兼容
- **System Prompt** — 自定义 AI 人设
- **对话持久化** — 保存为 JSON，随时加载继续
- **网络容错** — 指数退避自动重试

## 架构

```
ChatApp（控制层：命令路由 + 主循环）
├── Settings      — 配置管理（.env → Pydantic）
├── Conversation  — 对话状态（消息列表 + System Prompt）
├── Message       — 单条消息（role + content + timestamp）
└── LLMClient     — API 通信（httpx + SSE 流式解析）
```

读码入口：[ChatApp.py](ChatApp.py) → `class ChatApp.run()`

## 环境要求

- Python ≥ 3.9
- DeepSeek API Key（[免费注册](https://platform.deepseek.com)，新用户送 500 万 token）

## 安装

```bash
# 1. 进入项目目录
cd deepseek-chat

# 2. 创建虚拟环境（Python 3.9+）
python -m venv .venv

# 3. 激活虚拟环境
#    Windows:
.venv\Scripts\activate
#    macOS / Linux:
source .venv/bin/activate

# 4. 安装依赖
pip install httpx pydantic pydantic-settings
```

## 配置

在项目根目录创建 `.env` 文件：

```ini
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

获取 Key：登录 [platform.deepseek.com](https://platform.deepseek.com) → API Keys → 创建。

## 运行

```bash
python ChatApp.py
```

```
🤖 DeepSeek Chat | 模型: deepseek-chat | /help 查看帮助
--------------------------------------------------

你: 你好
AI: 你好！有什么可以帮助你的吗？

你: 用一句话解释什么是闭包
AI: 闭包是一个函数捕获并记住了其外部作用域的变量，
即使在外部函数执行完毕后仍然可以访问这些变量。

你:
```

## 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/help` | 显示帮助 | |
| `/model <name>` | 切换模型 | `/model deepseek-reasoner` |
| `/system <prompt>` | 设置 System Prompt | `/system 你是毒舌代码审查员` |
| `/clear` | 清空对话（保留 System Prompt） | |
| `/save <name>` | 保存对话到 JSON | `/save java-interview` |
| `/load <name>` | 从 JSON 加载对话 | `/load java-interview` |
| `/history` | 查看消息列表 | |
| `/exit` | 退出程序 | |

### 可用模型

| 模型名 | 说明 |
|--------|------|
| `deepseek-chat` | DeepSeek V3，快速对话，适合日常使用 |
| `deepseek-reasoner` | DeepSeek R1，深度推理，可见思维链 |
| `gpt-4o` | OpenAI GPT-4o（需自行配置 OpenAI API Key） |

## 项目结构

```
deepseek-chat/
├── .env                      # API Key（不提交到 Git）
├── .gitignore
├── pyproject.toml             # 项目元数据
├── README.md
├── ChatApp.py                 # 主程序入口
├── config/
│   ├── __init__.py
│   └── Settings.py            # 配置类（读取 .env）
├── model/
│   ├── __init__.py
│   ├── Message.py             # 消息模型
│   └── Conversation.py        # 对话模型（消息管理）
└── client/
    ├── __init__.py
    └── LLMClient.py           # LLM API 客户端（流式 + 重试）
```

## API 原理

### 请求

```
POST https://api.deepseek.com/v1/chat/completions
Authorization: Bearer <your-key>
Content-Type: application/json

{
  "model": "deepseek-chat",
  "messages": [
    {"role": "system", "content": "你是..."},
    {"role": "user", "content": "你好"}
  ],
  "stream": true,
  "temperature": 0.7,
  "max_tokens": 4096
}
```

### 流式响应（SSE）

```
data: {"choices":[{"delta":{"content":"你"},"index":0}]}

data: {"choices":[{"delta":{"content":"好"},"index":0}]}

data: {"choices":[{"delta":{"content":"！"},"index":0}]}

data: {"choices":[{"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

每行以 `data: ` 开头，`[DONE]` 表示结束。文字在 `choices[0].delta.content` 中逐块返回。

### 多轮对话

每次请求把**全部历史消息**一起发送：

```
第 1 轮：[system, user:"你好"]
第 2 轮：[system, user:"你好", assistant:"你好！", user:"我叫小明"]
第 3 轮：[system, ...前两轮..., user:"我叫什么？"]  → AI: "你叫小明"
```

为避免上下文过长，`Conversation.get_context()` 默认只取最近 20 条消息。

## 常见问题

**Q: 运行报 `ModuleNotFoundError`？**

```bash
pip install httpx pydantic pydantic-settings
```

**Q: 报 `401 Unauthorized`？**

检查 `.env` 文件是否在项目根目录，格式是否正确（没有引号、没有空格）：
```
DEEPSEEK_API_KEY=sk-xxx
```

**Q: 流式输出卡住不动？**

网络问题。等 30 秒看是否自动恢复，或 Ctrl+C 重试。

**Q: 对话越来越慢？**

消息历史太长了。用 `/clear` 清空，或减小 `Conversation.py` 中 `get_context(max_messages=20)` 的值。

## 技术栈

| 组件 | 用途 |
|------|------|
| `httpx` | 异步 HTTP 客户端 |
| `pydantic` | 数据校验 + 序列化 |
| `pydantic-settings` | 配置管理（.env） |
| `asyncio` | 异步 IO |
| `json` | SSE 数据解析 |

## 学习路径

本项目是「AI 应用开发学习路线」第一阶段的项目。完整路线：

1. ✅ **第一阶段** — Python 速成 + CLI 聊天工具（本项目）
2. **第二阶段** — Prompt Engineering + Function Calling + 结构化输出
3. **第三阶段** — RAG 检索增强生成（知识库问答）
4. **第四阶段** — AI Agent 开发
5. **第五阶段** — 工程化与生产部署
6. **第六阶段** — 前端与全栈

## License

MIT
