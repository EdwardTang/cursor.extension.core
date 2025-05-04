# Cloud Relay服务设计

## 1. 概述

Cloud Relay是Oppie.xyz系统中的关键组件，它连接本地工作站上的Sidecar Daemon与移动PWA客户端，使用户能够从手机远程触发和监控Cursor任务。Cloud Relay采用无状态设计，主要处理消息中继、身份验证和连接管理。

## 2. 架构

```
                   ┌──────────────┐
                   │   Mobile     │
                   │    PWA       │
                   └──────┬───────┘
                          │ WSS+JWT
                          ▼
┌─────────────────────────────────────────┐
│              Cloud Relay                 │
├─────────────────────────────────────────┤
│ ┌─────────────┐  ┌──────────────────┐   │
│ │ Auth Service│  │ Connection Manager│   │
│ └─────────────┘  └──────────────────┘   │
│ ┌─────────────┐  ┌──────────────────┐   │
│ │Message Queue│  │ Health Monitoring │   │
│ └─────────────┘  └──────────────────┘   │
└──────────────────────┬──────────────────┘
                       │ WSS+JWT
                       ▼
         ┌─────────────────────────────┐
         │      Sidecar Daemon         │
         │   (On Local Workstation)    │
         └─────────────────────────────┘
```

## 3. 核心组件

### 3.1 连接管理器 (Connection Manager)

- 维护所有活跃的WebSocket连接
- 处理连接生命周期（建立、保持活动、重连、关闭）
- 实现连接池和限流机制
- 提供会话识别和映射

### 3.2 身份验证服务 (Auth Service)

- JWT令牌验证和生成
- 权限控制和授权管理
- 可选的OTP (One-Time Password) 集成
- 用户账户和设备关联

### 3.3 消息队列 (Message Queue)

- 临时存储无法即时送达的消息
- 确保消息顺序和传递可靠性
- 支持优先级消息处理
- 实现消息过期和清理策略

### 3.4 健康监控 (Health Monitoring)

- 服务运行状态检查
- 连接统计和性能指标收集
- 异常检测和报警
- 提供标准Prometheus指标终端

## 4. API接口

### 4.1 WebSocket API

Relay服务主要通过WebSocket提供实时双向通信：

```
wss://relay.oppie.xyz/session?jwt=<token>
```

#### 认证流程
1. 客户端通过HTTPS获取JWT令牌（`POST /api/auth/token`）
2. 客户端使用JWT连接WebSocket端点
3. 服务器验证JWT并建立持久连接

### 4.2 REST API

除WebSocket外，还提供以下REST端点：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/auth/token` | POST | 获取访问令牌 |
| `/api/auth/devices` | GET | 获取关联设备列表 |
| `/api/health` | GET | 服务健康状态 |
| `/api/metrics` | GET | Prometheus格式的指标 |
| `/api/sessions` | GET | 活动会话状态 |

## 5. 消息格式

所有消息采用JSON格式，基本结构如下：

```json
{
  "type": "messageType",
  "timestamp": 1633046400000,
  "payload": {},
  "metadata": {
    "deviceId": "device-uuid",
    "sessionId": "session-uuid",
    "priority": 1
  }
}
```

### 5.1 主要消息类型

| 类型 | 方向 | 描述 |
|------|------|------|
| `runPlan` | PWA → Sidecar | 启动新计划执行 |
| `chat` | PWA → Sidecar | 发送聊天消息 |
| `progress` | Sidecar → PWA | 执行进度更新 |
| `diff` | Sidecar → PWA | 代码差异 |
| `recover` | Sidecar → PWA | 恢复操作状态 |
| `approve` | PWA → Sidecar | 批准/拒绝操作 |

## 6. 安全考虑

- 所有通信使用TLS/WSS加密
- JWT令牌使用强加密算法(RS256)，短期有效期
- 实现请求频率限制，防止DDoS攻击
- 消息负载大小限制防止资源耗尽
- 可选OTP用于高风险操作
- 所有API调用记录审计日志

## 7. 与MeshAdapter集成

Cloud Relay与本地MeshAdapter的集成通过Sidecar Daemon实现：

1. Sidecar Daemon同时连接本地MeshAdapter(通过IPC)和Cloud Relay(通过WSS)
2. Sidecar负责消息格式转换和映射
3. 对于特殊消息类型（如大型diff），实现增量传输和压缩
4. 添加端到端确认机制确保关键消息不丢失

## 8. 容错与稳定性

- 实现指数退避重连策略
- 使用心跳机制检测断开连接
- 本地缓冲未发送消息，连接恢复后自动同步
- 部署多实例集群，通过负载均衡实现高可用性
- 支持基于区域的路由，减少全球延迟

## 9. 开发和部署策略

Cloud Relay服务将采用以下技术栈和部署方式：

- **语言/框架**: Python FastAPI 或 Go + Fiber
- **WebSocket库**: uvicorn/FastAPI的WebSockets或gorilla/websocket
- **部署**: Docker容器，Kubernetes编排
- **监控**: Prometheus + Grafana
- **测试策略**: 单元测试、集成测试和负载测试
- **CI/CD**: GitHub Actions，自动部署到测试环境

## 10. 下一步行动

1. 定义详细的API协议和消息规范 (`cloud_relay/proto/relay.proto`)
2. 创建服务框架和基础设施代码
3. 实现核心WebSocket处理逻辑
4. 添加JWT认证和会话管理
5. 编写单元和集成测试
6. 设置CI管道和测试环境
7. 与Mobile PWA和VS Code扩展团队协调接口设计 