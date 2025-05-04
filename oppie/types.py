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