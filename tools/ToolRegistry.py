"""
工具注册与执行中心。

每个 Tool 由两部分组成：
  1. 定义（JSON Schema）→ 发给 LLM，告诉它"我能做什么"
  2. 处理器（Callable）  → LLM 决定调用时，实际执行的 Python 函数
"""

import asyncio
import json
from typing import Callable


class ToolRegistry:
    """工具注册表 —— 管理所有可用工具的注册、查询和执行。

    使用方式：
        registry = ToolRegistry()
        registry.register("get_weather", "获取天气", {...}, handler)
        tools = registry.get_tools()           # → 传给 LLM API 的 tools 字段
        result = await registry.execute("get_weather", {"city": "北京"})
    """

    def __init__(self):
        self._tools: dict[str, dict] = {}        # name → tool 定义（JSON Schema）
        self._handlers: dict[str, Callable] = {}  # name → 实际执行函数

    @property
    def count(self) -> int:
        """已注册的工具数量"""
        return len(self._tools)

    # ================================================================
    # 注册
    # ================================================================

    def register(self, name: str, description: str, parameters: dict, handler: Callable):
        """注册一个工具。

        Args:
            name:        工具名（必须唯一，LLM 用这个名字来调用）
            description: 工具的功能描述（LLM 据此判断何时调用该工具）
            parameters:  JSON Schema 格式的参数定义
            handler:     实际执行函数，接收关键字参数，返回 dict / str

        Example:
            registry.register(
                name="calculator",
                description="执行数学计算",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "数学表达式"}
                    },
                    "required": ["expression"],
                },
                handler=calculator,
            )
        """
        self._tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
        self._handlers[name] = handler

    # ================================================================
    # 查询
    # ================================================================

    def get_tools(self) -> list[dict]:
        """返回所有工具定义 —— 直接用于 API 请求的 tools 字段"""
        return list(self._tools.values())

    def list_tools(self) -> list[str]:
        """列出所有已注册的工具（给人看的格式化字符串）"""
        results = []
        for name, tool in self._tools.items():
            description = tool["function"]["description"]
            results.append(f"  {name:20s} — {description}")
        return results

    # ================================================================
    # 执行
    # ================================================================

    async def execute(self, name: str, arguments: dict) -> str:
        """执行指定工具，返回 JSON 字符串。

        Args:
            name:      工具名称
            arguments: 参数字典（已从 LLM 返回的 tool_calls 中解析）

        Returns:
            工具执行结果的 JSON 字符串。出错时返回 {"error": "..."}。

        执行流程：
            查找 handler → 调用 handler(**arguments)
            → 如果是协程则 await → 统一序列化为 JSON 字符串
        """
        if name not in self._handlers:
            return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)

        try:
            handler = self._handlers[name]
            res = handler(**arguments)

            # 支持异步处理器
            if asyncio.iscoroutine(res):
                res = await res

            # 统一返回 JSON 字符串
            if isinstance(res, str):
                return res
            return json.dumps(res, ensure_ascii=False)

        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
