from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ============ 用户相关 ============
class UserRegister(BaseModel):
    username: str
    password: str
    email: EmailStr


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    status: str
    created_at: datetime
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


# ============ 管理员相关 ============
class AdminLogin(BaseModel):
    username: str
    password: str


class AdminCreate(BaseModel):
    username: str
    password: str
    role: str = "admin"


class AdminResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 注册申请相关 ============
class RegistrationResponse(BaseModel):
    id: int
    username: str
    email: str
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reject_reason: Optional[str] = None

    class Config:
        from_attributes = True


class RegistrationApprove(BaseModel):
    pass


class RegistrationReject(BaseModel):
    reason: str


# ============ 节点相关 ============
class NodeCreate(BaseModel):
    name: str
    endpoint: str
    wg_port: int = 51820
    wg_interface: str = "wg0"
    address_pool: str
    dns: str = "8.8.8.8"
    mtu: int = 1420
    keepalive: int = 25
    default_upload_limit: int = 0  # 默认上传限速 Mbps
    default_download_limit: int = 0  # 默认下载限速 Mbps
    api_url: str
    api_key: str


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    endpoint: Optional[str] = None
    wg_port: Optional[int] = None
    wg_interface: Optional[str] = None
    address_pool: Optional[str] = None
    dns: Optional[str] = None
    mtu: Optional[int] = None
    keepalive: Optional[int] = None
    default_upload_limit: Optional[int] = None
    default_download_limit: Optional[int] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    blocked_patterns: Optional[str] = None  # JSON数组格式的正则列表


class NodeResponse(BaseModel):
    id: int
    name: str
    endpoint: str
    wg_port: int
    wg_interface: str
    public_key: str
    address_pool: str
    dns: str
    mtu: int
    keepalive: int
    default_upload_limit: int
    default_download_limit: int
    status: str
    api_url: str
    blocked_patterns: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NodeListResponse(BaseModel):
    id: int
    name: str
    endpoint: str
    wg_port: int
    default_upload_limit: int
    default_download_limit: int
    status: str

    class Config:
        from_attributes = True


# ============ Peer相关 ============
class PeerCreate(BaseModel):
    node_id: int
    mtu: Optional[int] = None
    dns: Optional[str] = None
    keepalive: Optional[int] = None


class PeerSettings(BaseModel):
    mtu: Optional[int] = None
    dns: Optional[str] = None
    keepalive: Optional[int] = None


class PeerLimit(BaseModel):
    upload_limit: int = 0
    download_limit: int = 0


class PeerResponse(BaseModel):
    id: int
    user_id: int
    node_id: int
    public_key: str
    address: str
    mtu: int
    dns: str
    keepalive: int
    upload_limit: int
    download_limit: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 配置相关 ============
class ConfigResponse(BaseModel):
    peer: PeerResponse
    node: NodeResponse


class ConfigDownload(BaseModel):
    config: str
    filename: str


# ============ Token相关 ============
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    is_admin: bool = False


# ============ Agent API相关 ============
class AgentPeerAdd(BaseModel):
    public_key: str
    address: str


class AgentPeerRemove(BaseModel):
    public_key: str


class AgentPeerLimit(BaseModel):
    address: str
    upload_limit: int  # Mbps
    download_limit: int  # Mbps


class AgentPeerInfo(BaseModel):
    public_key: str
    address: str
    upload_limit: int
    download_limit: int


class AgentStatus(BaseModel):
    interface: str
    public_key: str
    listen_port: int
    peer_count: int
