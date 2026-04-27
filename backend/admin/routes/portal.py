"""
Portal API 路由 - 供 Portal 服务调用
包含：节点列表、Peer 管理、配置下载等功能
支持多 Portal 站点
"""
import ipaddress
import subprocess
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import httpx

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.admin.database import get_db
from backend.admin.models import Node, Peer, PortalSite
from backend.shared.auth import encryption

router = APIRouter(prefix="/api/portal", tags=["Portal API"])


def verify_portal_site(
    api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    db: Session = Depends(get_db)
) -> PortalSite:
    """验证 Portal API 密钥并返回对应的 Portal 站点"""
    if not api_key:
        raise HTTPException(status_code=401, detail="缺少 API 密钥")

    # 查找匹配的 Portal 站点
    sites = db.query(PortalSite).filter(PortalSite.status == "active").all()
    for site in sites:
        try:
            decrypted_key = encryption.decrypt(site.api_key)
            if decrypted_key == api_key:
                return site
        except:
            continue

    raise HTTPException(status_code=403, detail="无效的 API 密钥")


def generate_keypair() -> tuple[str, str]:
    """生成WireGuard密钥对"""
    private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
    public_key = subprocess.run(
        ["wg", "pubkey"],
        input=private_key.encode(),
        capture_output=True
    ).stdout.decode().strip()
    return private_key, public_key


def allocate_ip(db: Session, node: Node) -> str:
    """分配IP地址"""
    peers = db.query(Peer).filter(Peer.node_id == node.id).all()
    used_ips = {peer.address for peer in peers}
    network = ipaddress.ip_network(node.address_pool, strict=False)
    hosts = list(network.hosts())

    for host in hosts[1:]:  # 从第二个IP开始分配
        ip = str(host)
        if ip not in used_ips:
            return ip

    raise HTTPException(status_code=500, detail="IP地址池已用尽")


async def call_agent(node: Node, endpoint: str, data: dict) -> dict:
    """调用Agent API"""
    api_key = encryption.decrypt(node.api_key)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{node.api_url.rstrip('/')}{endpoint}",
                json=data,
                headers={"X-API-Key": api_key},
                timeout=10.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Agent调用失败: {response.text}")
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Agent连接失败: {str(e)}")


async def remove_peer_from_agent(node: Node, public_key: str):
    """从Agent删除Peer"""
    api_key = encryption.decrypt(node.api_key)
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{node.api_url.rstrip('/')}/api/peer/remove",
                json={"public_key": public_key},
                headers={"X-API-Key": api_key},
                timeout=10.0
            )
        except Exception:
            pass


async def check_node_online(node: Node) -> bool:
    """检查节点是否在线"""
    try:
        api_key = encryption.decrypt(node.api_key)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node.api_url.rstrip('/')}/health",
                headers={"X-API-Key": api_key},
                timeout=3.0
            )
            return response.status_code == 200
    except:
        return False


async def sync_node_public_key(node: Node, db: Session) -> str:
    """从 Agent 同步节点公钥"""
    api_key = encryption.decrypt(node.api_key)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node.api_url.rstrip('/')}/api/status",
                headers={"X-API-Key": api_key},
                timeout=5.0
            )
            if response.status_code == 200:
                status = response.json()
                if status.get("public_key"):
                    if status["public_key"] != node.public_key:
                        node.public_key = status["public_key"]
                        db.commit()
                    return status["public_key"]
    except Exception:
        pass
    return node.public_key


# ============ 节点相关 API ============

@router.get("/nodes")
async def get_nodes(
    db: Session = Depends(get_db),
    portal_site: PortalSite = Depends(verify_portal_site)
):
    """获取可用节点列表"""
    nodes = db.query(Node).filter(Node.status == "active").all()

    result = []
    for node in nodes:
        is_online = await check_node_online(node)
        result.append({
            "id": node.id,
            "name": node.name,
            "endpoint": node.endpoint,
            "wg_port": node.wg_port,
            "default_upload_limit": node.default_upload_limit or 0,
            "default_download_limit": node.default_download_limit or 0,
            "status": "online" if is_online else "offline",
            "online": is_online
        })

    return result


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: int,
    db: Session = Depends(get_db),
    portal_site: PortalSite = Depends(verify_portal_site)
):
    """获取节点详情"""
    node = db.query(Node).filter(Node.id == node_id, Node.status == "active").first()

    if not node:
        raise HTTPException(status_code=404, detail="节点不存在或已禁用")

    is_online = await check_node_online(node)

    return {
        "id": node.id,
        "name": node.name,
        "endpoint": node.endpoint,
        "wg_port": node.wg_port,
        "address_pool": node.address_pool,
        "dns": node.dns,
        "mtu": node.mtu,
        "keepalive": node.keepalive,
        "default_upload_limit": node.default_upload_limit or 0,
        "default_download_limit": node.default_download_limit or 0,
        "status": "online" if is_online else "offline",
        "online": is_online
    }


# ============ Peer 相关 API ============

@router.get("/peer/{user_id}")
async def get_peer(
    user_id: int,
    db: Session = Depends(get_db),
    portal_site: PortalSite = Depends(verify_portal_site)
):
    """获取用户的 Peer 配置"""
    peer = db.query(Peer).filter(
        Peer.portal_site_id == portal_site.id,
        Peer.portal_user_id == user_id
    ).first()

    if not peer:
        raise HTTPException(status_code=404, detail="尚未生成配置")

    node = db.query(Node).filter(Node.id == peer.node_id).first()
    node_public_key = await sync_node_public_key(node, db)

    return {
        "peer": {
            "id": peer.id,
            "public_key": peer.public_key,
            "address": peer.address,
            "mtu": peer.mtu,
            "dns": peer.dns,
            "keepalive": peer.keepalive,
            "upload_limit": peer.upload_limit,
            "download_limit": peer.download_limit,
            "created_at": peer.created_at.isoformat() if peer.created_at else None
        },
        "node": {
            "id": node.id,
            "name": node.name,
            "endpoint": node.endpoint,
            "wg_port": node.wg_port,
            "public_key": node_public_key,
            "dns": node.dns,
            "mtu": node.mtu,
            "keepalive": node.keepalive
        }
    }


@router.post("/peer")
async def create_peer(
    user_id: int,
    username: str,
    node_id: int,
    mtu: int = None,
    dns: str = None,
    keepalive: int = None,
    db: Session = Depends(get_db),
    portal_site: PortalSite = Depends(verify_portal_site)
):
    """创建 Peer 配置"""
    import json
    import re

    node = db.query(Node).filter(Node.id == node_id, Node.status == "active").first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在或已禁用")

    # 检查用户是否被禁止访问该节点
    if node.blocked_patterns:
        try:
            patterns = json.loads(node.blocked_patterns)
            for pattern in patterns:
                try:
                    if re.match(pattern, username):
                        raise HTTPException(status_code=403, detail="您被禁止使用此节点")
                except re.error:
                    pass
        except json.JSONDecodeError:
            pass

    # 检查用户是否已有Peer (在该 Portal 站点下)
    existing_peer = db.query(Peer).filter(
        Peer.portal_site_id == portal_site.id,
        Peer.portal_user_id == user_id
    ).first()

    if existing_peer:
        old_node = db.query(Node).filter(Node.id == existing_peer.node_id).first()
        if old_node:
            await remove_peer_from_agent(old_node, existing_peer.public_key)
        db.delete(existing_peer)
        db.commit()

    await sync_node_public_key(node, db)

    private_key, public_key = generate_keypair()
    address = allocate_ip(db, node)
    upload_limit = node.default_upload_limit or 0
    download_limit = node.default_download_limit or 0

    peer = Peer(
        portal_site_id=portal_site.id,
        portal_user_id=user_id,
        username=username,
        node_id=node.id,
        public_key=public_key,
        private_key=encryption.encrypt(private_key),
        address=address,
        mtu=mtu or node.mtu,
        dns=dns or node.dns,
        keepalive=keepalive or node.keepalive,
        upload_limit=upload_limit,
        download_limit=download_limit
    )
    db.add(peer)
    db.commit()
    db.refresh(peer)

    try:
        await call_agent(node, "/api/peer/add", {
            "public_key": public_key,
            "address": address
        })

        if upload_limit > 0 or download_limit > 0:
            await call_agent(node, "/api/peer/limit", {
                "address": address,
                "upload_limit": upload_limit,
                "download_limit": download_limit
            })
    except HTTPException as e:
        db.delete(peer)
        db.commit()
        raise e

    return {
        "peer": {
            "id": peer.id,
            "public_key": peer.public_key,
            "address": peer.address,
            "mtu": peer.mtu,
            "dns": peer.dns,
            "keepalive": peer.keepalive,
            "upload_limit": peer.upload_limit,
            "download_limit": peer.download_limit,
            "created_at": peer.created_at.isoformat() if peer.created_at else None
        },
        "node": {
            "id": node.id,
            "name": node.name,
            "endpoint": node.endpoint,
            "wg_port": node.wg_port,
            "public_key": node.public_key
        }
    }


@router.put("/peer/{user_id}/settings")
async def update_peer_settings(
    user_id: int,
    mtu: int = None,
    dns: str = None,
    keepalive: int = None,
    db: Session = Depends(get_db),
    portal_site: PortalSite = Depends(verify_portal_site)
):
    """更新 Peer 设置"""
    peer = db.query(Peer).filter(
        Peer.portal_site_id == portal_site.id,
        Peer.portal_user_id == user_id
    ).first()

    if not peer:
        raise HTTPException(status_code=404, detail="尚未生成配置")

    if mtu is not None:
        peer.mtu = mtu
    if dns is not None:
        peer.dns = dns
    if keepalive is not None:
        peer.keepalive = keepalive

    db.commit()
    db.refresh(peer)

    node = db.query(Node).filter(Node.id == peer.node_id).first()

    return {
        "peer": {
            "id": peer.id,
            "public_key": peer.public_key,
            "address": peer.address,
            "mtu": peer.mtu,
            "dns": peer.dns,
            "keepalive": peer.keepalive,
            "upload_limit": peer.upload_limit,
            "download_limit": peer.download_limit,
            "created_at": peer.created_at.isoformat() if peer.created_at else None
        },
        "node": {
            "id": node.id,
            "name": node.name,
            "endpoint": node.endpoint,
            "wg_port": node.wg_port,
            "public_key": node.public_key
        }
    }


@router.delete("/peer/{user_id}")
async def delete_peer(
    user_id: int,
    db: Session = Depends(get_db),
    portal_site: PortalSite = Depends(verify_portal_site)
):
    """删除 Peer 配置"""
    peer = db.query(Peer).filter(
        Peer.portal_site_id == portal_site.id,
        Peer.portal_user_id == user_id
    ).first()

    if not peer:
        raise HTTPException(status_code=404, detail="尚未生成配置")

    node = db.query(Node).filter(Node.id == peer.node_id).first()
    if node:
        await remove_peer_from_agent(node, peer.public_key)

    db.delete(peer)
    db.commit()

    return {"message": "配置已删除"}


@router.get("/peer/{user_id}/config", response_class=PlainTextResponse)
async def get_peer_config(
    user_id: int,
    db: Session = Depends(get_db),
    portal_site: PortalSite = Depends(verify_portal_site)
):
    """获取 Peer 配置文件内容"""
    peer = db.query(Peer).filter(
        Peer.portal_site_id == portal_site.id,
        Peer.portal_user_id == user_id
    ).first()

    if not peer:
        raise HTTPException(status_code=404, detail="尚未生成配置")

    node = db.query(Node).filter(Node.id == peer.node_id).first()

    private_key = encryption.decrypt(peer.private_key)
    node_public_key = await sync_node_public_key(node, db)
    endpoint = f"{node.endpoint}:{node.wg_port}"

    config_content = f"""[Interface]
PrivateKey = {private_key}
Address = {peer.address}/32
DNS = {peer.dns}
MTU = {peer.mtu}

[Peer]
PublicKey = {node_public_key}
Endpoint = {endpoint}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = {peer.keepalive}
"""

    return config_content
