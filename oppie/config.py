#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置文件，包含系统各部分的配置参数
"""

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
    "enable_compression": False,    # 是否启用压缩（未实现）
    "compression_threshold": 1024,  # 压缩阈值（字节）
    "enable_retries": False,        # 是否启用重试（未实现）
    "max_retries": 3,               # 最大重试次数
    "retry_interval_ms": 500        # 重试间隔（毫秒）
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

# 默认配置
DEFAULT_CONFIG = {
    "mesh": MESH_CONFIG,
    "recovery": RECOVERY_CONFIG,
    "tool_proxy": TOOL_PROXY_CONFIG
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