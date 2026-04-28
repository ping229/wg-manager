from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.portal.database import get_db
from backend.portal.models import User, Registration
from backend.shared.schemas import UserRegister, UserLogin, UserResponse, PasswordChange, Token
from backend.shared.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from backend.portal.config import settings

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=dict)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """用户注册申请"""
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")

    if db.query(Registration).filter(Registration.username == data.username).first():
        raise HTTPException(status_code=400, detail="该用户名已有待审核的注册申请")

    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    if db.query(Registration).filter(Registration.email == data.email).first():
        raise HTTPException(status_code=400, detail="该邮箱已有待审核的注册申请")

    # 创建注册申请
    registration = Registration(
        username=data.username,
        password_hash=get_password_hash(data.password),
        email=data.email,
        status="pending"
    )
    db.add(registration)
    db.commit()

    return {"message": "注册申请已提交，请等待管理员审核"}


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "active":
        raise HTTPException(status_code=403, detail="账户未审核或已被禁用")

    access_token = create_access_token(
        data={"user_id": user.id, "is_admin": False},
        secret_key=settings.SECRET_KEY,
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return Token(access_token=access_token)


@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.put("/password")
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    current_user.password_hash = get_password_hash(data.new_password)
    db.commit()

    return {"message": "密码修改成功"}


@router.get("/status")
def get_registration_status(
    username: str = None,
    email: str = None,
    db: Session = Depends(get_db)
):
    """查询注册申请状态"""
    query = db.query(Registration)

    if username:
        query = query.filter(Registration.username == username)
    elif email:
        query = query.filter(Registration.email == email)
    else:
        raise HTTPException(status_code=400, detail="请提供用户名或邮箱")

    registration = query.first()

    if not registration:
        raise HTTPException(status_code=404, detail="未找到注册申请")

    return {
        "status": registration.status,
        "reject_reason": registration.reject_reason
    }


# ============ Admin API - 供 Admin 调用 ============

def verify_key(key: Optional[str] = Header(None, alias="X-Key")):
    """验证 KEY"""
    if not settings.KEY:
        raise HTTPException(status_code=500, detail="KEY 未配置")
    if key != settings.KEY:
        raise HTTPException(status_code=403, detail="无效的 KEY")
    return True


@router.get("/admin/users")
def admin_list_users(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_key)
):
    """Admin 获取用户列表"""
    users = db.query(User).all()
    return [{
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "status": u.status,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "approved_at": u.approved_at.isoformat() if u.approved_at else None
    } for u in users]


@router.get("/admin/registrations")
def admin_list_registrations(
    status_filter: str = None,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_key)
):
    """Admin 获取注册申请列表"""
    query = db.query(Registration)
    if status_filter:
        query = query.filter(Registration.status == status_filter)
    registrations = query.order_by(Registration.created_at.desc()).all()
    return [{
        "id": r.id,
        "username": r.username,
        "email": r.email,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "reject_reason": r.reject_reason
    } for r in registrations]


@router.post("/admin/approve/{reg_id}")
def admin_approve_registration(
    reg_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_key)
):
    """Admin 批准注册申请"""
    registration = db.query(Registration).filter(Registration.id == reg_id).first()
    if not registration:
        raise HTTPException(status_code=404, detail="注册申请不存在")

    if registration.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已处理")

    # 创建用户
    user = User(
        username=registration.username,
        password_hash=registration.password_hash,
        email=registration.email,
        status="active",
        approved_at=datetime.utcnow()
    )
    db.add(user)

    # 更新注册状态
    registration.status = "approved"
    registration.reviewed_at = datetime.utcnow()

    db.commit()

    return {"message": "用户已批准", "user_id": user.id}


@router.post("/admin/reject/{reg_id}")
def admin_reject_registration(
    reg_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    _: bool = Depends(verify_key)
):
    """Admin 拒绝注册申请"""
    registration = db.query(Registration).filter(Registration.id == reg_id).first()
    if not registration:
        raise HTTPException(status_code=404, detail="注册申请不存在")

    if registration.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已处理")

    registration.status = "rejected"
    registration.reviewed_at = datetime.utcnow()
    registration.reject_reason = reason

    db.commit()

    return {"message": "已拒绝注册申请"}


@router.get("/admin/user/{user_id}")
def admin_get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_key)
):
    """Admin 获取用户详情"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "status": user.status,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "approved_at": user.approved_at.isoformat() if user.approved_at else None
    }


@router.put("/admin/user/{user_id}/status")
def admin_update_user_status(
    user_id: int,
    status: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_key)
):
    """Admin 更新用户状态"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if status not in ["active", "disabled"]:
        raise HTTPException(status_code=400, detail="无效的状态")

    user.status = status
    db.commit()

    return {"message": f"用户状态已更新为 {status}"}


# ============ 用户创建/删除 API ============

from pydantic import BaseModel, EmailStr
from typing import List


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str
    password: str
    email: EmailStr


class BatchUserCreate(BaseModel):
    """批量创建用户请求"""
    users: List[UserCreate]


class BatchUserDelete(BaseModel):
    """批量删除用户请求"""
    user_ids: List[int]


@router.post("/admin/users/create")
def admin_create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_key)
):
    """Admin 创建用户"""
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被使用")

    # 创建用户
    user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        email=data.email,
        status="active",
        approved_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "用户创建成功",
        "user_id": user.id,
        "username": user.username,
        "email": user.email
    }


@router.post("/admin/users/batch-create")
def admin_batch_create_users(
    data: BatchUserCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_key)
):
    """Admin 批量创建用户"""
    created = []
    failed = []

    for user_data in data.users:
        try:
            # 检查用户名是否已存在
            if db.query(User).filter(User.username == user_data.username).first():
                failed.append({
                    "username": user_data.username,
                    "email": user_data.email,
                    "reason": "用户名已存在"
                })
                continue

            # 检查邮箱是否已存在
            if db.query(User).filter(User.email == user_data.email).first():
                failed.append({
                    "username": user_data.username,
                    "email": user_data.email,
                    "reason": "邮箱已被使用"
                })
                continue

            # 创建用户
            user = User(
                username=user_data.username,
                password_hash=get_password_hash(user_data.password),
                email=user_data.email,
                status="active",
                approved_at=datetime.utcnow()
            )
            db.add(user)
            db.flush()  # 获取 ID
            created.append({
                "user_id": user.id,
                "username": user.username,
                "email": user.email
            })
        except Exception as e:
            failed.append({
                "username": user_data.username,
                "email": user_data.email,
                "reason": str(e)
            })

    db.commit()

    return {
        "message": f"成功创建 {len(created)} 个用户，失败 {len(failed)} 个",
        "created": created,
        "failed": failed
    }


@router.delete("/admin/user/{user_id}")
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_key)
):
    """Admin 删除用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    username = user.username
    db.delete(user)
    db.commit()

    return {"message": f"用户 {username} 已删除"}


@router.post("/admin/users/batch-delete")
def admin_batch_delete_users(
    data: BatchUserDelete,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_key)
):
    """Admin 批量删除用户"""
    deleted = []
    not_found = []

    for user_id in data.user_ids:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            deleted.append({
                "user_id": user.id,
                "username": user.username
            })
            db.delete(user)
        else:
            not_found.append(user_id)

    db.commit()

    return {
        "message": f"成功删除 {len(deleted)} 个用户",
        "deleted": deleted,
        "not_found": not_found
    }
