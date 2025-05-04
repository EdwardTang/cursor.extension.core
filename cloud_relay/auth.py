#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
认证模块 - 处理JWT令牌生成、验证和刷新
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Union, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# JWT配置
JWT_SECRET_KEY = os.environ.get("JWT_SECRET", "development_secret_please_change_in_production")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))  # 默认24小时
JWT_REFRESH_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRE_MINUTES", 60 * 24 * 30))  # 默认30天
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "oppie.xyz")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "cloud-relay")

# 安全配置
security = HTTPBearer()

# 数据模型
class TokenPayload(BaseModel):
    sub: str  # 会话ID
    user_id: str
    device_id: str
    scopes: List[str] = []
    aud: str = JWT_AUDIENCE
    iss: str = JWT_ISSUER
    jti: str  # JWT ID，用于标识唯一令牌
    iat: int  # 发布时间
    exp: int  # 过期时间

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime

class TokenData(BaseModel):
    session_id: str
    user_id: str
    device_id: str
    scopes: List[str] = []
    exp: datetime

def create_token(
    session_id: str,
    user_id: str,
    device_id: str,
    scopes: List[str] = [],
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access"
) -> str:
    """
    创建JWT令牌
    
    Args:
        session_id: 会话ID
        user_id: 用户ID
        device_id: 设备ID
        scopes: 授权范围列表
        expires_delta: 过期时间增量
        token_type: 令牌类型 ("access" 或 "refresh")
    
    Returns:
        str: 编码的JWT令牌
    """
    if expires_delta is None:
        if token_type == "refresh":
            expires_delta = timedelta(minutes=JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
        else:
            expires_delta = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    issued_at = int(time.time())
    expire = issued_at + int(expires_delta.total_seconds())
    
    to_encode = {
        "sub": session_id,
        "user_id": user_id,
        "device_id": device_id,
        "scopes": scopes,
        "aud": JWT_AUDIENCE,
        "iss": JWT_ISSUER,
        "jti": f"{session_id}:{token_type}:{int(time.time() * 1000)}",
        "iat": issued_at,
        "exp": expire,
        "type": token_type
    }
    
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def create_tokens(
    session_id: str,
    user_id: str,
    device_id: str,
    scopes: List[str] = []
) -> TokenResponse:
    """
    创建访问令牌和刷新令牌
    
    Args:
        session_id: 会话ID
        user_id: 用户ID
        device_id: 设备ID
        scopes: 授权范围列表
    
    Returns:
        TokenResponse: 包含访问令牌和刷新令牌的响应
    """
    access_token = create_token(session_id, user_id, device_id, scopes)
    refresh_token = create_token(session_id, user_id, device_id, scopes, token_type="refresh")
    
    expires_at = datetime.now() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at
    )

def decode_token(token: str) -> Dict[str, Any]:
    """
    解码JWT令牌
    
    Args:
        token: JWT令牌
    
    Returns:
        Dict[str, Any]: 解码后的令牌负载
    
    Raises:
        jwt.PyJWTError: 如果令牌无效
    """
    return jwt.decode(
        token,
        JWT_SECRET_KEY, 
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={"verify_signature": True, "verify_exp": True, "verify_aud": True, "verify_iss": True}
    )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """
    从JWT令牌获取当前用户
    
    Args:
        credentials: HTTP授权凭据
    
    Returns:
        TokenData: 令牌数据
    
    Raises:
        HTTPException: 认证失败
    """
    try:
        payload = decode_token(credentials.credentials)
        
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="不是访问令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(
            session_id=payload["sub"],
            user_id=payload["user_id"],
            device_id=payload["device_id"],
            scopes=payload.get("scopes", []),
            exp=datetime.fromtimestamp(payload["exp"])
        )
        
        return token_data
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"无效的认证凭据: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_token_from_query(token: str) -> TokenData:
    """
    验证来自查询参数的令牌，用于WebSocket连接
    
    Args:
        token: JWT令牌
    
    Returns:
        TokenData: 令牌数据
    
    Raises:
        ValueError: 如果令牌无效
    """
    try:
        payload = decode_token(token)
        
        token_data = TokenData(
            session_id=payload["sub"],
            user_id=payload["user_id"],
            device_id=payload["device_id"],
            scopes=payload.get("scopes", []),
            exp=datetime.fromtimestamp(payload["exp"])
        )
        
        return token_data
    except jwt.PyJWTError as e:
        raise ValueError(f"无效的令牌: {str(e)}")

def refresh_access_token(refresh_token: str) -> TokenResponse:
    """
    使用刷新令牌生成新的访问令牌
    
    Args:
        refresh_token: 刷新令牌
    
    Returns:
        TokenResponse: 包含新访问令牌的响应
    
    Raises:
        HTTPException: 如果刷新令牌无效
    """
    try:
        payload = decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="不是刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        session_id = payload["sub"]
        user_id = payload["user_id"]
        device_id = payload["device_id"]
        scopes = payload.get("scopes", [])
        
        # 创建新的访问令牌
        access_token = create_token(session_id, user_id, device_id, scopes)
        
        expires_at = datetime.now() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # 返回相同的刷新令牌
            expires_at=expires_at
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"无效的刷新令牌: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
# 检查是否有必要的权限
def requires_scopes(required_scopes: List[str]):
    """
    检查用户是否有所需的权限范围
    
    Args:
        required_scopes: 所需权限范围列表
    
    Returns:
        Callable: FastAPI依赖函数
    """
    def dependency(token_data: TokenData = Depends(get_current_user)):
        for scope in required_scopes:
            if scope not in token_data.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"无权访问，缺少权限: {scope}",
                )
        return token_data
    return dependency 