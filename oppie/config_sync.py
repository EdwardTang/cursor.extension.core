#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置同步管理器
负责在多节点环境中同步配置
"""

import asyncio
import time
import logging
import copy
from typing import Dict, Any, Optional, List, Set, Tuple, Callable

from oppie.types import ConfigUpdateMsg
from oppie.config import get_config, update_config

class ConfigSyncManager:
    """配置同步管理器"""
    
    def __init__(self, mesh_adapter=None, config=None):
        """
        初始化配置同步管理器
        
        Args:
            mesh_adapter: 网格适配器
            config: 配置字典
        """
        self.mesh_adapter = mesh_adapter
        self.config = config or get_config()
        self.node_id = mesh_adapter.node_id if mesh_adapter else "unknown"
        
        # 版本控制
        self.version_vector = {self.node_id: 0}  # 版本向量
        self.message_handlers = {}  # 消息处理器
        
        # 跟踪已应用的配置
        self.applied_updates = {}  # {key: ConfigUpdateMsg}
        self.pending_updates = {}  # {key: ConfigUpdateMsg}
        
        # 活跃节点
        self.active_nodes = {}  # {node_id: last_seen_timestamp}
        
        # 协调器状态
        self.is_coordinator_node = True  # 默认认为自己是协调器，直到发现更适合的节点
        
        # 事件总线
        self.event_bus = asyncio.Queue()
        
        # 任务
        self.processor_task = None
        self.stopping = False
        
        # 日志
        self.logger = logging.getLogger("ConfigSyncManager")
        self.logger.setLevel(logging.INFO)
    
    async def start(self):
        """启动配置同步管理器"""
        if self.processor_task is not None:
            return
        
        self.stopping = False
        
        # 注册消息处理器
        if self.mesh_adapter:
            self.mesh_adapter.register_message_handler(
                ConfigUpdateMsg, self._on_config_update
            )
        
        # 启动处理任务
        self.processor_task = asyncio.create_task(self._process_events())
        
        self.logger.info(f"配置同步管理器已启动，节点ID: {self.node_id}")
    
    async def stop(self):
        """停止配置同步管理器"""
        self.stopping = True
        
        if self.processor_task and not self.processor_task.done():
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
            
            self.processor_task = None
        
        self.logger.info("配置同步管理器已停止")
    
    def set_mesh_adapter(self, mesh_adapter):
        """
        设置网格适配器
        
        Args:
            mesh_adapter: 网格适配器
        """
        self.mesh_adapter = mesh_adapter
        self.node_id = mesh_adapter.node_id
        
        if self.node_id not in self.version_vector:
            self.version_vector[self.node_id] = 0
        
        # 注册消息处理器
        mesh_adapter.register_message_handler(
            ConfigUpdateMsg, self._on_config_update
        )
    
    async def publish_update(self, section: str, parameter: str, value: Any, priority: int = 0) -> bool:
        """
        发布配置更新
        
        Args:
            section: 配置部分
            parameter: 参数名
            value: 参数值
            priority: 优先级
            
        Returns:
            是否成功发布
        """
        if not self.mesh_adapter:
            self.logger.warning("无法发布配置更新：未设置网格适配器")
            return False
        
        # 构建版本向量
        if self.node_id in self.version_vector:
            self.version_vector[self.node_id] += 1
        else:
            self.version_vector[self.node_id] = 1
        
        # 创建配置更新消息
        config_update = ConfigUpdateMsg(
            section=section,
            parameter=parameter,
            value=value,
            timestamp=time.time(),
            node_id=self.node_id,
            priority=priority,
            version_vector=copy.deepcopy(self.version_vector)
        )
        
        # 广播消息
        try:
            await self.mesh_adapter.broadcast(config_update)
            
            # 本地处理消息
            await self._apply_update(config_update)
            
            return True
        
        except Exception as e:
            self.logger.error(f"发布配置更新失败: {e}")
            return False
    
    async def _on_config_update(self, msg: ConfigUpdateMsg):
        """
        处理配置更新消息
        
        Args:
            msg: 配置更新消息
        """
        # 更新活跃节点
        self.active_nodes[msg.node_id] = time.time()
        
        # 更新自己的版本向量
        self._update_version_vector(msg.node_id, msg.version_vector)
        
        # 处理配置更新
        await self._process_update(msg)
    
    def _update_version_vector(self, node_id: str, remote_vector: Dict[str, int]):
        """
        更新版本向量
        
        Args:
            node_id: 节点ID
            remote_vector: 远程版本向量
        """
        # 对于每个远程节点的版本
        for remote_node_id, remote_version in remote_vector.items():
            # 如果本地没有该节点的版本记录，或者远程版本更高
            if (remote_node_id not in self.version_vector or 
                remote_version > self.version_vector[remote_node_id]):
                self.version_vector[remote_node_id] = remote_version
    
    async def _process_update(self, msg: ConfigUpdateMsg):
        """
        处理配置更新
        
        Args:
            msg: 配置更新消息
        """
        # 获取配置键
        key = msg.get_key()
        
        # 检查是否是已处理过的更新
        if key in self.applied_updates:
            applied_msg = self.applied_updates[key]
            
            # 检查版本
            comp_result = self._compare_versions(
                msg.version_vector, applied_msg.version_vector
            )
            
            if comp_result < 0:  # 当前消息版本较旧
                self.logger.debug(f"忽略较旧的配置更新: {msg}")
                return
            
            elif comp_result == 0:  # 版本相同，可能是重复消息
                if msg.timestamp <= applied_msg.timestamp:
                    self.logger.debug(f"忽略重复的配置更新: {msg}")
                    return
            
            # 继续处理
        
        # 检查是否与待处理的更新冲突
        if key in self.pending_updates:
            pending_msg = self.pending_updates[key]
            
            # 检查版本
            comp_result = self._compare_versions(
                msg.version_vector, pending_msg.version_vector
            )
            
            if comp_result < 0:  # 当前消息版本较旧
                self.logger.debug(f"忽略较旧的待处理配置更新: {msg}")
                return
            
            elif comp_result == 0:  # 版本冲突，需要解决
                # 解决冲突
                resolved_msg = self._resolve_conflict(msg, pending_msg)
                self.pending_updates[key] = resolved_msg
                
                self.logger.info(f"解决配置冲突: {resolved_msg}")
                return
            
            # 当前消息较新，替换待处理消息
            self.pending_updates[key] = msg
        else:
            # 新的配置项，直接加入待处理
            self.pending_updates[key] = msg
        
        # 应用更新
        await self._apply_update(msg)
    
    async def _apply_update(self, msg: ConfigUpdateMsg):
        """
        应用配置更新
        
        Args:
            msg: 配置更新消息
        """
        # 获取配置键
        key = msg.get_key()
        
        try:
            # 获取当前值
            current_value = get_config(msg.section).get(msg.parameter, None)
            
            # 应用更新
            update_config(msg.section, {msg.parameter: msg.value})
            
            # 记录已应用的更新
            self.applied_updates[key] = msg
            
            # 移除待处理的更新
            if key in self.pending_updates:
                del self.pending_updates[key]
            
            self.logger.info(f"应用配置更新: {msg.section}.{msg.parameter}={msg.value}")
            
            # 发送事件
            await self.event_bus.put({
                "type": "config_updated",
                "section": msg.section,
                "parameter": msg.parameter,
                "old_value": current_value,
                "new_value": msg.value,
                "source_node": msg.node_id
            })
        
        except Exception as e:
            self.logger.error(f"应用配置更新失败: {e}")
    
    def _compare_versions(self, v1: Dict[str, int], v2: Dict[str, int]) -> int:
        """
        比较两个版本向量
        
        Args:
            v1: 版本向量1
            v2: 版本向量2
            
        Returns:
            -1: v1 < v2
            0: v1 和 v2 不可比较
            1: v1 > v2
        """
        v1_gt_v2 = False  # v1是否大于v2
        v2_gt_v1 = False  # v2是否大于v1
        
        # 检查v1中的所有节点
        for node_id, version in v1.items():
            if node_id in v2:
                if version > v2[node_id]:
                    v1_gt_v2 = True
                elif version < v2[node_id]:
                    v2_gt_v1 = True
            else:
                v1_gt_v2 = True  # v1包含v2没有的节点
        
        # 检查v2中的所有节点
        for node_id, version in v2.items():
            if node_id not in v1:
                v2_gt_v1 = True  # v2包含v1没有的节点
        
        # 判断结果
        if v1_gt_v2 and not v2_gt_v1:
            return 1  # v1 > v2
        elif v2_gt_v1 and not v1_gt_v2:
            return -1  # v1 < v2
        else:
            return 0  # 不可比较
    
    def _resolve_conflict(self, msg1: ConfigUpdateMsg, msg2: ConfigUpdateMsg) -> ConfigUpdateMsg:
        """
        解决配置冲突
        
        Args:
            msg1: 配置更新消息1
            msg2: 配置更新消息2
            
        Returns:
            解决冲突后的配置更新消息
        """
        # 首先检查优先级
        if msg1.priority > msg2.priority:
            return msg1
        elif msg2.priority > msg1.priority:
            return msg2
        
        # 检查时间戳
        if msg1.timestamp > msg2.timestamp:
            return msg1
        elif msg2.timestamp > msg1.timestamp:
            return msg2
        
        # 时间戳相同，比较节点ID
        if msg1.node_id > msg2.node_id:
            return msg1
        else:
            return msg2
    
    async def _process_events(self):
        """处理事件循环"""
        while not self.stopping:
            try:
                # 从事件总线获取事件
                event = await self.event_bus.get()
                
                # 处理事件
                event_type = event.get("type", "")
                
                if event_type == "config_updated":
                    # 调用已注册的处理器
                    if event_type in self.message_handlers:
                        for handler in self.message_handlers[event_type]:
                            try:
                                await handler(event)
                            except Exception as e:
                                self.logger.error(f"处理事件'{event_type}'失败: {e}")
                
                # 标记任务完成
                self.event_bus.task_done()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"事件处理错误: {e}")
                await asyncio.sleep(1.0)
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type not in self.message_handlers:
            self.message_handlers[event_type] = []
        
        self.message_handlers[event_type].append(handler)
    
    def unregister_event_handler(self, event_type: str, handler: Callable) -> bool:
        """
        取消注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理函数
            
        Returns:
            是否成功取消注册
        """
        if event_type in self.message_handlers:
            if handler in self.message_handlers[event_type]:
                self.message_handlers[event_type].remove(handler)
                return True
        
        return False
    
    def is_coordinator(self) -> bool:
        """
        检查当前节点是否为协调器
        
        Returns:
            是否为协调器
        """
        if not self.active_nodes:
            return True  # 单节点情况
        
        # 根据节点ID选择协调器（字典序最小的）
        coordinator_id = min(list(self.active_nodes.keys()) + [self.node_id])
        return coordinator_id == self.node_id
    
    def update_coordinator_status(self):
        """更新协调器状态"""
        # 清理长时间不活跃的节点
        now = time.time()
        inactive_nodes = []
        
        for node_id, last_seen in self.active_nodes.items():
            # 超过3个心跳周期未见的节点视为不活跃
            if now - last_seen > 3 * get_config("mesh").get("initial_heartbeat_interval", 1.0):
                inactive_nodes.append(node_id)
        
        # 移除不活跃节点
        for node_id in inactive_nodes:
            if node_id in self.active_nodes:
                del self.active_nodes[node_id]
        
        # 更新协调器状态
        new_status = self.is_coordinator()
        
        if new_status != self.is_coordinator_node:
            self.is_coordinator_node = new_status
            if new_status:
                self.logger.info(f"节点 {self.node_id} 成为配置协调器")
            else:
                self.logger.info(f"节点 {self.node_id} 不再是配置协调器")
    
    def get_active_nodes(self) -> List[str]:
        """
        获取活跃节点列表
        
        Returns:
            活跃节点ID列表
        """
        return list(self.active_nodes.keys())
    
    def get_version_vector(self) -> Dict[str, int]:
        """
        获取版本向量
        
        Returns:
            版本向量副本
        """
        return copy.deepcopy(self.version_vector)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取状态信息
        
        Returns:
            状态信息
        """
        self.update_coordinator_status()
        
        return {
            "node_id": self.node_id,
            "is_coordinator": self.is_coordinator_node,
            "active_nodes": list(self.active_nodes.keys()),
            "version_vector": self.version_vector,
            "applied_updates_count": len(self.applied_updates),
            "pending_updates_count": len(self.pending_updates)
        } 