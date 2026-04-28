import sys
sys.path.insert(0, '/opt/wg-manager')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.admin.config import settings

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

    # 获取 portal_sites 表的列名
    if inspector.has_table('portal_sites'):
        portal_sites_columns = [col['name'] for col in inspector.get_columns('portal_sites')]
    else:
        portal_sites_columns = []

    # 获取 peers 表的列名
    if inspector.has_table('peers'):
        peers_columns = [col['name'] for col in inspector.get_columns('peers')]
    else:
        peers_columns = []

    with engine.connect() as conn:
        # portal_sites 表迁移
        if 'portal_sites' in portal_sites_columns and 'api_key' not in portal_sites_columns:
            print("Adding api_key column to portal_sites table...")
            conn.execute(text('ALTER TABLE portal_sites ADD COLUMN api_key VARCHAR(100) NOT NULL DEFAULT ""'))
            conn.commit()
            print("Column api_key added successfully")

        # peers 表迁移
        if 'peers' in peers_columns and 'portal_site_id' not in peers_columns:
            print("Adding portal_site_id column to peers table...")
            conn.execute(text('ALTER TABLE peers ADD COLUMN portal_site_id INTEGER'))
            conn.commit()
            print("Column portal_site_id added successfully")

        if 'peers' in peers_columns and 'username' not in peers_columns:
            print("Adding username column to peers table...")
            conn.execute(text('ALTER TABLE peers ADD COLUMN username VARCHAR(50)'))
            conn.commit()
            print("Column username added successfully")


def init_db():
    """初始化数据库表"""
    from . import models

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 执行迁移
    migrate_db()
