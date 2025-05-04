#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import asyncio
import threading
from typing import Optional, Callable, Dict, Any, List

class AgentSHelpers:
    """Agent S帮助类，用于GUI自动化恢复"""
    
    def __init__(self):
        """初始化Agent S帮助类"""
        # 在实际实现中，这里会初始化pyautogui等自动化工具
        pass
    
    def focus_cursor(self) -> bool:
        """
        聚焦Cursor编辑器的输入区域
        
        Returns:
            是否成功聚焦
        """
        # 实际实现将使用pyautogui点击输入区域
        print("模拟: 聚焦Cursor编辑器")
        return True
    
    def type_and_enter(self, text: str) -> bool:
        """
        输入文本并按Enter键
        
        Args:
            text: 要输入的文本
            
        Returns:
            是否成功输入并发送
        """
        # 实际实现将使用pyautogui输入文本并按Enter
        print(f"模拟: 输入文本 '{text}' 并按Enter")
        return True
    
    def take_screenshot(self, region=None) -> Optional[bytes]:
        """
        截取屏幕区域的截图
        
        Args:
            region: 要截取的区域(x, y, width, height)，如果为None则截取全屏
            
        Returns:
            图像数据
        """
        # 实际实现将使用pyautogui截取屏幕
        print("模拟: 截取屏幕")
        return None
    
    def copy_to_clipboard(self) -> bool:
        """
        复制选中内容到剪贴板
        
        Returns:
            是否成功复制
        """
        # 实际实现将使用pyautogui模拟Ctrl+C
        print("模拟: 复制到剪贴板")
        return True


class DevLoopWatcher:
    """开发循环监视器，监控Cursor输出并触发恢复机制"""
    
    def __init__(self, stdout_file: str = None, stderr_file: str = None, agent_s = None):
        """
        初始化监视器
        
        Args:
            stdout_file: 标准输出文件路径
            stderr_file: 标准错误文件路径
            agent_s: Agent S帮助类实例
        """
        self.stdout_file = stdout_file
        self.stderr_file = stderr_file
        self.agent_s = agent_s or AgentSHelpers()
        self.recovery_count = 0
        self.last_recovery_time = 0
        self.recovery_in_progress = False
        self._stopping = False
        self._task = None
        
        # 定义错误模式
        self.error_patterns = [
            # 工具调用限制错误 - 匹配"Exceeded 25 native tool calls"
            re.compile(r"Exceeded\s+25\s+native\s+tool\s+calls"),
            
            # 缺少Template A错误 - 改进的正则表达式
            # 匹配以下模式：
            # 1. assistant_bubble_end标记
            # 2. 之后没有出现"Template A"或"Plan-and-Execute Cycle"
            # 3. 且在同一行或附近几行内没有找到## CYCLE或## Template
            re.compile(r"🪄\s+assistant_bubble_end(?![^<>]{0,200}(Template\s+A|Plan-and-Execute\s+Cycle|##\s*CYCLE|##\s*Template))")
        ]
        
        # 添加事件处理器字典
        self.event_handlers = {
            "recovery_triggered": [],     # 恢复触发事件处理器
            "recovery_completed": []      # 恢复完成事件处理器
        }
    
    def start_monitoring(self) -> None:
        """开始监控"""
        if self._task:
            return  # 已经在监控
        
        self._stopping = False
        
        # 创建线程而不是asyncio任务，因为我们要监控文件
        self._task = threading.Thread(target=self._monitor_loop)
        self._task.daemon = True
        self._task.start()
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        self._stopping = True
        
        if self._task:
            self._task.join(timeout=1.0)
            self._task = None
    
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        添加事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理器函数
        """
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        移除事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理器函数
        """
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    def _emit_event(self, event_type: str, **kwargs) -> None:
        """
        发送事件到所有注册的处理器
        
        Args:
            event_type: 事件类型
            **kwargs: 事件参数
        """
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(**kwargs)
                except Exception as e:
                    print(f"事件处理器错误: {e}")
    
    def _monitor_loop(self) -> None:
        """监控循环，检查文件变化"""
        last_stdout_position = 0
        last_stderr_position = 0
        
        while not self._stopping:
            try:
                # 监控标准输出
                if self.stdout_file and os.path.exists(self.stdout_file):
                    with open(self.stdout_file, 'r', encoding='utf-8') as f:
                        f.seek(last_stdout_position)
                        lines = f.readlines()
                        last_stdout_position = f.tell()
                        
                        for line in lines:
                            self.handle_line(line)
                
                # 监控标准错误
                if self.stderr_file and os.path.exists(self.stderr_file):
                    with open(self.stderr_file, 'r', encoding='utf-8') as f:
                        f.seek(last_stderr_position)
                        lines = f.readlines()
                        last_stderr_position = f.tell()
                        
                        for line in lines:
                            self.handle_line(line, is_stderr=True)
                
                # 短暂休眠以减少CPU使用
                time.sleep(0.1)
                
            except Exception as e:
                print(f"监控错误: {e}")
                time.sleep(1.0)  # 出错时稍长的休眠
    
    def handle_line(self, line: str, is_stderr: bool = False) -> None:
        """
        处理单行输出
        
        Args:
            line: 输出行
            is_stderr: 是否来自标准错误
        """
        # 如果恢复正在进行，则忽略此行
        if self.recovery_in_progress:
            return
        
        # 检查是否匹配错误模式
        for pattern in self.error_patterns:
            if pattern.search(line):
                self.trigger_recovery()
                break
    
    def trigger_recovery(self) -> bool:
        """
        触发恢复机制
        
        Returns:
            是否成功触发恢复
        """
        # 检查上次恢复时间，防止过于频繁的恢复
        current_time = time.time()
        if current_time - self.last_recovery_time < 5:  # 至少5秒间隔
            return False
        
        try:
            self.recovery_in_progress = True
            self.last_recovery_time = current_time
            self.recovery_count += 1
            
            # 发送恢复触发事件
            self._emit_event("recovery_triggered", count=self.recovery_count, timestamp=current_time)
            
            # 使用Agent S聚焦Cursor
            if not self.agent_s.focus_cursor():
                print("无法聚焦Cursor编辑器")
                return False
            
            # 输入恢复提示并按Enter
            recovery_prompt = (
                "Cursor Executor, on top of @.cursorrules, @tech_stack.md and @scratchpad.md, "
                "strictly follow instructions from Codex Planner in the `Template Aₓ — Plan-and-Execute Loop` "
                "above to continue at where you stopped"
            )
            
            if not self.agent_s.type_and_enter(recovery_prompt):
                print("无法输入恢复提示")
                return False
            
            print(f"成功触发恢复机制，这是第{self.recovery_count}次恢复")
            
            # 发送恢复完成事件
            self._emit_event("recovery_completed", count=self.recovery_count, timestamp=time.time())
            
            return True
            
        except Exception as e:
            print(f"恢复过程中出错: {e}")
            return False
            
        finally:
            self.recovery_in_progress = False


class SidecarDaemon:
    """Sidecar守护进程，用于远程控制和监控Cursor"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        初始化守护进程
        
        Args:
            host: 监听主机
            port: 监听端口
        """
        self.host = host
        self.port = port
        self.connected = False
        self.socket = None
        self._task = None
        self._stopping = False
    
    async def connect(self) -> bool:
        """
        连接到Cursor
        
        Returns:
            是否成功连接
        """
        # 在实际实现中，这将连接到Cursor的IPC接口
        self.connected = True
        return True
    
    async def disconnect(self) -> bool:
        """
        断开与Cursor的连接
        
        Returns:
            是否成功断开
        """
        self.connected = False
        return True
    
    async def send_chat(self, prompt: str) -> bool:
        """
        发送聊天消息
        
        Args:
            prompt: 聊天提示
            
        Returns:
            是否成功发送
        """
        if not self.connected:
            return False
        
        # 在实际实现中，这将通过IPC发送消息到Cursor
        print(f"通过Sidecar发送聊天: {prompt}")
        return True
    
    async def send_recovery(self, timestamp: int = None) -> bool:
        """
        发送恢复消息
        
        Args:
            timestamp: 恢复时间戳
            
        Returns:
            是否成功发送恢复消息
        """
        if not self.connected:
            return False
        
        ts = timestamp or int(time.time() * 1000)
        
        # 在实际实现中，这将通过IPC发送恢复消息到Cursor
        print(f"通过Sidecar发送恢复: {ts}")
        return True 