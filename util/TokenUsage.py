"""
Token 用量追踪。

TokenUsage    → 单次 API 调用的 Token 消耗（输入 + 输出）
UsageTracker  → 会话级累积统计 + 费用估算
"""

from dataclasses import dataclass


@dataclass
class TokenUsage:
    """单次 API 调用的 Token 用量。

    对应 API 响应中的 usage 字段：
        {"prompt_tokens": N, "completion_tokens": M, "total_tokens": N+M}
    """
    prompt_token: int = 0       # 输入消耗的 Token（System Prompt + 历史消息 + 用户输入）
    completion_token: int = 0   # 输出消耗的 Token（AI 生成的回复）

    @property
    def total(self) -> int:
        """总 Token 消耗"""
        return self.prompt_token + self.completion_token


# ================================================================
# 各模型价格（元 / 百万 Token）
# 后续加入新模型时只需在此处添加一行
# ================================================================
PRICING = {
    "deepseek": {"input": 1.0, "output": 2.0},
    "glm":      {"input": 1.0, "output": 2.0},
}
DEFAULT_PRICING = {"input": 1.0, "output": 2.0}


class UsageTracker:
    """会话级用量追踪器 —— 记录每次调用的 Token 消耗并计算费用。

    使用方式：
        tracker = UsageTracker()
        tracker.record(usage)          # 每次 API 调用后记录
        print(tracker.summary(model))  # 打印统计报告
    """

    def __init__(self):
        self.total_prompt: int = 0
        self.total_completions: int = 0
        self.total_calls: int = 0

    def record(self, usage: 'TokenUsage'):
        """记录一次 API 调用的 Token 消耗。

        Args:
            usage: 从 API 响应中提取的 TokenUsage 对象
        """
        self.total_prompt += usage.prompt_token
        self.total_completions += usage.completion_token
        self.total_calls += 1

    def summary(self, model: str = "") -> str:
        """生成用量统计报告。

        根据模型名前缀自动匹配价格表，计算预估费用。

        Args:
            model: 当前使用的模型名（用于匹配定价）

        Returns:
            格式化的用量统计字符串
        """
        # 根据模型前缀匹配价格
        pricing = DEFAULT_PRICING
        for prefix, price in PRICING.items():
            if model.startswith(prefix):
                pricing = price
                break

        input_cost = self.total_prompt / 1_000_000 * pricing["input"]
        output_cost = self.total_completions / 1_000_000 * pricing["output"]

        lines = ["📊 当前会话用量统计"]
        if model:
            lines.append(f"  模型: {model}")
        lines += [
            f"  总调用次数: {self.total_calls}",
            f"  输入 Token: {self.total_prompt:,}（约 ¥{input_cost:.4f}）",
            f"  输出 Token: {self.total_completions:,}（约 ¥{output_cost:.4f}）",
            f"  Token 合计: {self.total_prompt + self.total_completions:,}",
            f"  💰 预估费用: ¥{input_cost + output_cost:.4f}",
        ]
        return "\n".join(lines)
