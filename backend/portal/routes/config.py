from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.portal.database import get_db
from backend.portal.models import User
from backend.shared.schemas import PeerCreate, PeerSettings
from backend.shared.auth import get_current_user
from backend.portal.services.admin_client import get_admin_client

router = APIRouter(prefix="/api/config", tags=["配置管理"])


@router.get("")
async def get_config(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """获取当前配置信息"""
    admin_client = get_admin_client(db)
    if not admin_client:
        raise HTTPException(status_code=503, detail="Admin 未配置或未接入")

    try:
        result = await admin_client.get_peer(current_user.id)
        if not result:
            raise HTTPException(status_code=404, detail="尚未生成配置")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_config(
    data: PeerCreate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """生成新配置"""
    admin_client = get_admin_client(db)
    if not admin_client:
        raise HTTPException(status_code=503, detail="Admin 未配置或未接入")

    try:
        result = await admin_client.create_peer(
            user_id=current_user.id,
            username=current_user.username,
            node_id=data.node_id,
            mtu=data.mtu,
            dns=data.dns,
            keepalive=data.keepalive
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
async def update_settings(
    data: PeerSettings,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """更新配置设置"""
    admin_client = get_admin_client(db)
    if not admin_client:
        raise HTTPException(status_code=503, detail="Admin 未配置或未接入")

    try:
        result = await admin_client.update_peer_settings(
            user_id=current_user.id,
            mtu=data.mtu,
            dns=data.dns,
            keepalive=data.keepalive
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download")
async def download_config(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """下载配置文件"""
    admin_client = get_admin_client(db)
    if not admin_client:
        raise HTTPException(status_code=503, detail="Admin 未配置或未接入")

    try:
        config_content = await admin_client.get_peer_config(current_user.id)

        filename = "wg-client.conf"
        lines = config_content.split('\n')
        for line in lines:
            if line.startswith('Endpoint'):
                endpoint = line.split('=')[1].strip().split(':')[0]
                filename = f"wg-{endpoint}.conf"
                break

        return PlainTextResponse(
            content=config_content,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("")
async def delete_config(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """删除当前配置"""
    admin_client = get_admin_client(db)
    if not admin_client:
        raise HTTPException(status_code=503, detail="Admin 未配置或未接入")

    try:
        result = await admin_client.delete_peer(current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
