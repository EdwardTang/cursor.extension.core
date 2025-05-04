#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List, Set
from oppie.types import Msg, CounterUpdateMsg
from oppie.config import get_config

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
            "heartbeat_intervals": []  # 心跳间隔列表
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
                            
                            event = {
                                "type": "counter_update",
                                "source_id": self.node_id,
                                "data": data
                            }
                            
                            # 记录开始时间
                            start_time = time.time()
                            
                            # 放入事件总线
                            await self.event_bus.put(event)
                            
                            # 记录结束时间和延迟
                            end_time = time.time()
                            duration_ms = (end_time - start_time) * 1000
                            self.metrics["message_send_times"].append(duration_ms)
                        
                        # 清空批处理缓冲区
                        self._counter_update_batch.clear()
                        self._last_batch_time = current_time
                
                # 短暂等待
                await asyncio.sleep(0.01)  # 10毫秒
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"批处理错误: {e}")
                await asyncio.sleep(0.1)
    
    async def _event_loop(self) -> None:
        """事件循环，处理传入的消息"""
        while not self._stopping:
            try:
                # 从事件总线获取消息
                event = await self.event_bus.get()
                
                # 记录开始时间
                start_time = time.time()
                
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
                print(f"Error in event loop: {e}")
                
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
        
        # 记录开始时间
        start_time = time.time()
        
        # 可选压缩消息
        msg_data = self._compress_data(msg)
        
        event = {
            "type": "message",
            "source_id": self.node_id,
            "data": msg_data
        }
        
        # 放入事件总线
        await self.event_bus.put(event)
        
        # 记录结束时间和延迟
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        self.metrics["message_send_times"].append(duration_ms)
    
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
            
            event = {
                "type": "counter_update",
                "source_id": self.node_id,
                "data": data
            }
            
            # 记录开始时间
            start_time = time.time()
            
            # 放入事件总线
            await self.event_bus.put(event)
            
            # 记录结束时间和延迟
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            self.metrics["message_send_times"].append(duration_ms)
    
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
                    # 放入事件总线
                    await self.event_bus.put(event)
                except Exception as e:
                    print(f"心跳发送错误: {e}")
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
        for task in [self._task, self._batch_task, self._metrics_task]:
            if task and not task.done():
                task.cancel()
                tasks.append(task)
        
        # 等待所有任务取消完成
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self._task = None
        self._batch_task = None
        self._metrics_task = None
        
        print(f"网格适配器 {self.node_id} 已关闭")
    
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
        
        # 添加当前批处理状态
        metrics["batch"] = {
            "current_size": len(self._counter_update_batch),
            "size_limit": self._batch_size_limit,
            "time_limit_ms": self._batch_time_limit_ms
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
            压缩后的数据
        """
        if not self.enable_compression:
            return data
        
        try:
            import gzip
            import pickle
            
            # 序列化数据
            serialized = pickle.dumps(data)
            
            # 仅在数据大小超过阈值时压缩
            if len(serialized) < self.compression_threshold:
                return data
            
            # 压缩序列化数据
            compressed = gzip.compress(serialized)
            
            return {
                "compressed": True,
                "data": compressed
            }
        except Exception as e:
            print(f"压缩错误: {e}")
            return data
    
    def _decompress_data(self, data):
        """
        解压数据
        
        Args:
            data: 要解压的数据
            
        Returns:
            解压后的数据
        """
        if not self.enable_compression or not isinstance(data, dict) or not data.get("compressed"):
            return data
        
        try:
            import gzip
            import pickle
            
            # 解压缩数据
            decompressed = gzip.decompress(data["data"])
            
            # 反序列化数据
            return pickle.loads(decompressed)
        except Exception as e:
            print(f"解压错误: {e}")
            return data 