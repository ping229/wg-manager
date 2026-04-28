"""
Portal 站点管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import httpx
import secrets

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.admin.database import get_db
from backend.admin.models import PortalSite, AdminUser
from backend.shared.auth import get_current_admin

router = APIRouter(prefix="/api/portal-sites", tags=["Portal站点管理"])


class PortalSiteCreate(BaseModel):
    name: str
    url: str
    api_key: str
    description: Optional[str] = None


class PortalSiteUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    api_key: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class PortalSiteResponse(BaseModel):
    id: int
    name: str
    url: str
    description: Optional[str] = None
    status: str
    online: bool = False
    created_at: str

    class Config:
        from_attributes = True


@router.get("")
async def list_portal_sites(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """获取 Portal 站点列表"""
    sites = db.query(PortalSite).all()

    result = []
    for site in sites:
        # 检查是否在线
        online = False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{site.url.rstrip('/')}/health",
                    headers={"X-Admin-API-Key": site.api_key},
                    timeout=3.0
                )
                online = response.status_code == 200
        except:
            pass

        result.append({
            "id": site.id,
            "name": site.name,
            "url": site.url,
            "description": site.description,
            "status": site.status,
            "online": online,
            "created_at": site.created_at.isoformat() if site.created_at else None
        })

    return result


@router.post("")
def create_portal_site(
    data: PortalSiteCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """创建 Portal 站点"""
    if db.query(PortalSite).filter(PortalSite.name == data.name).first():
        raise HTTPException(status_code=400, detail="站点名称已存在")

    # Portal API Key 明文存储（只是调用凭证，不需要加密）
    site = PortalSite(
        name=data.name,
        url=data.url,
        api_key=data.api_key,
        description=data.description,
        status="active"
    )
    db.add(site)
    db.commit()
    db.refresh(site)

    return {
        "id": site.id,
        "name": site.name,
        "url": site.url,
        "description": site.description,
        "status": site.status,
        "created_at": site.created_at.isoformat() if site.created_at else None
    }


@router.put("/{site_id}")
def update_portal_site(
    site_id: int,
    data: PortalSiteUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """更新 Portal 站点"""
    site = db.query(PortalSite).filter(PortalSite.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    if data.name is not None:
        existing = db.query(PortalSite).filter(
            PortalSite.name == data.name,
            PortalSite.id != site_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="站点名称已存在")
        site.name = data.name

    if data.url is not None:
        site.url = data.url

    if data.api_key is not None:
        site.api_key = data.api_key  # 明文存储

    if data.description is not None:
        site.description = data.description

    if data.status is not None:
        site.status = data.status

    db.commit()
    db.refresh(site)

    return {
        "id": site.id,
        "name": site.name,
        "url": site.url,
        "description": site.description,
        "status": site.status,
        "created_at": site.created_at.isoformat() if site.created_at else None
    }


@router.delete("/{site_id}")
def delete_portal_site(
    site_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """删除 Portal 站点"""
    from backend.admin.models import Peer

    site = db.query(PortalSite).filter(PortalSite.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    # 检查是否有关联的 Peer
    peer_count = db.query(Peer).filter(Peer.portal_site_id == site_id).count()
    if peer_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该站点下还有 {peer_count} 个 Peer，请先清理"
        )

    db.delete(site)
    db.commit()

    return {"message": "站点已删除"}


@router.post("/{site_id}/test")
async def test_portal_site(
    site_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """测试 Portal 站点连接"""
    site = db.query(PortalSite).filter(PortalSite.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{site.url.rstrip('/')}/health",
                headers={"X-Admin-API-Key": site.api_key},
                timeout=5.0
            )
            if response.status_code == 200:
                return {"success": True, "message": "连接成功"}
            else:
                return {"success": False, "message": f"HTTP {response.status_code}"}
    except httpx.RequestError as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"错误: {str(e)}"}


# ============ Admin API Key 管理 ============

from backend.admin.models import AdminSetting


@router.get("/admin-api-key")
def get_admin_api_key(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """获取 Admin API Key（用于 Portal 连接 Admin）"""
    setting = db.query(AdminSetting).filter(AdminSetting.key == "admin_api_key").first()
    if not setting:
        # 自动生成一个
        api_key = secrets.token_hex(16)
        setting = AdminSetting(key="admin_api_key", value=api_key)
        db.add(setting)
        db.commit()

    return {"admin_api_key": setting.value}


@router.post("/admin-api-key/regenerate")
def regenerate_admin_api_key(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """重新生成 Admin API Key"""
    new_key = secrets.token_hex(16)
    setting = db.query(AdminSetting).filter(AdminSetting.key == "admin_api_key").first()
    if setting:
        setting.value = new_key
    else:
        setting = AdminSetting(key="admin_api_key", value=new_key)
        db.add(setting)
    db.commit()

    return {"admin_api_key": new_key, "message": "API Key 已重新生成，请更新所有 Portal 的配置"}
