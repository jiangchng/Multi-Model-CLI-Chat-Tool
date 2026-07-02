import asyncio
import json

import httpx

from config.Settings import Settings
from model.Conversation import Conversation

"""负责与 LLM API 通信，支持 DeepSeek 和 OpenAI 兼容接口"""
class LLMClient:

    # 初始化
    def __init__(self, settings: Settings):
        # 客户端配置
        self.settings = settings
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0)
        )
    def _resolve_provider(self, model: str) -> tuple[str, str, str]:
        """根据模型名自动选择 API 服务商"""
        if model.startswith(("gpt-", "o1", "o3")):
            return ("openai", "https://api.openai.com", self.settings.deepseek_api_key)
        else:
            return ("deepseek", self.settings.deepseek_base_url, self.settings.deepseek_api_key)

    async def chat_stream(self, conversation: Conversation, max_retries: int = 3) -> str:
        provider, base_url, api_key = self._resolve_provider(conversation.model)
        messages = conversation.get_context()

        request_body = {
            "model": conversation.model,
            "messages": messages,
            "max_tokens": self.settings.max_tokens,
            "temperature": self.settings.temperature,
            "stream": True,
        }

        for attempt in range(max_retries):
            try:
                async with self.client.stream(
                    "POST",
                    f"{base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                # 返回的响应体
                ) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        raise RuntimeError(
                            f"API 返回 {response.status_code}: {error_body.decode()[:500]}"
                        )

                    full_response: list[str] = []
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
                        choices = chunk.get("choices", [])
                        if choices:
                            text = choices[0].get("delta", {}).get("content", "")
                            if text:
                                print(text, end="", flush=True)
                                full_response.append(text)

                    return "".join(full_response)

            except (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError) as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"\n⚠ 网络错误，{wait}s 后重试（{attempt+1}/{max_retries}）...")
                    await asyncio.sleep(wait)
                else:
                    raise RuntimeError(f"重试 {max_retries} 次后仍然失败: {e}")

    async def close(self):
        await self.client.aclose()
