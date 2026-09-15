"""
工具模块 —— 注册所有内置工具。

每个工具是一个纯函数 + JSON Schema 定义，
通过 ToolRegistry.register() 注册后，LLM 就能自动调用它们。

目前支持的工具：
    - get_weather   天气查询（模拟数据）
    - calculator    安全计算器（白名单 eval）
"""

from tools.ToolRegistry import ToolRegistry
from tools.calculator import calculator
from tools.weather import get_weather


def register_all_tools(registry: ToolRegistry):
    """向注册表添加所有内置工具。

    添加新工具的步骤：
        1. 在 tools/ 下新建一个 .py 文件，实现处理函数
        2. 在这里 import，然后 registry.register(...)
    """

    # ---- 工具 1：天气查询 ----
    registry.register(
        name="get_weather",
        description="获取指定城市的实时天气信息",
        parameters={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如：北京、上海、深圳、杭州",
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "温度单位，默认 celsius",
                },
            },
            "required": ["city"],
        },
        handler=get_weather,
    )

    # ---- 工具 2：计算器 ----
    registry.register(
        name="calculator",
        description="执行数学计算，支持基本运算符 (+ - * / ** %) 和常用数学函数 "
                    "(sqrt, sin, cos, log, abs, pi, e 等)",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，例如: (3+5)*2, sqrt(16), sin(pi/2)",
                },
            },
            "required": ["expression"],
        },
        handler=calculator,
    )
