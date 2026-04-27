from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.admin.database import get_db
from backend.admin.models import AdminUser, PortalSite
from backend.shared.auth import get_current_admin
from backend.shared.schemas import RegistrationReject
from backend.admin.services.portal_client import get_portal_client

router = APIRouter(prefix="/api/registrations", tags=["注册审核"])


@router.get("")
async def list_registrations(
    portal_site_id: int = Query(None, description="Portal站点ID"),
    status: str = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取注册申请列表"""
    # 获取所有 Portal 站点
    portal_sites = db.query(PortalSite).filter(PortalSite.status == "active").all()

    if not portal_sites:
        return []

    all_registrations = []

    # 如果指定了 portal_site_id，只查询该站点
    sites_to_query = portal_sites
    if portal_site_id:
        sites_to_query = [s for s in portal_sites if s.id == portal_site_id]

    for site in sites_to_query:
        try:
            client = get_portal_client(site)
            registrations = await client.get_registrations(status)

            for reg in registrations:
                reg["portal_site_id"] = site.id
                reg["portal_site_name"] = site.name
                all_registrations.append(reg)
        except Exception as e:
            print(f"Failed to get registrations from {site.name}: {e}")
            continue

    # 按创建时间排序
    all_registrations.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return all_registrations


@router.post("/{portal_site_id}/{reg_id}/approve")
async def approve_registration(
    portal_site_id: int,
    reg_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """批准注册申请"""
    site = db.query(PortalSite).filter(PortalSite.id == portal_site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Portal站点不存在")

    try:
        client = get_portal_client(site)
        result = await client.approve_registration(reg_id)
        result["portal_site_id"] = site.id
        result["portal_site_name"] = site.name
        return result
    except Exception as e:
        if "已处理" in str(e):
            raise HTTPException(status_code=400, detail="该申请已被处理")
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail="注册申请不存在")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{portal_site_id}/{reg_id}/reject")
async def reject_registration(
    portal_site_id: int,
    reg_id: int,
    data: RegistrationReject,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """拒绝注册申请"""
    site = db.query(PortalSite).filter(PortalSite.id == portal_site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Portal站点不存在")

    try:
        client = get_portal_client(site)
        result = await client.reject_registration(reg_id, data.reason)
        result["portal_site_id"] = site.id
        result["portal_site_name"] = site.name
        return result
    except Exception as e:
        if "已处理" in str(e):
            raise HTTPException(status_code=400, detail="该申请已被处理")
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail="注册申请不存在")
        raise HTTPException(status_code=500, detail=str(e))
