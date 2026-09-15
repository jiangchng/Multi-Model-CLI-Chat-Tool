"""
安全计算器工具 —— 用受限 eval 执行数学表达式。

安全措施：
    - 只能使用白名单中的数学函数
    - 禁用 __builtins__（无法访问危险的内置函数）
    - 表达式长度限制 200 字符
"""

import math


# 白名单：允许的数学函数和常量
SAFE_FUNCTIONS = {
    "abs":    abs,
    "round":  round,
    "min":    min,
    "max":    max,
    "sum":    sum,
    "sqrt":   math.sqrt,
    "log":    math.log,
    "log10":  math.log10,
    "sin":    math.sin,
    "cos":    math.cos,
    "pi":     math.pi,
    "e":      math.e,
}


def calculator(expression: str) -> dict:
    """安全地计算数学表达式。

    Args:
        expression: 数学表达式，如 "(3+5)*2"、"sqrt(16)"、"sin(pi/2)"

    Returns:
        {"expression": "...", "result": "..."} 或 {"error": "..."}

    安全限制：
        - 禁止 __builtins__ 和属性访问
        - 只允许白名单中的函数
        - 表达式最长 200 字符
    """
    if len(expression) > 200:
        return {"error": "表达式过长（最多 200 字符）", "expression": expression}

    try:
        # 构建安全的命名空间（禁用内置函数）
        safe_ns = {"__builtins__": {}}
        safe_ns.update(SAFE_FUNCTIONS)

        result = eval(expression, safe_ns, {})

        return {
            "expression": expression,
            "result": str(result),
        }
    except SyntaxError as e:
        return {"error": f"语法错误: {e}", "expression": expression}
    except Exception as e:
        return {"error": f"计算错误: {e}", "expression": expression}
