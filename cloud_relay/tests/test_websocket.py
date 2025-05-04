#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket功能测试
"""

import asyncio
import json
import pytest
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

try:
    from cloud_relay.auth import create_token
    from cloud_relay.connection import ConnectionManager, SessionClaims
    from cloud_relay.router import MessageRouter
except ImportError:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from auth import create_token
    from connection import ConnectionManager, SessionClaims
    from router import MessageRouter

class MockWebSocket:
    """模拟WebSocket类"""
    
    def __init__(self):
        self.client_state = "CONNECTED"
        self.sent_messages = []
        
    async def accept(self):
        """接受连接"""
        pass
        
    async def close(self, code=1000, reason=None):
        """关闭连接"""
        self.client_state = "DISCONNECTED"
        
    async def send_json(self, data):
        """发送JSON消息"""
        self.sent_messages.append(data)
        
    async def receive_json(self):
        """接收JSON消息"""
        return {"type": "test", "payload": {"message": "Hello"}}
        
@pytest.mark.asyncio
async def test_connection_manager():
    """测试连接管理器"""
    # 创建连接管理器
    manager = ConnectionManager()
    
    # 创建模拟WebSocket
    websocket = MockWebSocket()
    
    # 创建会话声明
    claims = SessionClaims(
        session_id="test-session-123",
        user_id="test-user-123",
        device_id="test-device-123",
        device_type="DEVICE_MOBILE",
        scopes=["default"]
    )
    
    # 测试连接
    await manager.connect(websocket, claims)
    
    # 验证连接已建立
    assert "test-session-123" in manager.active_connections
    assert manager.active_connections["test-session-123"].claims.user_id == "test-user-123"
    assert "test-user-123" in manager.user_sessions
    assert "test-device-123" in manager.device_sessions
    
    # 测试向会话发送消息
    test_message = {"type": "test", "payload": {"data": "test"}}
    result = await manager.send_to_session("test-session-123", test_message)
    
    # 验证消息已发送
    assert result is True
    assert len(websocket.sent_messages) > 0
    assert websocket.sent_messages[-1] == test_message
    
    # 测试向用户发送消息
    user_message = {"type": "user", "payload": {"data": "user-test"}}
    count = await manager.send_to_user("test-user-123", user_message)
    
    # 验证消息已发送给用户
    assert count == 1
    assert websocket.sent_messages[-1] == user_message
    
    # 测试向设备发送消息
    device_message = {"type": "device", "payload": {"data": "device-test"}}
    result = await manager.send_to_device("test-device-123", device_message)
    
    # 验证消息已发送给设备
    assert result is True
    assert websocket.sent_messages[-1] == device_message
    
    # 测试断开连接
    manager.disconnect("test-session-123")
    
    # 验证连接已断开
    assert "test-session-123" not in manager.active_connections
    assert "test-user-123" not in manager.user_sessions
    assert "test-device-123" not in manager.device_sessions
    
@pytest.mark.asyncio
async def test_message_router():
    """测试消息路由器"""
    # 创建模拟连接管理器
    mock_manager = MagicMock()
    mock_manager.send_to_session = AsyncMock(return_value=True)
    mock_manager.send_to_user = AsyncMock(return_value=1)
    mock_manager.send_to_device = AsyncMock(return_value=True)
    mock_manager.active_connections = {}
    
    # 创建路由器
    router = MessageRouter(mock_manager)
    
    # 启动路由器
    await router.start()
    
    try:
        # 将消息加入队列
        test_message = {
            "type": "test",
            "payload": {"data": "test"},
            "metadata": {
                "target_session": "target-session-123"
            }
        }
        await router.enqueue_message("source-session-123", test_message)
        
        # 等待路由处理
        await asyncio.sleep(0.1)
        
        # 验证消息已路由到目标会话
        mock_manager.send_to_session.assert_called_once_with("target-session-123", test_message)
        
    finally:
        # 停止路由器
        await router.stop()
        
@pytest.mark.asyncio
async def test_message_type_routing():
    """测试基于消息类型的路由"""
    # 创建模拟连接管理器
    mock_manager = MagicMock()
    mock_manager.send_to_session = AsyncMock(return_value=True)
    mock_manager.user_sessions = {"test-user-123": ["session-1", "session-2"]}
    mock_manager.active_connections = {
        "source-session-123": MagicMock(
            claims=MagicMock(
                user_id="test-user-123",
                device_type="DEVICE_MOBILE"
            )
        ),
        "session-1": MagicMock(
            claims=MagicMock(
                user_id="test-user-123",
                device_type="DEVICE_DESKTOP"
            )
        ),
        "session-2": MagicMock(
            claims=MagicMock(
                user_id="test-user-123",
                device_type="DEVICE_MOBILE"
            )
        )
    }
    
    # 创建路由器
    router = MessageRouter(mock_manager)
    
    # 启动路由器
    await router.start()
    
    try:
        # 测试runPlan消息路由
        run_plan_message = {
            "type": "runPlan",
            "payload": {"plan": "test-plan"}
        }
        await router.enqueue_message("source-session-123", run_plan_message)
        
        # 等待路由处理
        await asyncio.sleep(0.1)
        
        # 验证消息已路由到桌面设备（Sidecar）
        mock_manager.send_to_session.assert_called_with("session-1", run_plan_message)
        
    finally:
        # 停止路由器
        await router.stop() 