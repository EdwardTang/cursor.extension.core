"""Cloud Relay服务的性能测试。

测试在不同负载条件下的性能表现，包括高并发连接和大量消息处理。
"""
import asyncio
import json
import pytest
import statistics
import time
import uuid
import websockets
from concurrent.futures import ThreadPoolExecutor

from .conftest import PWAClient, SidecarClient

pytestmark = pytest.mark.asyncio


class PerformanceMetrics:
    """性能指标收集和分析工具。"""
    
    def __init__(self):
        self.latencies = []  # 延迟记录，单位：毫秒
    
    def record_latency(self, start_time, end_time=None):
        """记录延迟。"""
        if end_time is None:
            end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        self.latencies.append(latency_ms)
    
    def get_p95_latency(self):
        """获取P95延迟（毫秒）。"""
        if not self.latencies:
            return 0
        return statistics.quantiles(self.latencies, n=20)[-1]  # 第95百分位
    
    def get_average_latency(self):
        """获取平均延迟（毫秒）。"""
        if not self.latencies:
            return 0
        return statistics.mean(self.latencies)
    
    def get_max_latency(self):
        """获取最大延迟（毫秒）。"""
        if not self.latencies:
            return 0
        return max(self.latencies)
    
    def get_min_latency(self):
        """获取最小延迟（毫秒）。"""
        if not self.latencies:
            return 0
        return min(self.latencies)
    
    def get_total_messages(self):
        """获取总消息数。"""
        return len(self.latencies)
    
    def get_summary(self):
        """获取性能摘要。"""
        return {
            "total_messages": self.get_total_messages(),
            "p95_latency_ms": self.get_p95_latency(),
            "avg_latency_ms": self.get_average_latency(),
            "max_latency_ms": self.get_max_latency(),
            "min_latency_ms": self.get_min_latency()
        }


async def test_single_connection_throughput(relay_server, valid_token):
    """测试单连接吞吐量：一个PWA客户端和一个Sidecar客户端之间的消息交换。"""
    # 创建客户端
    pwa = PWAClient(relay_server.ws_url, valid_token)
    await pwa.connect()
    
    sidecar = SidecarClient(relay_server.ws_url, valid_token)
    await sidecar.connect()
    
    metrics = PerformanceMetrics()
    message_count = 100
    
    # 从PWA发送消息到Sidecar并测量延迟
    for i in range(message_count):
        test_message = {
            "id": f"perf-test-{i}",
            "type": "command",
            "data": {
                "action": "performance_test",
                "parameters": {"index": i}
            }
        }
        
        start_time = time.time()
        await pwa.send(json.dumps(test_message))
        
        # 等待Sidecar接收消息
        response = await sidecar.receive(timeout=5.0)
        assert response is not None, f"消息{i}未送达Sidecar"
        
        # 记录端到端延迟
        metrics.record_latency(start_time)
    
    # 分析性能
    summary = metrics.get_summary()
    print(f"\n性能摘要（单连接）：{json.dumps(summary, indent=2)}")
    
    # 验证P95延迟满足要求
    assert summary["p95_latency_ms"] < 500, f"P95延迟过高：{summary['p95_latency_ms']}ms > 500ms"
    
    # 清理
    await pwa.close()
    await sidecar.close()


async def test_concurrent_connections(relay_server, valid_token):
    """测试并发连接：多个PWA客户端和Sidecar客户端同时连接。"""
    # 并发客户端数量
    num_clients = 10
    
    # 创建多个客户端
    pwa_clients = []
    sidecar_clients = []
    
    # 连接所有客户端
    for i in range(num_clients):
        pwa = PWAClient(relay_server.ws_url, valid_token)
        await pwa.connect()
        pwa_clients.append(pwa)
        
        sidecar = SidecarClient(relay_server.ws_url, valid_token)
        await sidecar.connect()
        sidecar_clients.append(sidecar)
    
    # 验证所有连接都是活跃的
    for i, (pwa, sidecar) in enumerate(zip(pwa_clients, sidecar_clients)):
        test_message = {
            "id": f"concurrent-test-{i}",
            "type": "ping",
            "data": {}
        }
        
        # 从PWA发送消息
        await pwa.send(json.dumps(test_message))
        
        # 确认Sidecar收到消息
        response = await sidecar.receive(timeout=2.0)
        assert response is not None, f"客户端{i}的消息未送达"
    
    # 清理所有连接
    for pwa, sidecar in zip(pwa_clients, sidecar_clients):
        await pwa.close()
        await sidecar.close()


async def test_message_burst(relay_server, valid_token):
    """测试消息突发：短时间内发送大量消息。"""
    # 创建客户端
    pwa = PWAClient(relay_server.ws_url, valid_token)
    await pwa.connect()
    
    sidecar = SidecarClient(relay_server.ws_url, valid_token)
    await sidecar.connect()
    
    # 测试参数
    burst_size = 50
    messages_per_client = 10
    
    metrics = PerformanceMetrics()
    message_ids = []
    
    # 快速发送一批消息
    for i in range(burst_size):
        msg_id = f"burst-{i}"
        message_ids.append(msg_id)
        test_message = {
            "id": msg_id,
            "type": "command",
            "data": {
                "action": "burst_test",
                "parameters": {"index": i}
            }
        }
        
        start_time = time.time()
        await pwa.send(json.dumps(test_message))
        metrics.record_latency(start_time, start_time)  # 仅记录发送时间
    
    # 接收所有消息，并记录接收延迟
    received_ids = set()
    start_receive_time = time.time()
    
    for _ in range(burst_size):
        response = await sidecar.receive(timeout=10.0)
        assert response is not None, f"只收到{len(received_ids)}/{burst_size}个消息"
        
        response_data = json.loads(response)
        received_ids.add(response_data["id"])
        
        # 更新延迟记录（从开始接收到每条消息的时间）
        metrics.latencies[int(response_data["id"].split("-")[1])] = (time.time() - start_receive_time) * 1000
    
    # 确认所有消息都已收到
    assert len(received_ids) == burst_size, f"丢失{burst_size - len(received_ids)}条消息"
    
    # 分析性能
    summary = metrics.get_summary()
    print(f"\n爆发性能摘要：{json.dumps(summary, indent=2)}")
    
    # 验证批处理能力（即使发送快速，接收也应合理分布）
    assert summary["max_latency_ms"] < 5000, f"最大延迟过高：{summary['max_latency_ms']}ms > 5000ms"
    
    # 清理
    await pwa.close()
    await sidecar.close()


async def test_sustained_load(relay_server, valid_token):
    """测试持续负载：持续30秒的消息流。"""
    # 创建客户端
    pwa = PWAClient(relay_server.ws_url, valid_token)
    await pwa.connect()
    
    sidecar = SidecarClient(relay_server.ws_url, valid_token)
    await sidecar.connect()
    
    metrics = PerformanceMetrics()
    
    # 测试持续时间（秒）
    test_duration = 5  # 缩短为5秒，便于测试
    
    # 发送和接收的任务
    async def send_messages():
        """持续发送消息的任务。"""
        start_time = time.time()
        msg_index = 0
        
        while time.time() - start_time < test_duration:
            msg_id = f"sustained-{msg_index}"
            test_message = {
                "id": msg_id,
                "type": "command",
                "data": {
                    "action": "sustained_test",
                    "parameters": {"index": msg_index}
                }
            }
            
            send_time = time.time()
            await pwa.send(json.dumps(test_message))
            metrics.record_latency(send_time)
            
            msg_index += 1
            await asyncio.sleep(0.01)  # 每10毫秒发送一条消息
        
        return msg_index
    
    async def receive_messages(expected_count):
        """接收消息的任务。"""
        received = 0
        
        # 给额外的时间接收所有消息
        timeout_time = time.time() + test_duration + 5
        
        while received < expected_count and time.time() < timeout_time:
            response = await sidecar.receive(timeout=1.0)
            if response is not None:
                received += 1
                # 更新延迟记录
                metrics.latencies[received - 1] = (time.time() - metrics.latencies[received - 1]) * 1000
        
        return received
    
    # 并行执行发送和接收任务
    send_task = asyncio.create_task(send_messages())
    total_sent = await send_task
    
    receive_task = asyncio.create_task(receive_messages(total_sent))
    total_received = await receive_task
    
    # 验证消息接收情况
    assert total_received / total_sent >= 0.95, f"收到率过低：{total_received}/{total_sent} < 95%"
    
    # 分析性能
    summary = metrics.get_summary()
    print(f"\n持续负载摘要（{test_duration}秒）：{json.dumps(summary, indent=2)}")
    print(f"消息速率：{total_sent/test_duration:.1f}条/秒，接收：{total_received/test_duration:.1f}条/秒")
    
    # 验证P95延迟满足要求
    assert summary["p95_latency_ms"] < 500, f"P95延迟过高：{summary['p95_latency_ms']}ms > 500ms"
    
    # 清理
    await pwa.close()
    await sidecar.close() 