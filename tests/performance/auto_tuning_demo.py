#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动调整功能演示程序
在不同网络条件下展示自动调整机制如何优化系统性能
"""

import os
import sys
import time
import math
import json
import asyncio
import random
import logging
import argparse
from typing import Dict, Any, List, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from oppie.mesh_adapter import MeshAdapter
from oppie.config import get_config, update_config, AutoTuner, NetworkCondition
from tests.performance.network_emulator import NetworkEmulator
from tests.performance.metrics_collector import MetricsCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('auto_tuning_demo')

class NetworkScenario:
    """网络场景模拟器"""
    
    def __init__(self, 
                 name: str,
                 duration_seconds: int,
                 initial_latency_ms: float,
                 final_latency_ms: float = None,
                 initial_packet_loss: float = 0.0,
                 final_packet_loss: float = None,
                 transition_type: str = 'linear'):
        """
        初始化网络场景
        
        Args:
            name: 场景名称
            duration_seconds: 场景持续时间（秒）
            initial_latency_ms: 初始延迟（毫秒）
            final_latency_ms: 最终延迟（毫秒），如果为None则使用初始值
            initial_packet_loss: 初始丢包率（0.0-1.0）
            final_packet_loss: 最终丢包率（0.0-1.0），如果为None则使用初始值
            transition_type: 过渡类型（'linear', 'step', 'exponential'）
        """
        self.name = name
        self.duration_seconds = duration_seconds
        self.initial_latency_ms = initial_latency_ms
        self.final_latency_ms = final_latency_ms if final_latency_ms is not None else initial_latency_ms
        self.initial_packet_loss = initial_packet_loss
        self.final_packet_loss = final_packet_loss if final_packet_loss is not None else initial_packet_loss
        self.transition_type = transition_type
        self.start_time = None
    
    def start(self):
        """开始场景"""
        self.start_time = time.time()
        logger.info(f"开始网络场景: {self.name} (持续{self.duration_seconds}秒)")
        logger.info(f"  初始延迟: {self.initial_latency_ms}ms")
        logger.info(f"  最终延迟: {self.final_latency_ms}ms")
        logger.info(f"  初始丢包率: {self.initial_packet_loss:.1%}")
        logger.info(f"  最终丢包率: {self.final_packet_loss:.1%}")
    
    def is_active(self) -> bool:
        """检查场景是否处于活动状态"""
        if self.start_time is None:
            return False
        
        elapsed = time.time() - self.start_time
        return elapsed < self.duration_seconds
    
    def get_elapsed_percentage(self) -> float:
        """获取已过去时间百分比"""
        if self.start_time is None:
            return 0.0
        
        elapsed = time.time() - self.start_time
        return min(1.0, elapsed / self.duration_seconds)
    
    def get_current_conditions(self) -> Tuple[float, float]:
        """
        获取当前网络条件
        
        Returns:
            当前延迟（毫秒），当前丢包率（0.0-1.0）
        """
        if self.start_time is None:
            return self.initial_latency_ms, self.initial_packet_loss
        
        pct = self.get_elapsed_percentage()
        
        # 根据过渡类型计算当前值
        if self.transition_type == 'step':
            # 阶跃变化（前一半使用初始值，后一半使用最终值）
            if pct < 0.5:
                return self.initial_latency_ms, self.initial_packet_loss
            else:
                return self.final_latency_ms, self.final_packet_loss
        
        elif self.transition_type == 'exponential':
            # 指数变化
            factor = math.pow(pct, 2)  # 指数因子
            latency = self.initial_latency_ms + factor * (self.final_latency_ms - self.initial_latency_ms)
            loss = self.initial_packet_loss + factor * (self.final_packet_loss - self.initial_packet_loss)
            return latency, loss
        
        else:  # 默认为线性变化
            # 线性变化
            latency = self.initial_latency_ms + pct * (self.final_latency_ms - self.initial_latency_ms)
            loss = self.initial_packet_loss + pct * (self.final_packet_loss - self.initial_packet_loss)
            return latency, loss

class AutoTuningDemo:
    """自动调整演示"""
    
    def __init__(self, scenarios: List[NetworkScenario], enable_auto_tuning: bool = True):
        """
        初始化演示
        
        Args:
            scenarios: 网络场景列表
            enable_auto_tuning: 是否启用自动调整
        """
        self.scenarios = scenarios
        self.enable_auto_tuning = enable_auto_tuning
        self.current_scenario_index = 0
        
        # 创建组件
        self.mesh_adapter_a = MeshAdapter(node_id="节点A")
        self.mesh_adapter_b = MeshAdapter(node_id="节点B")
        
        # 设置网络模拟器
        self.network_emulator = NetworkEmulator()
        self.network_emulator.add_node(self.mesh_adapter_a)
        self.network_emulator.add_node(self.mesh_adapter_b)
        
        # 创建指标收集器
        self.metrics_collector = MetricsCollector()
        self.metrics_collector.register_mesh_adapter(self.mesh_adapter_a)
        self.metrics_collector.register_mesh_adapter(self.mesh_adapter_b)
        
        # 配置和创建自动调整器
        if enable_auto_tuning:
            update_config("auto_tuner", {"enable": True, "interval_seconds": 5.0})
            self.auto_tuner = AutoTuner(mesh_adapter=self.mesh_adapter_a)
        else:
            self.auto_tuner = None
        
        # 启用重试
        update_config("mesh", {"enable_retries": True})
        
        # 启用背压控制
        update_config("mesh", {"enable_backpressure": True})
        
        # 启用批处理
        update_config("mesh", {"enable_batch_processing": True})
        
        # 启用自适应心跳
        update_config("mesh", {"enable_adaptive_heartbeat": True})
        
        # 任务
        self.message_task = None
        self.metrics_task = None
        self.scenario_task = None
        self.stopping = False
    
    async def start(self):
        """启动演示"""
        logger.info("启动自动调整演示")
        
        # 开始第一个场景
        if self.scenarios:
            self.scenarios[0].start()
        
        # 启动自动调整器
        if self.auto_tuner:
            await self.auto_tuner.start()
            logger.info("已启动自动调整器")
        else:
            logger.info("自动调整器已禁用")
        
        # 启动任务
        self.stopping = False
        self.message_task = asyncio.create_task(self._send_messages())
        self.metrics_task = asyncio.create_task(self._collect_metrics())
        self.scenario_task = asyncio.create_task(self._manage_scenarios())
    
    async def stop(self):
        """停止演示"""
        logger.info("停止自动调整演示")
        self.stopping = True
        
        # 停止自动调整器
        if self.auto_tuner:
            await self.auto_tuner.stop()
        
        # 取消任务
        for task in [self.message_task, self.metrics_task, self.scenario_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("演示已停止")
    
    async def _send_messages(self):
        """发送消息任务"""
        counter = 0
        
        while not self.stopping:
            try:
                # 发送消息
                message = {
                    "type": "demo",
                    "counter": counter,
                    "timestamp": time.time(),
                    "data": "X" * random.randint(100, 1000)  # 随机大小的数据
                }
                
                await self.mesh_adapter_a.broadcast(json.dumps(message))
                counter += 1
                
                # 等待一段时间
                await asyncio.sleep(0.1)  # 每秒约10条消息
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"发送消息错误: {e}")
                await asyncio.sleep(1.0)
    
    async def _collect_metrics(self):
        """收集指标任务"""
        while not self.stopping:
            try:
                # 获取当前网络条件
                latency, loss = self._get_current_network_conditions()
                
                # 更新网络模拟器
                self.network_emulator.set_latency(latency)
                self.network_emulator.set_packet_loss(loss)
                
                # 收集指标
                metrics_a = self.mesh_adapter_a.get_performance_metrics()
                
                # 显示当前状态
                self._display_status(latency, loss, metrics_a)
                
                # 等待一段时间
                await asyncio.sleep(2.0)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"收集指标错误: {e}")
                await asyncio.sleep(1.0)
    
    async def _manage_scenarios(self):
        """管理场景任务"""
        while not self.stopping:
            try:
                # 获取当前场景
                if self.current_scenario_index >= len(self.scenarios):
                    logger.info("所有场景已完成")
                    self.stopping = True
                    break
                
                current_scenario = self.scenarios[self.current_scenario_index]
                
                # 检查当前场景是否已结束
                if not current_scenario.is_active():
                    # 进入下一个场景
                    self.current_scenario_index += 1
                    
                    if self.current_scenario_index < len(self.scenarios):
                        self.scenarios[self.current_scenario_index].start()
                    
                # 等待一段时间
                await asyncio.sleep(1.0)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"管理场景错误: {e}")
                await asyncio.sleep(1.0)
    
    def _get_current_network_conditions(self) -> Tuple[float, float]:
        """
        获取当前网络条件
        
        Returns:
            当前延迟（毫秒），当前丢包率（0.0-1.0）
        """
        if self.current_scenario_index >= len(self.scenarios):
            return 0.0, 0.0
        
        current_scenario = self.scenarios[self.current_scenario_index]
        return current_scenario.get_current_conditions()
    
    def _display_status(self, latency: float, loss: float, metrics: Dict[str, Any]):
        """
        显示当前状态
        
        Args:
            latency: 当前延迟（毫秒）
            loss: 当前丢包率（0.0-1.0）
            metrics: 性能指标
        """
        # 清屏（仅限于支持ANSI转义码的终端）
        print("\033[2J\033[H", end="")
        
        # 获取当前场景
        current_scenario = self.scenarios[self.current_scenario_index] if self.current_scenario_index < len(self.scenarios) else None
        
        # 显示场景信息
        print(f"========== 自动调整演示 ==========")
        print(f"场景: {current_scenario.name if current_scenario else '无'}")
        if current_scenario:
            print(f"进度: {current_scenario.get_elapsed_percentage():.1%}")
        
        # 显示网络条件
        print(f"\n当前网络条件:")
        print(f"  延迟: {latency:.1f}ms")
        print(f"  丢包率: {loss:.1%}")
        
        # 显示性能指标
        print(f"\n性能指标:")
        
        if "message_send" in metrics:
            msg_metrics = metrics["message_send"]
            print(f"  消息发送:")
            print(f"    总数: {msg_metrics.get('count', 0)}")
            print(f"    P50延迟: {msg_metrics.get('p50', 0.0):.1f}ms")
            print(f"    P95延迟: {msg_metrics.get('p95', 0.0):.1f}ms")
            print(f"    P99延迟: {msg_metrics.get('p99', 0.0):.1f}ms")
        
        if "retry" in metrics:
            retry_metrics = metrics["retry"]
            print(f"  重试:")
            print(f"    总重试次数: {retry_metrics.get('total_retries', 0)}")
            print(f"    平均重试次数: {retry_metrics.get('avg_retries', 0.0):.2f}")
            print(f"    最大重试次数: {retry_metrics.get('max_retries', 0)}")
        
        if "batch" in metrics:
            batch_metrics = metrics["batch"]
            print(f"  批处理:")
            print(f"    总批次数: {batch_metrics.get('batch_count', 0)}")
            print(f"    平均批大小: {batch_metrics.get('avg_batch_size', 0.0):.2f}")
            print(f"    最大批大小: {batch_metrics.get('max_batch_size', 0)}")
        
        # 显示当前配置
        print(f"\n当前配置:")
        mesh_config = get_config("mesh")
        print(f"  批处理大小限制: {mesh_config.get('batch_size_limit', 10)}")
        print(f"  批处理时间限制: {mesh_config.get('batch_time_limit_ms', 100)}ms")
        print(f"  最大重试次数: {mesh_config.get('max_retries', 3)}")
        print(f"  重试间隔: {mesh_config.get('retry_interval_ms', 500)}ms")
        print(f"  压缩: {'已启用' if mesh_config.get('enable_compression', False) else '已禁用'}")
        print(f"  背压控制: {'已启用' if mesh_config.get('enable_backpressure', False) else '已禁用'}")
        print(f"  令牌填充速率: {mesh_config.get('token_rate', 10.0):.1f}个/秒")
        print(f"  令牌桶容量: {mesh_config.get('token_capacity', 20.0):.1f}个")
        
        # 显示自动调整信息
        if self.auto_tuner:
            print(f"\n自动调整器:")
            status = self.auto_tuner.get_status()
            adjustments = self.auto_tuner.get_adjustment_history()
            
            print(f"  状态: {'运行中' if status.get('is_running', False) else '已停止'}")
            print(f"  目标P95延迟: {status.get('target_p95_latency_ms', 0.0):.1f}ms")
            print(f"  目标成功率: {status.get('target_success_rate', 0.0):.1%}")
            print(f"  调整次数: {status.get('adjustment_count', 0)}")
            
            # 显示最近的调整
            if adjustments:
                print(f"\n最近的调整:")
                for i, adj in enumerate(reversed(adjustments[-5:])):  # 显示最近5次调整
                    print(f"  {i+1}. {adj}")
        
        # 显示底部提示
        print("\n按Ctrl+C退出演示")

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自动调整演示程序')
    parser.add_argument('--no-auto-tuning', action='store_true', help='禁用自动调整')
    args = parser.parse_args()
    
    # 创建场景
    scenarios = [
        # 场景1：良好网络条件（基线）
        NetworkScenario(
            name="良好网络条件",
            duration_seconds=30,
            initial_latency_ms=30,
            initial_packet_loss=0.01
        ),
        
        # 场景2：网络延迟逐渐恶化
        NetworkScenario(
            name="网络延迟恶化",
            duration_seconds=60,
            initial_latency_ms=50,
            final_latency_ms=500,
            initial_packet_loss=0.01,
            final_packet_loss=0.05,
            transition_type='linear'
        ),
        
        # 场景3：高延迟稳定期
        NetworkScenario(
            name="高延迟稳定期",
            duration_seconds=60,
            initial_latency_ms=500,
            initial_packet_loss=0.05
        ),
        
        # 场景4：网络恢复
        NetworkScenario(
            name="网络恢复",
            duration_seconds=30,
            initial_latency_ms=500,
            final_latency_ms=50,
            initial_packet_loss=0.05,
            final_packet_loss=0.01,
            transition_type='exponential'
        ),
        
        # 场景5：网络丢包突然增加
        NetworkScenario(
            name="网络丢包突增",
            duration_seconds=60,
            initial_latency_ms=100,
            initial_packet_loss=0.01,
            final_packet_loss=0.2,
            transition_type='step'
        ),
        
        # 场景6：极端网络条件
        NetworkScenario(
            name="极端网络条件",
            duration_seconds=60,
            initial_latency_ms=800,
            initial_packet_loss=0.3
        ),
        
        # 场景7：网络完全恢复
        NetworkScenario(
            name="网络完全恢复",
            duration_seconds=30,
            initial_latency_ms=800,
            final_latency_ms=30,
            initial_packet_loss=0.3,
            final_packet_loss=0.01,
            transition_type='linear'
        )
    ]
    
    # 创建演示
    demo = AutoTuningDemo(scenarios, enable_auto_tuning=not args.no_auto_tuning)
    
    try:
        # 启动演示
        await demo.start()
        
        # 等待演示完成
        while not demo.stopping:
            await asyncio.sleep(1.0)
    
    except KeyboardInterrupt:
        logger.info("收到用户中断，正在停止...")
    
    finally:
        # 停止演示
        await demo.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n演示已中断") 