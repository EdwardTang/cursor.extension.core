#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Callable, Set, Union
from oppie.types import CoreState, Step, Msg, ExecResult, QuotaExceededError, TemplateMissingError

class CursorCore:
    """Cursor核心组件，负责状态管理和计划执行"""
    
    def __init__(self):
        """初始化CursorCore"""
        self.state = CoreState.INACTIVE
        self.tool_call_count = 0
        self.recovery_triggered = False
        self.auto_recovered = False
        self.last_recovery_ts = None
        self.server = None
        self.webview = None
        self.socket = None
        self.pocket_flow = None
        self.commands = ["cursor.openChat", "cursor.composer"]  # 默认可用命令
        self._event_handlers = {}  # 事件处理器字典
    
    def activate(self) -> bool:
        """
        激活CursorCore，创建IPC服务器
        
        Returns:
            是否成功激活
        """
        if self.state != CoreState.INACTIVE:
            return False
        
        try:
            # 创建IPC服务器（实际实现将根据具体IPC机制）
            self.server = True  # 简化实现，实际应创建服务器
            self.state = CoreState.ACTIVE
            self._emit_event("activated", {"timestamp": time.time()})
            return True
        except Exception as e:
            self._emit_event("error", {"message": str(e)})
            return False
    
    def handle_message(self, msg: Msg) -> ExecResult:
        """
        处理接收到的消息
        
        Args:
            msg: 要处理的消息
            
        Returns:
            执行结果
            
        Raises:
            ValueError: 当消息格式无效时
        """
        # 验证消息
        self._validate_message(msg)
        
        try:
            # 根据消息类型执行不同的处理
            if msg.type == "runPlan":
                # 检查工具调用限制
                if self.tool_call_count >= 25:
                    self.recovery_triggered = True
                    return ExecResult(status="recovery_needed", 
                                    message="Tool call limit exceeded")
                
                return self.execute_plan(msg.plan)
            
            elif msg.type == "chat":
                if not msg.prompt:
                    raise ValueError("Chat message must contain a prompt")
                
                # 处理聊天消息
                self._emit_event("chat_received", {"prompt": msg.prompt})
                return ExecResult(status="success", message="Chat processed")
            
            elif msg.type == "recover":
                # 处理恢复消息
                self.last_recovery_ts = msg.ts
                self.recovery_triggered = False
                self.auto_recovered = True
                self._emit_event("recovered", {"timestamp": msg.ts})
                return ExecResult(status="success", message="Recovery acknowledged")
            
            else:
                raise ValueError(f"Unsupported message type: {msg.type}")
                
        except QuotaExceededError as e:
            self.recovery_triggered = True
            return ExecResult(status="recovery_needed", message=str(e))
        
        except TemplateMissingError as e:
            self.recovery_triggered = True
            return ExecResult(status="recovery_needed", message=str(e))
        
        except Exception as e:
            return ExecResult(status="error", message=str(e))
    
    def execute_plan(self, plan: List[Step]) -> ExecResult:
        """
        执行计划
        
        Args:
            plan: 要执行的步骤列表
            
        Returns:
            执行结果
        """
        if not self.pocket_flow:
            self.pocket_flow = MagicMock()  # 简化实现，实际应初始化PocketFlow
        
        try:
            # 调用PocketFlow执行计划
            self.pocket_flow.run(plan)
            self._emit_event("plan_executed", {"step_count": len(plan)})
            return ExecResult(status="success", message="Plan executed successfully")
        
        except QuotaExceededError as e:
            self.recovery_triggered = True
            return ExecResult(status="recovery_needed", message=str(e))
        
        except Exception as e:
            return ExecResult(status="error", message=str(e))
    
    def webview_post(self, event: Dict[str, Any]) -> None:
        """
        向webview发送事件
        
        Args:
            event: 要发送的事件数据
        """
        if self.webview:
            self.webview.postMessage(event)
    
    def sidecar_notify(self, event: Dict[str, Any]) -> None:
        """
        向sidecar发送事件
        
        Args:
            event: 要发送的事件数据
        """
        if self.socket:
            message = json.dumps(event)
            self.socket.write(message)
    
    def discover_chat_command(self) -> str:
        """
        发现可用的聊天命令
        
        Returns:
            可用的聊天命令
        """
        # 按优先级返回首个可用的聊天命令
        for cmd in ["cursor.openChat", "cursor.composer"]:
            if cmd in self.commands:
                return cmd
        
        return "cursor.composer"  # 默认使用composer命令
    
    def _validate_message(self, msg: Msg) -> None:
        """
        验证消息格式
        
        Args:
            msg: 要验证的消息
            
        Raises:
            ValueError: 当消息格式无效时
        """
        if not isinstance(msg, Msg):
            raise ValueError("Message must be an instance of Msg class")
        
        # 检查消息类型是否支持
        valid_types = ["runPlan", "chat", "recover"]
        if msg.type not in valid_types:
            raise ValueError(f"Unsupported message type: {msg.type}")
        
        if msg.type == "runPlan" and not msg.plan:
            raise ValueError("runPlan message must contain a plan")
        
        if msg.type == "chat" and not msg.prompt:
            raise ValueError("chat message must contain a prompt")
        
        if msg.type == "recover" and msg.ts is None:
            raise ValueError("recover message must contain a timestamp")
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        触发事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                handler(data)
    
    def on(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = set()
        
        self._event_handlers[event_type].add(handler)
    
    def off(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        注销事件处理器
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type in self._event_handlers:
            self._event_handlers[event_type].discard(handler)
            
    def check_template_present(self, response: str) -> bool:
        """
        检查响应中是否包含Template A
        
        Args:
            response: 助手响应内容
            
        Returns:
            是否包含模板
            
        Raises:
            TemplateMissingError: 当模板缺失时
        """
        if "Template A" not in response and "Plan-and-Execute Cycle" not in response:
            raise TemplateMissingError()
        
        return True

# 临时的MagicMock类，用于测试目的
class MagicMock:
    """模拟类，用于测试"""
    
    def __init__(self, **kwargs):
        """初始化模拟对象"""
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        self.calls = []
    
    def __getattr__(self, name):
        """处理未定义的属性访问"""
        def _method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return kwargs.get('return_value', None)
        
        return _method 