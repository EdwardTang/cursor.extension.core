#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List, Set
from oppie.types import Msg

class MeshAdapter:
    """网格适配器，负责节点间通信和状态同步"""
    
    def __init__(self, node_id: Optional[str] = None, event_bus = None):
        """
        初始化网格适配器
        
        Args:
            node_id: 节点ID，如果为None则自动生成
            event_bus: 事件总线，如果为None则创建新的
        """
        self.node_id = node_id or str(uuid.uuid4())
        self.event_bus = event_bus or asyncio.Queue()
        self.connected = True
        self.core = None  # 将由调用者设置（CursorCore实例）
        self.state = {
            "cursor_position": 0,
            "last_msg_id": None,
            "timestamp": int(time.time() * 1000)
        }
        self.peers = set()  # 对等节点集合
        self.last_heartbeat_received = {}  # 节点ID -> 上次接收心跳的时间戳
        self._task = None  # 后台任务
        self._stopping = False  # 停止标志
    
    async def start(self) -> None:
        """启动网格适配器"""
        if self._task is not None:
            return  # 已经启动
        
        self._stopping = False
        self._task = asyncio.create_task(self._event_loop())
    
    async def _event_loop(self) -> None:
        """事件循环，处理传入的消息"""
        while not self._stopping:
            try:
                # 从事件总线获取消息
                event = await self.event_bus.get()
                
                # 处理消息
                if event["type"] == "message" and self.connected:
                    msg = event["data"]
                    source_id = event["source_id"]
                    
                    # 如果消息不是来自自己且有核心组件，则处理消息
                    if source_id != self.node_id and self.core:
                        await self._handle_message(msg)
                
                elif event["type"] == "heartbeat" and self.connected:
                    source_id = event["source_id"]
                    if source_id != self.node_id:
                        self.last_heartbeat_received[source_id] = time.time()
                
                elif event["type"] == "state_sync" and self.connected:
                    new_state = event["data"]
                    source_id = event["source_id"]
                    if source_id != self.node_id:
                        await self._handle_state_sync(new_state, source_id)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in event loop: {e}")
    
    async def _handle_message(self, msg: Msg) -> None:
        """
        处理接收到的消息
        
        Args:
            msg: 接收到的消息
        """
        if self.core:
            # 异步调用核心组件的handle_message方法
            asyncio.create_task(self._call_core_handle_message(msg))
    
    async def _call_core_handle_message(self, msg: Msg) -> None:
        """
        调用核心组件的handle_message方法
        
        Args:
            msg: 要处理的消息
        """
        # 在实际实现中，这可能是一个异步方法
        # 为简单起见，我们假设它是同步的
        self.core.handle_message(msg)
    
    async def _handle_state_sync(self, new_state: Dict[str, Any], source_id: str) -> None:
        """
        处理状态同步
        
        Args:
            new_state: 新状态
            source_id: 源节点ID
        """
        # 解决冲突：使用时间戳较大的状态
        if new_state.get("timestamp", 0) > self.state.get("timestamp", 0):
            self.state.update(new_state)
    
    async def broadcast(self, msg: Msg) -> None:
        """
        广播消息到所有节点
        
        Args:
            msg: 要广播的消息
        """
        if not self.connected:
            return  # 断开连接时不广播
        
        event = {
            "type": "message",
            "source_id": self.node_id,
            "data": msg
        }
        
        # 放入事件总线
        await self.event_bus.put(event)
    
    async def sync_state(self) -> None:
        """同步状态到所有节点"""
        if not self.connected:
            return  # 断开连接时不同步
        
        # 更新时间戳
        self.state["timestamp"] = int(time.time() * 1000)
        
        event = {
            "type": "state_sync",
            "source_id": self.node_id,
            "data": self.state
        }
        
        # 放入事件总线
        await self.event_bus.put(event)
    
    async def start_heartbeat(self, interval: float = 1.0) -> None:
        """
        开始发送心跳
        
        Args:
            interval: 心跳间隔（秒）
        """
        while not self._stopping:
            if self.connected:
                event = {
                    "type": "heartbeat",
                    "source_id": self.node_id,
                    "timestamp": time.time()
                }
                
                # 放入事件总线
                await self.event_bus.put(event)
            
            await asyncio.sleep(interval)
    
    async def reconnect(self) -> bool:
        """
        重新连接到网格
        
        Returns:
            是否成功重连
        """
        if self.connected:
            return True  # 已经连接
        
        self.connected = True
        
        # 同步状态
        await self.sync_state()
        
        return True
    
    async def disconnect(self) -> bool:
        """
        断开与网格的连接
        
        Returns:
            是否成功断开
        """
        self.connected = False
        return True
    
    async def shutdown(self) -> None:
        """关闭网格适配器"""
        self._stopping = True
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            
            self._task = None 