"""
认证API
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
import uuid

from app.core.auth import (
    create_access_token,
    authenticate_user,
    get_password_hash,
    get_current_user,
    get_current_superuser,
    User,
    UserInDB,
    Token
)
from app.core.database import get_db_cursor, get_db

router = APIRouter()


# ==================== 数据模型 ====================

class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户响应"""
    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime


# ==================== 初始化用户表 ====================

def init_users_table():
    """初始化用户表"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                username VARCHAR UNIQUE NOT NULL,
                email VARCHAR UNIQUE,
                full_name VARCHAR,
                hashed_password VARCHAR NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_superuser BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        get_db().commit()


# ==================== API端点 ====================

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user: UserRegister):
    """用户注册"""
    # 初始化用户表
    init_users_table()

    with get_db_cursor() as cursor:
        # 检查用户名是否已存在
        cursor.execute("SELECT id FROM users WHERE username = ?", [user.username])
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )

        # 检查邮箱是否已存在
        if user.email:
            cursor.execute("SELECT id FROM users WHERE email = ?", [user.email])
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被注册"
                )

        # 创建用户
        user_id = str(uuid.uuid4())
        hashed_password = get_password_hash(user.password)
        now = datetime.now()

        cursor.execute(
            """
            INSERT INTO users (id, username, email, full_name, hashed_password, is_active, is_superuser, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [user_id, user.username, user.email, user.full_name, hashed_password, True, False, now]
        )
        get_db().commit()

        return UserResponse(
            id=user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=True,
            is_superuser=False,
            created_at=now
        )


@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    """用户登录"""
    # 初始化用户表
    init_users_table()

    # 验证用户
    authenticated_user = authenticate_user(user.username, user.password)

    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建令牌
    access_token = create_access_token(
        data={"sub": authenticated_user.id, "username": authenticated_user.username}
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserInDB = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at
    )


@router.post("/init-admin", response_model=UserResponse, status_code=201)
async def init_admin_user(user: UserRegister):
    """初始化管理员账号（仅在没有用户时可用）"""
    # 初始化用户表
    init_users_table()

    with get_db_cursor() as cursor:
        # 检查是否已有用户
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]

        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="系统已初始化，请联系管理员"
            )

        # 创建管理员用户
        user_id = str(uuid.uuid4())
        hashed_password = get_password_hash(user.password)
        now = datetime.now()

        cursor.execute(
            """
            INSERT INTO users (id, username, email, full_name, hashed_password, is_active, is_superuser, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [user_id, user.username, user.email, user.full_name, hashed_password, True, True, now]
        )
        get_db().commit()

        return UserResponse(
            id=user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=True,
            is_superuser=True,
            created_at=now
        )