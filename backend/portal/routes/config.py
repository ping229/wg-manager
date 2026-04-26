import ipaddress
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import httpx

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.shared.database import get_db
from backend.shared.models import Node, User, Peer
from backend.shared.schemas import PeerCreate, PeerSettings, PeerLimit, ConfigResponse
from backend.shared.auth import get_current_user, encryption
from backend.shared.config import settings

router = APIRouter(prefix="/api/config", tags=["配置管理"])


def generate_keypair() -> tuple[str, str]:
    """生成WireGuard密钥对"""
    private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
    public_key = subprocess.run(
        ["wg", "pubkey"],
        input=private_key.encode(),
        capture_output=True
    ).stdout.decode().strip()
    return private_key, public_key


def get_next_ip(address_pool: str) -> str:
    """从地址池获取下一个可用IP"""
    network = ipaddress.ip_network(address_pool, strict=False)
    # 网络地址和广播地址不可用,从第2个开始
    hosts = list(network.hosts())
    # 第一个IP分配给服务器,从第二个开始分配给客户端
    for i, host in enumerate(hosts[1:], start=2):
        yield str(host)


def get_used_ips(db: Session, node_id: int) -> set:
    """获取节点已使用的IP"""
    peers = db.query(Peer).filter(Peer.node_id == node_id).all()
    return {peer.address for peer in peers}


def allocate_ip(db: Session, node: Node) -> str:
    """分配IP地址"""
    used_ips = get_used_ips(db, node.id)
    network = ipaddress.ip_network(node.address_pool, strict=False)
    hosts = list(network.hosts())

    # 从第二个IP开始分配(第一个给服务器)
    for host in hosts[1:]:
        ip = str(host)
        if ip not in used_ips:
            return ip

    raise HTTPException(status_code=500, detail="IP地址池已用尽")


async def call_agent(node: Node, endpoint: str, data: dict) -> dict:
    """调用Agent API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{node.api_url.rstrip('/')}{endpoint}",
                json=data,
                headers={"X-API-Key": encryption.decrypt(node.api_key)},
                timeout=10.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Agent调用失败: {response.text}")
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Agent连接失败: {str(e)}")


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
            pass  # 忽略删除失败


@router.get("", response_model=ConfigResponse)
async def get_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前配置信息"""
    peer = db.query(Peer).filter(Peer.user_id == current_user.id).first()

    if not peer:
        raise HTTPException(status_code=404, detail="尚未生成配置")

    node = db.query(Node).filter(Node.id == peer.node_id).first()

    # 从Agent同步公钥
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node.api_url.rstrip('/')}/api/status",
                headers={"X-API-Key": encryption.decrypt(node.api_key)},
                timeout=5.0
            )
            if response.status_code == 200:
                status = response.json()
                if status.get("public_key") and status["public_key"] != node.public_key:
                    node.public_key = status["public_key"]
                    db.commit()
                    print(f"Updated node {node.name} public_key from Agent")
    except Exception as e:
        print(f"Warning: Failed to sync public key from Agent: {e}")

    return ConfigResponse(
        peer=peer,
        node=node
    )


@router.post("/generate", response_model=ConfigResponse)
async def generate_config(
    data: PeerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """生成新配置"""
    import json
    import re

    # 检查节点
    node = db.query(Node).filter(Node.id == data.node_id, Node.status == "active").first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在或已禁用")

    # 检查用户是否被禁止访问该节点
    if node.blocked_patterns:
        try:
            patterns = json.loads(node.blocked_patterns)
            for pattern in patterns:
                try:
                    if re.match(pattern, current_user.username):
                        raise HTTPException(status_code=403, detail="您被禁止使用此节点")
                except re.error:
                    pass  # 忽略无效的正则表达式
        except json.JSONDecodeError:
            pass  # 忽略无效的JSON

    # 从Agent获取实际的公钥
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node.api_url.rstrip('/')}/api/status",
                headers={"X-API-Key": encryption.decrypt(node.api_key)},
                timeout=5.0
            )
            if response.status_code == 200:
                status = response.json()
                if status.get("public_key") and status["public_key"] != node.public_key:
                    node.public_key = status["public_key"]
                    db.commit()
                    print(f"Updated node {node.name} public_key from Agent")
    except Exception as e:
        print(f"Warning: Failed to sync public key from Agent: {e}")

    # 检查用户是否已有Peer
    existing_peer = db.query(Peer).filter(Peer.user_id == current_user.id).first()

    if existing_peer:
        # 删除旧Peer
        old_node = db.query(Node).filter(Node.id == existing_peer.node_id).first()
        if old_node:
            await remove_peer_from_agent(old_node, existing_peer.public_key)

        db.delete(existing_peer)
        db.commit()

    # 生成新密钥对
    private_key, public_key = generate_keypair()

    # 分配IP
    address = allocate_ip(db, node)

    # 获取节点的默认限速
    upload_limit = node.default_upload_limit or 0
    download_limit = node.default_download_limit or 0

    # 创建Peer记录
    peer = Peer(
        user_id=current_user.id,
        node_id=node.id,
        public_key=public_key,
        private_key=encryption.encrypt(private_key),
        address=address,
        mtu=data.mtu or node.mtu,
        dns=data.dns or node.dns,
        keepalive=data.keepalive or node.keepalive,
        upload_limit=upload_limit,
        download_limit=download_limit
    )
    db.add(peer)
    db.commit()
    db.refresh(peer)

    # 调用Agent添加Peer
    try:
        await call_agent(node, "/api/peer/add", {
            "public_key": public_key,
            "address": address
        })

        # 设置限速
        if upload_limit > 0 or download_limit > 0:
            await call_agent(node, "/api/peer/limit", {
                "address": address,
                "upload_limit": upload_limit,
                "download_limit": download_limit
            })
    except HTTPException as e:
        # Agent调用失败,删除本地记录
        db.delete(peer)
        db.commit()
        raise e

    return ConfigResponse(
        peer=peer,
        node=node
    )


@router.put("/settings")
def update_settings(
    data: PeerSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新配置设置"""
    peer = db.query(Peer).filter(Peer.user_id == current_user.id).first()

    if not peer:
        raise HTTPException(status_code=404, detail="尚未生成配置")

    if data.mtu is not None:
        peer.mtu = data.mtu
    if data.dns is not None:
        peer.dns = data.dns
    if data.keepalive is not None:
        peer.keepalive = data.keepalive

    db.commit()
    db.refresh(peer)

    node = db.query(Node).filter(Node.id == peer.node_id).first()

    return ConfigResponse(peer=peer, node=node)


@router.get("/download")
async def download_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载配置文件"""
    peer = db.query(Peer).filter(Peer.user_id == current_user.id).first()

    if not peer:
        raise HTTPException(status_code=404, detail="尚未生成配置")

    node = db.query(Node).filter(Node.id == peer.node_id).first()

    # 生成配置文件内容
    private_key = encryption.decrypt(peer.private_key)

    # 从Agent获取实际的公钥（确保使用正确的公钥）
    node_public_key = node.public_key  # 默认使用数据库中的公钥
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node.api_url.rstrip('/')}/api/status",
                headers={"X-API-Key": encryption.decrypt(node.api_key)},
                timeout=5.0
            )
            if response.status_code == 200:
                status = response.json()
                if status.get("public_key"):
                    node_public_key = status["public_key"]
                    # 如果公钥不一致，更新数据库
                    if node_public_key != node.public_key:
                        node.public_key = node_public_key
                        db.commit()
                        print(f"Updated node {node.name} public_key from Agent")
    except Exception as e:
        print(f"Warning: Failed to get public key from Agent: {e}")

    # Endpoint 格式: IP:端口 或 域名:端口
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

    filename = f"wg-{node.name}.conf"

    return PlainTextResponse(
        content=config_content,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.delete("")
async def delete_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除当前配置"""
    peer = db.query(Peer).filter(Peer.user_id == current_user.id).first()

    if not peer:
        raise HTTPException(status_code=404, detail="尚未生成配置")

    # 从Agent删除
    node = db.query(Node).filter(Node.id == peer.node_id).first()
    if node:
        await remove_peer_from_agent(node, peer.public_key)

    # 删除本地记录
    db.delete(peer)
    db.commit()

    return {"message": "配置已删除"}
