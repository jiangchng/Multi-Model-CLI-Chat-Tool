"""
应用全局配置。

自动从 .env 文件和环境变量读取，优先级：环境变量 > .env > 默认值。
对应 Java 中 Spring Boot 的 @ConfigurationProperties + application.yml。
"""

from pathlib import Path
from typing import Any, ClassVar

from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，自动从 .env 和环境变量加载。

    使用 pydantic-settings，每个字段都会自动匹配同名环境变量。
    Field(alias="XXX") 表示从名为 XXX 的环境变量读取。
    """

    model_config = {
        "env_file": Path(__file__).parent.parent / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    # --- LLM API 密钥 ---
    glm_api_key: str = Field(alias="GLM_API_KEY")
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"

    deepseek_api_key: str = Field(alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = "https://api.deepseek.com"

    models_name: list[str] = ["deepseek-v4-pro", "glm-5-turbo"]
    models_urls: ClassVar[dict] = {
        "deepseek-v4-pro": "https://api.deepseek.com",
        "glm-5-turbo": "https://open.bigmodel.cn/api/paas/v4"
    }

    @property
    def models_api_key(self) -> dict:
        """动态构建 API Key 映射表（实例化后执行）"""
        return {
            "deepseek-v4-pro": self.deepseek_api_key,
            "glm-5-turbo": self.glm_api_key
        }

    # --- 模型默认参数 ---
    default_model: str = "deepseek-v4-pro"
    max_tokens: int = 4096  # 单次回复最多生成的 Token 数
    temperature: float = 0.0  # 随机性：0=确定, 1=随机, 对话建议 0.7

    # --- 本地存储 ---
    history_dir: Path = Path("./chat_history")  # 对话保存/加载的目录
