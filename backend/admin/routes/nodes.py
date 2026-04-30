import subprocess
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.admin.database import get_db
from backend.admin.models import Node, Peer, AdminUser
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
    # 优先使用 key，否则使用解密的 api_key（向后兼容）
    auth_key = node.key or encryption.decrypt(node.api_key)
    async with httpx.AsyncClient() as client:
        try:
            url = f"{node.api_url.rstrip('/')}{endpoint}"
            headers = {"X-Key": auth_key}
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


def get_node_auth_key(node: Node) -> str:
    """获取节点认证密钥"""
    return node.key or encryption.decrypt(node.api_key)


@router.get("")
async def list_nodes(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """获取节点列表（包含在线状态）"""
    nodes = db.query(Node).all()

    result = []
    for node in nodes:
        is_online = await check_node_online(node)

        # 从Agent获取实际peer数量
        peer_count = 0
        if is_online:
            try:
                auth_key = get_node_auth_key(node)
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{node.api_url.rstrip('/')}/api/status",
                        headers={"X-Key": auth_key},
                        timeout=3.0
                    )
                    if response.status_code == 200:
                        status = response.json()
                        peer_count = status.get("peer_count", 0)
            except Exception:
                pass

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
            "peer_count": peer_count,
            "api_url": node.api_url,
            "key": node.key,
            "blocked_patterns": node.blocked_patterns,
            "created_at": node.created_at
        })

    return result


@router.get("/{node_id}")
async def get_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """获取单个节点详情"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    is_online = await check_node_online(node)
    return {
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
        "key": node.key,
        "blocked_patterns": node.blocked_patterns,
        "created_at": node.created_at
    }


@router.post("", response_model=NodeResponse)
def create_node(
    data: NodeCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """创建节点"""
    if db.query(Node).filter(Node.name == data.name).first():
        raise HTTPException(status_code=400, detail="节点名称已存在")

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
        key=data.key,
        api_key=encryption.encrypt(data.api_key) if data.api_key else "",
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
    current_admin: AdminUser = Depends(get_current_admin)
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

    for field in ["endpoint", "wg_port", "wg_interface", "address_pool", "dns", "mtu", "keepalive", "default_upload_limit", "default_download_limit", "api_url", "blocked_patterns", "key"]:
        value = getattr(data, field, None)
        if value is not None:
            setattr(node, field, value)

    if data.api_key is not None and data.api_key != '':
        node.api_key = encryption.encrypt(data.api_key)

    db.commit()
    db.refresh(node)

    return node


@router.delete("/{node_id}")
async def delete_node(
    node_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """删除节点"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    peers = db.query(Peer).filter(Peer.node_id == node_id).all()

    if peers:
        if not force:
            raise HTTPException(
                status_code=400,
                detail=f"该节点下还有 {len(peers)} 个Peer，请先清空或使用强制删除"
            )

        try:
            await call_agent(node, "/api/peer/clear")
        except HTTPException:
            pass

        for peer in peers:
            db.delete(peer)

    db.delete(node)
    db.commit()

    return {"message": "节点已删除", "cleared_peers": len(peers)}


@router.post("/{node_id}/disable")
async def disable_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """禁用节点"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    if node.status == "disabled":
        raise HTTPException(status_code=400, detail="节点已被禁用")

    peers = db.query(Peer).filter(Peer.node_id == node_id).all()
    try:
        await call_agent(node, "/api/peer/clear")
    except HTTPException:
        pass

    for peer in peers:
        db.delete(peer)

    node.status = "disabled"
    db.commit()

    return {"message": "节点已禁用，所有Peer已清空"}


@router.post("/{node_id}/enable")
def enable_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
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
    current_admin: AdminUser = Depends(get_current_admin)
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


# ============ 批量操作 ============

from typing import List
from pydantic import BaseModel


class BatchNodeIds(BaseModel):
    """批量节点 ID 列表"""
    node_ids: List[int]


@router.post("/batch-enable")
async def batch_enable_nodes(
    data: BatchNodeIds,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """批量启用节点"""
    success = 0
    failed = 0

    for node_id in data.node_ids:
        node = db.query(Node).filter(Node.id == node_id).first()
        if node and node.status != "active":
            node.status = "active"
            success += 1
        else:
            failed += 1

    db.commit()
    return {"message": f"成功启用 {success} 个节点", "success": success, "failed": failed}


@router.post("/batch-disable")
async def batch_disable_nodes(
    data: BatchNodeIds,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """批量禁用节点"""
    success = 0
    failed = 0

    for node_id in data.node_ids:
        node = db.query(Node).filter(Node.id == node_id).first()
        if node and node.status != "disabled":
            # 清空该节点的所有 Peer
            peers = db.query(Peer).filter(Peer.node_id == node_id).all()
            try:
                await call_agent(node, "/api/peer/clear")
            except:
                pass
            for peer in peers:
                db.delete(peer)
            node.status = "disabled"
            success += 1
        else:
            failed += 1

    db.commit()
    return {"message": f"成功禁用 {success} 个节点", "success": success, "failed": failed}


@router.post("/batch-delete")
async def batch_delete_nodes(
    data: BatchNodeIds,
    force: bool = False,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """批量删除节点"""
    success = 0
    failed = 0

    for node_id in data.node_ids:
        node = db.query(Node).filter(Node.id == node_id).first()
        if not node:
            failed += 1
            continue

        peers = db.query(Peer).filter(Peer.node_id == node_id).all()
        if peers and not force:
            failed += 1
            continue

        try:
            await call_agent(node, "/api/peer/clear")
        except:
            pass

        for peer in peers:
            db.delete(peer)
        db.delete(node)
        success += 1

    db.commit()
    return {"message": f"成功删除 {success} 个节点", "success": success, "failed": failed}


# ============ 导入导出 ============

import json


@router.get("/export")
def export_nodes(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """导出节点配置"""
    nodes = db.query(Node).all()

    export_data = []
    for node in nodes:
        export_data.append({
            "name": node.name,
            "endpoint": node.endpoint,
            "wg_port": node.wg_port,
            "wg_interface": node.wg_interface,
            "public_key": node.public_key,
            "private_key": encryption.decrypt(node.private_key),
            "address_pool": node.address_pool,
            "dns": node.dns,
            "mtu": node.mtu,
            "keepalive": node.keepalive,
            "default_upload_limit": node.default_upload_limit or 0,
            "default_download_limit": node.default_download_limit or 0,
            "api_url": node.api_url,
            "key": node.key,
            "blocked_patterns": node.blocked_patterns
        })

    return {"nodes": export_data, "count": len(export_data)}


class NodeImport(BaseModel):
    """节点导入数据"""
    name: str
    endpoint: str
    wg_port: int = 51820
    wg_interface: str = "wg0"
    public_key: str
    private_key: str
    address_pool: str
    dns: str = "8.8.8.8"
    mtu: int = 1420
    keepalive: int = 25
    default_upload_limit: int = 0
    default_download_limit: int = 0
    api_url: str
    key: str
    blocked_patterns: Optional[str] = None


class NodesImport(BaseModel):
    """批量导入节点"""
    nodes: List[NodeImport]


@router.post("/import")
def import_nodes(
    data: NodesImport,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """导入节点配置"""
    success = 0
    failed = 0
    errors = []

    for node_data in data.nodes:
        try:
            # 检查名称是否已存在
            if db.query(Node).filter(Node.name == node_data.name).first():
                errors.append(f"节点 {node_data.name}: 名称已存在")
                failed += 1
                continue

            node = Node(
                name=node_data.name,
                endpoint=node_data.endpoint,
                wg_port=node_data.wg_port,
                wg_interface=node_data.wg_interface,
                public_key=node_data.public_key,
                private_key=encryption.encrypt(node_data.private_key),
                address_pool=node_data.address_pool,
                dns=node_data.dns,
                mtu=node_data.mtu,
                keepalive=node_data.keepalive,
                default_upload_limit=node_data.default_upload_limit,
                default_download_limit=node_data.default_download_limit,
                api_url=node_data.api_url,
                key=node_data.key,
                api_key="",
                blocked_patterns=node_data.blocked_patterns,
                status="active"
            )
            db.add(node)
            success += 1
        except Exception as e:
            errors.append(f"节点 {node_data.name}: {str(e)}")
            failed += 1

    db.commit()
    return {
        "message": f"成功导入 {success} 个节点，失败 {failed} 个",
        "success": success,
        "failed": failed,
        "errors": errors
    }
