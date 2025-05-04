#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import asyncio
from unittest.mock import MagicMock, patch

# 导入实际实现
from oppie.cursor_core import CursorCore
from oppie.types import Msg, Step, ExecResult, QuotaExceededError, TemplateMissingError

class TestCursorCore(unittest.TestCase):
    """测试CursorCore组件的状态转换和边界条件"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        # 使用实际的CursorCore
        self.core = CursorCore()
        self.mock_ipc = MagicMock()
        self.mock_socket = MagicMock()
    
    def test_activation_creates_ipc_server(self):
        """测试激活时创建IPC服务器"""
        # 使用实际的CursorCore方法
        result = self.core.activate()
        
        self.assertTrue(result)
        self.assertIsNotNone(self.core.server)
    
    def test_handle_run_plan_message(self):
        """测试处理runPlan类型的消息"""
        # 创建一个runPlan消息
        plan = [Step(id="1", action="test")]
        msg = Msg(type="runPlan", plan=plan)
        
        # 模拟PocketFlow
        self.core.pocket_flow = MagicMock()
        
        # 处理消息
        result = self.core.handle_message(msg)
        
        self.assertEqual(result.status, "success")
    
    def test_handle_chat_message(self):
        """测试处理chat类型的消息"""
        # 创建一个chat消息
        msg = Msg(type="chat", prompt="Hello")
        
        # 处理消息
        result = self.core.handle_message(msg)
        
        self.assertEqual(result.status, "success")
    
    def test_execute_plan_calls_pocket_flow(self):
        """测试executePlan调用PocketFlow"""
        # 创建计划
        plan = [Step(id="1", action="test")]
        
        # 模拟PocketFlow
        self.core.pocket_flow = MagicMock()
        
        # 执行计划
        self.core.execute_plan(plan)
        
        # 验证PocketFlow.run被调用
        self.core.pocket_flow.run.assert_called_once_with(plan)
    
    def test_webview_post_sends_events(self):
        """测试webviewPost发送事件"""
        # 创建事件
        event = {"type": "progress", "pct": 50, "log": "Testing"}
        
        # 模拟webview
        self.core.webview = MagicMock()
        
        # 发送事件
        self.core.webview_post(event)
        
        # 验证postMessage被调用
        self.core.webview.postMessage.assert_called_once_with(event)
    
    def test_sidecar_notify_sends_events(self):
        """测试sidecarNotify发送事件"""
        # 创建事件
        event = {"type": "progress", "pct": 50, "log": "Testing"}
        
        # 模拟socket
        self.core.socket = MagicMock()
        
        # 发送事件
        self.core.sidecar_notify(event)
        
        # 验证socket.write被调用
        self.core.socket.write.assert_called_once()
    
    def test_discover_chat_command(self):
        """测试动态命令发现功能"""
        # 设置命令
        self.core.commands = ["cursor.openChat", "cursor.composer", "other.command"]
        
        # 发现命令
        command = self.core.discover_chat_command()
        
        # 验证返回的是支持的命令
        self.assertIn(command, ["cursor.openChat", "cursor.composer"])
    
    def test_handle_recover_message(self):
        """测试处理recover类型的消息"""
        # 创建recover消息
        msg = Msg(type="recover", ok=True, ts=123456789)
        
        # 处理消息
        result = self.core.handle_message(msg)
        
        # 验证结果和状态
        self.assertEqual(result.status, "success")
        self.assertEqual(self.core.last_recovery_ts, 123456789)

    def test_message_validation(self):
        """测试消息验证逻辑"""
        # 测试无效消息类型
        with self.assertRaises(ValueError):
            self.core.handle_message(Msg(type="invalid"))
        
        # 测试缺少必要字段的消息
        with self.assertRaises(ValueError):
            self.core.handle_message(Msg(type="runPlan"))  # 缺少plan字段
            
        with self.assertRaises(ValueError):
            self.core.handle_message(Msg(type="chat"))  # 缺少prompt字段
            
        with self.assertRaises(ValueError):
            self.core.handle_message(Msg(type="recover"))  # 缺少ts字段
    
    def test_25_tool_call_limit_handling(self):
        """测试25工具调用限制的处理"""
        # 模拟工具调用限制
        self.core.tool_call_count = 25
        msg = Msg(type="runPlan", plan=[Step(id="1", action="test")])
        
        # 处理消息
        result = self.core.handle_message(msg)
        
        # 验证触发恢复
        self.assertEqual(result.status, "recovery_needed")
        self.assertTrue(self.core.recovery_triggered)
        
    def test_template_missing_detection(self):
        """测试模板缺失检测"""
        # 测试缺少模板的响应
        with self.assertRaises(TemplateMissingError):
            self.core.check_template_present("Response without template")
            
        # 测试包含模板的响应
        self.assertTrue(self.core.check_template_present("Response with Template A example"))
        self.assertTrue(self.core.check_template_present("Response with Plan-and-Execute Cycle"))

if __name__ == "__main__":
    unittest.main() 