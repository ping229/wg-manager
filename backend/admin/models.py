from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
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


class PortalSite(Base):
    """Portal 站点表 - 管理多个 Portal"""
    __tablename__ = "portal_sites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # 站点名称，如 "北京Portal"
    url = Column(String(255), nullable=False)  # Portal 地址，如 http://portal-beijing:8080
    api_key = Column(String(100), nullable=False)  # 调用该 Portal 的 API 密钥
    description = Column(Text, nullable=True)  # 描述
    status = Column(String(20), default="active")  # active, disabled
    created_at = Column(DateTime, default=datetime.utcnow)

    peers = relationship("Peer", back_populates="portal_site")


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
    default_upload_limit = Column(Integer, default=0)
    default_download_limit = Column(Integer, default=0)
    status = Column(String(20), default="active")
    api_url = Column(String(255), nullable=False)  # Agent API地址
    api_key = Column(String(100), nullable=False)  # API密钥(加密存储)
    blocked_patterns = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    peers = relationship("Peer", back_populates="node")


class Peer(Base):
    """Peer表 - 关联Portal用户"""
    __tablename__ = "peers"

    id = Column(Integer, primary_key=True, index=True)
    portal_site_id = Column(Integer, ForeignKey("portal_sites.id"), nullable=False)  # 所属 Portal
    portal_user_id = Column(Integer, nullable=False)  # Portal中的用户ID
    username = Column(String(50), index=True, nullable=False)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    public_key = Column(String(100), nullable=False)
    private_key = Column(Text, nullable=False)
    address = Column(String(50), nullable=False)
    mtu = Column(Integer, default=1420)
    dns = Column(String(100), default="8.8.8.8")
    keepalive = Column(Integer, default=25)
    upload_limit = Column(Integer, default=0)
    download_limit = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    node = relationship("Node", back_populates="peers")
    portal_site = relationship("PortalSite", back_populates="peers")
