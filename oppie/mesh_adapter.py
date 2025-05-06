#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import time
import uuid
import random
import logging
import queue
from typing import Dict, Any, Optional, List, Set, Union, Tuple, Deque
from collections import deque
from oppie.types import Msg, CounterUpdateMsg
from oppie.config import get_config

class TokenBucket:
    """令牌桶流量控制器"""
    
    def __init__(self, rate: float = 10.0, capacity: float = 20.0):
        """
        初始化令牌桶
        
        Args:
            rate: 令牌填充速率（每秒令牌数）
            capacity: 桶容量（最大令牌数）
        """
        self.rate = rate  # 填充速率（每秒令牌数）
        self.capacity = capacity  # 桶容量（最大令牌数）
        self.tokens = capacity  # 当前令牌数
        self.last_refill = time.time()  # 上次填充时间
        self.lock = asyncio.Lock()  # 锁，用于并发控制
    
    async def acquire(self, count: float = 1.0) -> float:
        """
        获取令牌
        
        Args:
            count: 需要的令牌数
            
        Returns:
            等待时间（秒）
        """
        async with self.lock:
            self._refill()
            
            # 如果当前令牌足够
            if self.tokens >= count:
                self.tokens -= count
                return 0.0
            
            # 计算需要等待的时间
            required_tokens = count - self.tokens
            wait_time = required_tokens / self.rate
            
            # 将令牌数减为0
            self.tokens = 0
            
            return wait_time
    
    def _refill(self) -> None:
        """填充令牌"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # 计算应该添加的令牌数
        new_tokens = elapsed * self.rate
        
        # 添加令牌，不超过容量
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        
        # 更新上次填充时间
        self.last_refill = now
    
    def update_rate(self, new_rate: float) -> None:
        """
        更新填充速率
        
        Args:
            new_rate: 新的填充速率（每秒令牌数）
        """
        self.rate = max(0.1, new_rate)  # 确保速率不会太小
    
    def update_capacity(self, new_capacity: float) -> None:
        """
        更新桶容量
        
        Args:
            new_capacity: 新的桶容量（最大令牌数）
        """
        self.capacity = max(1.0, new_capacity)  # 确保容量不会太小
        self.tokens = min(self.tokens, self.capacity)  # 确保当前令牌数不超过新容量

class MeshAdapter:
    """网格适配器，负责节点间通信和状态同步"""
    
    def __init__(self, node_id: Optional[str] = None, event_bus = None, config = None):
        """
        初始化网格适配器
        
        Args:
            node_id: 节点ID，如果为None则自动生成
            event_bus: 事件总线，如果为None则创建新的
            config: 配置字典，如果为None则使用默认配置
        """
        self.node_id = node_id or str(uuid.uuid4())
        self.event_bus = event_bus or asyncio.Queue()
        self.connected = True
        self.core = None  # 将由调用者设置（CursorCore实例）
        self.state = {
            "cursor_position": 0,
            "last_msg_id": None,
            "timestamp": int(time.time() * 1000)
        }
        self.peers = set()  # 对等节点集合
        self.last_heartbeat_received = {}  # 节点ID -> 上次接收心跳的时间戳
        self._task = None  # 后台任务
        self._stopping = False  # 停止标志
        self.tool_proxy = None  # 将由调用者设置（ToolProxy实例）
        
        # 从配置中获取设置
        self.config = config or get_config("mesh")
        
        # 性能监控属性
        self.metrics = {
            "message_send_times": [],  # 消息发送时间列表
            "message_process_times": [],  # 消息处理时间列表
            "heartbeat_intervals": [],  # 心跳间隔列表
            "retry_counts": [],         # 重试次数列表
            "retry_intervals": [],      # 重试间隔列表
            "backpressure_waits": [],   # 背压等待时间列表
            "queue_lengths": []         # 队列长度列表
        }
        
        # 批处理属性
        self._counter_update_batch = []  # 计数器更新消息批处理缓冲区
        self._batch_task = None  # 批处理任务
        self._batch_size_limit = self.config.get("batch_size_limit", 10)  # 批大小限制
        self._batch_time_limit_ms = self.config.get("batch_time_limit_ms", 100)  # 批处理时间限制（毫秒）
        self._last_batch_time = 0  # 上次批处理时间
        
        # 自适应心跳属性
        self.heartbeat_interval = self.config.get("initial_heartbeat_interval", 1.0)  # 初始心跳间隔（秒）
        self.min_heartbeat_interval = self.config.get("min_heartbeat_interval", 0.2)  # 最小心跳间隔（秒）
        self.max_heartbeat_interval = self.config.get("max_heartbeat_interval", 5.0)  # 最大心跳间隔（秒）
        self.heartbeat_success_count = 0  # 成功心跳计数
        self.heartbeat_failure_count = 0  # 失败心跳计数
        self.heartbeat_success_threshold = self.config.get("heartbeat_success_threshold", 3)  # 成功心跳阈值
        self.heartbeat_failure_threshold = self.config.get("heartbeat_failure_threshold", 1)  # 失败心跳阈值
        
        # 创建指标收集任务
        self._metrics_task = None
        
        # 网络优化属性
        self.enable_compression = self.config.get("enable_compression", False)  # 是否启用压缩
        self.compression_threshold = self.config.get("compression_threshold", 1024)  # 压缩阈值（字节）
        self.enable_retries = self.config.get("enable_retries", False)  # 是否启用重试
        self.max_retries = self.config.get("max_retries", 3)  # 最大重试次数
        
        # 重试属性
        self._in_flight_messages = {}  # 消息ID -> (消息, 重试计数, 重试任务)
        self._message_responses = {}   # 消息ID -> 是否收到响应
        self._retry_base_interval_ms = self.config.get("retry_interval_ms", 500)  # 基本重试间隔（毫秒）
        self._retry_max_interval_ms = 30000  # 最大重试间隔（毫秒）
        self._message_timeout_ms = 10000  # 消息超时时间（毫秒）
        
        # 背压控制属性
        self.enable_backpressure = self.config.get("enable_backpressure", False)  # 是否启用背压控制
        self._token_bucket = TokenBucket(
            rate=self.config.get("token_rate", 10.0),  # 每秒填充10个令牌
            capacity=self.config.get("token_capacity", 20.0)  # 最大20个令牌
        )
        self._message_queue = deque()  # 消息队列
        self._max_queue_length = self.config.get("max_queue_length", 100)  # 最大队列长度
        self._queue_processor_task = None  # 队列处理任务
        self._message_priorities = {  # 消息优先级（越高越重要）
            "heartbeat": 10,
            "state_sync": 8,
            "counter_update": 5,
            "message": 3
        }
        
        # 创建一个日志记录器
        self.logger = logging.getLogger(f"MeshAdapter({self.node_id})")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def start(self) -> None:
        """启动网格适配器"""
        if self._task is not None:
            return  # 已经启动
        
        self._stopping = False
        self._task = asyncio.create_task(self._event_loop())
        
        # 根据配置决定是否启用批处理
        if self.config.get("enable_batch_processing", True):
            self._batch_task = asyncio.create_task(self._batch_processor())
        
        # 根据配置决定是否启用性能监控
        if self.config.get("enable_performance_monitoring", True):
            self._metrics_task = asyncio.create_task(self._collect_metrics())
        
        # 根据配置决定是否启用背压队列处理
        if self.enable_backpressure:
            self._queue_processor_task = asyncio.create_task(self._process_message_queue())
    
    async def _collect_metrics(self) -> None:
        """周期性收集和清理指标数据"""
        while not self._stopping:
            try:
                # 限制指标列表大小以避免内存泄漏
                max_metrics = self.config.get("max_metrics_per_category", 1000)
                if len(self.metrics["message_send_times"]) > max_metrics:
                    self.metrics["message_send_times"] = self.metrics["message_send_times"][-max_metrics:]
                if len(self.metrics["message_process_times"]) > max_metrics:
                    self.metrics["message_process_times"] = self.metrics["message_process_times"][-max_metrics:]
                if len(self.metrics["heartbeat_intervals"]) > max_metrics:
                    self.metrics["heartbeat_intervals"] = self.metrics["heartbeat_intervals"][-max_metrics:]
                
                # 使用配置中的收集间隔
                await asyncio.sleep(self.config.get("metrics_collection_interval", 10.0))
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"指标收集错误: {e}")
                await asyncio.sleep(1.0)
    
    async def _batch_processor(self) -> None:
        """批处理计数器更新消息"""
        while not self._stopping:
            try:
                current_time = time.time() * 1000
                time_since_last_batch = current_time - self._last_batch_time
                
                # 如果批达到大小限制或时间限制，则发送
                if (len(self._counter_update_batch) >= self._batch_size_limit or 
                    (len(self._counter_update_batch) > 0 and time_since_last_batch >= self._batch_time_limit_ms)):
                    
                    if len(self._counter_update_batch) > 0:
                        # 合并相同节点的计数器更新
                        node_batches = {}
                        for update in self._counter_update_batch:
                            node_id = update.node_id
                            if node_id not in node_batches:
                                node_batches[node_id] = update
                            else:
                                # 合并增量并更新时间戳
                                existing = node_batches[node_id]
                                existing.delta += update.delta
                                existing.logical_ts = max(existing.logical_ts, update.logical_ts)
                        
                        # 发送合并后的批次
                        for update in node_batches.values():
                            # 可选压缩消息
                            data = self._compress_data(update)
                            
                            # 使用重试机制发送消息
                            await self.send_with_retry("counter_update", data, idempotent=True)
                        
                        # 清空批处理缓冲区
                        self._counter_update_batch.clear()
                        self._last_batch_time = current_time
                
                # 短暂等待
                await asyncio.sleep(0.01)  # 10毫秒
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"批处理错误: {e}")
                await asyncio.sleep(0.1)
    
    async def _event_loop(self) -> None:
        """事件循环，处理传入的消息"""
        while not self._stopping:
            try:
                # 从事件总线获取消息
                event = await self.event_bus.get()
                
                # 记录开始时间
                start_time = time.time()
                
                # 处理消息ID和响应（如果存在）
                message_id = event.get("message_id")
                if message_id:
                    # 标记已收到响应
                    source_node = event.get("source_id", "")
                    if source_node != self.node_id and source_node in self._message_responses:
                        self._message_responses[source_node] = True
                
                # 处理消息
                if event["type"] == "message" and self.connected:
                    msg = event["data"]
                    source_id = event["source_id"]
                    
                    # 如果消息不是来自自己且有核心组件，则处理消息
                    if source_id != self.node_id and self.core:
                        await self._handle_message(msg)
                
                elif event["type"] == "counter_update" and self.connected:
                    update_msg = event["data"]
                    source_id = event["source_id"]
                    
                    if source_id != self.node_id:
                        await self._handle_counter_update(update_msg)
                
                elif event["type"] == "heartbeat" and self.connected:
                    source_id = event["source_id"]
                    if source_id != self.node_id:
                        current_time = time.time()
                        last_time = self.last_heartbeat_received.get(source_id, 0)
                        
                        # 记录心跳间隔
                        if last_time > 0:
                            interval = current_time - last_time
                            self.metrics["heartbeat_intervals"].append(interval)
                        
                        self.last_heartbeat_received[source_id] = current_time
                        
                        # 更新成功计数
                        self.heartbeat_success_count += 1
                        
                        # 如果连续成功次数达到阈值，增加心跳间隔（最多到最大值）
                        if self.heartbeat_success_count >= self.heartbeat_success_threshold:
                            self.heartbeat_success_count = 0
                            self.heartbeat_failure_count = 0
                            self.heartbeat_interval = min(self.heartbeat_interval * 1.5, self.max_heartbeat_interval)
                
                elif event["type"] == "state_sync" and self.connected:
                    new_state = event["data"]
                    source_id = event["source_id"]
                    if source_id != self.node_id:
                        await self._handle_state_sync(new_state, source_id)
                
                # 记录结束时间和处理延迟
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                self.metrics["message_process_times"].append(duration_ms)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"事件循环错误: {e}")
                
                # 更新失败计数
                self.heartbeat_failure_count += 1
                
                # 如果检测到连接问题，减少心跳间隔（最少到最小值）
                if self.heartbeat_failure_count >= self.heartbeat_failure_threshold:
                    self.heartbeat_success_count = 0
                    self.heartbeat_interval = max(self.heartbeat_interval / 2, self.min_heartbeat_interval)
    
    async def _handle_message(self, msg: Msg) -> None:
        """
        处理接收到的消息
        
        Args:
            msg: 接收到的消息
        """
        if self.core:
            # 解压消息（如果已压缩）
            decompressed_msg = self._decompress_data(msg)
            
            # 异步调用核心组件的handle_message方法
            asyncio.create_task(self._call_core_handle_message(decompressed_msg))
    
    async def _handle_counter_update(self, update_msg: CounterUpdateMsg) -> None:
        """
        处理计数器更新消息
        
        Args:
            update_msg: 计数器更新消息
        """
        if self.tool_proxy:
            # 解压消息（如果已压缩）
            decompressed_update = self._decompress_data(update_msg)
            
            # 应用计数器更新
            self.tool_proxy.apply_counter_update(decompressed_update)
    
    async def _call_core_handle_message(self, msg: Msg) -> None:
        """
        调用核心组件的handle_message方法
        
        Args:
            msg: 要处理的消息
        """
        # 在实际实现中，这可能是一个异步方法
        # 为简单起见，我们假设它是同步的
        self.core.handle_message(msg)
    
    async def _handle_state_sync(self, new_state: Dict[str, Any], source_id: str) -> None:
        """
        处理状态同步
        
        Args:
            new_state: 新状态
            source_id: 源节点ID
        """
        # 解决冲突：使用时间戳较大的状态
        if new_state.get("timestamp", 0) > self.state.get("timestamp", 0):
            # 使用深拷贝而不是简单更新，避免引用问题
            import copy
            self.state = copy.deepcopy(new_state)
    
    async def broadcast(self, msg: Msg) -> None:
        """
        广播消息到所有节点
        
        Args:
            msg: 要广播的消息
        """
        if not self.connected:
            return  # 断开连接时不广播
        
        # 可选压缩消息
        msg_data = self._compress_data(msg)
        
        # 使用重试机制发送消息
        await self.send_with_retry("message", msg_data, idempotent=True)
    
    async def broadcast_counter_update(self, update_msg: CounterUpdateMsg) -> None:
        """
        广播计数器更新消息到所有节点
        
        使用批处理方法以减少网络流量
        
        Args:
            update_msg: 计数器更新消息
        """
        if not self.connected:
            return  # 断开连接时不广播
        
        # 根据配置决定是否使用批处理
        if self.config.get("enable_batch_processing", True):
            # 将更新添加到批处理缓冲区
            self._counter_update_batch.append(update_msg)
            
            # 如果是首次添加到批处理，记录时间
            if len(self._counter_update_batch) == 1:
                self._last_batch_time = time.time() * 1000
        else:
            # 不使用批处理，直接发送消息
            
            # 可选压缩消息
            data = self._compress_data(update_msg)
            
            # 使用重试机制发送消息
            await self.send_with_retry("counter_update", data, idempotent=True)
    
    async def sync_state(self) -> None:
        """同步状态到所有节点"""
        if not self.connected:
            return  # 断开连接时不同步
        
        # 更新时间戳
        self.state["timestamp"] = int(time.time() * 1000)
        
        event = {
            "type": "state_sync",
            "source_id": self.node_id,
            "data": self.state
        }
        
        # 放入事件总线
        await self.event_bus.put(event)
    
    async def start_heartbeat(self, interval: float = None) -> None:
        """
        开始发送心跳
        
        Args:
            interval: 心跳间隔（秒），如果为None则使用自适应间隔
        """
        # 确定是否使用自适应心跳
        use_adaptive = self.config.get("enable_adaptive_heartbeat", True) and interval is None
        
        # 如果提供了固定间隔或禁用了自适应心跳，则使用固定间隔
        fixed_interval = interval is not None or not use_adaptive
        
        while not self._stopping:
            current_interval = interval if fixed_interval else self.heartbeat_interval
            
            if self.connected:
                event = {
                    "type": "heartbeat",
                    "source_id": self.node_id,
                    "timestamp": time.time()
                }
                
                try:
                    # 使用高优先级发送心跳
                    priority = self._message_priorities.get("heartbeat", 10)
                    await self.send_with_retry("heartbeat", event, idempotent=True, priority=priority)
                except Exception as e:
                    self.logger.error(f"心跳发送错误: {e}")
                    # 更新失败计数和减少心跳间隔（如果启用了自适应）
                    if use_adaptive:
                        self.heartbeat_failure_count += 1
                        # 减少心跳间隔（最少到最小值）
                        if self.heartbeat_failure_count >= self.heartbeat_failure_threshold:
                            self.heartbeat_success_count = 0
                            self.heartbeat_interval = max(self.heartbeat_interval / 2, self.min_heartbeat_interval)
            
            await asyncio.sleep(current_interval)
    
    async def reconnect(self) -> bool:
        """
        重新连接到网格
        
        Returns:
            是否成功重连
        """
        if self.connected:
            return True  # 已经连接
        
        self.connected = True
        
        # 同步状态
        await self.sync_state()
        
        # 重置心跳间隔
        self.heartbeat_interval = 1.0
        self.heartbeat_success_count = 0
        self.heartbeat_failure_count = 0
        
        return True
    
    async def disconnect(self) -> bool:
        """
        断开与网格的连接
        
        Returns:
            是否成功断开
        """
        self.connected = False
        return True
    
    async def shutdown(self) -> None:
        """关闭网格适配器"""
        self._stopping = True
        
        # 取消所有任务
        tasks = []
        for task in [self._task, self._batch_task, self._metrics_task, self._queue_processor_task]:
            if task and not task.done():
                task.cancel()
                tasks.append(task)
        
        # 等待所有任务取消完成
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self._task = None
        self._batch_task = None
        self._metrics_task = None
        self._queue_processor_task = None
        
        self.logger.info(f"网格适配器 {self.node_id} 已关闭")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标
        
        Returns:
            性能指标字典
        """
        import statistics
        
        metrics = {}
        
        # 计算消息发送时间统计
        send_times = self.metrics["message_send_times"]
        if send_times:
            metrics["message_send"] = {
                "mean": statistics.mean(send_times),
                "min": min(send_times),
                "max": max(send_times),
                "p50": sorted(send_times)[int(len(send_times) * 0.5)] if send_times else 0,
                "p95": sorted(send_times)[int(len(send_times) * 0.95)] if send_times else 0,
                "count": len(send_times)
            }
        
        # 计算消息处理时间统计
        process_times = self.metrics["message_process_times"]
        if process_times:
            metrics["message_process"] = {
                "mean": statistics.mean(process_times),
                "min": min(process_times),
                "max": max(process_times),
                "p50": sorted(process_times)[int(len(process_times) * 0.5)] if process_times else 0,
                "p95": sorted(process_times)[int(len(process_times) * 0.95)] if process_times else 0,
                "count": len(process_times)
            }
        
        # 计算心跳间隔统计
        heartbeat_intervals = self.metrics["heartbeat_intervals"]
        if heartbeat_intervals:
            metrics["heartbeat"] = {
                "mean": statistics.mean(heartbeat_intervals),
                "min": min(heartbeat_intervals),
                "max": max(heartbeat_intervals),
                "current_interval": self.heartbeat_interval,
                "count": len(heartbeat_intervals)
            }
        
        # 计算重试统计
        retry_counts = self.metrics["retry_counts"]
        if retry_counts:
            metrics["retry"] = {
                "mean": statistics.mean(retry_counts),
                "min": min(retry_counts),
                "max": max(retry_counts),
                "count": len(retry_counts),
                "total_retries": sum(retry_counts)
            }
        
        # 计算重试间隔统计
        retry_intervals = self.metrics["retry_intervals"]
        if retry_intervals:
            metrics["retry_interval"] = {
                "mean": statistics.mean(retry_intervals),
                "min": min(retry_intervals),
                "max": max(retry_intervals),
                "p50": sorted(retry_intervals)[int(len(retry_intervals) * 0.5)] if retry_intervals else 0,
                "p95": sorted(retry_intervals)[int(len(retry_intervals) * 0.95)] if retry_intervals else 0,
                "count": len(retry_intervals)
            }
        
        # 计算压缩比率统计
        if hasattr(self.metrics, "compression_ratios") and self.metrics.get("compression_ratios"):
            compression_ratios = self.metrics["compression_ratios"]
            metrics["compression"] = {
                "mean_ratio": statistics.mean(compression_ratios),
                "min_ratio": min(compression_ratios),
                "max_ratio": max(compression_ratios),
                "count": len(compression_ratios)
            }
            
            # 计算节省的字节数
            if hasattr(self.metrics, "bytes_saved") and self.metrics.get("bytes_saved"):
                bytes_saved = self.metrics["bytes_saved"]
                metrics["compression"]["total_bytes_saved"] = sum(bytes_saved)
                metrics["compression"]["mean_bytes_saved"] = statistics.mean(bytes_saved)
        
        # 计算背压等待时间统计
        backpressure_waits = self.metrics.get("backpressure_waits", [])
        if backpressure_waits:
            metrics["backpressure"] = {
                "mean_wait_ms": statistics.mean(backpressure_waits),
                "min_wait_ms": min(backpressure_waits),
                "max_wait_ms": max(backpressure_waits),
                "p50_wait_ms": sorted(backpressure_waits)[int(len(backpressure_waits) * 0.5)] if backpressure_waits else 0,
                "p95_wait_ms": sorted(backpressure_waits)[int(len(backpressure_waits) * 0.95)] if backpressure_waits else 0,
                "count": len(backpressure_waits)
            }
        
        # 计算队列长度统计
        queue_lengths = self.metrics.get("queue_lengths", [])
        if queue_lengths:
            metrics["queue"] = {
                "mean_length": statistics.mean(queue_lengths),
                "min_length": min(queue_lengths),
                "max_length": max(queue_lengths),
                "current_length": len(self._message_queue) if hasattr(self, '_message_queue') else 0,
                "max_capacity": self._max_queue_length if hasattr(self, '_max_queue_length') else 0
            }
        
        # 添加当前批处理状态
        metrics["batch"] = {
            "current_size": len(self._counter_update_batch),
            "size_limit": self._batch_size_limit,
            "time_limit_ms": self._batch_time_limit_ms
        }
        
        # 添加当前重试状态
        metrics["retry_status"] = {
            "in_flight_messages": len(self._in_flight_messages),
            "max_retries": self.max_retries,
            "base_interval_ms": self._retry_base_interval_ms,
            "enable_retries": self.enable_retries
        }
        
        # 添加压缩状态
        metrics["compression_status"] = {
            "enabled": self.enable_compression,
            "threshold": self.compression_threshold
        }
        
        # 添加背压控制状态
        metrics["backpressure_status"] = {
            "enabled": self.enable_backpressure,
            "token_rate": self._token_bucket.rate if hasattr(self, '_token_bucket') else 0,
            "token_capacity": self._token_bucket.capacity if hasattr(self, '_token_bucket') else 0,
            "current_tokens": self._token_bucket.tokens if hasattr(self, '_token_bucket') else 0
        }
        
        return metrics
    
    def configure_batch_settings(self, size_limit: int = None, time_limit_ms: int = None) -> None:
        """
        配置批处理设置
        
        Args:
            size_limit: 批大小限制
            time_limit_ms: 批处理时间限制（毫秒）
        """
        if size_limit is not None:
            self._batch_size_limit = max(1, size_limit)
        
        if time_limit_ms is not None:
            self._batch_time_limit_ms = max(10, time_limit_ms)  # 至少10毫秒
    
    def _compress_data(self, data):
        """
        压缩数据
        
        Args:
            data: 要压缩的数据
            
        Returns:
            压缩后的数据或原始数据
        """
        if not self.enable_compression:
            return data
        
        try:
            import gzip
            import pickle
            import sys
            
            # 序列化数据
            serialized = pickle.dumps(data)
            original_size = sys.getsizeof(serialized)
            
            # 仅在数据大小超过阈值时压缩
            if original_size < self.compression_threshold:
                return data
            
            # 压缩序列化数据
            compressed = gzip.compress(serialized)
            compressed_size = sys.getsizeof(compressed)
            
            # 只有当压缩率足够高时才使用压缩数据
            if compressed_size >= original_size * 0.9:  # 如果压缩后仍超过原始大小的90%，则不值得压缩
                return data
            
            # 记录压缩统计
            compression_ratio = compressed_size / original_size
            if not hasattr(self.metrics, "compression_ratios"):
                self.metrics["compression_ratios"] = []
            self.metrics["compression_ratios"].append(compression_ratio)
            
            if not hasattr(self.metrics, "bytes_saved"):
                self.metrics["bytes_saved"] = []
            self.metrics["bytes_saved"].append(original_size - compressed_size)
            
            self.logger.debug(f"压缩数据: 原始大小={original_size}字节, 压缩后={compressed_size}字节, 压缩率={compression_ratio:.2f}")
            
            return {
                "compressed": True,
                "data": compressed,
                "original_size": original_size,
                "compressed_size": compressed_size
            }
        except Exception as e:
            self.logger.warning(f"压缩错误: {e}")
            return data
    
    def _decompress_data(self, data):
        """
        解压数据
        
        Args:
            data: 要解压的数据
            
        Returns:
            解压后的数据或原始数据
        """
        if not isinstance(data, dict) or not data.get("compressed"):
            return data
        
        try:
            import gzip
            import pickle
            
            # 获取压缩数据
            compressed_data = data.get("data")
            if not compressed_data:
                self.logger.warning("解压数据中缺少压缩数据")
                return data
            
            # 解压缩数据
            decompressed = gzip.decompress(compressed_data)
            
            try:
                # 反序列化数据
                return pickle.loads(decompressed)
            except Exception as e:
                self.logger.warning(f"反序列化错误: {e}")
                
                # 尝试使用更宽松的反序列化设置
                try:
                    return pickle.loads(decompressed, encoding='latin1', errors='replace')
                except Exception as e2:
                    self.logger.error(f"反序列化数据失败（第二次尝试）: {e2}")
                    return data
        except Exception as e:
            self.logger.error(f"解压错误: {e}")
            return data
    
    def generate_message_id(self) -> str:
        """
        生成唯一的消息ID
        
        Returns:
            消息ID
        """
        return f"{self.node_id}-{str(uuid.uuid4())[:8]}-{int(time.time() * 1000)}"
    
    def _calculate_retry_interval(self, retry_count: int) -> float:
        """
        计算重试间隔，使用指数退避和全抖动策略
        
        Args:
            retry_count: 当前重试次数
            
        Returns:
            重试间隔（秒）
        """
        # 基本间隔（毫秒）
        base_interval_ms = self._retry_base_interval_ms
        
        # 如果有性能指标，使用P95延迟作为基本间隔
        if "message_send" in self.get_performance_metrics():
            p95_latency = self.get_performance_metrics()["message_send"].get("p95", 0)
            if p95_latency > 0:
                # 设置基本间隔为P95延迟的2倍
                base_interval_ms = max(base_interval_ms, p95_latency * 2)
        
        # 指数退避：间隔 = 基本间隔 * 2^(重试次数)
        # 全抖动：随机值在 [0, 计算间隔] 范围内
        max_interval = min(base_interval_ms * (2 ** retry_count), self._retry_max_interval_ms)
        jittered_interval = random.uniform(0, max_interval)
        
        # 记录重试间隔
        self.metrics["retry_intervals"].append(jittered_interval)
        
        # 转换为秒
        return jittered_interval / 1000.0
    
    async def send_with_retry(self, event_type: str, data: Any, idempotent: bool = True, priority: int = None) -> bool:
        """
        发送消息并在必要时重试
        
        Args:
            event_type: 事件类型
            data: 事件数据
            idempotent: 消息是否幂等（可重复发送）
            priority: 消息优先级，如果为None则使用默认优先级
            
        Returns:
            是否成功发送
        """
        if not self.connected:
            return False  # 断开连接时不发送
        
        # 生成消息ID
        message_id = self.generate_message_id()
        
        # 创建事件
        event = {
            "type": event_type,
            "source_id": self.node_id,
            "data": data,
            "message_id": message_id,
            "idempotent": idempotent,
            "timestamp": time.time()
        }
        
        # 如果未指定优先级，使用默认优先级
        if priority is None:
            priority = self._message_priorities.get(event_type, 0)
        
        # 使用背压控制
        if self.enable_backpressure:
            # 检查队列长度
            if len(self._message_queue) >= self._max_queue_length:
                # 队列已满，根据优先级决定是否丢弃低优先级消息
                lowest_priority = priority
                lowest_index = -1
                
                for i, (p, _) in enumerate(self._message_queue):
                    if p < lowest_priority:
                        lowest_priority = p
                        lowest_index = i
                
                if lowest_index >= 0:
                    # 丢弃低优先级消息，添加新消息
                    del self._message_queue[lowest_index]
                    self._message_queue.append((priority, event))
                    
                    # 如果启用重试，记录消息用于重试
                    if self.enable_retries and idempotent:
                        self._in_flight_messages[message_id] = (event, 0, None)
                        self._message_responses[message_id] = False
                        
                        # 创建重试任务
                        retry_task = asyncio.create_task(self._retry_message(message_id))
                        self._in_flight_messages[message_id] = (event, 0, retry_task)
                    
                    return True
                else:
                    # 队列已满且所有消息优先级都更高，丢弃新消息
                    self.logger.warning(f"队列已满且消息优先级较低，丢弃消息: {event_type}")
                    return False
            else:
                # 队列未满，添加消息
                self._message_queue.append((priority, event))
                
                # 如果启用重试，记录消息用于重试
                if self.enable_retries and idempotent:
                    self._in_flight_messages[message_id] = (event, 0, None)
                    self._message_responses[message_id] = False
                    
                    # 创建重试任务
                    retry_task = asyncio.create_task(self._retry_message(message_id))
                    self._in_flight_messages[message_id] = (event, 0, retry_task)
                
                return True
        
        # 不使用背压控制，直接发送
        if not self.enable_retries:
            # 不启用重试，直接发送
            return await self._send_message_with_id(event)
        
        # 记录消息
        self._in_flight_messages[message_id] = (event, 0, None)
        self._message_responses[message_id] = False
        
        # 首次发送
        success = await self._send_message_with_id(event)
        if success:
            self._message_responses[message_id] = True
            self._cleanup_message(message_id)
            return True
        
        # 如果不是幂等消息或不启用重试，则返回
        if not idempotent or not self.enable_retries:
            self._cleanup_message(message_id)
            return False
        
        # 创建重试任务
        retry_task = asyncio.create_task(self._retry_message(message_id))
        
        # 更新重试任务
        self._in_flight_messages[message_id] = (event, 0, retry_task)
        
        return True
    
    async def _retry_message(self, message_id: str) -> None:
        """
        重试发送消息
        
        Args:
            message_id: 消息ID
        """
        max_retries = self.max_retries
        retry_count = 0
        
        while retry_count < max_retries:
            # 检查消息是否仍在发送中
            if message_id not in self._in_flight_messages:
                return
            
            # 获取消息
            event, current_count, _ = self._in_flight_messages[message_id]
            
            # 增加重试计数
            retry_count = current_count + 1
            
            # 计算重试间隔
            retry_interval = self._calculate_retry_interval(retry_count)
            
            # 等待重试间隔
            await asyncio.sleep(retry_interval)
            
            # 再次检查消息是否仍在发送中
            if message_id not in self._in_flight_messages:
                return
            
            # 如果已收到响应，则清理并返回
            if self._message_responses.get(message_id, False):
                self._cleanup_message(message_id)
                return
            
            # 尝试重新发送
            self.logger.info(f"重试发送消息 {message_id}，第 {retry_count} 次重试")
            success = await self._send_message_with_id(event)
            
            # 更新重试计数
            self._in_flight_messages[message_id] = (event, retry_count, None)
            
            # 记录重试次数
            self.metrics["retry_counts"].append(retry_count)
            
            # 如果成功，则清理并返回
            if success:
                self._message_responses[message_id] = True
                self._cleanup_message(message_id)
                return
        
        # 达到最大重试次数，记录失败
        self.logger.warning(f"消息 {message_id} 达到最大重试次数 {max_retries}，发送失败")
        self._cleanup_message(message_id)
    
    async def _send_message_with_id(self, event: Dict[str, Any]) -> bool:
        """
        发送带ID的消息
        
        Args:
            event: 事件对象
            
        Returns:
            是否成功发送
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 放入事件总线
            await self.event_bus.put(event)
            
            # 记录结束时间和延迟
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            self.metrics["message_send_times"].append(duration_ms)
            
            return True
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False
    
    async def _send_message(self, event_type: str, data: Any) -> bool:
        """
        发送消息（不带重试）
        
        Args:
            event_type: 事件类型
            data: 事件数据
            
        Returns:
            是否成功发送
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 创建事件
            event = {
                "type": event_type,
                "source_id": self.node_id,
                "data": data
            }
            
            # 放入事件总线
            await self.event_bus.put(event)
            
            # 记录结束时间和延迟
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            self.metrics["message_send_times"].append(duration_ms)
            
            return True
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False
    
    def _cleanup_message(self, message_id: str) -> None:
        """
        清理消息记录
        
        Args:
            message_id: 消息ID
        """
        # 取消重试任务
        if message_id in self._in_flight_messages:
            _, _, task = self._in_flight_messages[message_id]
            if task and not task.done():
                task.cancel()
            
            # 删除消息记录
            del self._in_flight_messages[message_id]
        
        # 删除响应记录
        if message_id in self._message_responses:
            del self._message_responses[message_id]
    
    async def _process_message_queue(self) -> None:
        """处理消息队列"""
        while not self._stopping:
            try:
                # 如果队列为空，等待一段时间
                if not self._message_queue:
                    await asyncio.sleep(0.01)  # 10毫秒
                    continue
                
                # 获取队列长度统计
                self.metrics["queue_lengths"].append(len(self._message_queue))
                
                # 从队列中获取优先级最高的消息
                highest_priority = -1
                highest_index = -1
                
                for i, (priority, event) in enumerate(self._message_queue):
                    if priority > highest_priority:
                        highest_priority = priority
                        highest_index = i
                
                if highest_index >= 0:
                    # 获取令牌
                    wait_time = await self._token_bucket.acquire(1.0)
                    
                    # 记录等待时间
                    if wait_time > 0:
                        self.metrics["backpressure_waits"].append(wait_time * 1000)  # 转换为毫秒
                        await asyncio.sleep(wait_time)
                    
                    # 移除并发送消息
                    _, event = self._message_queue[highest_index]
                    del self._message_queue[highest_index]
                    
                    # 发送消息
                    await self.event_bus.put(event)
                
                # 短暂等待
                await asyncio.sleep(0.001)  # 1毫秒
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"队列处理错误: {e}")
                await asyncio.sleep(0.1)
    
    # 添加令牌桶配置方法
    def configure_token_bucket(self, rate: float = None, capacity: float = None) -> None:
        """
        配置令牌桶参数
        
        Args:
            rate: 令牌填充速率（每秒令牌数）
            capacity: 桶容量（最大令牌数）
        """
        if not hasattr(self, '_token_bucket'):
            self._token_bucket = TokenBucket()
        
        if rate is not None:
            self._token_bucket.update_rate(rate)
        
        if capacity is not None:
            self._token_bucket.update_capacity(capacity) 