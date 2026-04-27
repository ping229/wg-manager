import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 基础配置
    BASE_DIR: Path = Path("/opt/wg-manager")
    DATA_DIR: Path = Path("/opt/wg-manager/data")
    LOG_DIR: Path = Path("/opt/wg-manager/data/logs")

    # 数据库 - Portal 独立数据库
    DATABASE_URL: str = "sqlite:////opt/wg-manager/data/portal.db"

    # JWT配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # Portal服务配置
    PORTAL_HOST: str = os.getenv("PORTAL_HOST", "0.0.0.0")
    PORTAL_PORT: int = int(os.getenv("PORTAL_PORT", "8080"))

    # Admin服务配置 - 用于调用 Admin API
    ADMIN_URL: str = os.getenv("ADMIN_URL", "http://127.0.0.1:8081")
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")  # 调用 Admin API 的密钥

    # API 密钥 - 供 Admin 调用 Portal API
    PORTAL_API_KEY: str = os.getenv("PORTAL_API_KEY", "")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def ensure_directories():
    """确保必要的目录存在"""
    for directory in [settings.DATA_DIR, settings.LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
