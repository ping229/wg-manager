import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 基础配置
    BASE_DIR: Path = Path("/opt/wg-manager")
    DATA_DIR: Path = Path("/opt/wg-manager/data")
    LOG_DIR: Path = Path("/opt/wg-manager/data/logs")

    # 数据库
    DATABASE_URL: str = "sqlite:////opt/wg-manager/data/portal.db"

    # JWT配置 - Portal 独立密钥
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # Portal 服务配置
    PORTAL_HOST: str = os.getenv("PORTAL_HOST", "0.0.0.0")
    PORTAL_PORT: int = int(os.getenv("PORTAL_PORT", "8080"))

    # Portal 名称和 API 密钥（用于 Admin 回调）
    PORTAL_NAME: str = os.getenv("PORTAL_NAME", "WireGuard Portal")
    PORTAL_API_KEY: str = os.getenv("PORTAL_API_KEY", "")

    # 数据加密密钥（用于加密存储的 API Key）
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "change-this-encryption-key-32bytes!!")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def ensure_directories():
    """确保必要的目录存在"""
    for directory in [settings.DATA_DIR, settings.LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
