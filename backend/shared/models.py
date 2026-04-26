from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(20), default="active")  # active, disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("admins.id"), nullable=True)

    peer = relationship("Peer", back_populates="user", uselist=False)


class Admin(Base):
    """管理员表"""
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")  # super_admin, admin
    created_at = Column(DateTime, default=datetime.utcnow)

    approved_users = relationship("User", backref="approver")


class Registration(Base):
    """注册申请表"""
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(20), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("admins.id"), nullable=True)
    reject_reason = Column(String(255), nullable=True)


class Node(Base):
    """节点表"""
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    endpoint = Column(String(255), nullable=False)  # 公网地址:端口
    wg_port = Column(Integer, default=51820)
    wg_interface = Column(String(20), default="wg0")
    public_key = Column(String(100), nullable=False)
    private_key = Column(Text, nullable=False)  # 加密存储
    address_pool = Column(String(50), nullable=False)  # 如 10.100.0.0/24
    dns = Column(String(100), default="8.8.8.8")
    mtu = Column(Integer, default=1420)
    keepalive = Column(Integer, default=25)
    default_upload_limit = Column(Integer, default=0)  # 默认上传限速 Mbps, 0表示不限速
    default_download_limit = Column(Integer, default=0)  # 默认下载限速 Mbps, 0表示不限速
    status = Column(String(20), default="active")  # active, disabled
    api_url = Column(String(255), nullable=False)  # Agent API地址
    api_key = Column(String(100), nullable=False)  # API密钥(加密存储)
    created_at = Column(DateTime, default=datetime.utcnow)

    peers = relationship("Peer", back_populates="node")


class Peer(Base):
    """Peer表"""
    __tablename__ = "peers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    public_key = Column(String(100), nullable=False)
    private_key = Column(Text, nullable=False)  # 加密存储
    address = Column(String(50), nullable=False)  # 分配的IP
    mtu = Column(Integer, default=1420)
    dns = Column(String(100), default="8.8.8.8")
    keepalive = Column(Integer, default=25)
    upload_limit = Column(Integer, default=0)  # Mbps, 0表示不限速
    download_limit = Column(Integer, default=0)  # Mbps, 0表示不限速
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="peer")
    node = relationship("Node", back_populates="peers")
