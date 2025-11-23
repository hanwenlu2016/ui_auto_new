"""
安全认证模块

本模块提供应用的安全相关功能：
- JWT Token 生成和验证
- 密码哈希和验证
- 使用 bcrypt 算法进行密码加密
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
import jwt
from passlib.context import CryptContext
from app.core.config import settings

# 密码加密上下文 - 使用 bcrypt 算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 算法
ALGORITHM = "HS256"

def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 JWT 访问令牌
    
    Args:
        subject: 令牌主题（通常是用户 ID）
        expires_delta: 过期时间间隔，如果未指定则使用配置中的默认值
    
    Returns:
        str: 编码后的 JWT 令牌字符串
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码是否与哈希密码匹配
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码
    
    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    生成密码的哈希值
    
    Args:
        password: 明文密码
    
    Returns:
        str: 哈希后的密码字符串
    """
    return pwd_context.hash(password)
