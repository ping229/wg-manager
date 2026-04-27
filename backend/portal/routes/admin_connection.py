"""
Admin 连接管理路由 - Portal 端
用于配置和发起 Admin 接入申请
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import httpx

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.portal.database import get_db
from backend.portal.models import AdminConnection
from backend.portal.config import settings
from backend.shared.auth import get_password_hash

router = APIRouter(prefix="/api/admin-connection", tags=["Admin连接管理"])


class AdminConnectionCreate(BaseModel):
    name: str
    url: str
    api_key: str  # Admin 的 API 密钥
    portal_name: Optional[str] = None  # 本 Portal 名称


class AdminConnectionUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    api_key: Optional[str] = None
    portal_name: Optional[str] = None


class AdminConnectionResponse(BaseModel):
    id: int
    name: str
    url: str
    portal_name: str
    status: str
    reject_reason: Optional[str] = None
    created_at: str
    applied_at: Optional[str] = None

    class Config:
        from_attributes = True


def encrypt_api_key(api_key: str) -> str:
    """加密 API 密钥"""
    import os
    import base64
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    key = settings.ENCRYPTION_KEY.encode()[:32].ljust(32, b'\0')
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    data = api_key.encode()
    padding_length = 16 - (len(data) % 16)
    data += bytes([padding_length] * padding_length)

    encrypted = encryptor.update(data) + encryptor.finalize()
    return base64.b64encode(iv + encrypted).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """解密 API 密钥"""
    import os
    import base64
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    if not encrypted_key:
        return ""

    try:
        key = settings.ENCRYPTION_KEY.encode()[:32].ljust(32, b'\0')
        data = base64.b64decode(encrypted_key)
        iv = data[:16]
        encrypted = data[16:]

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        decrypted = decryptor.update(encrypted) + decryptor.finalize()
        padding_length = decrypted[-1]
        decrypted = decrypted[:-padding_length]

        return decrypted.decode()
    except Exception:
        return ""


@router.get("", response_model=Optional[AdminConnectionResponse])
def get_admin_connection(db: Session = Depends(get_db)):
    """获取当前 Admin 连接配置"""
    connection = db.query(AdminConnection).first()
    if not connection:
        return None

    return AdminConnectionResponse(
        id=connection.id,
        name=connection.name,
        url=connection.url,
        portal_name=connection.portal_name,
        status=connection.status,
        reject_reason=connection.reject_reason,
        created_at=connection.created_at.isoformat() if connection.created_at else None,
        applied_at=connection.applied_at.isoformat() if connection.applied_at else None
    )


@router.post("", response_model=AdminConnectionResponse)
def create_admin_connection(
    data: AdminConnectionCreate,
    db: Session = Depends(get_db)
):
    """创建 Admin 连接配置"""
    # 检查是否已存在
    existing = db.query(AdminConnection).first()
    if existing:
        raise HTTPException(status_code=400, detail="已存在 Admin 连接配置，请使用更新接口")

    connection = AdminConnection(
        name=data.name,
        url=data.url.rstrip('/'),
        api_key=encrypt_api_key(data.api_key),
        portal_name=data.portal_name or settings.PORTAL_NAME,
        portal_api_key=settings.PORTAL_API_KEY or generate_portal_api_key(),
        status="pending"
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)

    return AdminConnectionResponse(
        id=connection.id,
        name=connection.name,
        url=connection.url,
        portal_name=connection.portal_name,
        status=connection.status,
        reject_reason=connection.reject_reason,
        created_at=connection.created_at.isoformat() if connection.created_at else None,
        applied_at=connection.applied_at.isoformat() if connection.applied_at else None
    )


@router.put("", response_model=AdminConnectionResponse)
def update_admin_connection(
    data: AdminConnectionUpdate,
    db: Session = Depends(get_db)
):
    """更新 Admin 连接配置"""
    connection = db.query(AdminConnection).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Admin 连接配置不存在")

    if data.name is not None:
        connection.name = data.name
    if data.url is not None:
        connection.url = data.url.rstrip('/')
    if data.api_key is not None:
        connection.api_key = encrypt_api_key(data.api_key)
    if data.portal_name is not None:
        connection.portal_name = data.portal_name

    db.commit()
    db.refresh(connection)

    return AdminConnectionResponse(
        id=connection.id,
        name=connection.name,
        url=connection.url,
        portal_name=connection.portal_name,
        status=connection.status,
        reject_reason=connection.reject_reason,
        created_at=connection.created_at.isoformat() if connection.created_at else None,
        applied_at=connection.applied_at.isoformat() if connection.applied_at else None
    )


@router.post("/apply")
async def apply_to_admin(db: Session = Depends(get_db)):
    """向 Admin 发起接入申请"""
    connection = db.query(AdminConnection).first()
    if not connection:
        raise HTTPException(status_code=400, detail="请先配置 Admin 连接信息")

    # 发送申请到 Admin
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{connection.url}/api/portal-applications/apply",
                json={
                    "name": connection.portal_name,
                    "url": get_portal_url(),  # Portal 的访问地址
                    "api_key": connection.portal_api_key,  # 供 Admin 回调的密钥
                    "description": f"来自 {connection.portal_name} 的接入申请"
                },
                headers={"X-Admin-API-Key": decrypt_api_key(connection.api_key)},
                timeout=10.0
            )

            if response.status_code == 200:
                connection.status = "pending"
                connection.applied_at = datetime.utcnow()
                connection.reject_reason = None
                db.commit()
                return {"message": "接入申请已发送，请等待 Admin 审核", "status": "pending"}
            else:
                error_detail = response.json().get("detail", response.text)
                raise HTTPException(status_code=response.status_code, detail=error_detail)

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"无法连接到 Admin: {str(e)}")


@router.get("/status")
def get_connection_status(db: Session = Depends(get_db)):
    """获取连接状态（供前端轮询）"""
    connection = db.query(AdminConnection).first()
    if not connection:
        return {"configured": False}

    return {
        "configured": True,
        "name": connection.name,
        "url": connection.url,
        "portal_name": connection.portal_name,
        "status": connection.status,
        "reject_reason": connection.reject_reason,
        "applied_at": connection.applied_at.isoformat() if connection.applied_at else None
    }


@router.delete("")
def delete_admin_connection(db: Session = Depends(get_db)):
    """删除 Admin 连接配置"""
    connection = db.query(AdminConnection).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Admin 连接配置不存在")

    db.delete(connection)
    db.commit()

    return {"message": "Admin 连接配置已删除"}


def generate_portal_api_key() -> str:
    """生成 Portal API 密钥"""
    import secrets
    return secrets.token_hex(16)


def get_portal_url() -> str:
    """获取 Portal 的访问地址"""
    # 从环境变量或配置获取
    import os
    return os.getenv("PORTAL_URL", f"http://{settings.PORTAL_HOST}:{settings.PORTAL_PORT}")


# ============ Admin 回调接口 ============

@router.post("/approved")
def on_admin_approved(
    status: str,
    admin_url: str = None,
    db: Session = Depends(get_db)
):
    """
    Admin 审批通过的回调接口
    Admin 调用此接口通知 Portal 审批结果
    """
    from fastapi import Header
    connection = db.query(AdminConnection).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Admin 连接配置不存在")

    connection.status = "approved"
    connection.reject_reason = None
    if admin_url:
        connection.url = admin_url.rstrip('/')
    db.commit()

    return {"message": "Portal 接入状态已更新为已批准"}


@router.post("/rejected")
def on_admin_rejected(
    status: str,
    reject_reason: str = None,
    db: Session = Depends(get_db)
):
    """
    Admin 拒绝申请的回调接口
    Admin 调用此接口通知 Portal 被拒绝
    """
    connection = db.query(AdminConnection).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Admin 连接配置不存在")

    connection.status = "rejected"
    connection.reject_reason = reject_reason
    db.commit()

    return {"message": "Portal 接入状态已更新为已拒绝"}
