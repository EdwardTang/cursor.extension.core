#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
连接管理器 - 处理WebSocket连接的注册、注销和消息分发
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Set, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field

from fastapi import WebSocket
from starlette.websockets import WebSocketState
from pydantic import BaseModel

# 配置日志
logger = logging.getLogger("connection_manager")

# 数据模型
class SessionClaims(BaseModel):
    """会话声明数据，来自JWT验证"""
    session_id: str
    user_id: str
    device_id: str
    device_type: Optional[str] = None
    scopes: List[str] = []

@dataclass
class ConnectionInfo:
    """连接信息，包含WebSocket和元数据"""
    websocket: WebSocket
    claims: SessionClaims
    connected_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    last_ping: datetime = field(default_factory=datetime.now)
    messages_sent: int = 0
    messages_received: int = 0
    is_active: bool = True

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        """初始化连接管理器"""
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self.user_sessions: Dict[str, Set[str]] = {}
        self.device_sessions: Dict[str, str] = {}
        self.message_handlers: Dict[str, List[Callable[[str, Dict[str, Any]], Awaitable[None]]]] = {}
        self.ping_interval = 30  # 秒
        self.pong_timeout = 15   # 秒
        self._ping_task = None
        self._cleanup_task = None
        self._stopping = False
        
    async def connect(self, websocket: WebSocket, claims: SessionClaims) -> None:
        """
        注册新的WebSocket连接
        
        Args:
            websocket: WebSocket连接
            claims: 会话声明数据
        """
        await websocket.accept()
        
        session_id = claims.session_id
        conn_info = ConnectionInfo(
            websocket=websocket,
            claims=claims
        )
        
        self.active_connections[session_id] = conn_info
        
        # 更新用户会话映射
        user_id = claims.user_id
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)
        
        # 更新设备会话映射
        device_id = claims.device_id
        self.device_sessions[device_id] = session_id
        
        logger.info(f"WebSocket连接已建立: session_id={session_id}, user_id={user_id}, device_id={device_id}")
        
        # 发送欢迎消息
        welcome_message = {
            "type": "system",
            "action": "connected",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "session_id": session_id,
                "message": "Connection established"
            }
        }
        await self.send_to_session(session_id, welcome_message)
        
    def disconnect(self, session_id: str) -> None:
        """
        注销WebSocket连接
        
        Args:
            session_id: 会话ID
        """
        if session_id not in self.active_connections:
            return
            
        conn_info = self.active_connections[session_id]
        conn_info.is_active = False
        
        # 从用户会话映射中移除
        user_id = conn_info.claims.user_id
        if user_id in self.user_sessions and session_id in self.user_sessions[user_id]:
            self.user_sessions[user_id].remove(session_id)
            if not self.user_sessions[user_id]:  # 如果用户没有其他会话，移除用户
                del self.user_sessions[user_id]
                
        # 从设备会话映射中移除
        device_id = conn_info.claims.device_id
        if device_id in self.device_sessions:
            del self.device_sessions[device_id]
            
        # 从活跃连接中移除
        del self.active_connections[session_id]
        
        logger.info(f"WebSocket连接已断开: session_id={session_id}")
        
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[str] = None) -> int:
        """
        向所有连接广播消息
        
        Args:
            message: 要广播的消息
            exclude: 要排除的会话ID
            
        Returns:
            int: 成功发送的连接数
        """
        success_count = 0
        disconnected = []
        
        for session_id, conn_info in self.active_connections.items():
            if exclude and session_id == exclude:
                continue
                
            websocket = conn_info.websocket
            if websocket.client_state == WebSocketState.CONNECTED and conn_info.is_active:
                try:
                    await websocket.send_json(message)
                    conn_info.messages_sent += 1
                    conn_info.last_activity = datetime.now()
                    success_count += 1
                except Exception as e:
                    logger.error(f"向会话{session_id}发送消息失败: {str(e)}")
                    disconnected.append(session_id)
            else:
                disconnected.append(session_id)
                
        # 清理断开的连接
        for session_id in disconnected:
            self.disconnect(session_id)
            
        return success_count
        
    async def send_to_session(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        向特定会话发送消息
        
        Args:
            session_id: 会话ID
            message: 要发送的消息
            
        Returns:
            bool: 是否成功发送
        """
        if session_id not in self.active_connections:
            return False
            
        conn_info = self.active_connections[session_id]
        websocket = conn_info.websocket
        
        if websocket.client_state != WebSocketState.CONNECTED or not conn_info.is_active:
            self.disconnect(session_id)
            return False
            
        try:
            await websocket.send_json(message)
            conn_info.messages_sent += 1
            conn_info.last_activity = datetime.now()
            return True
        except Exception as e:
            logger.error(f"向会话{session_id}发送消息失败: {str(e)}")
            self.disconnect(session_id)
            return False
            
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> int:
        """
        向用户的所有会话发送消息
        
        Args:
            user_id: 用户ID
            message: 要发送的消息
            
        Returns:
            int: 成功发送的会话数
        """
        if user_id not in self.user_sessions:
            return 0
            
        success_count = 0
        for session_id in list(self.user_sessions[user_id]):  # 创建列表副本进行迭代
            if await self.send_to_session(session_id, message):
                success_count += 1
                
        return success_count
        
    async def send_to_device(self, device_id: str, message: Dict[str, Any]) -> bool:
        """
        向特定设备发送消息
        
        Args:
            device_id: 设备ID
            message: 要发送的消息
            
        Returns:
            bool: 是否成功发送
        """
        if device_id not in self.device_sessions:
            return False
            
        session_id = self.device_sessions[device_id]
        return await self.send_to_session(session_id, message)
        
    def register_handler(self, message_type: str, handler: Callable[[str, Dict[str, Any]], Awaitable[None]]) -> None:
        """
        注册消息处理器
        
        Args:
            message_type: 消息类型
            handler: 处理函数，接收会话ID和消息
        """
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
        
    async def process_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        处理接收到的消息
        
        Args:
            session_id: 会话ID
            message: 接收到的消息
        """
        if session_id not in self.active_connections:
            return
            
        conn_info = self.active_connections[session_id]
        conn_info.messages_received += 1
        conn_info.last_activity = datetime.now()
        
        message_type = message.get("type")
        if not message_type:
            logger.warning(f"收到没有类型的消息: {message}")
            return
            
        # 处理特殊消息类型
        if message_type == "pong":
            return  # 简单记录活动时间就足够了
            
        # 处理注册的处理器
        if message_type in self.message_handlers:
            for handler in self.message_handlers[message_type]:
                try:
                    await handler(session_id, message)
                except Exception as e:
                    logger.error(f"处理消息时出错: {str(e)}")
                    
    async def start_background_tasks(self) -> None:
        """启动后台任务"""
        if self._ping_task is None:
            self._ping_task = asyncio.create_task(self._ping_loop())
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    async def stop_background_tasks(self) -> None:
        """停止后台任务"""
        self._stopping = True
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None
            
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            
    async def _ping_loop(self) -> None:
        """定期发送ping消息"""
        while not self._stopping:
            try:
                now = datetime.now()
                disconnected = []
                
                for session_id, conn_info in self.active_connections.items():
                    # 检查超时
                    if (now - conn_info.last_activity).total_seconds() > self.pong_timeout:
                        logger.warning(f"会话{session_id}超时未响应")
                        disconnected.append(session_id)
                        continue
                        
                    # 发送ping
                    try:
                        ping_message = {
                            "type": "ping",
                            "timestamp": now.isoformat(),
                            "id": str(uuid.uuid4())
                        }
                        await conn_info.websocket.send_json(ping_message)
                        conn_info.last_ping = now
                    except Exception as e:
                        logger.error(f"向会话{session_id}发送ping失败: {str(e)}")
                        disconnected.append(session_id)
                        
                # 清理断开的连接
                for session_id in disconnected:
                    self.disconnect(session_id)
                    
            except Exception as e:
                logger.error(f"Ping循环错误: {str(e)}")
                
            # 等待下一个ping间隔
            await asyncio.sleep(self.ping_interval)
            
    async def _cleanup_loop(self) -> None:
        """定期清理过期会话"""
        while not self._stopping:
            try:
                now = datetime.now()
                to_disconnect = []
                
                for session_id, conn_info in self.active_connections.items():
                    # 如果超过10分钟没有活动，断开连接
                    if (now - conn_info.last_activity).total_seconds() > 600:
                        logger.info(f"会话{session_id}已超过10分钟无活动，清理中")
                        to_disconnect.append(session_id)
                        
                # 断开连接
                for session_id in to_disconnect:
                    try:
                        await self.active_connections[session_id].websocket.close(code=1000, reason="Session timeout")
                    except Exception:
                        pass  # 忽略关闭错误
                    self.disconnect(session_id)
                    
            except Exception as e:
                logger.error(f"清理循环错误: {str(e)}")
                
            # 每分钟检查一次
            await asyncio.sleep(60)
            
    def get_stats(self) -> Dict[str, Any]:
        """
        获取连接统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_messages_sent = sum(c.messages_sent for c in self.active_connections.values())
        total_messages_received = sum(c.messages_received for c in self.active_connections.values())
        
        return {
            "active_connections": len(self.active_connections),
            "unique_users": len(self.user_sessions),
            "unique_devices": len(self.device_sessions),
            "messages_sent": total_messages_sent,
            "messages_received": total_messages_received,
            "uptime_seconds": int(time.time() - self._start_time)
        }
        
    _start_time = time.time() 