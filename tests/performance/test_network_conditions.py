#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import asyncio
import time
import csv
import os
import pytest
import statistics
from typing import Dict, List, Tuple, Optional, Any
from unittest.mock import MagicMock, patch

# 导入系统组件
from oppie.mesh_adapter import MeshAdapter
from oppie.tool_proxy import ToolProxy, GlobalCounter
from oppie.types import Msg, CounterUpdateMsg

class NetworkEmulator:
    """网络模拟器，用于模拟网络延迟和丢包"""
    
    def __init__(self):
        """初始化网络模拟器"""
        self.latency_ms = 0  # 延迟（毫秒）
        self.jitter_ms = 0   # 抖动（毫秒）
        self.packet_loss = 0.0  # 丢包率（0.0-1.0）
        self.enabled = False
    
    def configure(self, latency_ms: int = 0, jitter_ms: int = 0, packet_loss: float = 0.0) -> None:
        """
        配置网络模拟参数
        
        Args:
            latency_ms: 延迟（毫秒）
            jitter_ms: 抖动（毫秒）
            packet_loss: 丢包率（0.0-1.0）
        """
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms
        self.packet_loss = max(0.0, min(1.0, packet_loss))  # 确保在0.0-1.0范围内
        self.enabled = True
    
    def disable(self) -> None:
        """禁用网络模拟"""
        self.enabled = False
    
    async def simulate_network(self) -> bool:
        """
        模拟网络延迟和丢包
        
        Returns:
            是否传递数据包（True表示通过，False表示丢包）
        """
        if not self.enabled:
            return True
        
        import random
        
        # 模拟丢包
        if random.random() < self.packet_loss:
            return False
        
        # 模拟延迟和抖动
        if self.latency_ms > 0:
            delay_ms = self.latency_ms
            if self.jitter_ms > 0:
                # 添加随机抖动（-jitter_ms到+jitter_ms范围内）
                delay_ms += random.randint(-self.jitter_ms, self.jitter_ms)
                delay_ms = max(0, delay_ms)  # 确保延迟不为负
            
            await asyncio.sleep(delay_ms / 1000.0)  # 毫秒转换为秒
        
        return True


class MetricsCollector:
    """指标收集器，用于收集和导出性能数据"""
    
    def __init__(self, output_path: str = "/tmp/perf_results.csv"):
        """
        初始化指标收集器
        
        Args:
            output_path: 输出CSV文件路径
        """
        self.timings = []  # 时间数据
        self.counters = {}  # 计数器数据
        self.output_path = output_path
        self.test_metadata = {}  # 测试元数据
    
    def record_timing(self, operation: str, duration_ms: float) -> None:
        """
        记录操作时间
        
        Args:
            operation: 操作名称
            duration_ms: 持续时间（毫秒）
        """
        self.timings.append({
            "operation": operation,
            "duration_ms": duration_ms,
            "timestamp": time.time()
        })
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """
        增加计数器
        
        Args:
            name: 计数器名称
            value: 增加值
        """
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += value
    
    def set_counter(self, name: str, value: int) -> None:
        """
        设置计数器
        
        Args:
            name: 计数器名称
            value: 计数器值
        """
        self.counters[name] = value
    
    def add_test_metadata(self, **kwargs) -> None:
        """
        添加测试元数据
        
        Args:
            **kwargs: 键值对元数据
        """
        self.test_metadata.update(kwargs)
    
    def calculate_percentile(self, operation: str, percentile: float) -> float:
        """
        计算操作时间的百分位数
        
        Args:
            operation: 操作名称
            percentile: 百分位数（0.0-1.0）
            
        Returns:
            百分位数值
        """
        durations = [t["duration_ms"] for t in self.timings if t["operation"] == operation]
        if not durations:
            return 0.0
        
        # 计算百分位数
        idx = int(len(durations) * percentile)
        return sorted(durations)[idx]
    
    def export_to_csv(self) -> None:
        """导出数据到CSV文件"""
        # 确保目录存在
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        
        # 准备数据
        rows = []
        
        # 添加元数据
        for key, value in self.test_metadata.items():
            rows.append(["metadata", key, str(value)])
        
        # 添加计数器
        for name, value in self.counters.items():
            rows.append(["counter", name, str(value)])
        
        # 添加时间统计
        operations = set(t["operation"] for t in self.timings)
        for op in operations:
            # 计算统计信息
            durations = [t["duration_ms"] for t in self.timings if t["operation"] == op]
            if durations:
                p50 = self.calculate_percentile(op, 0.5)
                p95 = self.calculate_percentile(op, 0.95)
                p99 = self.calculate_percentile(op, 0.99)
                mean = statistics.mean(durations)
                min_val = min(durations)
                max_val = max(durations)
                count = len(durations)
                
                # 添加统计行
                rows.append(["timing_stats", op, "p50", str(p50)])
                rows.append(["timing_stats", op, "p95", str(p95)])
                rows.append(["timing_stats", op, "p99", str(p99)])
                rows.append(["timing_stats", op, "mean", str(mean)])
                rows.append(["timing_stats", op, "min", str(min_val)])
                rows.append(["timing_stats", op, "max", str(max_val)])
                rows.append(["timing_stats", op, "count", str(count)])
        
        # 导出到CSV
        with open(self.output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["type", "name", "key", "value"])
            writer.writerows(rows)
        
        print(f"性能数据已导出到 {self.output_path}")


# 创建测试工具模拟
class MockTool:
    """模拟工具，用于测试ToolProxy"""
    
    def __init__(self, name: str = "mock_tool"):
        """
        初始化模拟工具
        
        Args:
            name: 工具名称
        """
        self.name = name
        self.call_count = 0
    
    def invoke(self, *args, **kwargs) -> Dict[str, Any]:
        """
        模拟工具调用
        
        Returns:
            调用结果
        """
        self.call_count += 1
        return {"result": "mock_result", "call_count": self.call_count}


# 测试夹具 - 网络模拟参数
@pytest.fixture(
    params=[
        # [延迟(ms), 抖动(ms), 丢包率(%)]
        (0, 0, 0),      # 基线 - 无延迟/丢包
        (50, 10, 0),    # 低延迟
        (100, 20, 0),   # 中等延迟
        (200, 30, 0),   # 高延迟
        (500, 50, 0),   # 非常高的延迟
        (1000, 100, 0), # 极端延迟
        (50, 10, 5),    # 低延迟 + 低丢包
        (100, 20, 10),  # 中等延迟 + 中等丢包
        (200, 30, 20),  # 高延迟 + 高丢包
    ]
)
def network_params(request) -> Tuple[int, int, float]:
    """
    提供不同的网络参数组合
    
    Returns:
        (延迟, 抖动, 丢包率)元组
    """
    return request.param


# 集成测试基类
class MeshPerformanceTestBase:
    """网格性能测试基类"""
    
    async def setup_mesh_network(self, node_count: int = 3) -> List[MeshAdapter]:
        """
        设置测试网格网络
        
        Args:
            node_count: 节点数量
            
        Returns:
            MeshAdapter实例列表
        """
        # 创建节点
        nodes = []
        event_bus = asyncio.Queue()  # 共享事件总线
        
        for i in range(node_count):
            node_id = f"node_{i}"
            adapter = MeshAdapter(node_id=node_id, event_bus=event_bus)
            nodes.append(adapter)
        
        # 启动所有节点
        for node in nodes:
            await node.start()
        
        return nodes
    
    async def create_tool_proxies(self, nodes: List[MeshAdapter]) -> List[ToolProxy]:
        """
        为每个节点创建工具代理
        
        Args:
            nodes: 节点列表
            
        Returns:
            工具代理列表
        """
        # 创建共享计数器
        counter = GlobalCounter()
        
        # 为每个节点创建工具代理
        proxies = []
        for node in nodes:
            mock_tool = MockTool(name=f"tool_{node.node_id}")
            proxy = ToolProxy(
                tool=mock_tool,
                call_limit=25,
                global_counter=counter,
                node_id=node.node_id,
                mesh_adapter=node
            )
            
            # 设置节点的工具代理
            node.tool_proxy = proxy
            
            proxies.append(proxy)
        
        return proxies
    
    def create_metrics_collector(self, test_name: str, network_params: Tuple[int, int, float]) -> MetricsCollector:
        """
        创建指标收集器
        
        Args:
            test_name: 测试名称
            network_params: 网络参数(延迟, 抖动, 丢包率)
            
        Returns:
            指标收集器实例
        """
        collector = MetricsCollector(
            output_path=f"/tmp/perf_{test_name}_{network_params[0]}ms_{network_params[2]}pct.csv"
        )
        
        # 添加测试元数据
        collector.add_test_metadata(
            test_name=test_name,
            latency_ms=network_params[0],
            jitter_ms=network_params[1],
            packet_loss_pct=network_params[2],
            timestamp=time.time()
        )
        
        return collector


class TestMeshAdapterPerformance(unittest.TestCase, MeshPerformanceTestBase):
    """测试MeshAdapter在不同网络条件下的性能"""
    
    def setUp(self):
        """测试准备"""
        # 创建网络模拟器
        self.net_emulator = NetworkEmulator()
        
        # 替换MeshAdapter的broadcast和broadcast_counter_update方法
        self.original_broadcast = MeshAdapter.broadcast
        self.original_broadcast_counter = MeshAdapter.broadcast_counter_update
        
        # 使用模拟网络替换方法
        async def mock_broadcast(self, msg):
            # 应用网络模拟
            if await self.test_instance.net_emulator.simulate_network():
                # 记录开始时间
                start_time = time.time()
                
                # 调用原始方法
                await self.test_instance.original_broadcast(self, msg)
                
                # 记录结束时间并计算延迟
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                # 记录指标
                if hasattr(self, 'metrics_collector'):
                    self.metrics_collector.record_timing("broadcast_message", duration_ms)
        
        async def mock_broadcast_counter(self, update_msg):
            # 应用网络模拟
            if await self.test_instance.net_emulator.simulate_network():
                # 记录开始时间
                start_time = time.time()
                
                # 调用原始方法
                await self.test_instance.original_broadcast_counter(self, update_msg)
                
                # 记录结束时间并计算延迟
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                # 记录指标
                if hasattr(self, 'metrics_collector'):
                    self.metrics_collector.record_timing("broadcast_counter", duration_ms)
        
        # 应用补丁
        MeshAdapter.broadcast = mock_broadcast
        MeshAdapter.broadcast_counter_update = mock_broadcast_counter
        MeshAdapter.test_instance = self
    
    def tearDown(self):
        """测试清理"""
        # 恢复原始方法
        MeshAdapter.broadcast = self.original_broadcast
        MeshAdapter.broadcast_counter_update = self.original_broadcast_counter
        delattr(MeshAdapter, 'test_instance')
    
    @pytest.mark.parametrize("network_params", [
        (0, 0, 0),      # 基线 - 无延迟/丢包
        (50, 10, 0),    # 低延迟
        (200, 30, 0),   # 高延迟
        (500, 50, 0),   # 非常高的延迟
        (50, 10, 5),    # 低延迟 + 低丢包
        (200, 30, 20),  # 高延迟 + 高丢包
    ], indirect=False)
    def test_counter_sync_performance(self, network_params):
        """
        测试计数器同步性能
        
        Args:
            network_params: 网络参数(延迟, 抖动, 丢包率)
        """
        latency_ms, jitter_ms, packet_loss_pct = network_params
        
        # 设置网络模拟器
        self.net_emulator.configure(
            latency_ms=latency_ms,
            jitter_ms=jitter_ms,
            packet_loss=packet_loss_pct / 100.0
        )
        
        # 创建指标收集器
        metrics = self.create_metrics_collector("counter_sync", network_params)
        
        # 运行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._test_counter_sync(metrics))
        finally:
            loop.close()
        
        # 导出指标
        metrics.export_to_csv()
        
        # 验证性能指标
        p95_broadcast = metrics.calculate_percentile("broadcast_counter", 0.95)
        print(f"P95 计数器广播延迟: {p95_broadcast} ms (网络参数: {network_params})")
        
        # 对于基线测试，严格验证性能
        if latency_ms == 0:
            self.assertLess(p95_broadcast, 100, "基线性能不应超过100ms")
    
    async def _test_counter_sync(self, metrics: MetricsCollector) -> None:
        """
        测试计数器同步实现
        
        Args:
            metrics: 指标收集器
        """
        # 设置测试网格
        nodes = await self.setup_mesh_network(node_count=3)
        
        # 为每个节点添加指标收集器
        for node in nodes:
            node.metrics_collector = metrics
        
        # 创建工具代理
        proxies = await self.create_tool_proxies(nodes)
        
        # 记录开始指标
        metrics.set_counter("node_count", len(nodes))
        metrics.set_counter("broadcast_count", 0)
        
        # 执行100次计数器增加并广播
        for i in range(100):
            try:
                # 从主节点调用并广播计数器更新
                start_time = time.time()
                proxies[0].invoke()
                end_time = time.time()
                
                # 记录调用延迟
                invoke_duration_ms = (end_time - start_time) * 1000
                metrics.record_timing("invoke", invoke_duration_ms)
                
                # 增加广播计数
                metrics.increment_counter("broadcast_count")
                
                # 短暂等待消息传播
                await asyncio.sleep(0.01)
            except Exception as e:
                # 记录错误
                metrics.increment_counter("error_count")
                print(f"调用错误: {e}")
        
        # 等待所有消息处理完成
        await asyncio.sleep(1.0)
        
        # 记录最终计数器状态
        for i, proxy in enumerate(proxies):
            count = proxy.call_count
            metrics.set_counter(f"node_{i}_count", count)
        
        # 关闭所有节点
        for node in nodes:
            await node.shutdown()


# 主测试执行
if __name__ == "__main__":
    # 使用pytest执行参数化测试
    pytest.main(["-xvs", __file__]) 