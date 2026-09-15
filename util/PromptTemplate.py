"""
Prompt 模板引擎 —— 可复用的 System Prompt 工厂。

让你预定义角色模板（代码审查员、苏格拉底导师...），
通过 /prompt 命令一键切换，不用每次手写长 Prompt。

使用 Python 标准库 string.Template 做变量替换，
比 str.format() 更适合 Prompt 场景（Prompt 里大量 {} 是 JSON 示例）。
"""

from string import Template


class PromptTemplate:
    """单个 Prompt 模板。

    使用方式：
        tpl = PromptTemplate("代码审查", "审查代码", "你是$language专家，请审查：\n$code")
        result = tpl.render(language="Java", code="public class...")
    """

    def __init__(self, name: str, description: str, template: str):
        self.name = name
        self.description = description
        self._template = Template(template)

    def render(self, **kwargs) -> str:
        """填充模板变量。

        使用 safe_substitute 而非 substitute：
        如果模板有未提供的变量，会保留占位符而不是抛异常。
        这样 /prompt 切换时不需要传所有参数就能看到模板骨架。
        """
        return self._template.safe_substitute(**kwargs)

    def __repr__(self):
        return f"PromptTemplate(name={self.name}, description={self.description})"


class PromptLibrary:
    """Prompt 模板库 —— 管理一组预设模板。

    使用方式：
        lib = build_default_library()
        lib.list_prompts()                    # 列出所有可用模板
        prompt = lib.render_prompt("code-reviewer", language="Java", code="...")
    """

    def __init__(self):
        self._prompts: dict[str, PromptTemplate] = {}

    def register_prompt(self, template: PromptTemplate):
        """注册一个模板"""
        self._prompts[template.name] = template

    def get_prompt(self, name: str) -> PromptTemplate | None:
        """根据名称获取模板，不存在时返回 None"""
        return self._prompts.get(name)

    def list_prompts(self) -> list[str]:
        """列出所有模板（给人看的格式化字符串）"""
        return [f"  {t.name:20s} — {t.description}" for t in self._prompts.values()]

    def render_prompt(self, name: str, **kwargs) -> str:
        """渲染指定模板。

        Raises:
            KeyError: 模板名不存在
        """
        tpl = self.get_prompt(name)
        if not tpl:
            available = [t.name for t in self._prompts.values()]
            raise KeyError(f"模板 '{name}' 不存在。可用: {available}")
        return tpl.render(**kwargs)


# ================================================================
# 预设模板库
# ================================================================

def build_default_library() -> PromptLibrary:
    """构建内置 Prompt 模板库。

    目前包含：
        - code-reviewer: 代码审查专家（可指定语言和审查重点）
    后续可扩展更多模板。
    """
    library = PromptLibrary()

    # ---- 模板 1：代码审查专家 ----
    library.register_prompt(PromptTemplate(
        name="code-reviewer",
        description="代码审查（可指定语言和审查重点）",
        template="""你是 $language 代码审查专家。

                ## 审查维度
                $focus_points
                
                ## 输出格式
                对每个问题按以下格式输出：
                - [$severity] 行号 — 问题描述 → 修复方案
                
                ## 严重程度
                - 🔴 致命：会导致生产事故
                - 🟡 警告：潜在风险
                - 🔵 建议：代码风格改进
                
                ## 待审查代码
                ```
                $code
                ```
                
                ## 开始审查
                请逐条指出问题。""",
    ))

    return library
