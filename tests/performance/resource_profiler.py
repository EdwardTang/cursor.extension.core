#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
资源使用分析工具
用于测量不同配置下的CPU和内存使用情况
"""

import os
import sys
import time
import asyncio
import psutil
import tracemalloc
import gc
import csv
from typing import Dict, Any, List, Callable, Tuple, Optional
from functools import wraps
from contextlib import contextmanager

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class ResourceUsage:
    """资源使用信息"""
    
    def __init__(self, 
                 cpu_percent: float = 0.0, 
                 memory_mb: float = 0.0,
                 peak_memory_mb: float = 0.0,
                 duration_ms: float = 0.0,
                 details: Dict[str, Any] = None):
        """
        初始化资源使用信息
        
        Args:
            cpu_percent: CPU使用率
            memory_mb: 内存使用（MB）
            peak_memory_mb: 峰值内存使用（MB）
            duration_ms: 执行时间（毫秒）
            details: 详细信息
        """
        self.cpu_percent = cpu_percent
        self.memory_mb = memory_mb
        self.peak_memory_mb = peak_memory_mb
        self.duration_ms = duration_ms
        self.details = details or {}
    
    def __str__(self) -> str:
        """字符串表示"""
        return (f"CPU: {self.cpu_percent:.1f}%, "
                f"内存: {self.memory_mb:.2f} MB, "
                f"峰值内存: {self.peak_memory_mb:.2f} MB, "
                f"耗时: {self.duration_ms:.2f} ms")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "duration_ms": self.duration_ms
        }
        
        # 添加详细信息
        for key, value in self.details.items():
            result[key] = value
        
        return result

class ResourceProfiler:
    """资源分析器"""
    
    def __init__(self, process=None, enable_tracemalloc=True):
        """
        初始化资源分析器
        
        Args:
            process: 进程对象，默认为当前进程
            enable_tracemalloc: 是否启用tracemalloc内存跟踪
        """
        self.process = process or psutil.Process()
        self.enable_tracemalloc = enable_tracemalloc
        self._snapshots = []
        self._profiling_active = False
        
        # 指标历史
        self.history = []
    
    def start(self):
        """开始分析"""
        if self._profiling_active:
            return
        
        self._profiling_active = True
        
        # 启用内存跟踪
        if self.enable_tracemalloc and not tracemalloc.is_tracing():
            tracemalloc.start()
        
        # 收集垃圾，减少干扰
        gc.collect()
        
        # 初始数据
        self.start_time = time.time()
        self._snapshots = []
        
        # 获取初始快照
        self._take_snapshot()
    
    def stop(self) -> ResourceUsage:
        """
        停止分析
        
        Returns:
            资源使用信息
        """
        if not self._profiling_active:
            return ResourceUsage()
        
        # 获取最终快照
        self._take_snapshot()
        
        # 计算结果
        self._profiling_active = False
        duration_ms = (time.time() - self.start_time) * 1000
        
        cpu_percent = 0.0
        memory_mb = 0.0
        peak_memory_mb = 0.0
        
        if self._snapshots:
            # 计算平均CPU使用率
            cpu_values = [s["cpu_percent"] for s in self._snapshots]
            cpu_percent = sum(cpu_values) / len(cpu_values) if cpu_values else 0.0
            
            # 计算平均和峰值内存使用
            memory_values = [s["memory_mb"] for s in self._snapshots]
            peak_memory_mb = max(memory_values) if memory_values else 0.0
            memory_mb = sum(memory_values) / len(memory_values) if memory_values else 0.0
            
            # 计算内存增长
            if len(memory_values) >= 2:
                memory_growth_mb = memory_values[-1] - memory_values[0]
            else:
                memory_growth_mb = 0.0
        
        # 创建资源使用信息
        result = ResourceUsage(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            peak_memory_mb=peak_memory_mb,
            duration_ms=duration_ms,
            details={
                "snapshot_count": len(self._snapshots),
                "memory_growth_mb": memory_growth_mb if 'memory_growth_mb' in locals() else 0.0,
                "start_memory_mb": self._snapshots[0]["memory_mb"] if self._snapshots else 0.0,
                "end_memory_mb": self._snapshots[-1]["memory_mb"] if self._snapshots else 0.0
            }
        )
        
        # 添加到历史
        self.history.append(result)
        
        # 停止内存跟踪
        if self.enable_tracemalloc and tracemalloc.is_tracing():
            tracemalloc.stop()
        
        return result
    
    def _take_snapshot(self):
        """获取当前资源快照"""
        # 获取CPU使用率
        cpu_percent = self.process.cpu_percent(interval=0.1)
        
        # 获取内存使用
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # RSS（物理内存）
        
        # 获取tracemalloc快照
        if self.enable_tracemalloc and tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            tracemalloc_mb = sum(stat.size for stat in top_stats) / (1024 * 1024)
        else:
            tracemalloc_mb = 0.0
        
        # 创建快照
        self._snapshots.append({
            "timestamp": time.time(),
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "tracemalloc_mb": tracemalloc_mb
        })
    
    def get_last_result(self) -> Optional[ResourceUsage]:
        """
        获取最近一次分析结果
        
        Returns:
            资源使用信息（如果有）
        """
        if self.history:
            return self.history[-1]
        return None
    
    def get_average_result(self) -> ResourceUsage:
        """
        获取平均分析结果
        
        Returns:
            平均资源使用信息
        """
        if not self.history:
            return ResourceUsage()
        
        # 计算平均值
        avg_cpu = sum(r.cpu_percent for r in self.history) / len(self.history)
        avg_memory = sum(r.memory_mb for r in self.history) / len(self.history)
        avg_peak = sum(r.peak_memory_mb for r in self.history) / len(self.history)
        avg_duration = sum(r.duration_ms for r in self.history) / len(self.history)
        
        return ResourceUsage(
            cpu_percent=avg_cpu,
            memory_mb=avg_memory,
            peak_memory_mb=avg_peak,
            duration_ms=avg_duration
        )
    
    def export_to_csv(self, filename: str):
        """
        导出历史数据到CSV文件
        
        Args:
            filename: 文件名
        """
        if not self.history:
            return
        
        # 获取所有唯一键
        keys = set()
        for item in self.history:
            keys.update(item.to_dict().keys())
        
        # 写入CSV
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=sorted(keys))
            writer.writeheader()
            
            for item in self.history:
                writer.writerow(item.to_dict())
    
    def reset_history(self):
        """重置历史数据"""
        self.history = []

def profile(func):
    """分析装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = ResourceProfiler()
        profiler.start()
        result = func(*args, **kwargs)
        usage = profiler.stop()
        print(f"函数 {func.__name__} 的资源使用: {usage}")
        return result
    return wrapper

async def async_profile(func):
    """异步分析装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = ResourceProfiler()
        profiler.start()
        result = await func(*args, **kwargs)
        usage = profiler.stop()
        print(f"异步函数 {func.__name__} 的资源使用: {usage}")
        return result
    return wrapper

@contextmanager
def profile_context(name="未命名块"):
    """分析上下文管理器"""
    profiler = ResourceProfiler()
    profiler.start()
    try:
        yield profiler
    finally:
        usage = profiler.stop()
        print(f"代码块 {name} 的资源使用: {usage}")

async def benchmark_function(func, args=None, kwargs=None, 
                             repetitions=3, warmup=1) -> ResourceUsage:
    """
    基准测试函数
    
    Args:
        func: 要基准测试的函数
        args: 位置参数
        kwargs: 关键字参数
        repetitions: 重复次数
        warmup: 预热次数
        
    Returns:
        平均资源使用信息
    """
    args = args or ()
    kwargs = kwargs or {}
    
    # 预热运行
    for _ in range(warmup):
        if asyncio.iscoroutinefunction(func):
            await func(*args, **kwargs)
        else:
            func(*args, **kwargs)
    
    # 清理内存
    gc.collect()
    
    # 创建分析器
    profiler = ResourceProfiler()
    
    # 运行基准测试
    for _ in range(repetitions):
        profiler.start()
        
        if asyncio.iscoroutinefunction(func):
            await func(*args, **kwargs)
        else:
            func(*args, **kwargs)
        
        profiler.stop()
    
    # 返回平均结果
    return profiler.get_average_result()

def compare_functions(funcs: List[Tuple[str, Callable, List, Dict]], 
                     repetitions=3, warmup=1) -> Dict[str, ResourceUsage]:
    """
    比较多个函数的性能
    
    Args:
        funcs: 函数列表，每项包含名称、函数、参数列表和关键字参数
        repetitions: 重复次数
        warmup: 预热次数
        
    Returns:
        函数名到资源使用信息的映射
    """
    results = {}
    
    for name, func, args, kwargs in funcs:
        print(f"正在基准测试函数: {name}")
        
        loop = asyncio.get_event_loop()
        
        if asyncio.iscoroutinefunction(func):
            result = loop.run_until_complete(
                benchmark_function(func, args, kwargs, repetitions, warmup)
            )
        else:
            result = loop.run_until_complete(
                benchmark_function(lambda: func(*args, **kwargs), None, None, repetitions, warmup)
            )
        
        results[name] = result
        print(f"  {result}")
    
    return results

def profile_with_different_configs(func, configs: List[Tuple[str, Dict]], 
                                  args=None, kwargs=None, repetitions=3,
                                  warmup=1) -> Dict[str, ResourceUsage]:
    """
    在不同配置下分析函数
    
    Args:
        func: 要分析的函数
        configs: 配置列表，每项包含名称和配置字典
        args: 位置参数
        kwargs: 关键字参数
        repetitions: 重复次数
        warmup: 预热次数
        
    Returns:
        配置名到资源使用信息的映射
    """
    args = args or ()
    kwargs = kwargs or {}
    kwargs = kwargs.copy()  # 创建副本，避免修改原始值
    
    results = {}
    original_config = {}
    
    for name, config in configs:
        print(f"正在测试配置: {name}")
        
        # 备份原始配置（仅首次）
        if not original_config:
            for key, value in config.items():
                section, parameter = key.split(".", 1)
                original_config[key] = get_config(section).get(parameter)
        
        # 应用配置
        for key, value in config.items():
            section, parameter = key.split(".", 1)
            update_config(section, {parameter: value})
        
        # 运行基准测试
        loop = asyncio.get_event_loop()
        
        if asyncio.iscoroutinefunction(func):
            result = loop.run_until_complete(
                benchmark_function(func, args, kwargs, repetitions, warmup)
            )
        else:
            result = loop.run_until_complete(
                benchmark_function(lambda: func(*args, **kwargs), None, None, repetitions, warmup)
            )
        
        # 添加配置信息到结果
        for key, value in config.items():
            result.details[key] = value
        
        results[name] = result
        print(f"  {result}")
    
    # 恢复原始配置
    for key, value in original_config.items():
        section, parameter = key.split(".", 1)
        update_config(section, {parameter: value})
    
    return results

# 测试代码
if __name__ == "__main__":
    from oppie.config import get_config, update_config
    
    # 定义测试函数
    def test_function():
        """测试函数"""
        # 模拟计算密集型操作
        result = 0
        for i in range(1000000):
            result += i
        return result
    
    # 定义内存密集型函数
    def memory_intensive():
        """内存密集型函数"""
        # 创建大数组
        large_list = [i for i in range(1000000)]
        return sum(large_list)
    
    # 测试分析装饰器
    @profile
    def profiled_function():
        """被分析的函数"""
        return test_function()
    
    # 异步函数示例
    async def async_function():
        """异步测试函数"""
        await asyncio.sleep(0.1)
        return test_function()
    
    # 运行测试
    print("1. 单函数基准测试:")
    profiled_function()
    
    print("\n2. 使用上下文管理器:")
    with profile_context("测试块"):
        test_function()
    
    print("\n3. 比较多个函数:")
    compare_functions([
        ("计算密集型", test_function, [], {}),
        ("内存密集型", memory_intensive, [], {})
    ])
    
    print("\n4. 用不同配置分析:")
    
    # 定义配置
    configs = [
        ("默认", {"mesh.batch_size_limit": 10, "mesh.enable_compression": False}),
        ("批处理提高", {"mesh.batch_size_limit": 20, "mesh.enable_compression": False}),
        ("启用压缩", {"mesh.batch_size_limit": 10, "mesh.enable_compression": True}),
        ("批处理+压缩", {"mesh.batch_size_limit": 20, "mesh.enable_compression": True})
    ]
    
    profile_with_different_configs(test_function, configs) 