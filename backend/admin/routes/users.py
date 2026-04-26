import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.shared.database import get_db
from backend.shared.models import User, Peer, Node, Admin
from backend.shared.schemas import UserResponse, UserUpdate
from backend.shared.auth import get_current_admin, get_password_hash, encryption

router = APIRouter(prefix="/api/users", tags=["用户管理"])


async def remove_peer_from_agent(node: Node, public_key: str):
    """从Agent删除Peer"""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{node.api_url.rstrip('/')}/api/peer/remove",
                json={"public_key": public_key},
                headers={"X-API-Key": encryption.decrypt(node.api_key)},
                timeout=10.0
            )
        except Exception:
            pass


@router.get("")
def list_users(
    status: str = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取用户列表"""
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    users = query.all()

    result = []
    for user in users:
        # 查找用户的Peer信息
        peer = db.query(Peer).filter(Peer.user_id == user.id).first()
        peer_info = None
        if peer:
            node = db.query(Node).filter(Node.id == peer.node_id).first()
            peer_info = {
                "id": peer.id,
                "node_id": peer.node_id,
                "node_name": node.name if node else None,
                "address": peer.address,
                "created_at": peer.created_at
            }

        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "status": user.status,
            "created_at": user.created_at,
            "approved_at": user.approved_at,
            "peer": peer_info
        })

    return result


@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取用户详情"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 查找用户的Peer信息
    peer = db.query(Peer).filter(Peer.user_id == user.id).first()
    peer_info = None
    if peer:
        node = db.query(Node).filter(Node.id == peer.node_id).first()
        peer_info = {
            "id": peer.id,
            "node_id": peer.node_id,
            "node_name": node.name if node else None,
            "address": peer.address,
            "created_at": peer.created_at
        }

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "status": user.status,
        "created_at": user.created_at,
        "approved_at": user.approved_at,
        "peer": peer_info
    }


@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """更新用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if data.email is not None:
        existing = db.query(User).filter(User.email == data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="邮箱已被使用")
        user.email = data.email

    if data.password is not None:
        user.password_hash = get_password_hash(data.password)

    db.commit()
    db.refresh(user)

    return {"message": "用户已更新", "user": UserResponse.model_validate(user)}


@router.post("/{user_id}/disable")
async def disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """禁用用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.status == "disabled":
        raise HTTPException(status_code=400, detail="用户已被禁用")

    # 删除用户的所有Peer
    peers = db.query(Peer).filter(Peer.user_id == user_id).all()
    for peer in peers:
        node = db.query(Node).filter(Node.id == peer.node_id).first()
        if node:
            await remove_peer_from_agent(node, peer.public_key)
        db.delete(peer)

    user.status = "disabled"
    db.commit()

    return {"message": "用户已禁用,所有Peer已清空"}


@router.post("/{user_id}/enable")
def enable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """启用用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.status == "active":
        raise HTTPException(status_code=400, detail="用户已处于启用状态")

    user.status = "active"
    db.commit()

    return {"message": "用户已启用"}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查是否有Peer
    peer = db.query(Peer).filter(Peer.user_id == user_id).first()
    if peer:
        raise HTTPException(status_code=400, detail="请先禁用用户以清空Peer")

    db.delete(user)
    db.commit()

    return {"message": "用户已删除"}


@router.delete("/{user_id}/peer")
async def delete_user_peer(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除用户的Peer配置"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    peer = db.query(Peer).filter(Peer.user_id == user_id).first()
    if not peer:
        raise HTTPException(status_code=404, detail="该用户没有Peer配置")

    # 从Agent删除Peer
    node = db.query(Node).filter(Node.id == peer.node_id).first()
    if node:
        await remove_peer_from_agent(node, peer.public_key)

    db.delete(peer)
    db.commit()

    return {"message": "Peer配置已删除"}
