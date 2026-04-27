from fastapi import APIRouter, Depends, HTTPException

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.portal.database import get_db
from backend.portal.models import User
from backend.shared.auth import get_current_user
from backend.portal.services.admin_client import get_admin_client

router = APIRouter(prefix="/api/nodes", tags=["节点"])


@router.get("")
async def get_nodes(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """获取可用节点列表（包含在线状态）"""
    admin_client = get_admin_client(db)
    if not admin_client:
        raise HTTPException(status_code=503, detail="Admin 未配置或未接入")

    try:
        nodes = await admin_client.get_nodes()
        return nodes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{node_id}")
async def get_node(
    node_id: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """获取节点详情"""
    admin_client = get_admin_client(db)
    if not admin_client:
        raise HTTPException(status_code=503, detail="Admin 未配置或未接入")

    try:
        node = await admin_client.get_node(node_id)
        return node
    except Exception as e:
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail="节点不存在或已禁用")
        raise HTTPException(status_code=500, detail=str(e))
