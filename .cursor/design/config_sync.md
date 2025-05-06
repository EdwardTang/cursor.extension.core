# ConfigSync 设计文档

## 1. 概述

ConfigSync是一个用于在Oppie网格中同步配置的机制，确保所有节点使用一致的优化参数，从而避免冲突并提高整体系统性能。

## 2. 设计目标

- **一致性**：确保所有节点最终使用相同的配置
- **低延迟**：配置变更应在短时间内（2×心跳间隔）传播到所有节点
- **冲突解决**：提供明确的规则处理同时发生的配置更改
- **无中心设计**：避免单点故障，任何节点都可以发起配置更改
- **资源效率**：最小化带宽和处理开销
- **可观测性**：提供配置同步状态的监控机制

## 3. 配置消息结构

```python
class ConfigUpdateMsg:
    """配置更新消息"""
    
    def __init__(self, 
                 section: str,
                 parameter: str,
                 value: Any,
                 timestamp: float,
                 node_id: str,
                 version_vector: Optional[Dict[str, int]] = None):
        """
        初始化配置更新消息
        
        Args:
            section: 配置部分，如"mesh", "auto_tuner"
            parameter: 参数名称，如"batch_size_limit"
            value: 新值
            timestamp: 更新时间戳
            node_id: 发起更新的节点ID
            version_vector: 版本向量，用于冲突检测
        """
        self.section = section
        self.parameter = parameter
        self.value = value
        self.timestamp = timestamp
        self.node_id = node_id
        self.version_vector = version_vector or {}
```

## 4. 版本控制方案

我们采用版本向量（Version Vector）作为主要的版本控制机制，并结合时间戳和节点ID作为冲突解决依据。

### 4.1 版本向量

每个节点维护一个版本向量，记录已看到的每个节点的更新计数：

```python
version_vector = {
    "node_1": 3,  # 已看到node_1的3次更新
    "node_2": 5,  # 已看到node_2的5次更新
    "node_3": 1   # 已看到node_3的1次更新
}
```

当节点发出新的配置更新时，它会将自己在版本向量中的计数加1。

### 4.2 比较规则

1. 如果版本向量A严格大于版本向量B（所有计数都大于或等于，且至少一个计数严格大于），那么A的配置更新较新
2. 如果版本向量A和B是不可比较的（一些计数大，一些计数小），表示并发更新，需要使用冲突解决规则
3. 如果版本向量相同，使用时间戳比较
4. 如果时间戳也相同，使用节点ID的字典序比较（较大值获胜）

## 5. 广播通道

ConfigSync利用现有的MeshAdapter基础设施进行消息广播：

1. 当配置更改发生时，创建ConfigUpdateMsg消息
2. 通过MeshAdapter.broadcast()广播消息
3. 各节点收到消息后处理，再通过事件总线通知其他组件

```python
# 发送配置更新
config_update = ConfigUpdateMsg(
    section="mesh", 
    parameter="batch_size_limit", 
    value=15, 
    timestamp=time.time(), 
    node_id=mesh_adapter.node_id,
    version_vector=config_sync_manager.get_version_vector()
)
await mesh_adapter.broadcast(config_update)

# 接收和处理配置更新
@mesh_adapter.on_message(ConfigUpdateMsg)
async def handle_config_update(msg):
    await config_sync_manager.process_update(msg)
```

## 6. 冲突解决规则

当检测到配置冲突时，我们使用以下规则解决：

1. **按优先级解决**：特定配置可以设置优先级标志，高优先级更新覆盖低优先级
2. **以时间戳为准**：在优先级相同的情况下，较晚的时间戳胜出
3. **节点ID决胜**：在时间戳相同的情况下，较大的节点ID胜出
4. **特殊处理规则**：某些参数可能有特殊的合并规则（如取最大值、取平均值等）

```python
def resolve_conflict(update1, update2):
    # 首先检查优先级
    if get_priority(update1) > get_priority(update2):
        return update1
    elif get_priority(update1) < get_priority(update2):
        return update2
    
    # 检查时间戳
    if update1.timestamp > update2.timestamp:
        return update1
    elif update1.timestamp < update2.timestamp:
        return update2
    
    # 时间戳相同，比较节点ID
    if update1.node_id > update2.node_id:
        return update1
    else:
        return update2
```

## 7. ConfigSyncManager设计

ConfigSyncManager作为配置同步的核心组件，负责处理配置更新、解决冲突并应用更改。

```python
class ConfigSyncManager:
    """配置同步管理器"""
    
    def __init__(self, mesh_adapter, config=None):
        """初始化配置同步管理器"""
        self.mesh_adapter = mesh_adapter
        self.config = config
        self.version_vector = {}  # 版本向量
        self.pending_updates = {}  # 等待应用的更新
        self.applied_updates = {}  # 已应用的更新
        self.event_bus = asyncio.Queue()  # 事件总线
        self.logger = logging.getLogger("ConfigSyncManager")
    
    async def start(self):
        """启动配置同步管理器"""
        # 注册消息处理器
        self.mesh_adapter.register_message_handler(
            ConfigUpdateMsg, self.process_update
        )
    
    async def process_update(self, msg):
        """处理配置更新消息"""
        # 检查版本向量，判断是否需要应用更新
        # 解决冲突
        # 应用更新
        # 通知其他组件
    
    async def publish_update(self, section, parameter, value):
        """发布配置更新"""
        # 增加自己的版本计数
        # 创建配置更新消息
        # 广播消息
        # 应用更新
    
    def get_version_vector(self):
        """获取当前版本向量"""
        return self.version_vector.copy()
```

## 8. 与AutoTuner的集成

AutoTuner与ConfigSyncManager的集成方式如下：

1. 当AutoTuner决定调整配置时，不直接应用更改，而是调用ConfigSyncManager.publish_update()
2. ConfigSyncManager广播配置更改并更新版本向量
3. 当收到合并后的配置更新时，AutoTuner应用更改

```python
class AutoTuner:
    # ... 现有代码 ...
    
    def __init__(self, mesh_adapter=None, config=None, config_sync_manager=None):
        # ... 现有初始化代码 ...
        self.config_sync_manager = config_sync_manager
    
    def set_config_sync_manager(self, config_sync_manager):
        """设置配置同步管理器"""
        self.config_sync_manager = config_sync_manager
    
    async def apply_adjustment(self, adjustment):
        """应用调整"""
        if self.config_sync_manager:
            # 通过配置同步管理器发布更新
            await self.config_sync_manager.publish_update(
                adjustment.section, 
                adjustment.parameter, 
                adjustment.new_value
            )
        else:
            # 直接应用更新（单节点模式）
            # ... 现有直接应用代码 ...
```

## 9. 协调器选举机制

为了避免多个AutoTuner同时运行导致的频繁配置更改，我们实现一个轻量级的协调器选举机制：

1. 每个节点启动后，发送Heartbeat消息包含其AutoTuner状态
2. 根据节点ID的字典序，选择最小ID的活跃节点作为协调器
3. 协调器节点的AutoTuner进入活跃模式，其他节点的AutoTuner进入观察模式
4. 如果协调器失联（超过3次心跳间隔无响应），重新选举

```python
def is_coordinator(self):
    """检查当前节点是否为协调器"""
    if not self.active_nodes:
        return True  # 单节点情况
    
    # 选择ID最小的活跃节点
    coordinator_id = min(self.active_nodes.keys())
    return coordinator_id == self.mesh_adapter.node_id
```

## 10. 故障处理

ConfigSync设计考虑了以下故障场景：

1. **网络分区**：分区恢复后，通过版本向量比较，自动合并配置更改
2. **节点崩溃**：节点重启后通过心跳机制获取最新配置
3. **消息丢失**：依靠MeshAdapter的重试机制确保配置消息的可靠传递
4. **时钟偏移**：主要依赖版本向量而非时间戳，降低时钟偏移影响

## 11. 资源使用优化

为了最小化带宽和处理开销，我们采取以下措施：

1. 仅发送变更的配置项，而非完整配置
2. 批量处理短时间内的多个配置更改
3. 对大型配置数据使用压缩
4. 在节点负载高时，降低配置同步优先级

## 12. 可观测性

ConfigSync提供以下观测和调试机制：

1. 详细的日志记录配置变更和冲突解决过程
2. 导出配置同步指标（传播延迟、冲突率等）
3. 配置同步状态API，用于监控和故障排除
4. 版本向量可视化工具，帮助理解配置历史 