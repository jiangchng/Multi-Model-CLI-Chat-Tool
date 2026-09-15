import json
from dataclasses import dataclass
from typing import TypeVar, Type

import httpx
from pydantic import BaseModel

from config.Settings import Settings
from model.Conversation import Conversation
from tools.ToolRegistry import ToolRegistry
from util.TokenUsage import TokenUsage

T = TypeVar("T", bound=BaseModel)


@dataclass
class ToolCallResult:
    """一次 Tool Use 调用的完整结果。

    Attributes:
        content:          最终给用户的文本回复
        tool_calls_made:  过程中调用了哪些工具（用于日志展示）
        usage:            本次调用链的累计 Token 消耗
    """
    content: str
    tool_calls_made: list[str]
    usage: TokenUsage | None


def _extract_usage(data: dict) -> TokenUsage | None:
    """从 API 响应中提取 usage 信息。"""
    if "usage" in data:
        u = data["usage"]
        return TokenUsage(
            prompt_token=u.get("prompt_tokens", 0),
            completion_token=u.get("completion_tokens", 0),
        )
    return None


class ToolUseClient:
    """封装 Tool Use 循环 + 结构化输出逻辑。

    需要一个 LLM Provider 实例和一个 ToolRegistry：
        client = ToolUseClient(provider, registry)
        result = await client.chat_stream_with_tools(messages, model)
    """

    MAX_TOOL_CALL_COUNT = 10  # 工具调用最大轮数（防无限循环）

    def __init__(self, settings: Settings, registry: ToolRegistry):
        self.settings = settings
        self.registry = registry

    # ================================================================
    # 内部方法
    # ================================================================

    def _build_request_body(
        self,
        model: str,
        messages: list[dict],
        with_tools: bool,
        tool_choice: str | None = "auto",
        response_format: dict | None = None,
        **kwargs,
    ) -> dict:
        """构造 API 请求体 —— 统一处理 tools / tool_choice / response_format。

        Args:
            model:           模型名
            messages:        消息列表
            with_tools:      是否携带 tools 定义
            tool_choice:     "auto" / "required" / "none"（DeepSeek 只支持字符串）
            response_format: {"type": "json_object"} 用于 JSON Mode
        """
        body = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.0),   # Tool Use 建议低温
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": False,
        }
        if with_tools and self.registry.count > 0:
            body["tools"] = self.registry.get_tools()
            if tool_choice:
                body["tool_choice"] = tool_choice
        if response_format:
            body["response_format"] = response_format
        return body

    # ================================================================
    # 1. 非流式 Tool Use 循环
    # ================================================================

    async def chat_with_tools(
        self, model: str, messages: list[dict],
        enable_tools: bool = True,
        **kwargs,
    ) -> ToolCallResult:
        """
        带 Tool Use 的非流式聊天。

        循环逻辑：
            1. 发送 messages + tools 定义
            2. 如果 LLM 返回 tool_calls → 执行工具 → 追加结果到 messages → 回到 1
            3. 如果 LLM 返回普通文本 → 结束，返回 ToolCallResult

        Args:
            model:        模型名
            messages:     消息列表（会被原地修改！追加 tool_calls 和 tool 结果）
            enable_tools: 是否启用工具

        Returns:
            ToolCallResult(content, tool_calls_made, usage)
        """
        tool_calls_made: list[str] = []
        total_usage = TokenUsage()

        for turn in range(self.MAX_TOOL_CALL_COUNT):
            body = self._build_request_body(
                model=model, messages=messages,
                with_tools=enable_tools,
                **kwargs,
            )

            response = await httpx.Client.post(
                f"{self.provider.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.provider.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            data = response.json()

            usage = _extract_usage(data)
            if usage:
                total_usage.prompt_token += usage.prompt_token
                total_usage.completion_token += usage.completion_token

            choice = data["choices"][0]
            msg = choice["message"]

            # ---- 情况 1：LLM 要调工具 ----
            if msg.get("tool_calls"):
                # 把 assistant 的 tool_calls 消息追加到对话历史
                messages.append({
                    "role": "assistant",
                    "content": msg.get("content") or "",
                    "tool_calls": msg["tool_calls"],
                })

                for tc in msg["tool_calls"]:
                    func_name = tc["function"]["name"]
                    func_args = json.loads(tc["function"]["arguments"])

                    print(f"\n🔧 调用工具: {func_name}({json.dumps(func_args, ensure_ascii=False)})")
                    tool_calls_made.append(func_name)

                    # 执行工具，结果作为 tool 角色消息追加
                    result = await self.registry.execute(func_name, func_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })
                continue  # 回到循环顶部，让 LLM 看到工具结果后再次判断

            # ---- 情况 2：LLM 直接文本回复（结束） ----
            return ToolCallResult(
                content=msg.get("content", ""),
                tool_calls_made=tool_calls_made,
                usage=total_usage,
            )

        # 超过最大循环轮数，强制终止
        return ToolCallResult(
            content="已达到最大工具调用轮数。",
            tool_calls_made=tool_calls_made,
            usage=total_usage,
        )

    # ================================================================
    # 2. 流式 + Tool Use 混合（主对话使用）
    # ================================================================

    async def chat_stream_with_tools(
        self,
        conversation: Conversation,
        enable_tools: bool = True,
        **kwargs,
    ) -> ToolCallResult:
        """
        流式聊天 + Tool Use 混合处理。

        和 chat_with_tools 的区别：
            - 流式输出文字（逐字打印）
            - Tool Call 的 name/arguments 也是分块到达的，需要状态机累积

        核心难点：tool_calls 在 SSE 流中逐块返回
            chunk 1: {"delta": {"tool_calls": [{"index": 0, "function": {"name": "get_"}}]}}
            chunk 2: {"delta": {"tool_calls": [{"index": 0, "function": {"name": "weather"}}]}}
            chunk 3: {"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\"ci"}}]}}
            ...
            我们需要把 name 和 arguments 各自拼接起来。
        """
        tool_calls_made: list[str] = []
        total_usage = TokenUsage()
        # 局部 messages —— 不直接污染 conversation.messages
        messages = conversation.get_context()

        for turn in range(self.MAX_TOOL_CALL_COUNT):
            body = {
                "model": conversation.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.0),
                "max_tokens": kwargs.get("max_tokens", 4096),
                "stream": True,
            }
            if enable_tools and self.registry.count > 0:
                body["tools"] = self.registry.get_tools()

            # ---- 状态机变量 ----
            content_buffer: list[str] = []           # 普通文字累积
            tool_call_buffers: dict[int, dict] = {}   # {index: {id, name, arguments}}
            current_tool_idx = -1                     # 当前处理的 tool_call index

            async with httpx.AsyncClient().stream(
                "POST",
                f"{self.settings.models_urls.get(conversation.model)}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.models_api_key.get(conversation.model)}",
                    "Content-Type": "application/json",
                },
                json=body,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break

                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    # 提取 usage（最终 chunk）
                    if "usage" in chunk:
                        u = chunk["usage"]
                        total_usage.prompt_token += u.get("prompt_tokens", 0)
                        total_usage.completion_token += u.get("completion_tokens", 0)

                    choices = chunk.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})

                    # ---- 分支 1：普通文字增量 ----
                    text = delta.get("content", "")
                    if text:
                        print(text, end="", flush=True)
                        content_buffer.append(text)
                        continue

                    # ---- 分支 2：Tool Call 增量 ----
                    tc_deltas = delta.get("tool_calls", [])
                    for tc in tc_deltas:
                        idx = tc.get("index", 0)

                        # 新的 tool_call 开始了
                        if idx != current_tool_idx:
                            current_tool_idx = idx
                            if idx not in tool_call_buffers:
                                tool_call_buffers[idx] = {
                                    "id": tc.get("id", ""),
                                    "name": "",
                                    "arguments": "",
                                }

                        buf = tool_call_buffers[idx]
                        func = tc.get("function", {})

                        # 累积 name 和 arguments（SSE 可能分多块发送）
                        if func.get("name"):
                            buf["name"] += func["name"]
                        if func.get("arguments"):
                            buf["arguments"] += func["arguments"]

            # ---- 流结束，判断是否有 tool_calls ----
            content = "".join(content_buffer)

            if tool_call_buffers:
                # 构造完整的 assistant tool_calls 消息
                tool_calls_msg = {
                    "role": "assistant",
                    "content": content or "",
                    "tool_calls": [],
                }

                for idx in sorted(tool_call_buffers.keys()):
                    buf = tool_call_buffers[idx]
                    tool_calls_msg["tool_calls"].append({
                        "id": buf["id"],
                        "type": "function",
                        "function": {
                            "name": buf["name"],
                            "arguments": buf["arguments"],
                        },
                    })

                # 追加到局部 messages（dict），不是 conversation.messages（Message 对象）
                messages.append(tool_calls_msg)

                # 执行所有工具调用
                for tc in tool_calls_msg["tool_calls"]:
                    func_name = tc["function"]["name"]
                    func_args = json.loads(tc["function"]["arguments"])

                    print(f"\n🔧 调用工具: {func_name}({json.dumps(func_args, ensure_ascii=False)})")
                    tool_calls_made.append(func_name)

                    result = await self.registry.execute(func_name, func_args)
                    messages.append({
                        "role": "tool",
                        "content": result,
                        "tool_call_id": tc["id"],
                    })

                continue  # 继续循环，让 LLM 基于工具结果生成回复

            # ---- 无 tool_calls：正常文本结束 ----
            return ToolCallResult(
                content=content,
                tool_calls_made=tool_calls_made,
                usage=total_usage,
            )

        return ToolCallResult(
            content="已达到最大工具调用轮数。",
            tool_calls_made=tool_calls_made,
            usage=total_usage,
        )

    # ================================================================
    # 3. 结构化输出（Pydantic + JSON Mode）
    # ================================================================

    async def ask_structured(
        self,
        prompt: str,
        output_model: Type[T],
        system_prompt: str = "你是一个数据提取专家。严格按照要求的 JSON 格式输出。",
        model: str = "deepseek-v4-pro",
        **kwargs,
    ) -> T:
        """
        通用结构化输出 —— 强制 LLM 返回指定 Pydantic 模型。

        原理：
            用 DeepSeek 的 JSON Mode（response_format: {type: "json_object"}）
            把 Pydantic 的 JSON Schema 注入 System Prompt，
            LLM 返回合法 JSON → json.loads → Pydantic 校验 → 返回类型安全的对象。

        为什么不直接解析 LLM 回复？
            Prompt 约束成功率 ~85%
            Tool Use 强制 成功率 ~99%
            JSON Mode     成功率 ~95%
            → 对 DeepSeek 来说 JSON Mode 是最兼容的选择

        用法：
            result = await client.ask_structured(
                prompt="分析这段文字...",
                output_model=ArticleAnalysis,
            )
            # result 是 ArticleAnalysis 实例，已通过 Pydantic 验证
            print(result.title, result.keywords)
        """
        schema = output_model.model_json_schema()
        schema_json = json.dumps(schema, indent=2, ensure_ascii=False)

        full_system = (
            f"{system_prompt}\n\n"
            f"你必须严格按照以下 JSON Schema 输出，只输出 JSON，不要有任何额外文字：\n"
            f"```json\n{schema_json}\n```"
        )

        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": prompt},
        ]

        response = await self.provider.client.post(
            f"{self.provider.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.provider.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.0),  # 结构化输出必须低温
                "max_tokens": kwargs.get("max_tokens", 4096),
                "response_format": {"type": "json_object"},     # DeepSeek JSON Mode
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        # Pydantic 自动校验类型 + 范围
        return output_model(**parsed)

    def close(self):
        httpx.AsyncClient.close()
