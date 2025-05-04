#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
from typing import Any, Dict, Optional
from oppie.types import QuotaExceededError

class GlobalCounter:
    """全局计数器，用于跨代理共享工具调用计数"""
    
    def __init__(self):
        self.count = 0
        self._lock = threading.Lock()
    
    def increment(self) -> int:
        """增加计数并返回新值"""
        with self._lock:
            self.count += 1
            return self.count
    
    def get_count(self) -> int:
        """获取当前计数"""
        with self._lock:
            return self.count
    
    def reset(self) -> None:
        """重置计数器"""
        with self._lock:
            self.count = 0


class ToolProxy:
    """工具代理，包装MCP工具调用，提供计数、配额控制等功能"""
    
    # 默认全局计数器，用于共享计数
    _default_global_counter = GlobalCounter()
    
    def __init__(self, tool, call_limit: int = 25, global_counter: GlobalCounter = None):
        """
        初始化工具代理
        
        Args:
            tool: 要代理的工具对象
            call_limit: 调用次数限制
            global_counter: 全局计数器，如果为None则使用默认计数器
        """
        self._tool = tool
        self.name = getattr(tool, 'name', str(tool))
        self.call_limit = call_limit
        self._quota_exhausted = False
        self._global_counter = global_counter or ToolProxy._default_global_counter
    
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
        count = self._global_counter.increment()
        if count > self.call_limit:
            raise QuotaExceededError(tool_name=self.name)
        
        # 调用实际工具
        return self._tool.invoke(*args, **kwargs)
    
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