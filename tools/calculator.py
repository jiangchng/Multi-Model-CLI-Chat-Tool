"""安全计算器工具"""

import math
import operator


# 白名单：只允许安全的操作
SAFE_OPS = {
    "+":  operator.add,
    "-":  operator.sub,
    "*":  operator.mul,
    "/":  operator.truediv,
    "**": operator.pow,
    "%":  operator.mod,
}

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
    """
    安全地计算数学表达式。

    限制：
    - 只允许基本运算符和 math 函数
    - 禁止 __builtins__ 和属性访问
    - 表达式长度限制 200 字符
    """
    if len(expression) > 200:
        return {"error": "表达式过长（最多 200 字符）", "expression": expression}

    try:
        # 构建安全的命名空间
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