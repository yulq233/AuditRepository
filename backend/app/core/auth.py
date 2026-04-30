"""
认证模块
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db_cursor


# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer认证
security = HTTPBearer()


# ==================== 数据模型 ====================

class Token(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token数据"""
    user_id: Optional[str] = None
    username: Optional[str] = None


class UserBase(BaseModel):
    """用户基础模型"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """创建用户"""
    password: str


class User(UserBase):
    """用户完整模型"""
    id: str
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime


class UserInDB(User):
    """数据库中的用户"""
    hashed_password: str


# ==================== 密码工具函数 ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


# ==================== JWT工具函数 ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")

        if user_id is None:
            return None

        return TokenData(user_id=user_id, username=username)
    except JWTError:
        return None


# ==================== 用户查询函数 ====================

def get_user_by_username(username: str) -> Optional[UserInDB]:
    """根据用户名获取用户"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, email, full_name, hashed_password,
                   is_active, is_superuser, created_at
            FROM users
            WHERE username = ?
            """,
            [username]
        )
        row = cursor.fetchone()

        if not row:
            return None

        return UserInDB(
            id=row[0],
            username=row[1],
            email=row[2],
            full_name=row[3],
            hashed_password=row[4],
            is_active=bool(row[5]),
            is_superuser=bool(row[6]),
            created_at=row[7]
        )


def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """根据ID获取用户"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, email, full_name, hashed_password,
                   is_active, is_superuser, created_at
            FROM users
            WHERE id = ?
            """,
            [user_id]
        )
        row = cursor.fetchone()

        if not row:
            return None

        return UserInDB(
            id=row[0],
            username=row[1],
            email=row[2],
            full_name=row[3],
            hashed_password=row[4],
            is_active=bool(row[5]),
            is_superuser=bool(row[6]),
            created_at=row[7]
        )


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """验证用户"""
    user = get_user_by_username(username)

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


# ==================== 认证依赖 ====================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInDB:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    token_data = decode_token(token)

    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    user = get_user_by_id(token_data.user_id)

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")

    return user


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return current_user


async def get_current_superuser(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """获取当前超级管理员"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[UserInDB]:
    """获取当前用户（可选，无token时返回None）"""
    if credentials is None:
        return None

    token = credentials.credentials
    token_data = decode_token(token)

    if token_data is None or token_data.user_id is None:
        return None

    user = get_user_by_id(token_data.user_id)
    return user