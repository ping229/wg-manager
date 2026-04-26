from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.shared.database import get_db
from backend.shared.models import User, Registration, Admin
from backend.shared.schemas import (
    RegistrationResponse,
    RegistrationApprove,
    RegistrationReject
)
from backend.shared.auth import get_current_admin, get_password_hash

router = APIRouter(prefix="/api/registrations", tags=["注册审核"])


@router.get("", response_model=list[RegistrationResponse])
def list_registrations(
    status: str = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取注册申请列表"""
    query = db.query(Registration)
    if status:
        query = query.filter(Registration.status == status)
    registrations = query.order_by(Registration.created_at.desc()).all()
    return registrations


@router.post("/{reg_id}/approve")
def approve_registration(
    reg_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """批准注册申请"""
    registration = db.query(Registration).filter(Registration.id == reg_id).first()
    if not registration:
        raise HTTPException(status_code=404, detail="注册申请不存在")

    if registration.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已被处理")

    # 检查用户名和邮箱是否已被使用
    if db.query(User).filter(User.username == registration.username).first():
        raise HTTPException(status_code=400, detail="用户名已被使用")

    if db.query(User).filter(User.email == registration.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被使用")

    # 创建用户
    user = User(
        username=registration.username,
        password_hash=registration.password_hash,
        email=registration.email,
        status="active",
        approved_at=datetime.utcnow(),
        approved_by=current_admin.id
    )
    db.add(user)

    # 更新注册申请状态
    registration.status = "approved"
    registration.reviewed_at = datetime.utcnow()
    registration.reviewed_by = current_admin.id

    db.commit()

    return {"message": "注册申请已批准", "user_id": user.id}


@router.post("/{reg_id}/reject")
def reject_registration(
    reg_id: int,
    data: RegistrationReject,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """拒绝注册申请"""
    registration = db.query(Registration).filter(Registration.id == reg_id).first()
    if not registration:
        raise HTTPException(status_code=404, detail="注册申请不存在")

    if registration.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已被处理")

    registration.status = "rejected"
    registration.reviewed_at = datetime.utcnow()
    registration.reviewed_by = current_admin.id
    registration.reject_reason = data.reason

    db.commit()

    return {"message": "注册申请已拒绝"}


@router.delete("/{reg_id}")
def delete_registration(
    reg_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除注册申请记录"""
    registration = db.query(Registration).filter(Registration.id == reg_id).first()
    if not registration:
        raise HTTPException(status_code=404, detail="注册申请不存在")

    db.delete(registration)
    db.commit()

    return {"message": "注册申请记录已删除"}
