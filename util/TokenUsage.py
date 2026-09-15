from dataclasses import dataclass


@dataclass
class TokenUsage:
    prompt_token: int = 0
    completion_token: int = 0

    @property
    def total(self) -> int:
        return self.prompt_token + self.completion_token


# 各模型价格（元 / 百万 Token）
PRICING = {
    "deepseek": {"input": 1.0, "output": 2.0},
    "glm":      {"input": 1.0, "output": 2.0},
}
DEFAULT_PRICING = {"input": 1.0, "output": 2.0}


class UsageTracker:
    """会话级用量追踪器，记录每次调用的 Token 消耗并计算费用。"""

    def __init__(self):
        self.total_prompt: int = 0
        self.total_completions: int = 0
        self.total_calls: int = 0

    def record(self, usage: TokenUsage):
        self.total_prompt += usage.prompt_token
        self.total_completions += usage.completion_token
        self.total_calls += 1

    def summary(self, model: str = "") -> str:
        # 根据模型前缀匹配价格
        pricing = DEFAULT_PRICING
        for prefix, price in PRICING.items():
            if model.startswith(prefix):
                pricing = price
                break

        input_cost = self.total_prompt / 1_000_000 * pricing["input"]
        output_cost = self.total_completions / 1_000_000 * pricing["output"]

        lines = [
            "📊 当前会话用量统计",
        ]
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
