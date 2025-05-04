#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloud Relay服务 - 连接本地工作站与移动PWA客户端的实时通信桥梁
"""

import os
import json
import uuid
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Union, Annotated

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocketState
from pydantic import BaseModel, Field

# 导入自定义模块
try:
    from cloud_relay.auth import get_current_user, create_tokens, verify_token_from_query, refresh_access_token, TokenResponse, TokenData
    from cloud_relay.connection import ConnectionManager, SessionClaims
    from cloud_relay.router import MessageRouter
except ImportError:
    # 处理作为本地模块导入的情况
    from auth import get_current_user, create_tokens, verify_token_from_query, refresh_access_token, TokenResponse, TokenData
    from connection import ConnectionManager, SessionClaims
    from router import MessageRouter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("cloud_relay")

# 创建FastAPI应用
app = FastAPI(
    title="Oppie Cloud Relay",
    description="连接Oppie本地工作站与移动PWA客户端的实时通信桥梁",
    version="0.1.0"
)

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class TokenRequest(BaseModel):
    device_id: str
    device_name: str
    user_id: str
    device_type: str

class RefreshRequest(BaseModel):
    refresh_token: str

class MessagePayload(BaseModel):
    type: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)

# 创建连接管理器和消息路由器
connection_manager = ConnectionManager()
message_router = MessageRouter(connection_manager)

# API路由
@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
        "connections": len(connection_manager.active_connections),
        "uptime_seconds": int(time.time() - start_time)
    }

@app.get("/api/metrics")
async def get_metrics():
    """Prometheus格式指标"""
    # 获取连接管理器统计信息
    stats = connection_manager.get_stats()
    
    return stats

@app.post("/api/auth/token", response_model=TokenResponse)
async def create_session_token(request: TokenRequest):
    """创建新会话并生成令牌"""
    # 创建会话ID
    session_id = str(uuid.uuid4())
    
    # 创建令牌
    token_response = create_tokens(
        session_id=session_id,
        user_id=request.user_id,
        device_id=request.device_id,
        scopes=["default"]  # 默认权限
    )
    
    # 生成WebSocket URL
    host = os.environ.get("RELAY_HOST", "relay.oppie.xyz")
    ws_protocol = "wss" if os.environ.get("USE_HTTPS", "true").lower() == "true" else "ws"
    ws_url = f"{ws_protocol}://{host}/ws?token={token_response.access_token}"
    
    # 返回响应
    return TokenResponse(
        access_token=token_response.access_token,
        refresh_token=token_response.refresh_token,
        expires_at=token_response.expires_at,
        ws_url=ws_url,
        session_id=session_id,
        token_type="bearer"
    )

@app.post("/api/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """刷新访问令牌"""
    token_response = refresh_access_token(request.refresh_token)
    
    # 生成WebSocket URL
    host = os.environ.get("RELAY_HOST", "relay.oppie.xyz")
    ws_protocol = "wss" if os.environ.get("USE_HTTPS", "true").lower() == "true" else "ws"
    ws_url = f"{ws_protocol}://{host}/ws?token={token_response.access_token}"
    
    return TokenResponse(
        access_token=token_response.access_token,
        refresh_token=token_response.refresh_token,
        expires_at=token_response.expires_at,
        ws_url=ws_url,
        session_id="",  # 保持兼容性，实际上refresh不创建新会话
        token_type="bearer"
    )

@app.get("/api/sessions")
async def list_sessions(token_data: TokenData = Depends(get_current_user)):
    """列出用户的所有会话"""
    user_id = token_data.user_id
    
    if user_id not in connection_manager.user_sessions:
        return {"sessions": [], "total": 0}
        
    user_session_ids = connection_manager.user_sessions[user_id]
    sessions = []
    
    for session_id in user_session_ids:
        if session_id in connection_manager.active_connections:
            conn_info = connection_manager.active_connections[session_id]
            sessions.append({
                "session_id": session_id,
                "device_id": conn_info.claims.device_id,
                "device_type": conn_info.claims.device_type,
                "connected_at": conn_info.connected_at.isoformat(),
                "last_activity": conn_info.last_activity.isoformat(),
                "is_active": conn_info.is_active,
                "messages": {
                    "sent": conn_info.messages_sent,
                    "received": conn_info.messages_received
                }
            })
            
    return {
        "sessions": sessions,
        "total": len(sessions)
    }

@app.post("/api/message")
async def send_message(message: MessagePayload, token_data: TokenData = Depends(get_current_user)):
    """通过REST API发送消息（WebSocket之外的备用通道）"""
    # 构建完整消息
    full_message = {
        "id": str(uuid.uuid4()),
        "type": message.type,
        "timestamp": datetime.now().isoformat(),
        "payload": message.payload,
        "metadata": {
            **message.metadata,
            "session_id": token_data.session_id,
            "user_id": token_data.user_id,
            "device_id": token_data.device_id
        }
    }
    
    # 将消息加入路由队列
    await message_router.enqueue_message(token_data.session_id, full_message)
    
    return {
        "message_id": full_message["id"],
        "status": "queued",
        "timestamp": full_message["timestamp"]
    }

# WebSocket处理
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        # 验证令牌
        token_data = verify_token_from_query(token)
        
        # 创建会话声明
        claims = SessionClaims(
            session_id=token_data.session_id,
            user_id=token_data.user_id,
            device_id=token_data.device_id,
            device_type=token_data.scopes[0] if token_data.scopes else "default",  # 临时方案，后续应改进
            scopes=token_data.scopes
        )
        
        # 连接到管理器
        await connection_manager.connect(websocket, claims)
        
        # 消息处理循环
        try:
            while True:
                # 接收消息
                try:
                    data = await websocket.receive_json()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {str(e)}")
                    continue
                
                # 将消息添加到路由队列
                await message_router.enqueue_message(token_data.session_id, data)
                
        except WebSocketDisconnect:
            connection_manager.disconnect(token_data.session_id)
            
    except ValueError as e:
        logger.error(f"WebSocket连接验证失败: {str(e)}")
        if websocket.client_state == WebSocketState.CONNECTING:
            await websocket.close(code=1008, reason=str(e))
    except Exception as e:
        logger.error(f"WebSocket处理错误: {str(e)}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011, reason="服务器内部错误")

# 启动时间记录
start_time = time.time()

# 服务器启动和停止事件
@app.on_event("startup")
async def startup_event():
    logger.info("Cloud Relay服务正在启动...")
    
    # 启动消息路由器
    await message_router.start()
    
    # 启动连接管理器的后台任务
    await connection_manager.start_background_tasks()
    
    logger.info("Cloud Relay服务已启动")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Cloud Relay服务正在关闭...")
    
    # 停止消息路由器
    await message_router.stop()
    
    # 停止连接管理器的后台任务
    await connection_manager.stop_background_tasks()
    
    logger.info("Cloud Relay服务已关闭")

# 如果直接运行此脚本
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("app:app", host=host, port=port, reload=True) 