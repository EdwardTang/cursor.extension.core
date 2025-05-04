#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
消息路由器 - 处理不同类型消息的路由逻辑
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Callable, Awaitable

# 配置日志
logger = logging.getLogger("message_router")

class MessageRouter:
    """消息路由器，负责基于类型和目标路由消息"""
    
    def __init__(self, connection_manager):
        """
        初始化路由器
        
        Args:
            connection_manager: 连接管理器实例
        """
        self.connection_manager = connection_manager
        self.message_queue = asyncio.Queue()
        self.router_task = None
        self.type_handlers = {}
        self._stopping = False
        self.default_handlers = {}
        
        # 注册基本消息类型处理器
        self.register_type_handler("runPlan", self.handle_run_plan)
        self.register_type_handler("chat", self.handle_chat)
        self.register_type_handler("progress", self.handle_progress)
        self.register_type_handler("diff", self.handle_diff)
        self.register_type_handler("recover", self.handle_recover)
        self.register_type_handler("approve", self.handle_approve)
        
    def register_type_handler(self, message_type: str, handler: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        """
        注册消息类型处理器
        
        Args:
            message_type: 消息类型
            handler: 异步处理函数
        """
        self.type_handlers[message_type] = handler
        
    def register_default_handler(self, device_type: str, handler: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        """
        注册设备类型默认处理器
        
        Args:
            device_type: 设备类型 (MOBILE, DESKTOP, VSCODE_EXTENSION)
            handler: 异步处理函数
        """
        self.default_handlers[device_type] = handler
        
    async def start(self):
        """启动路由器"""
        if self.router_task is None:
            self._stopping = False
            self.router_task = asyncio.create_task(self._router_loop())
            logger.info("消息路由器已启动")
        
    async def stop(self):
        """停止路由器"""
        self._stopping = True
        if self.router_task:
            self.router_task.cancel()
            try:
                await self.router_task
            except asyncio.CancelledError:
                pass
            self.router_task = None
            logger.info("消息路由器已停止")
            
    async def enqueue_message(self, session_id: str, message: Dict[str, Any]):
        """
        将消息加入队列
        
        Args:
            session_id: 发送消息的会话ID
            message: 消息内容
        """
        # 构建完整的内部消息
        if "id" not in message:
            message["id"] = str(uuid.uuid4())
            
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
            
        internal_message = {
            "session_id": session_id,
            "message": message
        }
        
        await self.message_queue.put(internal_message)
            
    async def _router_loop(self):
        """消息路由循环"""
        try:
            while not self._stopping:
                try:
                    # 等待消息
                    internal_message = await self.message_queue.get()
                    session_id = internal_message["session_id"]
                    message = internal_message["message"]
                    
                    await self._route_message(session_id, message)
                    
                    # 标记任务完成
                    self.message_queue.task_done()
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"处理消息时出错: {str(e)}")
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("路由器循环已退出")
            
    async def _route_message(self, sender_session_id: str, message: Dict[str, Any]):
        """
        路由单个消息
        
        Args:
            sender_session_id: 发送者会话ID
            message: 消息内容
        """
        try:
            message_type = message.get("type")
            if not message_type:
                logger.warning(f"消息没有类型: {message}")
                return
                
            metadata = message.get("metadata", {})
            
            # 确定目标会话或用户
            target_session = metadata.get("target_session")
            target_user = metadata.get("target_user")
            target_device = metadata.get("target_device")
            
            # 记录路由信息
            logger.debug(f"路由消息: type={message_type}, sender={sender_session_id}, target_session={target_session}, target_user={target_user}, target_device={target_device}")
            
            # 1. 首先尝试特定目标路由
            if target_session:
                # 直接发送到特定会话
                await self.connection_manager.send_to_session(target_session, message)
                return
                
            if target_device:
                # 发送到特定设备
                await self.connection_manager.send_to_device(target_device, message)
                return
                
            if target_user:
                # 发送到用户的所有会话
                await self.connection_manager.send_to_user(target_user, message)
                return
                
            # 2. 基于消息类型的智能路由
            if message_type in self.type_handlers:
                await self.type_handlers[message_type](sender_session_id, message)
                return
                
            # 3. 获取发送者设备类型，尝试默认路由
            if sender_session_id in self.connection_manager.active_connections:
                sender_info = self.connection_manager.active_connections[sender_session_id]
                device_type = sender_info.claims.device_type
                
                if device_type and device_type in self.default_handlers:
                    await self.default_handlers[device_type](sender_session_id, message)
                    return
                    
            # 4. 无法确定路由，记录警告
            logger.warning(f"无法确定消息路由: type={message_type}, sender={sender_session_id}")
            
        except Exception as e:
            logger.error(f"路由消息时出错: {str(e)}")
            
    async def handle_run_plan(self, sender_session_id: str, message: Dict[str, Any]):
        """
        处理runPlan消息 (PWA → Sidecar)
        
        Args:
            sender_session_id: 发送者会话ID
            message: 消息内容
        """
        try:
            # 获取发送者信息
            if sender_session_id not in self.connection_manager.active_connections:
                return
                
            sender_info = self.connection_manager.active_connections[sender_session_id]
            user_id = sender_info.claims.user_id
            
            # 查找该用户的所有Sidecar类型会话
            sidecar_sessions = []
            if user_id in self.connection_manager.user_sessions:
                for session_id in self.connection_manager.user_sessions[user_id]:
                    if session_id in self.connection_manager.active_connections:
                        conn_info = self.connection_manager.active_connections[session_id]
                        if conn_info.claims.device_type == "DEVICE_DESKTOP":  # 假设Sidecar是桌面设备
                            sidecar_sessions.append(session_id)
                            
            if not sidecar_sessions:
                # 没有可用的Sidecar，发送错误回应
                error_message = {
                    "type": "error",
                    "timestamp": datetime.now().isoformat(),
                    "id": str(uuid.uuid4()),
                    "payload": {
                        "original_message_id": message.get("id"),
                        "error": "No available Sidecar found",
                        "code": "NO_SIDECAR"
                    }
                }
                await self.connection_manager.send_to_session(sender_session_id, error_message)
                return
                
            # 发送计划到所有Sidecar
            # 在实际实现中，可能只发送到特定的Sidecar
            for session_id in sidecar_sessions:
                await self.connection_manager.send_to_session(session_id, message)
                
        except Exception as e:
            logger.error(f"处理runPlan消息时出错: {str(e)}")
            
    async def handle_chat(self, sender_session_id: str, message: Dict[str, Any]):
        """
        处理chat消息 (PWA → Sidecar)
        
        Args:
            sender_session_id: 发送者会话ID
            message: 消息内容
        """
        # 与runPlan处理类似，查找Sidecar并发送
        await self.handle_run_plan(sender_session_id, message)
            
    async def handle_progress(self, sender_session_id: str, message: Dict[str, Any]):
        """
        处理progress消息 (Sidecar → PWA)
        
        Args:
            sender_session_id: 发送者会话ID
            message: 消息内容
        """
        try:
            # 获取发送者信息
            if sender_session_id not in self.connection_manager.active_connections:
                return
                
            sender_info = self.connection_manager.active_connections[sender_session_id]
            user_id = sender_info.claims.user_id
            
            # 查找该用户的所有PWA类型会话
            pwa_sessions = []
            if user_id in self.connection_manager.user_sessions:
                for session_id in self.connection_manager.user_sessions[user_id]:
                    if session_id in self.connection_manager.active_connections:
                        conn_info = self.connection_manager.active_connections[session_id]
                        if conn_info.claims.device_type in ["DEVICE_MOBILE", "DEVICE_WEB"]:  # PWA是移动或Web设备
                            pwa_sessions.append(session_id)
                            
            # 发送进度到所有PWA
            for session_id in pwa_sessions:
                await self.connection_manager.send_to_session(session_id, message)
                
        except Exception as e:
            logger.error(f"处理progress消息时出错: {str(e)}")
            
    async def handle_diff(self, sender_session_id: str, message: Dict[str, Any]):
        """
        处理diff消息 (Sidecar → PWA)
        
        Args:
            sender_session_id: 发送者会话ID
            message: 消息内容
        """
        # 与progress处理类似
        await self.handle_progress(sender_session_id, message)
            
    async def handle_recover(self, sender_session_id: str, message: Dict[str, Any]):
        """
        处理recover消息 (Sidecar → PWA)
        
        Args:
            sender_session_id: 发送者会话ID
            message: 消息内容
        """
        # 与progress处理类似
        await self.handle_progress(sender_session_id, message)
            
    async def handle_approve(self, sender_session_id: str, message: Dict[str, Any]):
        """
        处理approve消息 (PWA → Sidecar)
        
        Args:
            sender_session_id: 发送者会话ID
            message: 消息内容
        """
        # 与runPlan处理类似
        await self.handle_run_plan(sender_session_id, message) 