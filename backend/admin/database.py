import sys
sys.path.insert(0, '/opt/wg-manager')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.admin.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite需要
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表"""
    from . import models
    Base.metadata.create_all(bind=engine)
