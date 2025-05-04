#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import time
import asyncio
from typing import Any, Dict, Optional, List, Set
from oppie.types import QuotaExceededError, CounterUpdateMsg

class GlobalCounter:
    """全局计数器，用于跨代理共享工具调用计数"""
    
    def __init__(self):
        self.count = 0
        self._lock = threading.Lock()
        # 节点ID到计数映射，用于跟踪每个节点的贡献
        self.node_counts = {}
        # 节点ID到最后时间戳的映射，用于冲突解决
        self.node_timestamps = {}
    
    def increment(self, node_id: str = "local") -> int:
        """
        增加指定节点的计数并返回总计数
        
        Args:
            node_id: 节点ID，默认为"local"
            
        Returns:
            更新后的总计数
        """
        with self._lock:
            # 初始化节点计数（如果不存在）
            if node_id not in self.node_counts:
                self.node_counts[node_id] = 0
            
            # 增加节点计数
            self.node_counts[node_id] += 1
            
            # 更新节点时间戳
            self.node_timestamps[node_id] = int(time.time() * 1000)
            
            # 计算总计数
            self.count = sum(self.node_counts.values())
            
            return self.count
    
    def apply_update(self, update: CounterUpdateMsg) -> int:
        """
        应用来自其他节点的计数器更新
        
        Args:
            update: 计数器更新消息
            
        Returns:
            更新后的总计数
        """
        with self._lock:
            node_id = update.node_id
            
            # 检查时间戳，只有更新的时间戳比已知的大时才处理
            current_ts = self.node_timestamps.get(node_id, 0)
            if update.logical_ts <= current_ts:
                # 忽略过时的更新
                return self.count
            
            # 初始化节点计数（如果不存在）
            if node_id not in self.node_counts:
                self.node_counts[node_id] = 0
            
            # 应用增量
            self.node_counts[node_id] += update.delta
            
            # 更新时间戳
            self.node_timestamps[node_id] = update.logical_ts
            
            # 重新计算总计数
            self.count = sum(self.node_counts.values())
            
            return self.count
    
    def get_count(self) -> int:
        """获取当前总计数"""
        with self._lock:
            return self.count
    
    def get_node_count(self, node_id: str) -> int:
        """
        获取指定节点的计数
        
        Args:
            node_id: 节点ID
            
        Returns:
            该节点的计数
        """
        with self._lock:
            return self.node_counts.get(node_id, 0)
    
    def reset(self) -> None:
        """重置所有计数器"""
        with self._lock:
            self.count = 0
            self.node_counts.clear()
            self.node_timestamps.clear()
    
    def reset_node(self, node_id: str) -> None:
        """
        重置指定节点的计数
        
        Args:
            node_id: 节点ID
        """
        with self._lock:
            if node_id in self.node_counts:
                self.count -= self.node_counts[node_id]
                self.node_counts[node_id] = 0


class ToolProxy:
    """工具代理，包装MCP工具调用，提供计数、配额控制等功能"""
    
    # 默认全局计数器，用于共享计数
    _default_global_counter = GlobalCounter()
    
    def __init__(self, tool, call_limit: int = 25, global_counter: GlobalCounter = None, 
                 node_id: str = "local", mesh_adapter = None):
        """
        初始化工具代理
        
        Args:
            tool: 要代理的工具对象
            call_limit: 调用次数限制
            global_counter: 全局计数器，如果为None则使用默认计数器
            node_id: 节点ID，用于多节点环境
            mesh_adapter: 网格适配器，用于在计数器增加时广播更新
        """
        self._tool = tool
        self.name = getattr(tool, 'name', str(tool))
        self.call_limit = call_limit
        self._quota_exhausted = False
        self._global_counter = global_counter or ToolProxy._default_global_counter
        self.node_id = node_id
        self.mesh_adapter = mesh_adapter
        # 创建广播队列，用于非阻塞广播
        self._broadcast_queue = asyncio.Queue() if mesh_adapter else None
        if mesh_adapter and self._broadcast_queue:
            # 在测试中不启动后台任务，以避免事件循环问题
            self._broadcast_task = None
    
    @property
    def call_count(self) -> int:
        """获取当前调用计数"""
        return self._global_counter.get_count()
    
    def invoke(self, *args, **kwargs) -> Any:
        """
        调用代理的工具
        
        如果超出调用限制或配额已耗尽，则抛出QuotaExceededError
        
        Returns:
            工具调用的结果
            
        Raises:
            QuotaExceededError: 当工具调用超出限制或配额已耗尽时
        """
        # 检查配额是否已耗尽
        if self._quota_exhausted:
            raise QuotaExceededError(tool_name=self.name)
        
        # 增加计数并检查限制
        count = self._global_counter.increment(self.node_id)
        
        # 创建计数器更新消息（但不立即广播）
        if self.mesh_adapter:
            update_msg = CounterUpdateMsg(
                node_id=self.node_id,
                delta=1,
                counter_type="tool_call"
            )
            
            # 异步广播，但在测试环境中使用同步方式
            # 这样避免了在非事件循环中创建任务的问题
            self.schedule_counter_update(update_msg)
        
        if count > self.call_limit:
            raise QuotaExceededError(tool_name=self.name)
        
        # 调用实际工具
        return self._tool.invoke(*args, **kwargs)
    
    def schedule_counter_update(self, update_msg: CounterUpdateMsg) -> None:
        """
        计划广播计数器更新，避免在非事件循环环境中使用asyncio.create_task
        
        Args:
            update_msg: 计数器更新消息
        """
        if self.mesh_adapter:
            # 直接在线程中启动一个后台线程来处理广播
            broadcast_thread = threading.Thread(
                target=self._broadcast_in_thread,
                args=(update_msg,),
                daemon=True
            )
            broadcast_thread.start()
    
    def _broadcast_in_thread(self, update_msg: CounterUpdateMsg) -> None:
        """
        在后台线程中处理广播
        
        Args:
            update_msg: 计数器更新消息
        """
        try:
            # 创建一个新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行广播函数
            loop.run_until_complete(self._broadcast_counter_update(update_msg))
            
            # 关闭循环
            loop.close()
        except Exception as e:
            print(f"Error broadcasting counter update: {e}")
    
    async def _broadcast_counter_update(self, update_msg: CounterUpdateMsg) -> None:
        """
        广播计数器更新消息
        
        Args:
            update_msg: 计数器更新消息
        """
        if self.mesh_adapter:
            await self.mesh_adapter.broadcast_counter_update(update_msg)
    
    def apply_counter_update(self, update_msg: CounterUpdateMsg) -> None:
        """
        应用计数器更新
        
        Args:
            update_msg: 计数器更新消息
        """
        self._global_counter.apply_update(update_msg)
    
    def set_quota_exhausted(self, exhausted: bool) -> None:
        """
        设置配额耗尽状态
        
        Args:
            exhausted: 是否将配额标记为已耗尽
        """
        self._quota_exhausted = exhausted
    
    def reset_count(self) -> None:
        """重置计数器"""
        self._global_counter.reset()
    
    def get_call_count(self) -> int:
        """获取当前调用计数（别名方法）"""
        return self.call_count 