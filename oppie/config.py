#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置文件，包含系统各部分的配置参数
"""

import time
import asyncio
import logging
import statistics
from typing import Dict, Any, Optional, List, Callable, Tuple

# 网格适配器配置
MESH_CONFIG = {
    # 批处理配置
    "enable_batch_processing": True,  # 是否启用批处理
    "batch_size_limit": 10,           # 批处理大小限制
    "batch_time_limit_ms": 100,       # 批处理时间限制（毫秒）
    
    # 心跳配置
    "enable_adaptive_heartbeat": True,  # 是否启用自适应心跳
    "initial_heartbeat_interval": 1.0,  # 初始心跳间隔（秒）
    "min_heartbeat_interval": 0.2,      # 最小心跳间隔（秒）
    "max_heartbeat_interval": 5.0,      # 最大心跳间隔（秒）
    "heartbeat_success_threshold": 3,   # 成功心跳阈值（连续成功次数）
    "heartbeat_failure_threshold": 1,   # 失败心跳阈值（连续失败次数）
    
    # 性能监控配置
    "enable_performance_monitoring": True,  # 是否启用性能监控
    "metrics_collection_interval": 10.0,    # 指标收集间隔（秒）
    "max_metrics_per_category": 1000,       # 每个类别的最大指标数
    
    # 网络优化配置
    "enable_compression": False,    # 是否启用压缩
    "compression_threshold": 1024,  # 压缩阈值（字节）
    "enable_retries": False,        # 是否启用重试
    "max_retries": 3,               # 最大重试次数
    "retry_interval_ms": 500,       # 重试间隔（毫秒）
    
    # 背压控制配置
    "enable_backpressure": False,   # 是否启用背压控制
    "token_rate": 10.0,             # 令牌填充速率（每秒令牌数）
    "token_capacity": 20.0,         # 令牌桶容量（最大令牌数）
    "max_queue_length": 100,        # 最大队列长度
    
    # 自动调整配置
    "enable_auto_tuning": False,    # 是否启用自动调整
    "auto_tuning_interval": 30.0,   # 自动调整间隔（秒）
    "target_p95_latency": 500.0,    # 目标P95延迟（毫秒）
    "target_success_rate": 0.95,    # 目标成功率
}

# 恢复机制配置
RECOVERY_CONFIG = {
    "min_recovery_interval": 5.0,   # 最小恢复间隔（秒）
    "max_consecutive_recoveries": 3,  # 最大连续恢复次数
    "recovery_cool_down": 60.0,     # 恢复冷却时间（秒）
    "retry_failed_recovery": True   # 是否重试失败的恢复
}

# 工具代理配置
TOOL_PROXY_CONFIG = {
    "default_call_limit": 25,     # 默认调用限制
    "shared_counter": True,       # 是否使用共享计数器
    "propagate_count_updates": True  # 是否传播计数器更新
}

# 自动调整配置
AUTO_TUNER_CONFIG = {
    "enable": False,                 # 是否启用自动调整
    "interval_seconds": 30.0,        # 自动调整间隔（秒）
    "target_p95_latency_ms": 500.0,  # 目标P95延迟（毫秒）
    "target_success_rate": 0.95,     # 目标成功率
    "min_samples": 10,               # 最小样本数
    "max_adjustment_pct": 0.2,       # 最大调整百分比（20%）
    "hysteresis_factor": 0.1,        # 滞后因子（10%）
    "network_condition_buckets": [   # 网络条件桶
        {"latency_max": 50, "loss_max": 0.01},  # 良好网络
        {"latency_max": 200, "loss_max": 0.05}, # 中等网络
        {"latency_max": 500, "loss_max": 0.1},  # 差网络
        {"latency_max": 99999, "loss_max": 1.0} # 极端网络
    ]
}

# 配置同步配置
CONFIG_SYNC_CONFIG = {
    "enable": False,                # 是否启用配置同步
    "coordinator_election": True,   # 是否启用协调器选举
    "sync_interval_seconds": 5.0,   # 同步间隔（秒）
    "propagation_delay_ms": 500,    # 传播延迟（毫秒）
    "retry_failed_updates": True    # 是否重试失败的更新
}

# 默认配置
DEFAULT_CONFIG = {
    "mesh": MESH_CONFIG,
    "recovery": RECOVERY_CONFIG,
    "tool_proxy": TOOL_PROXY_CONFIG,
    "auto_tuner": AUTO_TUNER_CONFIG,
    "config_sync": CONFIG_SYNC_CONFIG
}

def get_config(section=None):
    """
    获取配置
    
    Args:
        section: 配置部分，如果为None则返回整个配置
        
    Returns:
        配置字典
    """
    if section:
        return DEFAULT_CONFIG.get(section, {})
    return DEFAULT_CONFIG

def update_config(section, updates):
    """
    更新配置
    
    Args:
        section: 配置部分
        updates: 更新字典
        
    Returns:
        更新后的配置部分
    """
    if section in DEFAULT_CONFIG:
        DEFAULT_CONFIG[section].update(updates)
    return get_config(section)

class NetworkCondition:
    """网络条件描述"""
    
    def __init__(self, latency_ms: float = 0.0, jitter_ms: float = 0.0, packet_loss: float = 0.0):
        """
        初始化网络条件
        
        Args:
            latency_ms: 延迟（毫秒）
            jitter_ms: 抖动（毫秒）
            packet_loss: 丢包率（0.0-1.0）
        """
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms
        self.packet_loss = packet_loss
    
    def get_condition_bucket(self) -> int:
        """
        获取网络条件桶索引
        
        Returns:
            桶索引
        """
        # 使用配置中的桶定义
        buckets = get_config("auto_tuner").get("network_condition_buckets", [])
        
        for i, bucket in enumerate(buckets):
            if (self.latency_ms <= bucket.get("latency_max", float('inf')) and 
                self.packet_loss <= bucket.get("loss_max", float('inf'))):
                return i
        
        # 默认返回最后一个桶
        return len(buckets) - 1
    
    @staticmethod
    def from_metrics(metrics: Dict[str, Any]) -> 'NetworkCondition':
        """
        从性能指标创建网络条件
        
        Args:
            metrics: 性能指标
            
        Returns:
            网络条件
        """
        # 获取P50延迟作为基本延迟
        latency_ms = 0.0
        if "message_send" in metrics:
            latency_ms = metrics["message_send"].get("p50", 0.0)
        
        # 估计抖动为P95和P50的差异
        jitter_ms = 0.0
        if "message_send" in metrics:
            p95 = metrics["message_send"].get("p95", 0.0)
            p50 = metrics["message_send"].get("p50", 0.0)
            jitter_ms = max(0.0, p95 - p50)
        
        # 估计丢包率
        packet_loss = 0.0
        if "retry" in metrics and "message_send" in metrics:
            total_messages = metrics["message_send"].get("count", 0)
            total_retries = metrics["retry"].get("total_retries", 0)
            if total_messages > 0:
                packet_loss = min(1.0, total_retries / (total_messages + total_retries))
        
        return NetworkCondition(latency_ms, jitter_ms, packet_loss)

class OptimizationGoal:
    """优化目标"""
    
    def __init__(self, 
                 target_p95_latency_ms: float = 500.0,
                 target_success_rate: float = 0.95):
        """
        初始化优化目标
        
        Args:
            target_p95_latency_ms: 目标P95延迟（毫秒）
            target_success_rate: 目标成功率
        """
        self.target_p95_latency_ms = target_p95_latency_ms
        self.target_success_rate = target_success_rate
    
    def evaluate_metrics(self, metrics: Dict[str, Any]) -> Tuple[bool, float, str]:
        """
        评估性能指标
        
        Args:
            metrics: 性能指标
            
        Returns:
            是否达到目标，误差比例，主要问题描述
        """
        # 获取当前P95延迟
        current_p95 = float('inf')
        if "message_send" in metrics:
            current_p95 = metrics["message_send"].get("p95", float('inf'))
        
        # 获取当前成功率
        current_success_rate = 0.0
        total_messages = 0
        total_successes = 0
        
        if "message_send" in metrics:
            total_messages = metrics["message_send"].get("count", 0)
        
        if "retry" in metrics:
            total_retries = metrics["retry"].get("total_retries", 0)
            if total_messages > 0:
                total_successes = total_messages - total_retries
                current_success_rate = total_successes / total_messages
        
        # 计算误差
        latency_error = 0.0
        if current_p95 > 0:
            latency_error = (current_p95 - self.target_p95_latency_ms) / self.target_p95_latency_ms
        
        success_error = 0.0
        if current_success_rate > 0:
            success_error = (self.target_success_rate - current_success_rate) / self.target_success_rate
        
        # 确定主要问题
        issue = "当前性能符合目标"
        max_error = max(latency_error, success_error)
        
        if max_error > 0:
            if latency_error > success_error:
                issue = f"延迟过高 (P95={current_p95:.1f}ms vs 目标={self.target_p95_latency_ms:.1f}ms)"
            else:
                issue = f"成功率过低 ({current_success_rate:.1%} vs 目标={self.target_success_rate:.1%})"
        
        # 检查是否达到目标
        goal_met = (current_p95 <= self.target_p95_latency_ms and 
                    current_success_rate >= self.target_success_rate)
        
        return goal_met, max_error, issue

class ConfigAdjustment:
    """配置调整"""
    
    def __init__(self, 
                 section: str,
                 parameter: str, 
                 old_value: Any,
                 new_value: Any,
                 reason: str):
        """
        初始化配置调整
        
        Args:
            section: 配置部分
            parameter: 参数名
            old_value: 旧值
            new_value: 新值
            reason: 调整原因
        """
        self.section = section
        self.parameter = parameter
        self.old_value = old_value
        self.new_value = new_value
        self.reason = reason
        self.timestamp = time.time()
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.section}.{self.parameter}: {self.old_value} -> {self.new_value} ({self.reason})"

class AutoTuner:
    """自动调整器"""
    
    def __init__(self, mesh_adapter=None, config=None, config_sync_manager=None):
        """
        初始化自动调整器
        
        Args:
            mesh_adapter: 网格适配器
            config: 配置信息
            config_sync_manager: 配置同步管理器
        """
        self.mesh_adapter = mesh_adapter
        self.config = config or get_config("auto_tuner")
        self.config_sync_manager = config_sync_manager
        self.last_adjustment_time = 0.0
        self.adjustment_history = []
        self.task = None
        self.stopping = False
        self.observe_only_mode = False  # 观察模式（非协调器节点）
        
        # 创建日志记录器
        self.logger = logging.getLogger("AutoTuner")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        # 创建优化目标
        self.goal = OptimizationGoal(
            target_p95_latency_ms=self.config.get("target_p95_latency_ms", 500.0),
            target_success_rate=self.config.get("target_success_rate", 0.95)
        )
    
    async def start(self) -> None:
        """启动自动调整器"""
        if self.task is not None or not self.config.get("enable", False):
            return
        
        self.stopping = False
        
        # 如果使用配置同步，注册事件处理器
        if self.config_sync_manager:
            self.config_sync_manager.register_event_handler(
                "config_updated", self._on_config_updated
            )
            
            # 初始状态检查
            self._update_coordinator_status()
        
        self.task = asyncio.create_task(self._adjustment_loop())
        self.logger.info("自动调整器已启动")
    
    async def stop(self) -> None:
        """停止自动调整器"""
        self.stopping = True
        
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            
            self.task = None
            self.logger.info("自动调整器已停止")
        
        # 取消注册事件处理器
        if self.config_sync_manager:
            self.config_sync_manager.unregister_event_handler(
                "config_updated", self._on_config_updated
            )
    
    def set_mesh_adapter(self, mesh_adapter) -> None:
        """
        设置网格适配器
        
        Args:
            mesh_adapter: 网格适配器
        """
        self.mesh_adapter = mesh_adapter
    
    def set_config_sync_manager(self, config_sync_manager) -> None:
        """
        设置配置同步管理器
        
        Args:
            config_sync_manager: 配置同步管理器
        """
        self.config_sync_manager = config_sync_manager
        
        # 注册事件处理器
        if config_sync_manager:
            config_sync_manager.register_event_handler(
                "config_updated", self._on_config_updated
            )
            
            # 初始状态检查
            self._update_coordinator_status()
    
    async def _on_config_updated(self, event: Dict[str, Any]) -> None:
        """
        处理配置更新事件
        
        Args:
            event: 配置更新事件
        """
        # 只处理不是本节点发出的更新
        if event.get("source_node") != self.mesh_adapter.node_id:
            section = event.get("section")
            parameter = event.get("parameter")
            new_value = event.get("old_value")
            
            self.logger.debug(f"收到配置更新: {section}.{parameter}={new_value}，来自节点{event.get('source_node')}")
            
            # 更新自动调整器状态（如果是auto_tuner部分的更新）
            if section == "auto_tuner":
                if parameter == "enable":
                    if not new_value and self.task is not None:
                        await self.stop()
                    elif new_value and self.task is None:
                        await self.start()
                
                # 更新目标
                if parameter == "target_p95_latency_ms":
                    self.goal.target_p95_latency_ms = new_value
                elif parameter == "target_success_rate":
                    self.goal.target_success_rate = new_value
            
            # 更新坐标器状态
            if self.config_sync_manager:
                self._update_coordinator_status()
    
    def _update_coordinator_status(self) -> None:
        """更新协调器状态"""
        if not self.config_sync_manager:
            return
        
        # 更新配置同步管理器状态
        self.config_sync_manager.update_coordinator_status()
        
        # 检查是否为协调器
        new_status = not self.config_sync_manager.is_coordinator_node
        
        if new_status != self.observe_only_mode:
            self.observe_only_mode = new_status
            
            if new_status:
                self.logger.info("自动调整器进入观察模式（非协调器节点）")
            else:
                self.logger.info("自动调整器进入活跃模式（协调器节点）")
    
    async def adjust_now(self) -> List[ConfigAdjustment]:
        """
        立即进行一次调整
        
        Returns:
            配置调整列表
        """
        # 检查是否在观察模式
        if self.observe_only_mode and self.config_sync_manager:
            self.logger.debug("处于观察模式，跳过调整")
            return []
        
        if self.mesh_adapter is None:
            self.logger.warning("无法调整：未设置网格适配器")
            return []
        
        # 获取当前性能指标
        metrics = self.mesh_adapter.get_performance_metrics()
        
        # 检查样本数量
        if ("message_send" not in metrics or 
            metrics["message_send"].get("count", 0) < self.config.get("min_samples", 10)):
            self.logger.info("样本数量不足，跳过调整")
            return []
        
        # 评估当前性能
        goal_met, error, issue = self.goal.evaluate_metrics(metrics)
        
        # 如果达到目标，则不调整
        if goal_met:
            self.logger.info("当前性能符合目标，无需调整")
            return []
        
        # 确定网络条件
        network_condition = NetworkCondition.from_metrics(metrics)
        bucket = network_condition.get_condition_bucket()
        
        # 生成调整策略
        adjustments = self._generate_adjustments(metrics, error, issue, bucket)
        
        # 应用调整
        applied_adjustments = []
        for adj in adjustments:
            # 使用配置同步管理器发布更新
            if self.config_sync_manager:
                success = await self.config_sync_manager.publish_update(
                    adj.section, adj.parameter, adj.new_value
                )
                
                if success:
                    self.logger.info(f"已通过配置同步发布调整: {adj}")
                    applied_adjustments.append(adj)
                else:
                    self.logger.warning(f"通过配置同步发布调整失败: {adj}")
            
            else:
                # 直接使用配置更新函数
                current_value = get_config(adj.section).get(adj.parameter, None)
                if current_value is not None:
                    adj.old_value = current_value
                    update_config(adj.section, {adj.parameter: adj.new_value})
                    
                    # 特殊处理：令牌桶参数
                    if adj.section == "mesh" and adj.parameter == "token_rate":
                        if hasattr(self.mesh_adapter, "_token_bucket"):
                            self.mesh_adapter._token_bucket.update_rate(adj.new_value)
                    
                    elif adj.section == "mesh" and adj.parameter == "token_capacity":
                        if hasattr(self.mesh_adapter, "_token_bucket"):
                            self.mesh_adapter._token_bucket.update_capacity(adj.new_value)
                    
                    # 特殊处理：压缩和重试
                    elif adj.section == "mesh" and adj.parameter == "enable_compression":
                        self.mesh_adapter.enable_compression = adj.new_value
                    
                    elif adj.section == "mesh" and adj.parameter == "enable_retries":
                        self.mesh_adapter.enable_retries = adj.new_value
                    
                    # 特殊处理：背压控制
                    elif adj.section == "mesh" and adj.parameter == "enable_backpressure":
                        self.mesh_adapter.enable_backpressure = adj.new_value
                        # 如果启用背压控制，但队列处理任务未启动，则启动
                        if adj.new_value and not hasattr(self.mesh_adapter, "_queue_processor_task"):
                            self.mesh_adapter._queue_processor_task = asyncio.create_task(
                                self.mesh_adapter._process_message_queue()
                            )
                    
                    # 特殊处理：批处理参数
                    elif adj.section == "mesh" and adj.parameter == "batch_size_limit":
                        if hasattr(self.mesh_adapter, "configure_batch_settings"):
                            self.mesh_adapter.configure_batch_settings(size_limit=adj.new_value)
                    
                    elif adj.section == "mesh" and adj.parameter == "batch_time_limit_ms":
                        if hasattr(self.mesh_adapter, "configure_batch_settings"):
                            self.mesh_adapter.configure_batch_settings(time_limit_ms=adj.new_value)
                    
                    self.logger.info(f"已应用调整: {adj}")
                    applied_adjustments.append(adj)
                else:
                    self.logger.warning(f"无法应用调整，参数不存在: {adj}")
        
        # 记录调整历史
        self.adjustment_history.extend(applied_adjustments)
        self.last_adjustment_time = time.time()
        
        return applied_adjustments
    
    def _generate_adjustments(self, 
                              metrics: Dict[str, Any], 
                              error: float, 
                              issue: str,
                              network_bucket: int) -> List[ConfigAdjustment]:
        """
        生成调整策略
        
        Args:
            metrics: 性能指标
            error: 误差比例
            issue: 主要问题描述
            network_bucket: 网络条件桶
            
        Returns:
            配置调整列表
        """
        adjustments = []
        
        # 只有当误差大于滞后因子时才调整
        hysteresis = self.config.get("hysteresis_factor", 0.1)
        if error <= hysteresis:
            return []
        
        # 计算调整因子（受最大调整百分比限制）
        max_adjustment = self.config.get("max_adjustment_pct", 0.2)
        adjustment_factor = min(error, max_adjustment)
        
        # 基于网络桶和问题选择最佳调整策略
        if "延迟过高" in issue:
            # 高延迟问题
            
            # 查看批处理配置
            if network_bucket >= 2:  # 差网络或极端网络
                # 增加批处理大小
                current_batch_size = get_config("mesh").get("batch_size_limit", 10)
                new_batch_size = max(1, int(current_batch_size * (1 + adjustment_factor)))
                
                adjustments.append(ConfigAdjustment(
                    "mesh", "batch_size_limit", current_batch_size, new_batch_size,
                    "增加批处理大小以减少消息数量"
                ))
                
                # 增加批处理时间限制
                current_time_limit = get_config("mesh").get("batch_time_limit_ms", 100)
                new_time_limit = int(current_time_limit * (1 + adjustment_factor))
                
                adjustments.append(ConfigAdjustment(
                    "mesh", "batch_time_limit_ms", current_time_limit, new_time_limit,
                    "增加批处理时间限制以提高批处理有效性"
                ))
                
                # 启用背压控制
                if not get_config("mesh").get("enable_backpressure", False):
                    adjustments.append(ConfigAdjustment(
                        "mesh", "enable_backpressure", False, True,
                        "启用背压控制以平滑流量"
                    ))
                
                # 启用压缩（对于极端网络）
                if network_bucket >= 3 and not get_config("mesh").get("enable_compression", False):
                    adjustments.append(ConfigAdjustment(
                        "mesh", "enable_compression", False, True,
                        "启用消息压缩以减少传输数据量"
                    ))
            
            # 对于所有网络条件，调整令牌桶速率
            if get_config("mesh").get("enable_backpressure", False):
                current_rate = get_config("mesh").get("token_rate", 10.0)
                new_rate = current_rate * (1 - adjustment_factor / 2)  # 降低速率
                
                adjustments.append(ConfigAdjustment(
                    "mesh", "token_rate", current_rate, new_rate,
                    "降低令牌填充速率以减轻网络负载"
                ))
        
        elif "成功率过低" in issue:
            # 低成功率问题
            
            # 启用重试
            if not get_config("mesh").get("enable_retries", False):
                adjustments.append(ConfigAdjustment(
                    "mesh", "enable_retries", False, True,
                    "启用重试以提高成功率"
                ))
            
            # 调整重试参数
            current_retries = get_config("mesh").get("max_retries", 3)
            new_retries = min(10, int(current_retries * (1 + adjustment_factor)))
            
            if new_retries > current_retries:
                adjustments.append(ConfigAdjustment(
                    "mesh", "max_retries", current_retries, new_retries,
                    "增加最大重试次数以提高成功率"
                ))
            
            # 针对高丢包环境，减少批处理大小
            if network_bucket >= 2:  # 差网络或极端网络
                current_batch_size = get_config("mesh").get("batch_size_limit", 10)
                new_batch_size = max(1, int(current_batch_size * (1 - adjustment_factor)))
                
                adjustments.append(ConfigAdjustment(
                    "mesh", "batch_size_limit", current_batch_size, new_batch_size,
                    "减少批处理大小以降低丢包影响"
                ))
            
            # 调整重试间隔
            current_interval = get_config("mesh").get("retry_interval_ms", 500)
            
            # 根据网络延迟调整重试间隔
            latency_ms = metrics.get("message_send", {}).get("p95", 100)
            new_interval = max(100, min(2000, int(latency_ms * 2)))
            
            adjustments.append(ConfigAdjustment(
                "mesh", "retry_interval_ms", current_interval, new_interval,
                "调整重试间隔以匹配网络延迟"
            ))
        
        return adjustments
    
    async def _adjustment_loop(self) -> None:
        """调整循环"""
        while not self.stopping:
            try:
                # 更新协调器状态
                if self.config_sync_manager:
                    self._update_coordinator_status()
                
                # 等待调整间隔
                await asyncio.sleep(self.config.get("interval_seconds", 30.0))
                
                # 检查是否可以调整
                if self.mesh_adapter is None:
                    continue
                
                # 检查是否在观察模式
                if self.observe_only_mode and self.config_sync_manager:
                    self.logger.debug("处于观察模式，跳过调整")
                    continue
                
                # 执行调整
                await self.adjust_now()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"调整循环错误: {e}")
                await asyncio.sleep(5.0)
    
    def get_adjustment_history(self) -> List[ConfigAdjustment]:
        """
        获取调整历史
        
        Returns:
            调整历史列表
        """
        return self.adjustment_history.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取状态信息
        
        Returns:
            状态信息
        """
        if self.config_sync_manager:
            self._update_coordinator_status()
        
        return {
            "enabled": self.config.get("enable", False),
            "is_running": self.task is not None and not self.task.done(),
            "is_coordinator": not self.observe_only_mode if self.config_sync_manager else True,
            "last_adjustment_time": self.last_adjustment_time,
            "adjustment_count": len(self.adjustment_history),
            "target_p95_latency_ms": self.goal.target_p95_latency_ms,
            "target_success_rate": self.goal.target_success_rate
        } 