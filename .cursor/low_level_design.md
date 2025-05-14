#  Oppie.xyz 低级设计文档

---

## 1. 实现范围

以下是Oppie.xyz系统M1阶段的实现范围，包括每个组件的详细规格：

| 组件 | M1阶段状态 | 编程语言 | 目标代码行数 | 备注 |
|------|------------|----------|--------------|------|
| **Planner** | 核心功能 | Python | 1500-2000 | 基于Codex CLI，负责分析和计划生成 |
| **Executor** | 核心功能 | JavaScript | 2000-2500 | 基于Cursor，负责执行计划 |
| **Reflexion** | 基础实现 | Python | 1000-1500 | 简化版强化学习实现 |
| **Template管理** | 完整实现 | JavaScript/Python | 500-800 | 实现Template A格式处理 |
| **Remote Desktop** | 基础集成 | JavaScript/TypeScript | 2000-2500 | 集成billd-desk核心功能 |
| **Computer Use Agent** | 基础集成 | Python/JavaScript | 1500-2000 | 集成UI-TARS-desktop核心功能 |
| **OpenHands集成** | 概念验证 | Python | 500-1000 | 基础API集成 |
| **Trajectory Visualizer** | 基础实现 | React Native | 2000-2500 | 基础监控功能 |
| **状态管理** | 核心功能 | Python/JavaScript | 1000-1500 | 基础checkpoint和恢复机制 |

---

## 2. 组件接口定义

### 2.1 Planner-Executor接口

**接口类型**：基于文件的通信（Template A格式）

**接口定义**：
```typescript
interface TemplateA {
  cycleNumber: number;
  project: string;
  previousGoal?: string;
  previousOutcome?: string;
  currentBlockers: string[];
  nextGoal: string;
  historyPath: string;
  timeBox: string;
  relevantArtifacts: string[];
  scratchpadDelta: string;
  availableMcpTools: string;
  adrLink?: string;
  
  // Executor to Planner questions
  analysisQuestions?: string;
  planQuestions?: string;
  blockerSolutionsQuestions?: string;
  bestPracticesQuestions?: string;
  mcpToolsQuestions?: string;
  
  // Planner to Executor responses
  analysisJustification?: string;
  plan?: string[];
  blockerSolutions?: string[];
  bestPractices?: string[];
  recommendedMcpTools?: string[];
  executorFollowUpChecklist?: string[];
}
```

**通信流程**：
1. Executor填写Template A，写入`.scratchpad_logs/{timestamp}_plan_request.md`
2. Planner读取文件，生成响应
3. Planner将响应写入`.scratchpad_logs/{timestamp}_plan_response.md`
4. Executor读取响应，执行计划

### 2.2 Oppie-Core与UI-TARS-desktop接口

**接口类型**：REST API

**主要端点**：
```
POST   /api/v1/ui-tars/execute      - 执行GUI操作
GET    /api/v1/ui-tars/status       - 获取当前状态
PUT    /api/v1/ui-tars/resume       - 恢复中断的循环
PUT    /api/v1/ui-tars/rollback     - 回滚到指定checkpoint
```

**请求/响应示例**：
```json
// 执行GUI操作请求
{
  "operation": "click",
  "selector": {
    "type": "xpath",
    "value": "//*[@id='continue-button']"
  },
  "timeout": 5000
}

// 状态响应
{
  "status": "running",
  "currentOperation": "executing_plan",
  "progress": 75,
  "lastUpdate": "2023-05-08T19:15:30Z",
  "checkpoints": [
    {
      "id": "cp-2023-05-08-18-30-45",
      "description": "After completing task #123",
      "timestamp": "2023-05-08T18:30:45Z"
    }
  ]
}
```

### 2.3 Remote Desktop接口

**接口类型**：billd-desk Web API

**主要端点**：
```
GET    /api/v1/sessions             - 获取可用会话
POST   /api/v1/sessions             - 创建新会话
GET    /api/v1/sessions/{id}        - 获取会话详情
DELETE /api/v1/sessions/{id}        - 终止会话
POST   /api/v1/sessions/{id}/input  - 发送输入到会话
```

**权限和认证**：
- 基于JWT的身份验证
- 角色基础访问控制
- HTTPS加密

### 2.4 OpenHands接口

**接口类型**：RESTful API

**主要端点**：
```
POST   /api/v1/hands/move           - 移动手臂
POST   /api/v1/hands/grasp          - 抓取物体
POST   /api/v1/hands/release        - 释放物体
GET    /api/v1/hands/position       - 获取当前位置
```

**集成策略**：
- 使用适配器模式将软件操作转换为物理操作
- 实现命令队列，确保操作按顺序执行
- 提供回调机制，报告操作结果

---

## 3. 数据模型详细设计

### 3.1 系统状态模型

**主要实体**：
```typescript
interface SystemState {
  id: string;                // 唯一标识符
  timestamp: string;         // 创建时间
  description: string;       // 描述
  repositoryState: {         // 代码仓库状态
    commitHash: string;      // 当前提交的哈希值
    branch: string;          // 当前分支
    modifiedFiles: string[]; // 修改的文件列表
  };
  environmentState: {        // 执行环境状态
    variables: Record<string, string>; // 环境变量
    toolsAvailable: string[];          // 可用工具
  };
  taskState: {               // 任务状态
    currentCycle: number;    // 当前循环
    currentGoal: string;     // 当前目标
    progress: number;        // 进度（0-100）
    status: TaskStatus;      // 任务状态（枚举）
  };
}

enum TaskStatus {
  PENDING = 'pending',
  INITIALIZING = 'initializing',
  RUNNING = 'running',
  AWAITING_TOOL_INPUT = 'awaiting_tool_input',
  PROCESSING_TOOL_OUTPUT = 'processing_tool_output',
  RECOVERING_TOOL_LIMIT = 'recovering_tool_limit',
  RECOVERING_NETWORK = 'recovering_network',
  FAILED = 'failed',
  COMPLETED = 'completed'
}
```

**存储策略**：
- 使用Redis存储活动状态（快速访问）
- 使用PostgreSQL存储历史状态（持久化）
- 实现事务性操作，确保状态更新的一致性

### 3.2 Plan-Execute-Reflect循环数据模型

**基础数据结构**：
```typescript
interface PlanExecuteReflectCycle {
  id: string;                 // 唯一标识符
  cycleNumber: number;        // 循环编号
  timestamp: string;          // 创建时间
  
  // Plan阶段
  plan: {
    goal: string;             // 目标
    analysis: string;         // 分析
    steps: string[];          // 计划步骤
    blockerSolutions: string[]; // 障碍解决方案
  };
  
  // Execute阶段
  execution: {
    status: ExecutionStatus;  // 执行状态
    completedSteps: number;   // 已完成步骤数
    results: string[];        // 执行结果
    errors: string[];         // 执行错误
  };
  
  // Reflect阶段
  reflection: {
    success: boolean;         // 是否成功
    learnings: string[];      // 学习内容
    improvements: string[];   // 改进建议
    feedback: string;         // 反馈
  };
}

enum ExecutionStatus {
  NOT_STARTED = 'not_started',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  INTERRUPTED = 'interrupted'
}
```

**扩展Reflexion支持**：
```typescript
interface ReflexionExtension {
  cycleId: string;            // 关联的循环ID
  reinforcementSignals: {
    positive: string[];       // 正向强化信号
    negative: string[];       // 负向强化信号
  };
  verbalFeedback: string;     // 语言反馈
  learningRate: number;       // 学习率
  explorationRate: number;    // 探索率
}
```

### 3.3 用户任务和反馈模型

```typescript
interface UserTask {
  id: string;                 // 唯一标识符
  userId: string;             // 用户ID
  title: string;              // 标题
  description: string;        // 描述
  priority: TaskPriority;     // 优先级
  status: UserTaskStatus;     // 状态
  createdAt: string;          // 创建时间
  updatedAt: string;          // 更新时间
  deadline?: string;          // 截止时间
  tags: string[];             // 标签
}

enum TaskPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

enum UserTaskStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

interface UserFeedback {
  id: string;                 // 唯一标识符
  taskId: string;             // 关联的任务ID
  userId: string;             // 用户ID
  rating: number;             // 评分（1-5）
  comments: string;           // 评论
  createdAt: string;          // 创建时间
  suggestedImprovements?: string; // 建议改进
}
```

---

## 4. 技术选择详细说明

### 4.1 后端技术

**Python**：
- 版本：3.10+
- 主要框架：FastAPI（API服务）、Celery（任务队列）
- 用途：Planner组件、Reflexion组件、与第三方API集成

**JavaScript/TypeScript**：
- 版本：Node.js 18+，TypeScript 4.9+
- 主要框架：Express.js（API服务）、Socket.IO（实时通信）
- 用途：Executor组件、Template管理、前端开发

**Rust**（可选，用于性能关键部分）：
- 版本：1.68+
- 主要库：Tokio（异步运行时）、Serde（序列化）
- 用途：性能关键的系统组件，如状态管理、并发处理

### 4.2 数据存储

**Redis**：
- 版本：7.0+
- 用途：活动状态存储、消息队列、缓存
- 配置：启用持久化，配置适当的内存限制

**PostgreSQL**：
- 版本：15.0+
- 用途：持久化存储、关系数据、历史记录
- 模式：规范化设计，适当使用JSON字段存储半结构化数据

**Git**：
- 用途：代码版本控制
- 集成：通过libgit2或简单的命令行接口

### 4.3 通信技术

**REST API**：
- 使用OpenAPI/Swagger定义接口
- 使用JSON作为数据交换格式
- 实现适当的速率限制和缓存

**WebSocket**：
- 用于实时更新和通知
- 实现重连和心跳机制
- 使用JSON进行数据序列化

**消息队列**：
- RabbitMQ或Redis Streams
- 用于异步操作和组件间通信
- 实现可靠的消息传递和错误处理

### 4.4 前端技术

**Web界面**：
- React（18+）或Vue.js（3+）
- TypeScript用于类型安全
- 响应式设计，支持移动和桌面

**移动应用**：
- React Native（对于快速开发）
- 使用TypeScript
- 支持iOS和Android

**可视化**：
- D3.js用于复杂可视化
- Chart.js用于简单图表
- 使用WebGL进行高性能渲染（如需要）

---

## 5. 错误处理和恢复机制

### 5.1 错误分类

1. **工具调用限制错误**：
   - 症状：达到工具调用的次数限制
   - 检测：监控工具调用计数，识别特定错误消息
   - 处理：暂停执行，保存状态，启动新的执行实例

2. **网络错误**：
   - 症状：API调用超时、连接重置
   - 检测：捕获网络异常，监控响应时间
   - 处理：实现指数退避重试，在恢复后继续

3. **执行环境错误**：
   - 症状：进程崩溃、内存不足
   - 检测：监控进程健康状态，捕获异常
   - 处理：重启执行环境，从最近的checkpoint恢复

4. **逻辑错误**：
   - 症状：计划步骤失败、预期外结果
   - 检测：比较结果与预期，设置超时
   - 处理：回滚到安全状态，通知用户或尝试替代方案

### 5.2 恢复策略

1. **渐进式重试**：
   - 对于暂时性错误，使用指数退避重试
   - 设置最大重试次数和超时时间
   - 记录重试历史，用于后续分析

2. **Checkpoint和恢复**：
   - 定期创建系统状态的checkpoint
   - 为每个checkpoint生成唯一ID和描述
   - 提供回滚到特定checkpoint的机制

3. **降级服务**：
   - 定义关键功能和非关键功能
   - 在资源受限或出现错误时，优先保证关键功能
   - 提供明确的降级通知

4. **人工干预**：
   - 对于无法自动恢复的情况，提供人工干预接口
   - 发送通知给用户或管理员
   - 提供详细的错误信息和上下文

---

## 6. 安全设计

### 6.1 认证和授权

**认证机制**：
- 使用OAuth2/JWT认证
- 实现安全的密码存储（bcrypt）
- 支持多因素认证（可选）

**授权控制**：
- 基于角色的访问控制（RBAC）
- 细粒度的权限定义
- 强制执行最小权限原则

### 6.2 数据安全

**传输安全**：
- 所有API通信使用HTTPS（TLS 1.3）
- 实现证书固定（Certificate Pinning）
- 使用安全的WebSocket连接（wss://）

**存储安全**：
- 敏感数据加密存储（AES-256）
- 数据库级别的访问控制
- 定期备份和灾难恢复机制

### 6.3 代码和环境安全

**代码安全**：
- 实施代码审查流程
- 使用静态分析工具检测漏洞
- 定期更新依赖以修复已知漏洞

**环境安全**：
- 沙箱执行用户代码
- 实现资源限制和隔离
- 定期安全审计和渗透测试

---

## 7. 测试策略

### 7.1 单元测试

- 使用PyTest（Python）、Jest（JavaScript）等框架
- 目标代码覆盖率：80%+
- 重点测试核心算法和错误处理路径

### 7.2 集成测试

- 测试组件间接口
- 使用模拟服务模拟外部依赖
- 验证数据流和通信协议

### 7.3 系统测试

- 端到端测试完整工作流
- 性能和负载测试
- 故障注入测试恢复机制

### 7.4 用户接受测试

- 真实场景下的功能验证
- 用户体验评估
- 部署前的最终验收

---

## 8. 部署和运维计划

### 8.1 环境配置

**开发环境**：
- 使用Docker Compose配置的本地环境
- 使用mock服务模拟第三方API
- 热重载开发服务器

**测试环境**：
- 配置与生产环境相似
- 使用测试数据库和服务
- 自动化测试运行

**生产环境**：
- 高可用配置
- 负载均衡
- 定期备份

### 8.2 CI/CD流程

- 使用GitHub Actions/Jenkins自动化构建和测试
- 实现持续集成，每次提交时运行测试
- 使用环境分支策略管理部署

### 8.3 监控和日志

- 使用Prometheus/Grafana监控系统
- 集中式日志收集（ELK Stack）
- 设置关键指标的告警

### 8.4 扩展策略

- 识别可能的瓶颈
- 实现水平扩展能力
- 定义自动扩展触发条件

---

## 9. 开发计划和里程碑

### 9.1 阶段1：基础架构（1个月）

**目标**：建立基本框架和开发环境
- 设置项目结构和构建系统
- 实现核心数据模型
- 开发基础API和通信层

**可交付成果**：
- 项目框架和开发环境
- 基础数据库结构
- API定义文档

### 9.2 阶段2：核心功能（2个月）

**目标**：实现Oppie-Core的基本功能
- 开发Planner和Executor核心组件
- 实现基础Template管理
- 开发简单的Reflexion机制

**可交付成果**：
- 功能性的Plan-Execute-Reflect循环
- 基础错误处理和恢复
- 简单的测试套件

### 9.3 阶段3：集成和扩展（3个月）

**目标**：集成外部组件，扩展功能
- 集成Remote Desktop功能
- 集成Computer Use Agent
- 开发Trajectory Visualizer基础版

**可交付成果**：
- 集成的远程访问和控制
- 基础监控和可视化
- 扩展的错误恢复机制

### 9.4 阶段4：完善和优化（2个月）

**目标**：完善系统功能，优化性能
- 增强安全性
- 优化性能和可扩展性
- 完善用户界面和体验

**可交付成果**：
- 生产就绪的系统
- 完整的文档
- 全面的测试套件
- 用户培训材料