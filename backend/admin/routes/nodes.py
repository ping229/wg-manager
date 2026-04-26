import subprocess
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.shared.database import get_db
from backend.shared.models import Node, Peer, Admin
from backend.shared.schemas import NodeCreate, NodeUpdate, NodeResponse
from backend.shared.auth import get_current_admin, encryption

router = APIRouter(prefix="/api/nodes", tags=["节点管理"])


def generate_keypair() -> tuple[str, str]:
    """生成WireGuard密钥对"""
    private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
    public_key = subprocess.run(
        ["wg", "pubkey"],
        input=private_key.encode(),
        capture_output=True
    ).stdout.decode().strip()
    return private_key, public_key


async def call_agent(node: Node, endpoint: str, data: dict = None) -> dict:
    """调用Agent API"""
    async with httpx.AsyncClient() as client:
        try:
            url = f"{node.api_url.rstrip('/')}{endpoint}"
            headers = {"X-API-Key": encryption.decrypt(node.api_key)}
            if data:
                response = await client.post(url, json=data, headers=headers, timeout=10.0)
            else:
                response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Agent调用失败: {response.text}")
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Agent连接失败: {str(e)}")


async def check_node_online(node: Node) -> bool:
    """检查节点是否在线"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node.api_url.rstrip('/')}/health",
                timeout=3.0
            )
            return response.status_code == 200
    except:
        return False


@router.get("")
async def list_nodes(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取节点列表（包含在线状态）"""
    nodes = db.query(Node).all()

    result = []
    for node in nodes:
        is_online = await check_node_online(node)
        result.append({
            "id": node.id,
            "name": node.name,
            "endpoint": node.endpoint,
            "wg_port": node.wg_port,
            "wg_interface": node.wg_interface,
            "public_key": node.public_key,
            "address_pool": node.address_pool,
            "dns": node.dns,
            "mtu": node.mtu,
            "keepalive": node.keepalive,
            "default_upload_limit": node.default_upload_limit or 0,
            "default_download_limit": node.default_download_limit or 0,
            "status": node.status,
            "online": is_online,
            "api_url": node.api_url,
            "created_at": node.created_at
        })

    return result


@router.post("", response_model=NodeResponse)
def create_node(
    data: NodeCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """创建节点"""
    # 检查名称是否重复
    if db.query(Node).filter(Node.name == data.name).first():
        raise HTTPException(status_code=400, detail="节点名称已存在")

    # 生成密钥对
    private_key, public_key = generate_keypair()

    node = Node(
        name=data.name,
        endpoint=data.endpoint,
        wg_port=data.wg_port,
        wg_interface=data.wg_interface,
        public_key=public_key,
        private_key=encryption.encrypt(private_key),
        address_pool=data.address_pool,
        dns=data.dns,
        mtu=data.mtu,
        keepalive=data.keepalive,
        default_upload_limit=data.default_upload_limit,
        default_download_limit=data.default_download_limit,
        api_url=data.api_url,
        api_key=encryption.encrypt(data.api_key),
        status="active"
    )
    db.add(node)
    db.commit()
    db.refresh(node)

    return node


@router.put("/{node_id}", response_model=NodeResponse)
def update_node(
    node_id: int,
    data: NodeUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """更新节点"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    if data.name is not None:
        existing = db.query(Node).filter(Node.name == data.name, Node.id != node_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="节点名称已存在")
        node.name = data.name

    for field in ["endpoint", "wg_port", "wg_interface", "address_pool", "dns", "mtu", "keepalive", "default_upload_limit", "default_download_limit", "api_url"]:
        value = getattr(data, field, None)
        if value is not None:
            setattr(node, field, value)

    if data.api_key is not None:
        node.api_key = encryption.encrypt(data.api_key)

    db.commit()
    db.refresh(node)

    return node


@router.delete("/{node_id}")
def delete_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除节点"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    # 检查是否有Peer
    peer_count = db.query(Peer).filter(Peer.node_id == node_id).count()
    if peer_count > 0:
        raise HTTPException(status_code=400, detail=f"该节点下还有 {peer_count} 个Peer,请先清空")

    db.delete(node)
    db.commit()

    return {"message": "节点已删除"}


@router.post("/{node_id}/disable")
async def disable_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """禁用节点"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    if node.status == "disabled":
        raise HTTPException(status_code=400, detail="节点已被禁用")

    # 清空所有Peer
    peers = db.query(Peer).filter(Peer.node_id == node_id).all()
    try:
        await call_agent(node, "/api/peer/clear")
    except HTTPException:
        pass  # 即使Agent调用失败也继续

    for peer in peers:
        db.delete(peer)

    node.status = "disabled"
    db.commit()

    return {"message": "节点已禁用,所有Peer已清空"}


@router.post("/{node_id}/enable")
def enable_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """启用节点"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    if node.status == "active":
        raise HTTPException(status_code=400, detail="节点已处于启用状态")

    node.status = "active"
    db.commit()

    return {"message": "节点已启用"}


@router.post("/{node_id}/sync")
async def sync_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """同步节点状态"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    try:
        status = await call_agent(node, "/api/status")
        return {
            "node_status": node.status,
            "agent_status": status,
            "synced": True
        }
    except HTTPException as e:
        return {
            "node_status": node.status,
            "agent_status": None,
            "synced": False,
            "error": str(e.detail)
        }
