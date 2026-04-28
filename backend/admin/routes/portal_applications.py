"""
Portal 接入申请管理路由 - Admin 端
用于审核 Portal 的接入申请
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import httpx

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.admin.database import get_db
from backend.admin.models import PortalApplication, PortalSite, AdminUser
from backend.shared.auth import get_current_admin

router = APIRouter(prefix="/api/portal-applications", tags=["Portal接入申请"])


class PortalApplyRequest(BaseModel):
    """Portal 发起的接入申请"""
    name: str
    url: str
    key: str  # Portal 的 KEY
    description: Optional[str] = None


class PortalApplicationResponse(BaseModel):
    id: int
    name: str
    url: str
    description: Optional[str] = None
    status: str
    reject_reason: Optional[str] = None
    created_at: str
    reviewed_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/apply")
async def apply_portal(
    data: PortalApplyRequest,
    db: Session = Depends(get_db)
):
    """
    Portal 发起接入申请
    Portal 使用自己的 KEY 作为认证凭证
    """
    # 检查是否已存在相同 URL 的申请
    existing = db.query(PortalApplication).filter(
        PortalApplication.url == data.url
    ).first()

    if existing:
        # 更新申请信息，状态重置为 pending
        existing.name = data.name
        existing.key = data.key
        existing.description = data.description
        existing.status = "pending"
        existing.reject_reason = None
        existing.created_at = datetime.utcnow()
        existing.reviewed_at = None
        existing.reviewed_by = None
        db.commit()
        return {"message": "接入申请已更新，请等待审核", "application_id": existing.id}

    # 创建新申请
    application = PortalApplication(
        name=data.name,
        url=data.url,
        key=data.key,
        description=data.description,
        status="pending"
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return {"message": "接入申请已提交，请等待审核", "application_id": application.id}


@router.get("", response_model=list[PortalApplicationResponse])
def list_applications(
    status: str = None,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """获取 Portal 接入申请列表"""
    query = db.query(PortalApplication)

    if status:
        query = query.filter(PortalApplication.status == status)

    applications = query.order_by(PortalApplication.created_at.desc()).all()

    return [{
        "id": a.id,
        "name": a.name,
        "url": a.url,
        "description": a.description,
        "status": a.status,
        "reject_reason": a.reject_reason,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None
    } for a in applications]


@router.get("/{application_id}", response_model=PortalApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """获取单个接入申请详情"""
    application = db.query(PortalApplication).filter(PortalApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="申请不存在")

    return {
        "id": application.id,
        "name": application.name,
        "url": application.url,
        "description": application.description,
        "status": application.status,
        "reject_reason": application.reject_reason,
        "created_at": application.created_at.isoformat() if application.created_at else None,
        "reviewed_at": application.reviewed_at.isoformat() if application.reviewed_at else None
    }


@router.post("/{application_id}/approve")
async def approve_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """批准 Portal 接入申请"""
    application = db.query(PortalApplication).filter(PortalApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="申请不存在")

    if application.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已被处理")

    # 检查是否已存在同名 Portal
    existing_site = db.query(PortalSite).filter(PortalSite.name == application.name).first()
    if existing_site:
        raise HTTPException(status_code=400, detail=f"已存在同名 Portal 站点: {application.name}")

    # 创建 PortalSite（KEY 明文存储）
    portal_site = PortalSite(
        name=application.name,
        url=application.url,
        key=application.key,
        description=application.description,
        status="active"
    )
    db.add(portal_site)
    db.commit()
    db.refresh(portal_site)

    # 更新申请状态
    application.status = "approved"
    application.reviewed_at = datetime.utcnow()
    application.reviewed_by = current_admin.id
    application.portal_site_id = portal_site.id
    db.commit()

    # 通知 Portal 审批通过
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{application.url.rstrip('/')}/api/admin-connection/approved",
                json={"status": "approved"},
                headers={"X-Key": application.key},
                timeout=5.0
            )
    except Exception as e:
        print(f"Warning: Failed to notify Portal: {e}")

    return {
        "message": "Portal 接入申请已批准",
        "portal_site_id": portal_site.id
    }


@router.post("/{application_id}/reject")
async def reject_application(
    application_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """拒绝 Portal 接入申请"""
    application = db.query(PortalApplication).filter(PortalApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="申请不存在")

    if application.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已被处理")

    application.status = "rejected"
    application.reject_reason = reason
    application.reviewed_at = datetime.utcnow()
    application.reviewed_by = current_admin.id
    db.commit()

    # 通知 Portal 被拒绝
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{application.url.rstrip('/')}/api/admin-connection/rejected",
                json={"status": "rejected", "reject_reason": reason},
                headers={"X-Key": application.key},
                timeout=5.0
            )
    except Exception as e:
        print(f"Warning: Failed to notify Portal: {e}")

    return {"message": "Portal 接入申请已拒绝"}


@router.delete("/{application_id}")
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """删除接入申请记录"""
    application = db.query(PortalApplication).filter(PortalApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="申请不存在")

    db.delete(application)
    db.commit()

    return {"message": "申请记录已删除"}
