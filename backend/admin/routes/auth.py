from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.shared.database import get_db
from backend.shared.models import Admin
from backend.shared.schemas import AdminLogin, AdminResponse, Token
from backend.shared.auth import (
    verify_password,
    create_access_token,
    get_current_admin
)

router = APIRouter(prefix="/api/auth", tags=["管理员认证"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """管理员登录"""
    admin = db.query(Admin).filter(Admin.username == form_data.username).first()

    if not admin or not verify_password(form_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"user_id": admin.id, "is_admin": True}
    )

    return Token(access_token=access_token)


@router.get("/profile", response_model=AdminResponse)
def get_profile(current_admin: Admin = Depends(get_current_admin)):
    """获取当前管理员信息"""
    return current_admin
