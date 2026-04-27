from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from .database import Base


class User(Base):
    """用户表 - Portal 独立管理"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(20), default="pending")  # pending(待审核), active, disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    reject_reason = Column(String(255), nullable=True)


class Registration(Base):
    """注册申请表 - Portal 独立管理"""
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(20), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reject_reason = Column(String(255), nullable=True)
