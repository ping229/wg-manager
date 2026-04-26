import os
import base64
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import User, Admin
from .schemas import TokenData

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 schemes
oauth2_scheme_user = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
oauth2_scheme_admin = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """解码JWT令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("user_id")
        is_admin: bool = payload.get("is_admin", False)
        if user_id is None:
            return None
        return TokenData(user_id=user_id, is_admin=is_admin)
    except JWTError:
        return None


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme_user),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    token_data = decode_token(token)
    if token_data is None or token_data.is_admin:
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception

    if user.status != "active":
        raise HTTPException(status_code=403, detail="账户已被禁用")

    return user


async def get_current_admin(
    token: Optional[str] = Depends(oauth2_scheme_admin),
    db: Session = Depends(get_db)
) -> Admin:
    """获取当前登录管理员"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    token_data = decode_token(token)
    if token_data is None or not token_data.is_admin:
        raise credentials_exception

    admin = db.query(Admin).filter(Admin.id == token_data.user_id).first()
    if admin is None:
        raise credentials_exception

    return admin


# ============ 敏感数据加密 ============
class Encryption:
    """AES加密工具类"""

    def __init__(self, key: str):
        # 确保密钥长度为32字节(AES-256)
        self.key = key.encode()[:32].ljust(32, b'\0')

    def encrypt(self, plaintext: str) -> str:
        """加密"""
        if not plaintext:
            return ""

        iv = os.urandom(16)
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        # PKCS7 padding
        data = plaintext.encode()
        padding_length = 16 - (len(data) % 16)
        data += bytes([padding_length] * padding_length)

        encrypted = encryptor.update(data) + encryptor.finalize()
        return base64.b64encode(iv + encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """解密"""
        if not ciphertext:
            return ""

        try:
            data = base64.b64decode(ciphertext)
            iv = data[:16]
            encrypted = data[16:]

            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()

            decrypted = decryptor.update(encrypted) + decryptor.finalize()

            # Remove PKCS7 padding
            padding_length = decrypted[-1]
            decrypted = decrypted[:-padding_length]

            return decrypted.decode()
        except Exception:
            return ""


encryption = Encryption(settings.ENCRYPTION_KEY)
