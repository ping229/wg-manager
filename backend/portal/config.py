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

    # Portal 名称
    PORTAL_NAME: str = os.getenv("PORTAL_NAME", "WireGuard Portal")

    # Portal 外部访问地址（发送给 Admin）
    PORTAL_URL: str = os.getenv("PORTAL_URL", "")

    # 统一 KEY - 用于 Portal 与 Admin 之间的双向认证
    # Portal 只有一个 KEY，Admin 端必须配置相同的 KEY 才能通信
    KEY: str = os.getenv("KEY", "")

    # Admin 连接地址
    ADMIN_URL: str = os.getenv("ADMIN_URL", "")

    # 数据加密密钥
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "change-this-encryption-key-32bytes!!")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def ensure_directories():
    """确保必要的目录存在"""
    for directory in [settings.DATA_DIR, settings.LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
