import os
import base64
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
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


def create_access_token(data: dict, secret_key: str, algorithm: str = "HS256",
                        expires_minutes: int = 1440) -> str:
    """创建JWT令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_token(token: str, secret_key: str, algorithm: str = "HS256") -> Optional[dict]:
    """解码JWT令牌"""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        user_id: int = payload.get("user_id")
        is_admin: bool = payload.get("is_admin", False)
        if user_id is None:
            return None
        return {"user_id": user_id, "is_admin": is_admin}
    except JWTError:
        return None


# ============ Portal 用户认证 ============
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme_user)):
    """获取当前登录用户 - Portal"""
    from backend.portal.database import get_db, SessionLocal
    from backend.portal.models import User
    from backend.portal.config import settings

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    token_data = decode_token(token, settings.SECRET_KEY, settings.ALGORITHM)
    if token_data is None or token_data.get("is_admin"):
        raise credentials_exception

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == token_data["user_id"]).first()
        if user is None:
            raise credentials_exception

        if user.status != "active":
            raise HTTPException(status_code=403, detail="账户未审核或已被禁用")

        return user
    finally:
        db.close()


# ============ Admin 管理员认证 ============
async def get_current_admin(token: Optional[str] = Depends(oauth2_scheme_admin)):
    """获取当前登录管理员 - Admin"""
    from backend.admin.database import SessionLocal
    from backend.admin.models import AdminUser
    from backend.admin.config import settings

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    token_data = decode_token(token, settings.SECRET_KEY, settings.ALGORITHM)
    if token_data is None or not token_data.get("is_admin"):
        raise credentials_exception

    db = SessionLocal()
    try:
        admin = db.query(AdminUser).filter(AdminUser.id == token_data["user_id"]).first()
        if admin is None:
            raise credentials_exception

        return admin
    finally:
        db.close()


# ============ 敏感数据加密 ============
class Encryption:
    """AES加密工具类"""

    def __init__(self, key: str):
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
            padding_length = decrypted[-1]
            decrypted = decrypted[:-padding_length]

            return decrypted.decode()
        except Exception:
            return ""


# 延迟初始化加密实例
_encryption_instance = None

def get_encryption():
    """获取加密实例"""
    global _encryption_instance
    if _encryption_instance is None:
        from backend.admin.config import settings
        _encryption_instance = Encryption(settings.ENCRYPTION_KEY)
    return _encryption_instance

# 兼容旧代码的属性
class EncryptionWrapper:
    def __getattr__(self, name):
        return getattr(get_encryption(), name)

encryption = EncryptionWrapper()
