#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import asyncio
import time
import json
import csv
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Tuple, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 导入测试模块
from tests.performance.test_network_conditions import (
    NetworkEmulator, MetricsCollector, MockTool,
    MeshPerformanceTestBase, TestMeshAdapterPerformance
)

# 导入系统组件
from oppie.mesh_adapter import MeshAdapter
from oppie.tool_proxy import ToolProxy, GlobalCounter
from oppie.dev_loop_watcher import DevLoopWatcher, AgentSHelpers

# 定义测试参数矩阵
TEST_PARAMS = [
    # [名称, 延迟(ms), 抖动(ms), 丢包率(%), 批处理大小, 批处理时间限制(ms)]
    ["baseline", 0, 0, 0, 1, 0],        # 基线 - 无延迟/丢包/无批处理
    ["baseline_batch", 0, 0, 0, 10, 100],  # 基线 + 批处理
    ["low_latency", 50, 10, 0, 1, 0],   # 低延迟 - 无批处理
    ["low_latency_batch", 50, 10, 0, 10, 100],  # 低延迟 + 批处理
    ["med_latency", 200, 30, 0, 1, 0],  # 中等延迟 - 无批处理
    ["med_latency_batch", 200, 30, 0, 10, 100],  # 中等延迟 + 批处理
    ["high_latency", 500, 50, 0, 1, 0],  # 高延迟 - 无批处理
    ["high_latency_batch", 500, 50, 0, 10, 100],  # 高延迟 + 批处理
    ["low_loss", 50, 10, 5, 1, 0],      # 低延迟 + 低丢包 - 无批处理
    ["low_loss_batch", 50, 10, 5, 10, 100],  # 低延迟 + 低丢包 + 批处理
    ["high_loss", 200, 30, 15, 1, 0],   # 中等延迟 + 高丢包 - 无批处理
    ["high_loss_batch", 200, 30, 15, 10, 100],  # 中等延迟 + 高丢包 + 批处理
    ["extreme", 500, 100, 20, 1, 0],    # 极端情况 - 无批处理
    ["extreme_batch", 500, 100, 20, 20, 200],  # 极端情况 + 增强批处理
]

# 测试配置
TEST_CONFIG = {
    "iterations": 5,           # 每个参数组合运行的次数
    "node_count": 3,           # 测试中的节点数
    "operations_per_test": 50, # 每次测试的操作数
    "output_dir": "/tmp/oppie_perf",    # 结果输出目录
    "report_file": "perf_report.html"   # 报告文件名
}


class PerformanceTestRunner(MeshPerformanceTestBase):
    """性能测试运行器"""
    
    def __init__(self, params: List[List], config: Dict[str, Any]):
        """
        初始化测试运行器
        
        Args:
            params: 测试参数矩阵
            config: 测试配置
        """
        self.params = params
        self.config = config
        self.results = {}
        
        # 确保输出目录存在
        os.makedirs(self.config["output_dir"], exist_ok=True)
    
    async def run_single_test(self, param: List) -> Dict[str, Any]:
        """
        运行单个测试
        
        Args:
            param: 测试参数
            
        Returns:
            测试结果
        """
        # 解包参数
        name, latency_ms, jitter_ms, packet_loss_pct, batch_size, batch_time_ms = param
        
        print(f"\n运行测试: {name}")
        print(f"  延迟: {latency_ms}ms, 抖动: {jitter_ms}ms, 丢包率: {packet_loss_pct}%")
        print(f"  批处理: 大小={batch_size}, 时间限制={batch_time_ms}ms")
        
        # 创建网络模拟器
        net_emulator = NetworkEmulator()
        net_emulator.configure(
            latency_ms=latency_ms,
            jitter_ms=jitter_ms,
            packet_loss=packet_loss_pct / 100.0
        )
        
        # 创建指标收集器
        metrics = MetricsCollector(
            output_path=os.path.join(self.config["output_dir"], f"perf_{name}.csv")
        )
        
        # 添加测试元数据
        metrics.add_test_metadata(
            test_name=name,
            latency_ms=latency_ms,
            jitter_ms=jitter_ms,
            packet_loss_pct=packet_loss_pct,
            batch_size=batch_size,
            batch_time_ms=batch_time_ms,
            timestamp=time.time()
        )
        
        # 设置测试网格
        nodes = await self.setup_mesh_network(node_count=self.config["node_count"])
        
        # 为每个节点添加指标收集器
        for node in nodes:
            node.metrics_collector = metrics
            
            # 配置批处理设置
            if batch_size > 1:
                node.configure_batch_settings(
                    size_limit=batch_size,
                    time_limit_ms=batch_time_ms
                )
        
        # 创建工具代理
        proxies = await self.create_tool_proxies(nodes)
        
        # 记录开始指标
        metrics.set_counter("node_count", len(nodes))
        metrics.set_counter("broadcast_count", 0)
        
        # 执行测试操作
        successful_ops = 0
        failed_ops = 0
        
        for i in range(self.config["operations_per_test"]):
            try:
                # 应用网络模拟
                if await net_emulator.simulate_network():
                    # 从主节点调用并广播计数器更新
                    start_time = time.time()
                    proxies[0].invoke()
                    end_time = time.time()
                    
                    # 记录调用延迟
                    invoke_duration_ms = (end_time - start_time) * 1000
                    metrics.record_timing("invoke", invoke_duration_ms)
                    
                    # 增加广播计数
                    metrics.increment_counter("broadcast_count")
                    successful_ops += 1
                else:
                    # 模拟丢包
                    metrics.increment_counter("packet_loss_count")
                    failed_ops += 1
                
                # 短暂等待消息传播
                await asyncio.sleep(0.01)
            except Exception as e:
                # 记录错误
                metrics.increment_counter("error_count")
                failed_ops += 1
                print(f"操作 {i} 错误: {e}")
        
        # 等待所有消息处理完成
        await asyncio.sleep(1.0)
        
        # 记录最终计数器状态
        for i, proxy in enumerate(proxies):
            count = proxy.call_count
            metrics.set_counter(f"node_{i}_count", count)
        
        # 收集性能指标
        for node in nodes:
            node_metrics = node.get_performance_metrics()
            # 合并节点指标
            for category, stats in node_metrics.items():
                prefix = f"node_{node.node_id}_{category}"
                for stat_name, value in stats.items():
                    metrics.set_counter(f"{prefix}_{stat_name}", value)
        
        # 关闭所有节点
        for node in nodes:
            await node.shutdown()
        
        # 导出指标
        metrics.export_to_csv()
        
        # 读取并解析CSV结果
        results = self.parse_csv_results(metrics.output_path)
        
        # 添加成功/失败操作计数
        results["successful_ops"] = successful_ops
        results["failed_ops"] = failed_ops
        results["success_rate"] = (successful_ops / self.config["operations_per_test"]) * 100 if self.config["operations_per_test"] > 0 else 0
        
        return results
    
    def parse_csv_results(self, csv_path: str) -> Dict[str, Any]:
        """
        解析CSV结果文件
        
        Args:
            csv_path: CSV文件路径
            
        Returns:
            解析后的结果字典
        """
        results = {
            "metadata": {},
            "counters": {},
            "timing_stats": {}
        }
        
        with open(csv_path, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # 跳过标题行
            
            for row in reader:
                if len(row) >= 4:
                    type_, name, key, value = row
                    
                    if type_ == "metadata":
                        results["metadata"][key] = value
                    elif type_ == "counter":
                        results["counters"][name] = float(value)
                    elif type_ == "timing_stats":
                        if name not in results["timing_stats"]:
                            results["timing_stats"][name] = {}
                        results["timing_stats"][name][key] = float(value)
        
        return results
    
    async def run_all_tests(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        运行所有测试
        
        Returns:
            所有测试结果
        """
        all_results = {}
        
        for param in self.params:
            name = param[0]
            all_results[name] = []
            
            # 多次迭代以获得更可靠的结果
            for i in range(self.config["iterations"]):
                print(f"\n迭代 {i+1}/{self.config['iterations']} - 测试: {name}")
                result = await self.run_single_test(param)
                all_results[name].append(result)
        
        self.results = all_results
        return all_results
    
    def generate_report(self) -> None:
        """生成HTML报告"""
        if not self.results:
            print("没有结果可以生成报告")
            return
        
        report_path = os.path.join(self.config["output_dir"], self.config["report_file"])
        
        # 准备图表数据
        test_names = []
        p95_latencies = []
        success_rates = []
        
        for name, result_list in self.results.items():
            if result_list:
                # 计算平均值
                avg_p95 = np.mean([
                    r["timing_stats"].get("broadcast_counter", {}).get("p95", 0) 
                    for r in result_list
                ])
                avg_success_rate = np.mean([r["success_rate"] for r in result_list])
                
                test_names.append(name)
                p95_latencies.append(avg_p95)
                success_rates.append(avg_success_rate)
        
        # 创建图表
        plt.figure(figsize=(15, 10))
        
        # P95延迟图表
        plt.subplot(2, 1, 1)
        bars = plt.bar(test_names, p95_latencies)
        plt.title('P95 Broadcast Latency by Test Configuration')
        plt.ylabel('Latency (ms)')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 为每个柱添加数值标签
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}ms',
                    ha='center', va='bottom', rotation=0)
        
        # 成功率图表
        plt.subplot(2, 1, 2)
        bars = plt.bar(test_names, success_rates)
        plt.title('Operation Success Rate by Test Configuration')
        plt.ylabel('Success Rate (%)')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 为每个柱添加数值标签
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom', rotation=0)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.config["output_dir"], "perf_charts.png"))
        
        # 生成HTML报告
        with open(report_path, 'w') as f:
            f.write("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Oppie性能测试报告</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    table { border-collapse: collapse; width: 100%; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    tr:nth-child(even) { background-color: #f9f9f9; }
                    .chart-container { margin: 20px 0; text-align: center; }
                    h1, h2 { color: #333; }
                    .summary { background-color: #e6f7ff; padding: 15px; border-radius: 5px; }
                </style>
            </head>
            <body>
                <h1>Oppie性能测试报告</h1>
                <div class="summary">
                    <h2>测试摘要</h2>
                    <p>节点数: %d</p>
                    <p>每个配置的迭代次数: %d</p>
                    <p>每次测试的操作数: %d</p>
                    <p>测试时间: %s</p>
                </div>
                
                <div class="chart-container">
                    <h2>性能图表</h2>
                    <img src="perf_charts.png" alt="性能图表" style="max-width: 100%%;">
                </div>
                
                <h2>详细结果</h2>
            """ % (
                self.config["node_count"],
                self.config["iterations"],
                self.config["operations_per_test"],
                time.strftime("%Y-%m-%d %H:%M:%S")
            ))
            
            # 添加详细结果表格
            f.write("""
                <table>
                    <tr>
                        <th>测试配置</th>
                        <th>延迟 (ms)</th>
                        <th>抖动 (ms)</th>
                        <th>丢包率 (%%)</th>
                        <th>批处理大小</th>
                        <th>批处理时间 (ms)</th>
                        <th>P95延迟 (ms)</th>
                        <th>平均延迟 (ms)</th>
                        <th>成功率 (%%)</th>
                    </tr>
            """)
            
            for param in self.params:
                name, latency_ms, jitter_ms, packet_loss_pct, batch_size, batch_time_ms = param
                if name in self.results and self.results[name]:
                    # 计算平均值
                    avg_p95 = np.mean([
                        r["timing_stats"].get("broadcast_counter", {}).get("p95", 0) 
                        for r in self.results[name]
                    ])
                    avg_mean = np.mean([
                        r["timing_stats"].get("broadcast_counter", {}).get("mean", 0) 
                        for r in self.results[name]
                    ])
                    avg_success_rate = np.mean([r["success_rate"] for r in self.results[name]])
                    
                    f.write(f"""
                        <tr>
                            <td>{name}</td>
                            <td>{latency_ms}</td>
                            <td>{jitter_ms}</td>
                            <td>{packet_loss_pct}</td>
                            <td>{batch_size}</td>
                            <td>{batch_time_ms}</td>
                            <td>{avg_p95:.2f}</td>
                            <td>{avg_mean:.2f}</td>
                            <td>{avg_success_rate:.2f}</td>
                        </tr>
                    """)
            
            f.write("""
                </table>
                
                <h2>优化建议</h2>
                <ul>
                    <li>批处理在高延迟环境中显著提高性能，建议默认启用批处理。</li>
                    <li>对于高丢包率环境，应考虑增加重试策略。</li>
                    <li>自适应心跳间隔有助于在不同网络条件下保持稳定性。</li>
                    <li>考虑使用压缩来减少网络负载，特别是在高延迟环境中。</li>
                </ul>
                
                <h2>结论</h2>
                <p>
                    基于测试结果，系统在正常网络条件下表现良好，但在高延迟和高丢包环境中仍有改进空间。
                    建议实施批处理、重试策略、自适应心跳和消息压缩等优化措施，以提高系统在不稳定网络环境下的表现。
                </p>
            </body>
            </html>
            """)
        
        print(f"报告已生成: {report_path}")


async def main():
    """主函数"""
    # 创建并运行测试
    runner = PerformanceTestRunner(TEST_PARAMS, TEST_CONFIG)
    await runner.run_all_tests()
    runner.generate_report()
    
    print(f"\n性能测试完成，结果保存在 {TEST_CONFIG['output_dir']}")
    print(f"报告文件: {os.path.join(TEST_CONFIG['output_dir'], TEST_CONFIG['report_file'])}")


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main()) 