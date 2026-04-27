from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.admin.database import get_db
from backend.admin.models import AdminUser
from backend.shared.schemas import AdminCreate, AdminResponse
from backend.shared.auth import get_current_admin, get_password_hash

router = APIRouter(prefix="/api/admins", tags=["管理员管理"])


@router.get("")
def list_admins(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """获取管理员列表"""
    if current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="权限不足")

    admins = db.query(AdminUser).all()
    return admins


@router.post("", response_model=AdminResponse)
def create_admin(
    data: AdminCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """创建管理员"""
    if current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="权限不足")

    if db.query(AdminUser).filter(AdminUser.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")

    admin = AdminUser(
        username=data.username,
        password_hash=get_password_hash(data.password),
        role=data.role
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    return admin


@router.put("/{admin_id}")
def update_admin(
    admin_id: int,
    password: str = None,
    role: str = None,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """更新管理员"""
    if current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="权限不足")

    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    if password:
        admin.password_hash = get_password_hash(password)

    if role:
        if admin.role == "super_admin" and role != "super_admin":
            raise HTTPException(status_code=400, detail="不能修改超级管理员角色")
        admin.role = role

    db.commit()
    db.refresh(admin)

    return {"message": "管理员已更新", "admin": AdminResponse.model_validate(admin)}


@router.delete("/{admin_id}")
def delete_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """删除管理员"""
    if current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="权限不足")

    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    if admin.role == "super_admin":
        raise HTTPException(status_code=400, detail="不能删除超级管理员")

    if admin.id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    db.delete(admin)
    db.commit()

    return {"message": "管理员已删除"}
