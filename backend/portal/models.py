from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from .database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    password = Column(String(100), nullable=False)  # 明文密码，供 Admin 查看
    email = Column(String(100), index=True, nullable=False)  # 邮箱可重复
    status = Column(String(20), default="pending")  # pending, active, disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    reject_reason = Column(String(255), nullable=True)


class Registration(Base):
    """注册申请表"""
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    password = Column(String(100), nullable=False)  # 明文密码
    email = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reject_reason = Column(String(255), nullable=True)


class AdminConnection(Base):
    """Admin 连接配置表 - 存储 Portal 要连接的 Admin 信息"""
    __tablename__ = "admin_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Admin 名称，如"主Admin"
    url = Column(String(255), nullable=False)  # Admin 地址
    api_key = Column(String(100), nullable=False)  # Admin 的 API 密钥（加密存储）
    portal_name = Column(String(100), nullable=False)  # 本 Portal 名称，发送给 Admin
    portal_api_key = Column(String(100), nullable=False)  # 本 Portal 的 API 密钥，供 Admin 回调
    status = Column(String(20), default="pending")  # pending, approved, rejected, disconnected
    reject_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    applied_at = Column(DateTime, nullable=True)  # 发起申请的时间
