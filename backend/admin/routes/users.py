from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import httpx

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.admin.database import get_db
from backend.admin.models import AdminUser, Peer, Node, PortalSite
from backend.shared.auth import get_current_admin, encryption
from backend.admin.services.portal_client import get_portal_client

router = APIRouter(prefix="/api/users", tags=["用户管理"])


# ============ 请求模型 ============

class UserCreate(BaseModel):
    username: str
    password: str
    email: EmailStr


class BatchUserCreate(BaseModel):
    portal_site_id: int
    users: List[UserCreate]


class BatchUserDelete(BaseModel):
    portal_site_id: int
    user_ids: List[int]


# ============ 用户列表 ============

@router.get("")
async def list_users(
    portal_site_id: int = Query(None, description="Portal站点ID"),
    status: str = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    portal_sites = db.query(PortalSite).filter(PortalSite.status == "active").all()

    if not portal_sites:
        return []

    all_users = []

    if portal_site_id:
        portal_sites = [s for s in portal_sites if s.id == portal_site_id]

    for site in portal_sites:
        try:
            client = get_portal_client(site)
            users = await client.get_users()

            for user in users:
                user["portal_site_id"] = site.id
                user["portal_site_name"] = site.name

                peer = db.query(Peer).filter(
                    Peer.portal_site_id == site.id,
                    Peer.portal_user_id == user["id"]
                ).first()

                if peer:
                    node = db.query(Node).filter(Node.id == peer.node_id).first()
                    user["peer"] = {
                        "id": peer.id,
                        "node_id": peer.node_id,
                        "node_name": node.name if node else None,
                        "address": peer.address,
                        "created_at": peer.created_at.isoformat() if peer.created_at else None
                    }
                else:
                    user["peer"] = None

                all_users.append(user)
        except Exception as e:
            print(f"Failed to get users from {site.name}: {e}")
            continue

    if status:
        all_users = [u for u in all_users if u.get("status") == status]

    return all_users


# ============ 创建用户 ============

@router.post("/create")
async def create_user(
    portal_site_id: int = Body(...),
    username: str = Body(...),
    password: str = Body(...),
    email: str = Body(...),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """创建用户"""
    site = db.query(PortalSite).filter(PortalSite.id == portal_site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Portal站点不存在")

    try:
        client = get_portal_client(site)
        result = await client.create_user(username, password, email)
        result["portal_site_id"] = site.id
        result["portal_site_name"] = site.name
        return result
    except Exception as e:
        if "已存在" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-create")
async def batch_create_users(
    data: BatchUserCreate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """批量创建用户"""
    site = db.query(PortalSite).filter(PortalSite.id == data.portal_site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Portal站点不存在")

    try:
        client = get_portal_client(site)
        users_data = [u.model_dump() for u in data.users]
        result = await client.batch_create_users(users_data)
        result["portal_site_id"] = site.id
        result["portal_site_name"] = site.name
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 删除用户 ============

@router.delete("/{portal_site_id}/{user_id}")
async def delete_user(
    portal_site_id: int,
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """删除用户"""
    site = db.query(PortalSite).filter(PortalSite.id == portal_site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Portal站点不存在")

    try:
        client = get_portal_client(site)
        result = await client.delete_user(user_id)
        return result
    except Exception as e:
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail="用户不存在")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-delete")
async def batch_delete_users(
    data: BatchUserDelete,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """批量删除用户"""
    site = db.query(PortalSite).filter(PortalSite.id == data.portal_site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Portal站点不存在")

    try:
        client = get_portal_client(site)
        result = await client.batch_delete_users(data.user_ids)
        result["portal_site_id"] = site.id
        result["portal_site_name"] = site.name
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 用户详情 ============

@router.get("/{portal_site_id}/{user_id}")
async def get_user(
    portal_site_id: int,
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取用户详情"""
    site = db.query(PortalSite).filter(PortalSite.id == portal_site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Portal站点不存在")

    try:
        client = get_portal_client(site)
        user = await client.get_user(user_id)
        user["portal_site_id"] = site.id
        user["portal_site_name"] = site.name

        peer = db.query(Peer).filter(
            Peer.portal_site_id == site.id,
            Peer.portal_user_id == user_id
        ).first()

        if peer:
            node = db.query(Node).filter(Node.id == peer.node_id).first()
            user["peer"] = {
                "id": peer.id,
                "node_id": peer.node_id,
                "node_name": node.name if node else None,
                "address": peer.address,
                "created_at": peer.created_at.isoformat() if peer.created_at else None
            }
        else:
            user["peer"] = None

        return user
    except Exception as e:
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail="用户不存在")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 用户状态管理 ============

@router.post("/{portal_site_id}/{user_id}/disable")
async def disable_user(
    portal_site_id: int,
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """禁用用户"""
    site = db.query(PortalSite).filter(PortalSite.id == portal_site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Portal站点不存在")

    try:
        client = get_portal_client(site)
        await client.update_user_status(user_id, "disabled")

        # 删除用户的所有 Peer
        peers = db.query(Peer).filter(
            Peer.portal_site_id == portal_site_id,
            Peer.portal_user_id == user_id
        ).all()

        for peer in peers:
            node = db.query(Node).filter(Node.id == peer.node_id).first()
            if node:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            f"{node.api_url.rstrip('/')}/api/peer/remove",
                            json={"public_key": peer.public_key},
                            headers={"X-API-Key": encryption.decrypt(node.api_key)},
                            timeout=10.0
                        )
                except Exception:
                    pass
            db.delete(peer)

        db.commit()

        return {"message": "用户已禁用，所有 Peer 已清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{portal_site_id}/{user_id}/enable")
async def enable_user(
    portal_site_id: int,
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """启用用户"""
    site = db.query(PortalSite).filter(PortalSite.id == portal_site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Portal站点不存在")

    try:
        client = get_portal_client(site)
        await client.update_user_status(user_id, "active")
        return {"message": "用户已启用"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{portal_site_id}/{user_id}/peer")
async def delete_user_peer(
    portal_site_id: int,
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """删除用户的 Peer 配置"""
    peer = db.query(Peer).filter(
        Peer.portal_site_id == portal_site_id,
        Peer.portal_user_id == user_id
    ).first()

    if not peer:
        raise HTTPException(status_code=404, detail="该用户没有 Peer 配置")

    node = db.query(Node).filter(Node.id == peer.node_id).first()
    if node:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{node.api_url.rstrip('/')}/api/peer/remove",
                    json={"public_key": peer.public_key},
                    headers={"X-API-Key": encryption.decrypt(node.api_key)},
                    timeout=10.0
                )
        except Exception:
            pass

    db.delete(peer)
    db.commit()

    return {"message": "Peer 配置已删除"}


@router.put("/{portal_site_id}/{user_id}/password")
async def update_user_password(
    portal_site_id: int,
    user_id: int,
    password: str = Body(..., embed=True),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """修改用户密码"""
    site = db.query(PortalSite).filter(PortalSite.id == portal_site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Portal站点不存在")

    try:
        client = get_portal_client(site)
        result = await client.update_user_password(user_id, password)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
