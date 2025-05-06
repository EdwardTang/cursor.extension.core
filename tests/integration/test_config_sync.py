#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置同步集成测试
测试多节点环境下的配置同步功能
"""

import os
import sys
import time
import asyncio
import unittest
from unittest.mock import MagicMock, patch
import logging
import random
from typing import Dict, Any, List, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from oppie.mesh_adapter import MeshAdapter
from oppie.config import get_config, update_config, AutoTuner
from oppie.config_sync import ConfigSyncManager
from oppie.types import ConfigUpdateMsg

# 禁用日志
logging.basicConfig(level=logging.CRITICAL)

class TestConfigSync(unittest.TestCase):
    """配置同步测试"""
    
    async def asyncSetUp(self):
        """异步设置"""
        # 重置配置
        update_config("mesh", {"enable_batch_processing": True})
        update_config("config_sync", {"enable": True})
        
        # 创建多个网格适配器
        self.node_a = MeshAdapter(node_id="node_A")
        self.node_b = MeshAdapter(node_id="node_B")
        self.node_c = MeshAdapter(node_id="node_C")
        
        # 连接节点
        self.node_a.connect_to_node(self.node_b)
        self.node_a.connect_to_node(self.node_c)
        self.node_b.connect_to_node(self.node_c)
        
        # 创建配置同步管理器
        self.sync_a = ConfigSyncManager(mesh_adapter=self.node_a)
        self.sync_b = ConfigSyncManager(mesh_adapter=self.node_b)
        self.sync_c = ConfigSyncManager(mesh_adapter=self.node_c)
        
        # 启动配置同步管理器
        await self.sync_a.start()
        await self.sync_b.start()
        await self.sync_c.start()
        
        # 确保所有节点已经连接
        await asyncio.sleep(0.1)
    
    async def asyncTearDown(self):
        """异步清理"""
        # 停止配置同步管理器
        await self.sync_a.stop()
        await self.sync_b.stop()
        await self.sync_c.stop()
        
        # 断开节点
        self.node_a.disconnect_from_all()
        self.node_b.disconnect_from_all()
        self.node_c.disconnect_from_all()
    
    async def test_basic_config_sync(self):
        """测试基本配置同步"""
        # 从节点A发布配置更新
        await self.sync_a.publish_update("mesh", "batch_size_limit", 15)
        
        # 等待同步
        await asyncio.sleep(0.2)
        
        # 检查所有节点是否收到更新
        self.assertEqual(get_config("mesh")["batch_size_limit"], 15)
        
        # 检查每个节点的配置值
        config_a = {
            "section": "mesh",
            "parameter": "batch_size_limit",
            "value": self.sync_a.applied_updates.get("mesh.batch_size_limit").value if "mesh.batch_size_limit" in self.sync_a.applied_updates else None
        }
        
        config_b = {
            "section": "mesh",
            "parameter": "batch_size_limit",
            "value": self.sync_b.applied_updates.get("mesh.batch_size_limit").value if "mesh.batch_size_limit" in self.sync_b.applied_updates else None
        }
        
        config_c = {
            "section": "mesh",
            "parameter": "batch_size_limit",
            "value": self.sync_c.applied_updates.get("mesh.batch_size_limit").value if "mesh.batch_size_limit" in self.sync_c.applied_updates else None
        }
        
        self.assertEqual(config_a["value"], 15)
        self.assertEqual(config_b["value"], 15)
        self.assertEqual(config_c["value"], 15)
    
    async def test_multiple_updates(self):
        """测试多个配置更新"""
        # 从不同节点发布不同配置更新
        await self.sync_a.publish_update("mesh", "batch_size_limit", 20)
        await self.sync_b.publish_update("mesh", "batch_time_limit_ms", 200)
        await self.sync_c.publish_update("mesh", "enable_compression", True)
        
        # 等待同步
        await asyncio.sleep(0.5)
        
        # 检查所有节点是否收到所有更新
        mesh_config = get_config("mesh")
        self.assertEqual(mesh_config["batch_size_limit"], 20)
        self.assertEqual(mesh_config["batch_time_limit_ms"], 200)
        self.assertEqual(mesh_config["enable_compression"], True)
        
        # 检查每个节点的应用更新数量
        self.assertGreaterEqual(len(self.sync_a.applied_updates), 3)
        self.assertGreaterEqual(len(self.sync_b.applied_updates), 3)
        self.assertGreaterEqual(len(self.sync_c.applied_updates), 3)
    
    async def test_conflict_resolution(self):
        """测试冲突解决"""
        # 从不同节点几乎同时发布对同一配置项的更新
        tasks = [
            asyncio.create_task(self.sync_a.publish_update("mesh", "max_retries", 5)),
            asyncio.create_task(self.sync_b.publish_update("mesh", "max_retries", 8)),
            asyncio.create_task(self.sync_c.publish_update("mesh", "max_retries", 3))
        ]
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
        # 等待同步和冲突解决
        await asyncio.sleep(0.5)
        
        # 检查最终值是否一致（不管是哪个值获胜）
        final_value = get_config("mesh")["max_retries"]
        
        # 检查所有节点是否同步到相同的值
        self.assertEqual(self.sync_a.applied_updates["mesh.max_retries"].value, final_value)
        self.assertEqual(self.sync_b.applied_updates["mesh.max_retries"].value, final_value)
        self.assertEqual(self.sync_c.applied_updates["mesh.max_retries"].value, final_value)
    
    async def test_priority_based_conflict_resolution(self):
        """测试基于优先级的冲突解决"""
        # 从不同节点发布不同优先级的更新
        await self.sync_a.publish_update("mesh", "retry_interval_ms", 300, priority=1)  # 低优先级
        await asyncio.sleep(0.1)  # 确保时间戳不同
        await self.sync_b.publish_update("mesh", "retry_interval_ms", 600, priority=5)  # 高优先级
        
        # 等待同步
        await asyncio.sleep(0.3)
        
        # 检查是否高优先级的值获胜
        final_value = get_config("mesh")["retry_interval_ms"]
        self.assertEqual(final_value, 600)
        
        # 再次测试，这次低优先级更新较晚
        await self.sync_c.publish_update("mesh", "retry_interval_ms", 900, priority=8)  # 更高优先级
        
        # 等待同步
        await asyncio.sleep(0.3)
        
        # 检查是否更高优先级的值获胜
        final_value = get_config("mesh")["retry_interval_ms"]
        self.assertEqual(final_value, 900)
    
    async def test_version_vector_comparison(self):
        """测试版本向量比较"""
        # 测试版本向量比较逻辑
        v1 = {"node_A": 3, "node_B": 2}
        v2 = {"node_A": 3, "node_B": 1}
        self.assertEqual(self.sync_a._compare_versions(v1, v2), 1)  # v1 > v2
        
        v3 = {"node_A": 3, "node_B": 2}
        v4 = {"node_A": 4, "node_B": 1}
        self.assertEqual(self.sync_a._compare_versions(v3, v4), 0)  # 不可比较
        
        v5 = {"node_A": 3, "node_B": 2}
        v6 = {"node_A": 4, "node_B": 3}
        self.assertEqual(self.sync_a._compare_versions(v5, v6), -1)  # v5 < v6
    
    async def test_coordinator_election(self):
        """测试协调器选举"""
        # 检查初始协调器（应该是字典序最小的节点）
        self.assertTrue(self.sync_a.is_coordinator())
        self.assertFalse(self.sync_b.is_coordinator())
        self.assertFalse(self.sync_c.is_coordinator())
        
        # 更新活跃节点状态
        self.sync_a.active_nodes["node_B"] = time.time()
        self.sync_a.active_nodes["node_C"] = time.time()
        self.sync_b.active_nodes["node_A"] = time.time()
        self.sync_b.active_nodes["node_C"] = time.time()
        self.sync_c.active_nodes["node_A"] = time.time()
        self.sync_c.active_nodes["node_B"] = time.time()
        
        # 更新协调器状态
        self.sync_a.update_coordinator_status()
        self.sync_b.update_coordinator_status()
        self.sync_c.update_coordinator_status()
        
        # 检查协调器状态
        self.assertTrue(self.sync_a.is_coordinator())
        self.assertFalse(self.sync_b.is_coordinator())
        self.assertFalse(self.sync_c.is_coordinator())
        
        # 模拟节点A下线（从B和C的视角）
        self.sync_b.active_nodes.pop("node_A", None)
        self.sync_c.active_nodes.pop("node_A", None)
        
        # 更新协调器状态
        self.sync_b.update_coordinator_status()
        self.sync_c.update_coordinator_status()
        
        # 检查新的协调器状态（应该是节点B）
        self.assertTrue(self.sync_a.is_coordinator())  # A仍然认为自己是协调器
        self.assertTrue(self.sync_b.is_coordinator())  # B现在应该是协调器
        self.assertFalse(self.sync_c.is_coordinator())
    
    async def test_auto_tuner_integration(self):
        """测试与AutoTuner的集成"""
        # 创建带配置同步的AutoTuner
        tuner_a = AutoTuner(mesh_adapter=self.node_a, config_sync_manager=self.sync_a)
        tuner_b = AutoTuner(mesh_adapter=self.node_b, config_sync_manager=self.sync_b)
        
        # 启动自动调整器
        await tuner_a.start()
        await tuner_b.start()
        
        try:
            # 模拟性能指标
            self.node_a.get_performance_metrics = MagicMock(return_value={
                "message_send": {"count": 100, "p95": 800, "p50": 400},
                "retry": {"total_retries": 20}
            })
            
            # 调整批处理大小
            adjustments = await tuner_a.adjust_now()
            self.assertGreater(len(adjustments), 0)
            
            # 等待同步
            await asyncio.sleep(0.5)
            
            # 检查调整是否同步到所有节点
            self.assertEqual(
                self.sync_a.applied_updates.get("mesh.batch_size_limit").value if "mesh.batch_size_limit" in self.sync_a.applied_updates else None,
                self.sync_b.applied_updates.get("mesh.batch_size_limit").value if "mesh.batch_size_limit" in self.sync_b.applied_updates else None
            )
        
        finally:
            # 停止自动调整器
            await tuner_a.stop()
            await tuner_b.stop()
    
    async def test_large_scale_sync(self):
        """测试大规模同步（多个配置项）"""
        # 生成多个配置更新
        parameters = [
            ("batch_size_limit", 15),
            ("batch_time_limit_ms", 150),
            ("enable_compression", True),
            ("max_retries", 5),
            ("retry_interval_ms", 800),
            ("token_rate", 5.0),
            ("token_capacity", 15.0),
            ("enable_backpressure", True)
        ]
        
        # 随机从不同节点发送更新
        sync_managers = [self.sync_a, self.sync_b, self.sync_c]
        
        tasks = []
        for param, value in parameters:
            # 随机选择一个节点
            sync = random.choice(sync_managers)
            tasks.append(asyncio.create_task(sync.publish_update("mesh", param, value)))
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
        # 等待同步
        await asyncio.sleep(1.0)
        
        # 检查所有节点是否同步到相同的配置
        for param, value in parameters:
            key = f"mesh.{param}"
            
            # 检查所有节点是否都有这个配置项
            self.assertIn(key, self.sync_a.applied_updates)
            self.assertIn(key, self.sync_b.applied_updates)
            self.assertIn(key, self.sync_c.applied_updates)
            
            # 检查值是否一致
            self.assertEqual(
                self.sync_a.applied_updates[key].value,
                self.sync_b.applied_updates[key].value
            )
            self.assertEqual(
                self.sync_b.applied_updates[key].value,
                self.sync_c.applied_updates[key].value
            )
    
    async def test_network_partition_recovery(self):
        """测试网络分区恢复"""
        # 先同步一个配置
        await self.sync_a.publish_update("mesh", "batch_size_limit", 15)
        await asyncio.sleep(0.2)
        
        # 断开节点C与其他节点的连接（创建网络分区）
        self.node_a.disconnect_from_node(self.node_c)
        self.node_b.disconnect_from_node(self.node_c)
        
        # 在分区的两侧发布不同的更新
        await self.sync_a.publish_update("mesh", "batch_size_limit", 20)  # 分区A-B
        await self.sync_c.publish_update("mesh", "batch_size_limit", 25)  # 分区C
        
        # 在分区上发布其他更新
        await self.sync_b.publish_update("mesh", "batch_time_limit_ms", 200)  # 分区A-B
        await self.sync_c.publish_update("mesh", "enable_compression", True)  # 分区C
        
        # 等待本地更新应用
        await asyncio.sleep(0.2)
        
        # 检查分区前的值
        value_ab = self.sync_a.applied_updates["mesh.batch_size_limit"].value
        value_c = self.sync_c.applied_updates["mesh.batch_size_limit"].value
        self.assertNotEqual(value_ab, value_c)
        
        # 恢复连接
        self.node_a.connect_to_node(self.node_c)
        self.node_b.connect_to_node(self.node_c)
        
        # 等待同步
        await asyncio.sleep(0.5)
        
        # 检查所有节点是否同步到相同的配置
        final_value_a = self.sync_a.applied_updates["mesh.batch_size_limit"].value
        final_value_b = self.sync_b.applied_updates["mesh.batch_size_limit"].value
        final_value_c = self.sync_c.applied_updates["mesh.batch_size_limit"].value
        
        self.assertEqual(final_value_a, final_value_b)
        self.assertEqual(final_value_b, final_value_c)
        
        # 检查其他配置项也被同步
        self.assertEqual(
            self.sync_a.applied_updates["mesh.batch_time_limit_ms"].value,
            self.sync_c.applied_updates["mesh.batch_time_limit_ms"].value
        )
        self.assertEqual(
            self.sync_a.applied_updates["mesh.enable_compression"].value,
            self.sync_c.applied_updates["mesh.enable_compression"].value
        )

# 运行测试
def run_tests():
    """运行测试"""
    runner = unittest.TextTestRunner()
    
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 加载所有测试方法
    test_case = TestConfigSync()
    for method_name in dir(TestConfigSync):
        if method_name.startswith('test_'):
            suite.addTest(TestConfigSync(method_name))
    
    # 运行测试
    runner.run(suite)

# 异步测试运行器
def async_test(coro):
    """异步测试装饰器"""
    def wrapper(*args, **kwargs):
        """包装器"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper

# 修改TestCase的方法为异步
unittest.TestCase.setUp = async_test(TestConfigSync.asyncSetUp)
unittest.TestCase.tearDown = async_test(TestConfigSync.asyncTearDown)

# 替换原始测试方法为异步版本
for method_name in dir(TestConfigSync):
    if method_name.startswith('test_'):
        setattr(TestConfigSync, method_name, async_test(getattr(TestConfigSync, method_name)))

if __name__ == '__main__':
    run_tests() 