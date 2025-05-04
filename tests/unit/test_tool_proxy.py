#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import MagicMock, patch

# 导入实际实现
from oppie.tool_proxy import ToolProxy, GlobalCounter
from oppie.types import QuotaExceededError

class TestToolProxy(unittest.TestCase):
    """测试ToolProxy组件，验证工具调用计数和配额耗尽功能"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.mock_tool = MagicMock()
        self.mock_tool.name = "test_tool"
        self.mock_tool.invoke = MagicMock(return_value={"result": "success"})
        
        # 使用实际的ToolProxy
        self.tool_proxy = ToolProxy(self.mock_tool)
    
    def test_tool_proxy_counts_calls(self):
        """测试工具代理正确计数调用"""
        # 重置计数
        self.tool_proxy.reset_count()
        
        # 调用工具三次
        self.tool_proxy.invoke("arg1", "arg2")
        self.tool_proxy.invoke("arg1", "arg2")
        self.tool_proxy.invoke("arg1", "arg2")
        
        self.assertEqual(self.tool_proxy.call_count, 3)
        self.mock_tool.invoke.assert_called_with("arg1", "arg2")
    
    def test_tool_proxy_enforces_call_limit(self):
        """测试工具代理强制执行调用限制"""
        # 创建一个新的工具代理，设置较低的调用限制
        proxy = ToolProxy(self.mock_tool, call_limit=5)
        
        # 重置计数
        proxy.reset_count()
        
        # 调用工具5次（达到限制）
        for _ in range(5):
            result = proxy.invoke("arg1", "arg2")
            self.assertEqual(result, {"result": "success"})
        
        # 第6次调用应该触发配额耗尽
        with self.assertRaises(QuotaExceededError) as context:
            proxy.invoke("arg1", "arg2")
        
        self.assertIn("Tool call limit exceeded", str(context.exception))
    
    def test_tool_proxy_preset_quota_exhausted(self):
        """测试工具代理可以预设配额耗尽状态"""
        # 重置计数
        self.tool_proxy.reset_count()
        
        # 预设配额耗尽
        self.tool_proxy.set_quota_exhausted(True)
        
        # 尝试调用工具应该立即失败
        with self.assertRaises(QuotaExceededError) as context:
            self.tool_proxy.invoke("arg1", "arg2")
        
        self.assertIn("Tool call limit exceeded", str(context.exception))
        
        # 重置配额耗尽状态
        self.tool_proxy.set_quota_exhausted(False)
        
        # 现在调用应该成功
        result = self.tool_proxy.invoke("arg1", "arg2")
        self.assertEqual(result, {"result": "success"})
    
    def test_tool_proxy_forwards_calls_correctly(self):
        """测试工具代理正确转发调用"""
        # 重置计数
        self.tool_proxy.reset_count()
        
        # 调用带有多个参数的工具
        result = self.tool_proxy.invoke("arg1", "arg2", keyword=True)
        
        # 验证调用和参数传递正确
        self.mock_tool.invoke.assert_called_once_with("arg1", "arg2", keyword=True)
        self.assertEqual(result, {"result": "success"})
    
    def test_tool_proxy_resets_count(self):
        """测试工具代理重置计数功能"""
        # 重置计数
        self.tool_proxy.reset_count()
        
        # 调用工具几次
        for _ in range(3):
            self.tool_proxy.invoke("arg1", "arg2")
        
        self.assertEqual(self.tool_proxy.call_count, 3)
        
        # 重置计数
        self.tool_proxy.reset_count()
        
        self.assertEqual(self.tool_proxy.call_count, 0)
        
        # 再次调用
        self.tool_proxy.invoke("arg1", "arg2")
        self.assertEqual(self.tool_proxy.call_count, 1)
    
    def test_multiple_tool_proxies_share_count(self):
        """测试多个工具代理共享计数"""
        # 创建一个全局计数器
        counter = GlobalCounter()
        
        # 创建两个共享计数的代理
        proxy1 = ToolProxy(self.mock_tool, global_counter=counter)
        
        mock_tool2 = MagicMock()
        mock_tool2.name = "test_tool2"
        mock_tool2.invoke = MagicMock(return_value={"result": "tool2"})
        proxy2 = ToolProxy(mock_tool2, global_counter=counter)
        
        # 重置计数
        counter.reset()
        
        # 每个代理调用一次
        proxy1.invoke("arg1")
        self.assertEqual(proxy1.call_count, 1)
        self.assertEqual(proxy2.call_count, 1)
        
        proxy2.invoke("arg2")
        self.assertEqual(proxy1.call_count, 2)
        self.assertEqual(proxy2.call_count, 2)

if __name__ == "__main__":
    unittest.main() 