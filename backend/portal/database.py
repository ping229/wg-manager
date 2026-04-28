import sys
sys.path.insert(0, '/opt/wg-manager')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.portal.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
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


def migrate_db():
    """数据库迁移 - 添加缺失的字段"""
    from sqlalchemy import inspect
    inspector = inspect(engine)

    # 获取 users 表的列名
    if inspector.has_table('users'):
        users_columns = [col['name'] for col in inspector.get_columns('users')]
    else:
        users_columns = []

    # 获取 registrations 表的列名
    if inspector.has_table('registrations'):
        registrations_columns = [col['name'] for col in inspector.get_columns('registrations')]
    else:
        registrations_columns = []

    # 添加缺失的字段
    with engine.connect() as conn:
        # users 表
        if users_columns and 'password' not in users_columns:
            print("Adding password column to users table...")
            conn.execute(text('ALTER TABLE users ADD COLUMN password VARCHAR(100) NOT NULL DEFAULT ""'))
            conn.commit()
            print("Column password added successfully")

        if users_columns and 'reject_reason' not in users_columns:
            print("Adding reject_reason column to users table...")
            conn.execute(text('ALTER TABLE users ADD COLUMN reject_reason VARCHAR(255)'))
            conn.commit()
            print("Column reject_reason added successfully")

        if users_columns and 'approved_at' not in users_columns:
            print("Adding approved_at column to users table...")
            conn.execute(text('ALTER TABLE users ADD COLUMN approved_at DATETIME'))
            conn.commit()
            print("Column approved_at added successfully")

        # registrations 表
        if registrations_columns and 'password' not in registrations_columns:
            print("Adding password column to registrations table...")
            conn.execute(text('ALTER TABLE registrations ADD COLUMN password VARCHAR(100) NOT NULL DEFAULT ""'))
            conn.commit()
            print("Column password added successfully")


def init_db():
    """初始化数据库表"""
    from . import models

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 执行迁移
    migrate_db()
