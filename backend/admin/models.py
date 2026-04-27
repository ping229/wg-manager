from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


class AdminUser(Base):
    """管理员表 - Admin 独立管理"""
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")  # super_admin, admin
    created_at = Column(DateTime, default=datetime.utcnow)


class PortalUser(Base):
    """Portal用户缓存表 - 从Portal同步"""
    __tablename__ = "portal_users"

    id = Column(Integer, primary_key=True, index=True)
    portal_user_id = Column(Integer, unique=True, nullable=False)  # Portal中的用户ID
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), nullable=False)
    status = Column(String(20), default="pending")  # pending, active, disabled
    synced_at = Column(DateTime, default=datetime.utcnow)


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
    blocked_patterns = Column(Text, nullable=True)  # 禁止访问的用户名正则列表(JSON数组)
    created_at = Column(DateTime, default=datetime.utcnow)

    peers = relationship("Peer", back_populates="node")


class Peer(Base):
    """Peer表 - 关联Portal用户"""
    __tablename__ = "peers"

    id = Column(Integer, primary_key=True, index=True)
    portal_user_id = Column(Integer, nullable=False)  # Portal中的用户ID
    username = Column(String(50), index=True, nullable=False)  # 冗余存储便于查询
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

    node = relationship("Node", back_populates="peers")
