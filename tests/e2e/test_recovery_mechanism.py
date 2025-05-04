#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import asyncio
import tempfile
import os
import time
from unittest.mock import MagicMock, patch

# 导入实际实现
from oppie.dev_loop_watcher import DevLoopWatcher, AgentSHelpers, SidecarDaemon
from oppie.cursor_core import CursorCore

class TestRecoveryMechanism(unittest.TestCase):
    """测试系统恢复机制的端到端测试"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        # 创建临时文件用于模拟输出
        self.temp_stdout = tempfile.NamedTemporaryFile(delete=False)
        self.temp_stderr = tempfile.NamedTemporaryFile(delete=False)
        
        # 保存文件名
        self.stdout_path = self.temp_stdout.name
        self.stderr_path = self.temp_stderr.name
        
        # 关闭文件以便于后续写入
        self.temp_stdout.close()
        self.temp_stderr.close()
        
        # 实际的组件
        self.agent_s = AgentSHelpers()
        self.watcher = DevLoopWatcher(
            stdout_file=self.stdout_path, 
            stderr_file=self.stderr_path,
            agent_s=self.agent_s
        )
        self.core = CursorCore()
        self.sidecar = SidecarDaemon()
    
    def tearDown(self):
        """每个测试后的清理工作"""
        # 删除临时文件
        os.unlink(self.stdout_path)
        os.unlink(self.stderr_path)
    
    def test_recovery_from_25_tool_call_limit(self):
        """测试从25工具调用限制恢复"""
        # 将测试输出写入临时文件
        with open(self.stdout_path, 'w') as f:
            # 模拟Cursor输出包含工具调用限制错误
            f.write("Log line 1\n")
            f.write("Log line 2\n")
            f.write("Exceeded 25 native tool calls\n")
            f.write("Log line 4\n")
        
        # 模拟AgentS和Watcher的行为
        agent_s_mock = MagicMock()
        agent_s_mock.focus_cursor.return_value = True
        agent_s_mock.type_and_enter.return_value = True
        
        # 使用模拟的AgentS创建Watcher
        watcher = DevLoopWatcher(
            stdout_file=self.stdout_path,
            agent_s=agent_s_mock
        )
        
        # 添加事件处理器
        triggered_mock = MagicMock()
        completed_mock = MagicMock()
        watcher.add_event_handler("recovery_triggered", triggered_mock)
        watcher.add_event_handler("recovery_completed", completed_mock)
        
        # 启动监控
        watcher.start_monitoring()
        
        # 等待足够的时间让监控器处理文件
        time.sleep(0.5)
        
        # 停止监控
        watcher.stop_monitoring()
        
        # 验证行为
        agent_s_mock.focus_cursor.assert_called_once()
        agent_s_mock.type_and_enter.assert_called_once()
        self.assertEqual(watcher.recovery_count, 1)
        
        # 验证事件触发
        triggered_mock.assert_called_once()
        completed_mock.assert_called_once()
    
    def test_recovery_from_missing_template(self):
        """测试从缺少Template A恢复"""
        # 将测试输出写入临时文件，模拟缺少Template A的情况
        with open(self.stdout_path, 'w') as f:
            f.write("Log line 1\n")
            f.write("🪄 assistant_bubble_end\n")  # 缺少Template A的气泡结束
            f.write("Log line 3\n")
        
        # 模拟AgentS和Watcher的行为
        agent_s_mock = MagicMock()
        agent_s_mock.focus_cursor.return_value = True
        agent_s_mock.type_and_enter.return_value = True
        
        # 使用模拟的AgentS创建Watcher
        watcher = DevLoopWatcher(
            stdout_file=self.stdout_path,
            agent_s=agent_s_mock
        )
        
        # 启动监控
        watcher.start_monitoring()
        
        # 等待足够的时间让监控器处理文件
        time.sleep(0.5)
        
        # 停止监控
        watcher.stop_monitoring()
        
        # 验证行为
        agent_s_mock.focus_cursor.assert_called_once()
        agent_s_mock.type_and_enter.assert_called_once()
        self.assertEqual(watcher.recovery_count, 1)
    
    def test_no_recovery_for_valid_template(self):
        """测试有效的Template A不会触发恢复"""
        # 将测试输出写入临时文件，包含有效的Template A
        with open(self.stdout_path, 'w') as f:
            f.write("Log line 1\n")
            f.write("🪄 assistant_bubble_end Template A — Plan-and-Execute Cycle\n")  # 包含Template A
            f.write("Log line 3\n")
        
        # 模拟AgentS和Watcher的行为
        agent_s_mock = MagicMock()
        agent_s_mock.focus_cursor.return_value = True
        agent_s_mock.type_and_enter.return_value = True
        
        # 使用模拟的AgentS创建Watcher
        watcher = DevLoopWatcher(
            stdout_file=self.stdout_path,
            agent_s=agent_s_mock
        )
        
        # 启动监控
        watcher.start_monitoring()
        
        # 等待足够的时间让监控器处理文件
        time.sleep(0.5)
        
        # 停止监控
        watcher.stop_monitoring()
        
        # 验证行为 - 不应该触发恢复
        agent_s_mock.focus_cursor.assert_not_called()
        agent_s_mock.type_and_enter.assert_not_called()
        self.assertEqual(watcher.recovery_count, 0)
    
    def test_end_to_end_recovery_workflow(self):
        """测试端到端恢复工作流"""
        # 激活核心组件
        self.core.activate()
        
        # 模拟Sidecar连接
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.sidecar.connect())
        
        # 模拟工具调用限制
        self.core.tool_call_count = 25
        
        # 事件处理器
        recovery_completed = MagicMock()
        
        # 使用模拟的AgentS
        agent_s_mock = MagicMock()
        agent_s_mock.focus_cursor.return_value = True
        agent_s_mock.type_and_enter.return_value = True
        
        # 创建Watcher
        watcher = DevLoopWatcher(
            stdout_file=self.stdout_path,
            agent_s=agent_s_mock
        )
        
        # 添加事件处理器
        watcher.add_event_handler("recovery_completed", recovery_completed)
        
        # 将模拟的工具调用限制错误输出到文件
        with open(self.stdout_path, 'w') as f:
            f.write("Exceeded 25 native tool calls\n")
        
        # 启动监控
        watcher.start_monitoring()
        
        # 等待足够的时间让监控器处理文件
        time.sleep(0.5)
        
        # 停止监控
        watcher.stop_monitoring()
        
        # 验证恢复机制激活
        agent_s_mock.focus_cursor.assert_called_once()
        agent_s_mock.type_and_enter.assert_called_once()
        self.assertEqual(watcher.recovery_count, 1)
        
        # 验证事件触发
        recovery_completed.assert_called_once()
    
    def test_recovery_performance(self):
        """测试恢复性能，确保在目标时间内完成"""
        # 将模拟的工具调用限制错误输出到文件
        with open(self.stdout_path, 'w') as f:
            f.write("Exceeded 25 native tool calls\n")
        
        # 模拟AgentS和Watcher的行为
        agent_s_mock = MagicMock()
        agent_s_mock.focus_cursor.return_value = True
        agent_s_mock.type_and_enter.return_value = True
        
        # 使用模拟的AgentS创建Watcher
        watcher = DevLoopWatcher(
            stdout_file=self.stdout_path,
            agent_s=agent_s_mock
        )
        
        # 直接调用trigger_recovery方法进行测量
        start_time = time.time()
        result = watcher.trigger_recovery()
        end_time = time.time()
        
        # 计算恢复时间（毫秒）
        recovery_time = (end_time - start_time) * 1000
        
        # 验证结果和性能
        self.assertTrue(result)
        self.assertTrue(recovery_time < 250, f"恢复时间为{recovery_time}毫秒，超过了250毫秒的目标")
    
    def test_false_positive_rate(self):
        """测试假阳性率，确保不会错误触发恢复"""
        # 创建一个包含类似但不完全匹配错误条件的输出
        with open(self.stdout_path, 'w') as f:
            f.write("Log discussing exceeding 25 native tool calls as a concept\n")
            f.write("🪄 assistant_bubble_end with some content Template A\n")  # 包含Template A
            f.write("Normal log line mentioning Template A\n")
        
        # 模拟AgentS和Watcher的行为
        agent_s_mock = MagicMock()
        agent_s_mock.focus_cursor.return_value = True
        agent_s_mock.type_and_enter.return_value = True
        
        # 使用模拟的AgentS创建Watcher
        watcher = DevLoopWatcher(
            stdout_file=self.stdout_path,
            agent_s=agent_s_mock
        )
        
        # 启动监控
        watcher.start_monitoring()
        
        # 等待足够的时间让监控器处理文件
        time.sleep(0.5)
        
        # 停止监控
        watcher.stop_monitoring()
        
        # 验证不会错误触发恢复
        agent_s_mock.focus_cursor.assert_not_called()
        agent_s_mock.type_and_enter.assert_not_called()
    
    def test_event_handlers(self):
        """测试事件处理器机制"""
        # 模拟AgentS
        agent_s_mock = MagicMock()
        agent_s_mock.focus_cursor.return_value = True
        agent_s_mock.type_and_enter.return_value = True
        
        # 创建Watcher
        watcher = DevLoopWatcher(
            stdout_file=self.stdout_path,
            agent_s=agent_s_mock
        )
        
        # 创建模拟的事件处理器
        trigger_handler = MagicMock()
        complete_handler = MagicMock()
        
        # 添加事件处理器
        watcher.add_event_handler("recovery_triggered", trigger_handler)
        watcher.add_event_handler("recovery_completed", complete_handler)
        
        # 触发恢复
        watcher.trigger_recovery()
        
        # 验证事件处理器被调用
        trigger_handler.assert_called_once()
        complete_handler.assert_called_once()
        
        # 移除事件处理器
        watcher.remove_event_handler("recovery_triggered", trigger_handler)
        watcher.remove_event_handler("recovery_completed", complete_handler)
        
        # 重置模拟
        trigger_handler.reset_mock()
        complete_handler.reset_mock()
        
        # 再次触发恢复
        watcher.trigger_recovery()
        
        # 验证事件处理器未被调用
        trigger_handler.assert_not_called()
        complete_handler.assert_not_called()

if __name__ == "__main__":
    unittest.main() 