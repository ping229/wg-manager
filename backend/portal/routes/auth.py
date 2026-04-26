from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.shared.database import get_db
from backend.shared.models import User, Registration
from backend.shared.schemas import UserRegister, UserLogin, UserResponse, PasswordChange, Token
from backend.shared.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from backend.shared.config import settings

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
        raise HTTPException(status_code=403, detail="账户已被禁用")

    access_token = create_access_token(
        data={"user_id": user.id, "is_admin": False}
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
