import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.shared.database import get_db
from backend.shared.models import Node, User
from backend.shared.schemas import NodeListResponse, NodeResponse
from backend.shared.auth import get_current_user, encryption

router = APIRouter(prefix="/api/nodes", tags=["节点"])


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
async def get_nodes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取可用节点列表（包含在线状态）"""
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


@router.get("/{node_id}", response_model=NodeResponse)
def get_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取节点详情"""
    node = db.query(Node).filter(Node.id == node_id, Node.status == "active").first()

    if not node:
        raise HTTPException(status_code=404, detail="节点不存在或已禁用")

    return node
