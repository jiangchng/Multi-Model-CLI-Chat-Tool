from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置。自动从 .env 读取，优先级：环境变量 > .env > 默认值。"""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # API
    deepseek_api_key: str = Field(alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = "https://api.deepseek.com"

    # 模型默认参数
    default_model: str = "deepseek-chat"
    # 上下文限制
    max_tokens: int = 4096
    # 温度
    temperature: float = 0.7

    # 本地存储
    history_dir: Path = Path("./chat_history")
