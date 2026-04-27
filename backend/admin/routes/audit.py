from fastapi import APIRouter, Depends, HTTPException

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.admin.models import AdminUser
from backend.shared.auth import get_current_admin
from backend.shared.schemas import RegistrationReject
from backend.admin.services.portal_client import portal_client

router = APIRouter(prefix="/api/registrations", tags=["注册审核"])


@router.get("")
async def list_registrations(
    status: str = None,
    current_admin: AdminUser = Depends(get_current_admin)
):
    """获取注册申请列表"""
    try:
        registrations = await portal_client.get_registrations(status)
        return registrations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{reg_id}/approve")
async def approve_registration(
    reg_id: int,
    current_admin: AdminUser = Depends(get_current_admin)
):
    """批准注册申请"""
    try:
        result = await portal_client.approve_registration(reg_id)
        return result
    except Exception as e:
        if "已处理" in str(e):
            raise HTTPException(status_code=400, detail="该申请已被处理")
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail="注册申请不存在")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{reg_id}/reject")
async def reject_registration(
    reg_id: int,
    data: RegistrationReject,
    current_admin: AdminUser = Depends(get_current_admin)
):
    """拒绝注册申请"""
    try:
        result = await portal_client.reject_registration(reg_id, data.reason)
        return result
    except Exception as e:
        if "已处理" in str(e):
            raise HTTPException(status_code=400, detail="该申请已被处理")
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail="注册申请不存在")
        raise HTTPException(status_code=500, detail=str(e))
