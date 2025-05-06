#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Oppie - 远程游标控制网格 (RCCM)
用于在不同节点之间同步状态和操作
"""

__version__ = '0.3.0'  # 添加了高级网络优化功能

# 从子模块导入主要类
from oppie.types import (
    CoreState, Step, Msg, ExecResult, 
    QuotaExceededError, TemplateMissingError
)
from oppie.cursor_core import CursorCore
from oppie.tool_proxy import ToolProxy, GlobalCounter
from oppie.mesh_adapter import MeshAdapter
from oppie.dev_loop_watcher import (
    AgentSHelpers, DevLoopWatcher, SidecarDaemon
)
from .config import (
    get_config, update_config, 
    AutoTuner, NetworkCondition, OptimizationGoal, ConfigAdjustment
)

# 导出所有模块
__all__ = [
    'CoreState', 'Step', 'Msg', 'ExecResult', 
    'QuotaExceededError', 'TemplateMissingError',
    'CursorCore', 'ToolProxy', 'GlobalCounter',
    'MeshAdapter', 'AgentSHelpers', 'DevLoopWatcher',
    'SidecarDaemon',
    'get_config',
    'update_config',
    'AutoTuner',
    'NetworkCondition',
    'OptimizationGoal',
    'ConfigAdjustment',
    'create_auto_tuner',
    'enable_network_optimizations',
    'configure_for_environment'
]

def create_auto_tuner(mesh_adapter=None, enable=True):
    """
    创建并配置自动调整器
    
    Args:
        mesh_adapter: 要监控和调整的网格适配器
        enable: 是否启用自动调整
        
    Returns:
        配置好的自动调整器
    """
    # 更新配置
    update_config("auto_tuner", {"enable": enable})
    
    # 创建自动调整器
    tuner = AutoTuner(mesh_adapter=mesh_adapter)
    
    return tuner

def enable_network_optimizations(mesh_adapter=None, 
                                 enable_retries=True, 
                                 enable_compression=True,
                                 enable_backpressure=True,
                                 enable_batch_processing=True,
                                 enable_adaptive_heartbeat=True,
                                 enable_auto_tuning=True):
    """
    启用网络优化
    
    Args:
        mesh_adapter: 要应用优化的网格适配器
        enable_retries: 是否启用重试
        enable_compression: 是否启用压缩
        enable_backpressure: 是否启用背压控制
        enable_batch_processing: 是否启用批处理
        enable_adaptive_heartbeat: 是否启用自适应心跳
        enable_auto_tuning: 是否启用自动调整
        
    Returns:
        更新后的配置
    """
    # 更新配置
    mesh_config = {
        "enable_retries": enable_retries,
        "enable_compression": enable_compression,
        "enable_backpressure": enable_backpressure,
        "enable_batch_processing": enable_batch_processing,
        "enable_adaptive_heartbeat": enable_adaptive_heartbeat
    }
    
    update_config("mesh", mesh_config)
    update_config("auto_tuner", {"enable": enable_auto_tuning})
    
    # 如果提供了网格适配器，则直接应用配置
    if mesh_adapter is not None:
        mesh_adapter.enable_retries = enable_retries
        mesh_adapter.enable_compression = enable_compression
        mesh_adapter.enable_backpressure = enable_backpressure
        
        # 应用批处理设置
        if hasattr(mesh_adapter, "configure_batch_settings"):
            mesh_adapter.configure_batch_settings(
                enabled=enable_batch_processing
            )
        
        # 应用心跳设置
        if hasattr(mesh_adapter, "configure_heartbeat_settings"):
            mesh_adapter.configure_heartbeat_settings(
                adaptive=enable_adaptive_heartbeat
            )
    
    return get_config()

def configure_for_environment(environment='normal', mesh_adapter=None):
    """
    为特定环境配置系统
    
    Args:
        environment: 环境类型 ('normal', 'high_latency', 'high_loss', 'extreme')
        mesh_adapter: 要应用配置的网格适配器
        
    Returns:
        更新后的配置
    """
    # 基本配置（所有环境都启用）
    base_config = {
        "enable_batch_processing": True,
        "enable_adaptive_heartbeat": True,
        "enable_performance_monitoring": True
    }
    
    # 环境特定配置
    if environment == 'high_latency':
        # 高延迟环境（200-500ms）
        specific_config = {
            "batch_size_limit": 15,
            "batch_time_limit_ms": 200,
            "enable_compression": True,
            "enable_retries": True,
            "max_retries": 3,
            "retry_interval_ms": 1000,
            "enable_backpressure": True,
            "token_rate": 5.0,
            "token_capacity": 20.0
        }
    
    elif environment == 'high_loss':
        # 高丢包环境（5-20%丢包率）
        specific_config = {
            "batch_size_limit": 5,  # 减小批处理大小以降低单个丢包的影响
            "batch_time_limit_ms": 50,
            "enable_compression": True,
            "enable_retries": True,
            "max_retries": 5,
            "retry_interval_ms": 300,
            "enable_backpressure": True,
            "token_rate": 8.0,
            "token_capacity": 15.0
        }
    
    elif environment == 'extreme':
        # 极端环境（高延迟+高丢包率）
        specific_config = {
            "batch_size_limit": 10,
            "batch_time_limit_ms": 300,
            "enable_compression": True,
            "enable_retries": True,
            "max_retries": 8,
            "retry_interval_ms": 1500,
            "enable_backpressure": True,
            "token_rate": 3.0,
            "token_capacity": 30.0,
            "initial_heartbeat_interval": 2.0,
            "min_heartbeat_interval": 1.0,
            "max_heartbeat_interval": 10.0
        }
    
    else:  # 'normal' 或默认
        # 正常环境（低延迟，低丢包率）
        specific_config = {
            "batch_size_limit": 10,
            "batch_time_limit_ms": 100,
            "enable_compression": False,
            "enable_retries": True,
            "max_retries": 2,
            "retry_interval_ms": 200,
            "enable_backpressure": False,
            "token_rate": 20.0,
            "token_capacity": 30.0
        }
    
    # 合并配置
    combined_config = {**base_config, **specific_config}
    
    # 更新配置
    update_config("mesh", combined_config)
    
    # 如果提供了网格适配器，则直接应用配置
    if mesh_adapter is not None:
        # 应用基本参数
        for key, value in combined_config.items():
            if hasattr(mesh_adapter, key):
                setattr(mesh_adapter, key, value)
        
        # 应用批处理设置
        if hasattr(mesh_adapter, "configure_batch_settings"):
            mesh_adapter.configure_batch_settings(
                enabled=combined_config.get("enable_batch_processing", True),
                size_limit=combined_config.get("batch_size_limit", 10),
                time_limit_ms=combined_config.get("batch_time_limit_ms", 100)
            )
        
        # 应用心跳设置
        if hasattr(mesh_adapter, "configure_heartbeat_settings"):
            mesh_adapter.configure_heartbeat_settings(
                adaptive=combined_config.get("enable_adaptive_heartbeat", True),
                initial_interval=combined_config.get("initial_heartbeat_interval", 1.0),
                min_interval=combined_config.get("min_heartbeat_interval", 0.2),
                max_interval=combined_config.get("max_heartbeat_interval", 5.0)
            )
    
    return get_config() 