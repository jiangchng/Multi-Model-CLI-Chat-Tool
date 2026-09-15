import asyncio
import json
from typing import Callable


class ToolRegistry:

    def __init__(self):
        self._tools = dict[str, dict] = {}  # name → tool 定义
        self._handlers: dict[str, Callable] = {}  # name → 实际函数

    def registry(self, name: str, description: str, parameters: dict, handler: Callable):
        self._tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            }
        }
        self._handlers[name] = handler

    def get_definitions(self) -> list[dict]:
        return list(self._tools.values())

    async def execute(self, name: str, arguments: dict) -> str:
        if name not in self._handlers:
            return f"错误"

        handler = self._handlers.get(name)
        result = handler(**arguments)
        if asyncio.iscoroutine(result):
            result = await result

        return json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result