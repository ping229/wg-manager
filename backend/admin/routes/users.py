from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.admin.database import get_db
from backend.admin.models import AdminUser, Peer, Node, PortalSite
from backend.shared.auth import get_current_admin, encryption
from backend.admin.services.portal_client import get_portal_client

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("")
async def list_users(
    portal_site_id: int = Query(None, description="Portal站点ID"),
    status: str = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    # 获取所有 Portal 站点
    portal_sites = db.query(PortalSite).filter(PortalSite.status == "active").all()

    if not portal_sites:
        return []

    all_users = []

    # 如果指定了 portal_site_id，只查询该站点
    if portal_site_id:
        portal_sites = [s for s in portal_sites if s.id == portal_site_id]

    for site in portal_sites:
        try:
            client = get_portal_client(site)
            users = await client.get_users()

            for user in users:
                user["portal_site_id"] = site.id
                user["portal_site_name"] = site.name

                # 获取 Peer 信息
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
            # 跳过连接失败的站点
            print(f"Failed to get users from {site.name}: {e}")
            continue

    # 按状态过滤
    if status:
        all_users = [u for u in all_users if u.get("status") == status]

    return all_users


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

        # 获取 Peer 信息
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


@router.post("/{portal_site_id}/{user_id}/disable")
async def disable_user(
    portal_site_id: int,
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """禁用用户"""
    import httpx

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
    import httpx

    peer = db.query(Peer).filter(
        Peer.portal_site_id == portal_site_id,
        Peer.portal_user_id == user_id
    ).first()

    if not peer:
        raise HTTPException(status_code=404, detail="该用户没有 Peer 配置")

    # 从 Agent 删除 Peer
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
