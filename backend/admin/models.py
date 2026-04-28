from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from .database import Base


class AdminSetting(Base):
    """Admin 配置表（键值对存储）"""
    __tablename__ = "admin_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdminUser(Base):
    """管理员表"""
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")  # super_admin, admin
    created_at = Column(DateTime, default=datetime.utcnow)


class PortalApplication(Base):
    """Portal 接入申请表"""
    __tablename__ = "portal_applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Portal 名称
    url = Column(String(255), nullable=False)  # Portal 地址
    key = Column(String(100), nullable=False)  # Portal 的 KEY
    description = Column(Text, nullable=True)  # 申请说明
    status = Column(String(20), default="pending")  # pending, approved, rejected
    reject_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("admins.id"), nullable=True)

    # 审批通过后关联的 PortalSite
    portal_site_id = Column(Integer, ForeignKey("portal_sites.id"), nullable=True)


class PortalSite(Base):
    """已接入的 Portal 站点表"""
    __tablename__ = "portal_sites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    url = Column(String(255), nullable=False)
    key = Column(String(100), nullable=False)  # Portal 的 KEY（与 Portal 端 KEY 相同）
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active")  # active, disabled
    created_at = Column(DateTime, default=datetime.utcnow)

    peers = relationship("Peer", back_populates="portal_site")


class Node(Base):
    """节点表"""
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    endpoint = Column(String(255), nullable=False)
    wg_port = Column(Integer, default=51820)
    wg_interface = Column(String(20), default="wg0")
    public_key = Column(String(100), nullable=False)
    private_key = Column(Text, nullable=False)
    address_pool = Column(String(50), nullable=False)
    dns = Column(String(100), default="8.8.8.8")
    mtu = Column(Integer, default=1420)
    keepalive = Column(Integer, default=25)
    default_upload_limit = Column(Integer, default=0)
    default_download_limit = Column(Integer, default=0)
    status = Column(String(20), default="active")
    api_url = Column(String(255), nullable=False)
    api_key = Column(String(100), nullable=False)
    blocked_patterns = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    peers = relationship("Peer", back_populates="node")


class Peer(Base):
    """Peer表"""
    __tablename__ = "peers"

    id = Column(Integer, primary_key=True, index=True)
    portal_site_id = Column(Integer, ForeignKey("portal_sites.id"), nullable=False)
    portal_user_id = Column(Integer, nullable=False)
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
