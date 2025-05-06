#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import time

class CoreState(Enum):
    """CursorCore的状态枚举"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    RECOVERING = "recovering"
    ERROR = "error"

@dataclass
class Step:
    """表示计划中的一个步骤"""
    id: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class Msg:
    """表示节点间传递的消息"""
    type: str  # runPlan, chat, recover, etc.
    timestamp: float = field(default_factory=time.time)
    plan: List[Step] = field(default_factory=list)
    prompt: Optional[str] = None
    ok: bool = True
    ts: Optional[int] = None
    
@dataclass
class CounterUpdateMsg:
    """表示计数器更新消息，用于节点间同步调用计数"""
    node_id: str
    delta: int = 1  # 默认增加1
    logical_ts: int = field(default_factory=lambda: int(time.time() * 1000))
    counter_type: str = "tool_call"  # 计数器类型
    
@dataclass
class ExecResult:
    """表示执行结果"""
    status: str  # success, error, recovery_needed
    message: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    
class QuotaExceededError(Exception):
    """工具调用配额耗尽异常"""
    def __init__(self, message="Tool call limit exceeded", tool_name=None):
        self.tool_name = tool_name
        self.message = f"{message}: {tool_name}" if tool_name else message
        super().__init__(self.message)
        
class TemplateMissingError(Exception):
    """模板缺失异常"""
    def __init__(self, message="Required Template A is missing from assistant response"):
        self.message = message
        super().__init__(self.message)

class ConfigUpdateMsg:
    """配置更新消息"""
    
    def __init__(self, 
                 section: str,
                 parameter: str,
                 value: Any,
                 timestamp: float,
                 node_id: str,
                 priority: int = 0,
                 version_vector: Optional[Dict[str, int]] = None):
        """
        初始化配置更新消息
        
        Args:
            section: 配置部分，如"mesh", "auto_tuner"
            parameter: 参数名称，如"batch_size_limit"
            value: 新值
            timestamp: 更新时间戳
            node_id: 发起更新的节点ID
            priority: 优先级（0-10，值越大优先级越高）
            version_vector: 版本向量，用于冲突检测
        """
        self.section = section
        self.parameter = parameter
        self.value = value
        self.timestamp = timestamp
        self.node_id = node_id
        self.priority = priority
        self.version_vector = version_vector or {}
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"ConfigUpdate({self.section}.{self.parameter}={self.value}, from={self.node_id})"
    
    def get_key(self) -> str:
        """获取配置键"""
        return f"{self.section}.{self.parameter}" 