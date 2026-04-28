"""
Admin 连接管理路由 - Portal 端
用于检查连接状态和发起接入申请
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

router = APIRouter(prefix="/api/admin-connection", tags=["Admin连接管理"])


class ConnectionStatus(BaseModel):
    configured: bool
    admin_url: Optional[str] = None
    portal_name: Optional[str] = None
    status: str = "not_configured"  # not_configured, pending, approved, rejected, disconnected
    reject_reason: Optional[str] = None
    applied_at: Optional[str] = None


@router.get("/status", response_model=ConnectionStatus)
def get_connection_status(db: Session = Depends(get_db)):
    """获取 Admin 连接状态"""
    # 检查配置文件中是否配置了 Admin
    if not settings.ADMIN_URL or not settings.ADMIN_API_KEY:
        return ConnectionStatus(configured=False, status="not_configured")

    # 检查数据库中的连接状态
    connection = db.query(AdminConnection).first()

    if not connection:
        # 配置文件有配置但还没发起过申请
        return ConnectionStatus(
            configured=True,
            admin_url=settings.ADMIN_URL,
            portal_name=settings.PORTAL_NAME,
            status="pending"  # 待申请
        )

    return ConnectionStatus(
        configured=True,
        admin_url=connection.url or settings.ADMIN_URL,
        portal_name=connection.portal_name or settings.PORTAL_NAME,
        status=connection.status,
        reject_reason=connection.reject_reason,
        applied_at=connection.applied_at.isoformat() if connection.applied_at else None
    )


@router.post("/apply")
async def apply_to_admin(db: Session = Depends(get_db)):
    """向 Admin 发起接入申请"""
    # 检查配置文件
    if not settings.ADMIN_URL or not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=400, detail="未配置 Admin 连接信息，请在 .env 中设置 ADMIN_URL 和 ADMIN_API_KEY")

    # 检查 Portal API Key
    if not settings.PORTAL_API_KEY:
        raise HTTPException(status_code=500, detail="未配置 PORTAL_API_KEY，请在 .env 中设置")

    # 获取 Portal URL
    portal_url = settings.PORTAL_URL
    if not portal_url:
        portal_url = f"http://{settings.PORTAL_HOST}:{settings.PORTAL_PORT}"

    # 发送申请到 Admin
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.ADMIN_URL.rstrip('/')}/api/portal-applications/apply",
                json={
                    "name": settings.PORTAL_NAME,
                    "url": portal_url,
                    "api_key": settings.PORTAL_API_KEY,
                    "description": f"来自 {settings.PORTAL_NAME} 的接入申请"
                },
                headers={"X-Admin-API-Key": settings.ADMIN_API_KEY},
                timeout=10.0
            )

            if response.status_code == 200:
                # 更新或创建连接记录
                connection = db.query(AdminConnection).first()
                if not connection:
                    connection = AdminConnection(
                        name="Admin",
                        url=settings.ADMIN_URL,
                        api_key=settings.ADMIN_API_KEY,
                        portal_name=settings.PORTAL_NAME,
                        portal_api_key=settings.PORTAL_API_KEY,
                        status="pending",
                        applied_at=datetime.utcnow()
                    )
                    db.add(connection)
                else:
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
    connection = db.query(AdminConnection).first()
    if not connection:
        # 如果数据库没有记录，创建一个
        connection = AdminConnection(
            name="Admin",
            url=settings.ADMIN_URL,
            api_key=settings.ADMIN_API_KEY,
            portal_name=settings.PORTAL_NAME,
            portal_api_key=settings.PORTAL_API_KEY,
            status="approved"
        )
        db.add(connection)
    else:
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
        connection = AdminConnection(
            name="Admin",
            url=settings.ADMIN_URL,
            api_key=settings.ADMIN_API_KEY,
            portal_name=settings.PORTAL_NAME,
            portal_api_key=settings.PORTAL_API_KEY,
            status="rejected",
            reject_reason=reject_reason
        )
        db.add(connection)
    else:
        connection.status = "rejected"
        connection.reject_reason = reject_reason

    db.commit()
    return {"message": "Portal 接入状态已更新为已拒绝"}
