import json
import re

from client import ToolUseClient
from config import Settings
from tools import ToolRegistry


class ReactAgent:
    MAX_STEPS = 10

    SYSTEM_PROMPT = """你是一个能使用工具的 AI Agent。请按照以下格式逐步解决问题：

## 可用工具
{tools}

## 回复格式（严格遵守）
Thought: <你的思考过程——分析当前状态、下一步该做什么>
Action: <工具名>
Action Input: <JSON 格式的参数>

当你获得足够信息后，用以下格式给出最终答案：
Thought: 信息收集完毕，可以回答用户问题了
Final Answer: <最终答案>

## 示例
用户: 北京今天天气怎么样？
Thought: 用户想知道北京天气，需要调用天气工具
Action: get_weather
Action Input: {{"city": "北京"}}
Observation: 北京今天晴，25°C
Thought: 已经获取到天气信息，可以回复了
Final Answer: 北京今天晴，气温25°C。"""

    def __init__(self, llm_client, tools_register):
        self.llm_client = llm_client
        self.tools = tools_register

    async def run(self, question: str, max_steps: int | None = None) -> dict:

        if max_steps is None:
            max_steps = ReactAgent.MAX_STEPS

        tools = "\n".join(
            f"- {name}: {defn['function']['description']}"
            for name, defn in self.tools._tools.items()
        )

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT.format(tools=tools)},
            {"role": "user", "content": question},
        ]

        steps = []
        for _ in range(max_steps):
            response = await self.llm_client.chat(messages, temperature=0.0)
            thought = self._extract(response, "Thought")
            action = self._extract(response, "Action")
            final_answer = self._extract(response, "Final Answer")

            step = {"step": _ + 1, "thought": thought, "action": action}

            if final_answer:
                step["final_answer"] = final_answer
                steps.append(step)
                return {"answer": final_answer, "steps": steps}

            if not action:
                return {"answer": response, "steps": steps}

            action_input = self._extract(response, "Action Input")
            try:
                args = json.loads(action_input) if action_input else {}
            except json.JSONDecodeError:
                args = {}

            observation = self.tools.execute(action, args)
            step["observation"] = observation
            steps.append(step)

            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Observation: {observation}"})
        return {"answer": "上限", "steps": steps}

    def _extract(self, response: str, param: str) -> str | None:
        pattern = rf'{param}\s*[:：]\s*(.+?)(?=\n\s*(?:Thought|Action|Final Answer|Observation)[:：]|\Z)'
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

