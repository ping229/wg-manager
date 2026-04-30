import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """共享配置 - 用于 Agent 服务"""
    # 基础配置
    BASE_DIR: Path = Path("/opt/wg-manager")
    DATA_DIR: Path = Path("/opt/wg-manager/data")
    LOG_DIR: Path = Path("/opt/wg-manager/data/logs")
    CONFIG_DIR: Path = Path("/opt/wg-manager/data/configs")

    # Agent服务配置
    AGENT_HOST: str = os.getenv("AGENT_HOST", "0.0.0.0")
    AGENT_PORT: int = int(os.getenv("AGENT_PORT", "8082"))

    # 统一 KEY - 用于 Admin 与 Agent 之间的认证
    KEY: str = os.getenv("KEY", "")

    # 向后兼容
    AGENT_API_KEY: str = os.getenv("AGENT_API_KEY", "")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

    class Config:
        env_file = "/opt/wg-manager/.env"
        extra = "ignore"


settings = Settings()


def ensure_directories():
    """确保必要的目录存在"""
    for directory in [settings.DATA_DIR, settings.LOG_DIR, settings.CONFIG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
