from fastapi import APIRouter, Depends, HTTPException, Header

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.shared.config import settings
from backend.shared.schemas import (
    AgentPeerAdd,
    AgentPeerRemove,
    AgentPeerLimit,
    AgentPeerInfo,
    AgentStatus
)
from backend.agent.services.wireguard import WireGuardService
from backend.agent.services.traffic import TrafficControlService

router = APIRouter(prefix="/api/peer", tags=["Peer管理"])

# 服务实例
wg_service = WireGuardService()
traffic_service = TrafficControlService()


def verify_api_key(x_api_key: str = Header(None)):
    """验证API密钥"""
    # 从环境变量或配置中获取有效密钥
    valid_key = settings.ENCRYPTION_KEY  # 实际使用时应该从配置中读取
    if not x_api_key or x_api_key != valid_key:
        raise HTTPException(status_code=401, detail="无效的API密钥")
    return True


@router.post("/add")
def add_peer(
    data: AgentPeerAdd,
    authorized: bool = Depends(verify_api_key)
):
    """添加Peer"""
    if not wg_service.add_peer(data.public_key, data.address):
        raise HTTPException(status_code=500, detail="添加Peer失败")

    return {"success": True, "message": "Peer已添加"}


@router.post("/remove")
def remove_peer(
    data: AgentPeerRemove,
    authorized: bool = Depends(verify_api_key)
):
    """删除Peer"""
    if not wg_service.remove_peer(data.public_key):
        raise HTTPException(status_code=500, detail="删除Peer失败")

    return {"success": True, "message": "Peer已删除"}


@router.post("/clear")
def clear_peers(authorized: bool = Depends(verify_api_key)):
    """清空所有Peer"""
    count = wg_service.clear_peers()
    traffic_service.clear_all()

    return {"success": True, "message": f"已清空 {count} 个Peer"}


@router.get("/list")
def list_peers(authorized: bool = Depends(verify_api_key)):
    """获取Peer列表"""
    peers = wg_service.get_peers()
    return {"peers": peers, "count": len(peers)}


@router.post("/limit")
def set_peer_limit(
    data: AgentPeerLimit,
    authorized: bool = Depends(verify_api_key)
):
    """设置Peer限速"""
    if not traffic_service.set_peer_limit(
        data.address,
        data.upload_limit,
        data.download_limit
    ):
        raise HTTPException(status_code=500, detail="设置限速失败")

    return {"success": True, "message": "限速已设置"}
