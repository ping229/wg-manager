import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.shared.database import get_db
from backend.shared.models import Peer, Node, Admin
from backend.shared.schemas import PeerResponse, PeerLimit
from backend.shared.auth import get_current_admin, encryption

router = APIRouter(prefix="/api/peers", tags=["Peer管理"])


async def remove_peer_from_agent(node: Node, public_key: str):
    """从Agent删除Peer"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{node.api_url.rstrip('/')}/api/peer/remove",
                json={"public_key": public_key},
                headers={"X-API-Key": encryption.decrypt(node.api_key)},
                timeout=10.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Agent调用失败: {response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Agent连接失败: {str(e)}")


async def set_peer_limit(node: Node, address: str, upload: int, download: int):
    """设置Peer限速"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{node.api_url.rstrip('/')}/api/peer/limit",
                json={
                    "address": address,
                    "upload_limit": upload,
                    "download_limit": download
                },
                headers={"X-API-Key": encryption.decrypt(node.api_key)},
                timeout=10.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Agent调用失败: {response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Agent连接失败: {str(e)}")


@router.get("", response_model=list[PeerResponse])
def list_peers(
    node_id: int = None,
    user_id: int = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取Peer列表"""
    query = db.query(Peer)

    if node_id:
        query = query.filter(Peer.node_id == node_id)
    if user_id:
        query = query.filter(Peer.user_id == user_id)

    peers = query.all()
    return peers


@router.get("/{peer_id}", response_model=PeerResponse)
def get_peer(
    peer_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取Peer详情"""
    peer = db.query(Peer).filter(Peer.id == peer_id).first()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer不存在")
    return peer


@router.delete("/{peer_id}")
async def delete_peer(
    peer_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除Peer"""
    peer = db.query(Peer).filter(Peer.id == peer_id).first()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer不存在")

    node = db.query(Node).filter(Node.id == peer.node_id).first()
    if node:
        await remove_peer_from_agent(node, peer.public_key)

    db.delete(peer)
    db.commit()

    return {"message": "Peer已删除"}


@router.put("/{peer_id}/limit")
async def update_peer_limit(
    peer_id: int,
    data: PeerLimit,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """设置Peer限速"""
    peer = db.query(Peer).filter(Peer.id == peer_id).first()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer不存在")

    node = db.query(Node).filter(Node.id == peer.node_id).first()
    if node:
        await set_peer_limit(node, peer.address, data.upload_limit, data.download_limit)

    peer.upload_limit = data.upload_limit
    peer.download_limit = data.download_limit
    db.commit()

    return {"message": "限速设置已更新"}
