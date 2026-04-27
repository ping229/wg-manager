from fastapi import APIRouter, Depends, HTTPException

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.admin.database import get_db
from backend.admin.models import AdminUser, Peer, Node
from backend.shared.auth import get_current_admin
from backend.admin.services.portal_client import portal_client

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("")
async def list_users(
    status: str = None,
    current_admin: AdminUser = Depends(get_current_admin)
):
    """获取用户列表"""
    try:
        users = await portal_client.get_users()

        # 获取所有 Peer 信息
        db = next(get_db())
        for user in users:
            peer = db.query(Peer).filter(Peer.portal_user_id == user["id"]).first()
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

        # 按状态过滤
        if status:
            users = [u for u in users if u["status"] == status]

        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin)
):
    """获取用户详情"""
    try:
        user = await portal_client.get_user(user_id)

        # 获取 Peer 信息
        db = next(get_db())
        peer = db.query(Peer).filter(Peer.portal_user_id == user_id).first()
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


@router.post("/{user_id}/disable")
async def disable_user(
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin)
):
    """禁用用户"""
    import httpx
    from backend.admin.config import settings
    from backend.shared.auth import encryption

    try:
        # 获取用户信息
        user = await portal_client.get_user(user_id)

        # 更新用户状态
        await portal_client.update_user_status(user_id, "disabled")

        # 删除用户的所有 Peer
        db = next(get_db())
        peers = db.query(Peer).filter(Peer.portal_user_id == user_id).all()

        for peer in peers:
            node = db.query(Node).filter(Node.id == peer.node_id).first()
            if node:
                # 从 Agent 删除 Peer
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


@router.post("/{user_id}/enable")
async def enable_user(
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin)
):
    """启用用户"""
    try:
        await portal_client.update_user_status(user_id, "active")
        return {"message": "用户已启用"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}/peer")
async def delete_user_peer(
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin)
):
    """删除用户的 Peer 配置"""
    import httpx
    from backend.shared.auth import encryption

    db = next(get_db())
    peer = db.query(Peer).filter(Peer.portal_user_id == user_id).first()
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
