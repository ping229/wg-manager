import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 基础配置
    BASE_DIR: Path = Path("/opt/wg-manager")
    DATA_DIR: Path = Path("/opt/wg-manager/data")
    LOG_DIR: Path = Path("/opt/wg-manager/data/logs")
    CONFIG_DIR: Path = Path("/opt/wg-manager/data/configs")

    # 数据库 - Admin 独立数据库
    DATABASE_URL: str = "sqlite:////opt/wg-manager/data/admin.db"

    # JWT配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # 加密密钥(用于加密私钥等敏感数据)
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "change-this-encryption-key-32bytes!!")

    # Admin服务配置
    ADMIN_HOST: str = os.getenv("ADMIN_HOST", "127.0.0.1")
    ADMIN_PORT: int = int(os.getenv("ADMIN_PORT", "8081"))

    # Portal服务配置 - 用于调用 Portal API
    PORTAL_URL: str = os.getenv("PORTAL_URL", "http://127.0.0.1:8080")
    PORTAL_API_KEY: str = os.getenv("PORTAL_API_KEY", "")  # 调用 Portal API 的密钥

    # Agent服务配置
    AGENT_HOST: str = os.getenv("AGENT_HOST", "127.0.0.1")
    AGENT_PORT: int = int(os.getenv("AGENT_PORT", "8082"))
    DEFAULT_AGENT_URL: str = os.getenv("DEFAULT_AGENT_URL", "http://127.0.0.1:8082")
    AGENT_API_KEY: str = os.getenv("AGENT_API_KEY", "")  # Agent API密钥，为空时使用ENCRYPTION_KEY

    # API 密钥 - 供 Portal 调用 Admin API
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")

    # WireGuard配置
    WG_DEFAULT_PORT: int = 51820
    WG_DEFAULT_INTERFACE: str = "wg0"
    WG_DEFAULT_DNS: str = "8.8.8.8"
    WG_DEFAULT_MTU: int = 1420
    WG_DEFAULT_KEEPALIVE: int = 25

    # 超级管理员初始密码
    SUPER_ADMIN_PASSWORD: str = os.getenv("SUPER_ADMIN_PASSWORD", "admin123")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def ensure_directories():
    """确保必要的目录存在"""
    for directory in [settings.DATA_DIR, settings.LOG_DIR, settings.CONFIG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
