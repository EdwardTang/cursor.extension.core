# Oppie.xyz 产品需求文档 (PRD)

## 1. 概述

### 1.1 背景
Oppie.xyz系统的灵感来自NASA的火星车Opportunity，旨在创建一个自主的代码开发助手，能够在用户离开键盘后继续执行开发任务。系统采用"规划→执行→反思→自愈"的循环工作模式，结合了多个先进技术组件。

### 1.2 目标
- 创建一个能够自主执行代码开发任务的系统
- 提供远程访问和控制能力
- 实现实时监控和用户接管功能
- 支持循环中断恢复和checkpoint回滚
- 将AI代码开发能力与物理交互能力结合

### 1.3 用户场景
- 开发者需要在离开键盘后继续执行开发任务
- 用户需要远程监控和控制开发过程
- 系统出现异常行为时，用户需要介入和纠正
- 用户需要回滚到之前的稳定状态

## 2. 系统架构

### 2.1 核心组件

#### 2.1.1 Oppie-Core (Legacy Monolithic Concept)
本节描述的是Oppie-Core在模块化重构前的概念性设计。其核心功能（规划、执行、反思、模板管理）已被分解并由2.3节中定义的多个独立服务实现。
原始设想包括：
* **Planner（基于Codex CLI）**：负责分析当前状态、生成计划和解决方案 (现由PlanningService及相关模块处理)
* **Executor（基于Cursor）**：执行Planner生成的计划，实施代码更改和命令 (现由ExecutionService及相关模块处理)
* **Reflexion组件**：提供语言代理的强化学习能力，使系统能够从过去的执行中学习 (现由ReflexionService处理)
* **Template管理**：使用drop-in_template_A.mdc定义标准格式，促进Planner和Executor之间的交流 (现由各服务间的API契约及ExternalInterfaceService管理)

#### 2.1.2 Remote Desktop服务（基于billd-desk）
- 提供远程访问能力，允许用户从任何位置连接到oppie.xyz系统
- 支持多平台访问（Web、移动设备等）
- 实现安全的远程控制和文件传输

#### 2.1.3 Computer Use Agent（基于UI-TARS-desktop）
- GUI自动化引擎：允许AI控制计算机界面
- 各种Operator（浏览器、桌面应用等）：提供特定应用程序的交互能力
- 视觉识别和分析：理解和响应界面变化

#### 2.1.4 OpenHands集成
- 将Oppie-Core嵌入All-Hands-AI/OpenHands模块化架构中
- 利用OpenHands的事件驱动总线实现Plan-Execute-Reflect循环的可靠触发和状态追踪
- 基于OpenHands的会话管理系统实现任务状态持久化和中断恢复
- 使用OpenHands的多运行时环境支持（本地、Docker、远程等）提高部署灵活性
- 集成OpenHands的错误处理和恢复机制增强系统稳定性

#### 2.1.5 Trajectory Visualizer（移动客户端）
- 实时监控dashboard
- 系统状态和行为可视化
- 允许用户评估AI是否脱轨
- **晨报推送功能**：自动生成并推送每日任务执行摘要，包括完成情况、问题分析和今日预期

##### 2.1.5.1 晨报推送用户故事

**场景**：用户在早晨查看手机，希望快速了解过夜执行的任务状态，而无需登录系统或浏览仪表板。

**用户故事**：
1. **晨报接收**
   - 作为开发者，我希望在每天早上8点收到一份系统晨报推送，以便在开始工作前了解系统状态
   - 推送内容应包含：过去24小时的任务完成情况、发生的问题、今日待执行任务预览
   - 推送应以简洁可视化方式呈现，适合手机屏幕查看

2. **执行摘要**
   - 作为团队负责人，我需要晨报中包含每个任务的执行时间、资源使用和成功率
   - 系统应提供关键指标的趋势比较（与前一天或前一周相比）
   - 对特别长时间运行或高资源消耗的任务应有突出显示

3. **问题分析**
   - 作为开发者，我希望晨报中包含失败任务的简要分析和可能原因
   - 系统应对重复出现的错误模式进行分类和汇总
   - 针对关键问题，提供可点击的深入分析链接

4. **今日预期**
   - 作为项目经理，我希望晨报展示今日计划执行的任务列表和预计完成时间
   - 系统应标识可能的资源冲突或瓶颈
   - 重要里程碑或截止日期应特别突出显示

##### 2.1.5.2 正向场景示例

**早间任务摘要**

小王是一位开发团队负责人，他每天早上8点准时收到Oppie.xyz的晨报推送。今天的推送显示：

1. **昨日执行摘要**：
   - 完成了15个任务，成功率93%（比上周平均高3%）
   - 总执行时间：7.5小时，资源使用率：65%
   - 最耗时任务：数据库迁移脚本（2.5小时）

2. **问题分析**：
   - 1个任务失败：API集成测试（网络超时）
   - 系统自动尝试了3次恢复，最终需要人工干预
   - 推荐操作：检查测试环境网络设置，点击查看详细日志

3. **今日计划**：
   - 计划执行12个任务，预计总时间：6小时
   - 重要里程碑：前端组件库v2.0发布准备（预计14:00完成）
   - 潜在瓶颈：并行构建可能导致CI资源压力，建议调整队列优先级

小王在早餐时浏览这份报告，立即了解到API测试环境的问题。他点击详细日志链接，确认了网络配置错误，并在到达办公室前通过移动客户端发送了修复指令。由于提前了解情况并快速响应，团队避免了工作日开始时的阻塞，保持了开发节奏。

### 2.2 系统流程

#### 2.2.1 正常操作流程
1. 用户提交任务（通过Remote Desktop或移动客户端）
2. Oppie-Core的Planner组件分析任务，生成计划（使用Template A）
3. Executor执行计划，实现代码更改和命令
4. Reflexion组件评估执行结果，提供反馈
5. 系统更新状态，准备下一个循环
6. Trajectory Visualizer提供实时监控，显示系统状态和行为

#### 2.2.2 异常处理流程
1. 当Plan-Execute循环中断时：
   - UI-TARS-desktop检测到中断
   - 提供GUI界面让用户或AI继续循环
   - 重新启动循环或调整计划

2. 当需要回滚到上一个checkpoint时：
   - UI-TARS-desktop提供GUI界面让用户选择checkpoint
   - 系统恢复到选定的checkpoint
   - 重新启动Plan-Execute循环

3. 当系统行为异常时：
   - Trajectory Visualizer检测异常
   - 通知用户并提供接管选项
   - 用户可以直接通过Remote Desktop接管系统

#### 2.2.3 失败处理和回滚用户故事

以下是系统在不同失败场景下的用户故事和自动恢复机制：

1. **工具调用次数限制耗尽**
   - **场景**：Executor在执行过程中达到25次工具调用限制
   - **系统响应**：
     * 自动保存当前状态到checkpoint
     * UI-TARS-desktop检测到限制并触发恢复程序
     * 系统自动重启Executor，从最近的checkpoint继续
   - **用户体验**：任务自动继续执行，用户通过Trajectory Visualizer可看到短暂暂停和恢复通知，无需干预

2. **网络连接失败**
   - **场景**：与OpenAI API或其他外部服务的连接中断
   - **系统响应**：
     * 实现指数退避重试策略（最多尝试5次，间隔时间逐渐增加）
     * 记录失败点和上下文
     * 连接恢复后自动继续操作
   - **用户体验**：系统显示网络重连倒计时，用户可选择等待、手动重试或切换到本地模式

3. **依赖服务不可用**
   - **场景**：OpenHands、UI-TARS或billd-desk等关键服务不响应
   - **系统响应**：
     * 自动切换到预配置的备选方案（如ACTION 8中定义的接口）
     * 保持核心功能运行，降级非关键功能
     * 记录服务恢复后需要同步的操作
   - **用户体验**：收到服务降级通知，可继续使用核心功能，系统提供预计恢复时间

4. **意外工具输出**
   - **场景**：工具返回非预期结果或格式异常的数据
   - **系统响应**：
     * Executor尝试重新格式化或解析输出
     * 如果多次尝试失败，将请求Planner生成替代方案
     * 记录异常模式以供Reflexion组件学习
   - **用户体验**：系统显示工具错误但继续尝试替代方法，用户可查看详细错误日志或提供手动修正

5. **代码执行错误**
   - **场景**：生成的代码导致编译或运行时错误
   - **系统响应**：
     * 捕获错误信息和上下文
     * Reflexion组件分析错误原因
     * Planner生成修复方案
     * Executor实施修复
   - **用户体验**：系统显示错误分析和修复进度，用户可查看分析过程或提供自己的修复建议

6. **系统资源耗尽**
   - **场景**：内存、CPU或磁盘资源不足
   - **系统响应**：
     * 监控系统定期检查资源使用情况
     * 当资源接近阈值时，主动释放非关键资源
     * 如果资源仍然不足，暂停执行并保存checkpoint
   - **用户体验**：收到资源警告，系统建议清理资源或提供自动清理选项，完成后可从checkpoint恢复

7. **Planner-Executor同步失败**
   - **场景**：Template A格式不一致或内容损坏
   - **系统响应**：
     * 检测模板格式不匹配或内容完整性问题
     * 尝试自动修复或回退到上一个有效模板
     * 必要时请求用户确认修复策略
   - **用户体验**：系统显示同步问题并提供修复选项，用户可查看差异并选择修复方法

8. **外部代码仓库变更冲突**
   - **场景**：远程代码库更新导致与当前任务的潜在冲突
   - **系统响应**：
     * 定期检查远程仓库变更
     * 检测到冲突时暂停执行并创建checkpoint
     * 生成冲突分析和解决方案供用户评审
   - **用户体验**：收到变更冲突通知，可查看详细差异，选择合并策略或调整当前任务

9. **长时间运行任务的中断恢复**
   - **场景**：操作系统重启或电源故障导致长时间任务中断
   - **系统响应**：
     * 系统启动时自动检测未完成的任务
     * 提供从最近checkpoint恢复的选项
     * 重建执行环境和上下文
   - **用户体验**：系统重启后显示恢复选项，包括任务状态摘要和预计剩余时间，用户可选择继续或取消

10. **人工干预后的恢复**
    - **场景**：用户临时接管后需要将控制权交回系统
    - **系统响应**：
      * 分析用户干预期间的变更
      * Reflexion组件学习用户操作模式
      * 更新状态和计划以适应新情况
    - **用户体验**：提供"恢复自动模式"选项，显示系统对变更的理解和后续计划，用户可确认或进一步调整

### 2.3 Oppie-Core模块化架构

#### 2.3.1 当前Oppie-Core职责分析

目前Oppie-Core承担了系统中的多种关键职责，导致组件耦合度高、边界模糊，不利于维护和扩展。主要职责包括：

1. **任务规划与分解**：分析用户输入，生成执行计划，将复杂任务分解为步骤序列
2. **上下文管理**：维护代码库和任务相关上下文信息，确保规划和执行的一致性
3. **工具调用与协调**：管理和执行各种工具调用，处理工具调用限制和错误
4. **状态追踪与恢复**：监控执行状态，创建checkpoint，支持任务恢复
5. **模板管理**：管理和应用Template A格式，确保Planner和Executor之间的通信
6. **依赖服务集成**：与UI-TARS、OpenHands等外部服务的集成和通信
7. **反思与学习**：分析执行结果，提取经验教训，改进未来规划
8. **用户交互**：接收用户指令，显示执行状态，提供干预界面

这种职责过于集中的设计导致以下问题：

- 单一组件变更风险大，可能影响多个功能
- 测试难度增加，难以针对特定功能进行隔离测试
- 扩展性受限，难以集成新的规划算法或执行环境
- 团队协作障碍，不同开发者难以并行工作
- 性能优化困难，无法针对特定瓶颈进行优化

#### 2.3.2 模块化架构设计

基于单一职责原则和关注点分离原则，原先的单体Oppie-Core被重构为以下七个核心服务。这些服务共同组成了新的Oppie-Core，取代了2.1.1节中描述的旧概念模型。每个服务都有明确定义的职责和接口，以提高系统的可维护性、可扩展性和可靠性。

![Oppie-Core模块化架构](./docs/images/oppie_modular_architecture.png)
(*注意: `oppie_modular_architecture.png` 文件待创建并放置于 `./docs/images/` 目录下*)

1. **TaskManagementService（任务管理服务）**
   - **核心职责**：
     * 处理用户输入的任务请求
     * 管理任务生命周期（创建、暂停、恢复、取消）
     * 维护任务队列和优先级
     * 提供任务状态查询接口
   - **主要交互**：
     * 接收来自用户界面的任务请求
     * 将任务分配给PlanningService进行规划
     * 向监控系统报告任务状态变更

2. **PlanningService（规划服务）**
   - **核心职责**：
     * 分析任务需求和上下文
     * 生成详细的执行计划（步骤序列）
     * 处理计划调整和动态重规划
     * 集成反馈数据改进规划
   - **主要交互**：
     * 从TaskManagementService接收任务
     * 从ContextManagementService获取上下文信息
     * 将计划传递给ExecutionService执行
     * 从ReflexionService接收学习反馈

3. **ExecutionService（执行服务）**
   - **核心职责**：
     * 执行PlanningService生成的计划
     * 管理工具调用（包括与Codex CLI/Cursor的交互）
     * 实施代码更改和命令执行
     * 处理执行过程中的错误和异常
   - **主要交互**：
     * 从PlanningService接收执行计划
     * 与ContextManagementService交互获取和更新上下文
     * 与ToolIntegrationService协调工具调用
     * 向StateTrackingService报告执行状态和结果

4. **ContextManagementService（上下文管理服务）**
   - **核心职责**：
     * 维护代码库状态、文件内容等上下文信息
     * 提供上下文查询和更新接口
     * 管理不同任务和会话的上下文隔离
   - **主要交互**：
     * 为PlanningService提供规划所需的上下文
     * 为ExecutionService提供执行所需的上下文
     * 接收来自FileSystemMonitorService的文件变更通知

5. **StateTrackingService（状态追踪与恢复服务）**
   - **核心职责**：
     * 监控Plan-Execute-Reflect循环的整体状态
     * 创建和管理任务执行的checkpoint
     * 支持从checkpoint恢复任务
     * 记录详细的执行轨迹（logs, metrics）
   - **主要交互**：
     * 接收来自各服务的状态更新
     * 与CheckpointStorageService交互存储和检索checkpoint
     * 为ReflexionService提供执行历史数据

6. **ReflexionService（反思与学习服务）**
   - **核心职责**：
     * 分析执行结果、错误、用户反馈
     * 生成经验教训和改进建议
     * 更新规划策略或知识库
   - **主要交互**：
     * 从StateTrackingService获取执行历史和结果
     * 将学习到的知识反馈给PlanningService
     * 可能与外部知识库或模型交互

7. **ExternalInterfaceService（外部接口服务）**
   - **核心职责**：
     * 管理与外部工具和服务的集成（UI-TARS, OpenHands, billd-desk, Codex CLI, Cursor等）
     * 处理API调用、数据格式转换、认证授权
     * 管理Template A等通信模板的适配与演进
   - **主要交互**：
     * 为ExecutionService提供工具调用能力
     * 与Remote Desktop服务和Trajectory Visualizer通信
     * 封装与OpenHands事件总线的交互

#### 2.3.3 接口契约原型

*详细的OpenAPI规范将在后续迭代中提供。*

**PlanningService API (Simplified)**
```yaml
openapi: 3.0.0
info:
  title: PlanningService API
  version: v1
paths:
  /plan:
    post:
      summary: Generate a new plan for a task
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                taskId:
                  type: string
                context:
                  type: object # Detailed context structure TBD
      responses:
        '200':
          description: Plan generated successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  planId:
                    type: string
                  steps:
                    type: array
                    items:
                      type: object # Step structure TBD
```

**ExecutionService API (Simplified)**
```yaml
openapi: 3.0.0
info:
  title: ExecutionService API
  version: v1
paths:
  /execute:
    post:
      summary: Execute a given plan
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                planId:
                  type: string
      responses:
        '200':
          description: Plan execution started
          content:
            application/json:
              schema:
                type: object
                properties:
                  executionId:
                    type: string
                  status:
                    type: string
  /execution/{executionId}/status:
    get:
      summary: Get execution status
      parameters:
        - name: executionId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Execution status
          # ... schema for status ...
```

*（其他服务API原型待补充）*

### 2.4 Checkpoint和恢复策略

#### 2.4.1 Checkpoint粒度
- **细粒度Checkpoint**：在每个Plan-Execute-Reflect循环的关键步骤后（例如，计划生成后、工具调用前/后、代码提交后）。
- **粗粒度Checkpoint**：在用户定义的里程碑或长时间操作（例如，完成一个主要功能模块）后。

#### 2.4.2 Checkpoint数据结构
```json
{
  "checkpointId": "uuid",
  "timestamp": "iso_datetime",
  "taskId": "uuid",
  "goal": "current_goal_description",
  "cycleNumber": "integer",
  "planState": { // State of PlanningService
    "currentPlanId": "uuid",
    "planHistory": [],
    // ... other planning related state
  },
  "executionState": { // State of ExecutionService
    "lastExecutedStepId": "uuid",
    "toolCallHistory": [],
    "pendingActions": [],
    // ... other execution related state
  },
  "contextState": { // State of ContextManagementService
    "fileSystemSnapshot": { // Or references to version control commits
      "file_path_1": "checksum_or_version_id",
      "file_path_2": "checksum_or_version_id"
    },
    "environmentVariables": {},
    // ... other context related state
  },
  "reflexionState": { // State of ReflexionService
    "learnings": [],
    "feedbackLoopData": {}
    // ... other reflexion related state
  },
  "mcpToolState": { // State of any MCP tools if applicable
      "cursorState": {
          "tool_call_budget_remaining": "integer",
          "session_id": "string"
      }
  }
}
```

#### 2.4.3 Checkpoint存储
- **本地存储**：用于快速恢复和开发测试。
- **远程持久化存储**（例如，S3、数据库）：用于生产环境和跨会话恢复。

#### 2.4.4 恢复流程
1. 用户或系统触发恢复请求，指定checkpoint ID或"最新"。
2. StateTrackingService从存储中加载checkpoint数据。
3. 各相关服务（Planning, Execution, Context, Reflexion）根据checkpoint数据重建其内部状态。
4. 系统从中断点继续执行，或根据需要调整计划。

### 2.5 Reflexion → Planner反馈循环

#### 2.5.1 数据流
1. **ExecutionService** 执行计划，记录结果、错误、工具输出。
2. **StateTrackingService** 收集这些执行数据，形成执行轨迹。
3. **ReflexionService** 分析执行轨迹：
   - 识别成功/失败模式。
   - 评估计划的有效性。
   - 提取可操作的见解（例如，"当使用X工具处理Y类型文件时，增加Z参数可提高成功率"）。
4. **ReflexionService** 将这些结构化的"经验教训"或"启发式规则"传递给 **PlanningService**。
5. **PlanningService** 在生成新计划或调整现有计划时，整合这些反馈，以提高未来任务的成功率和效率。

#### 2.5.2 反馈数据结构 (示例)
```json
{
  "feedbackId": "uuid",
  "timestamp": "iso_datetime",
  "sourceExecutionId": "uuid",
  "type": "heuristic_improvement | error_pattern_avoidance | efficiency_tip",
  "severity": "high | medium | low", // Impact on future planning
  "description": "User-readable summary of the learning.",
  "conditions": [ // When this feedback is applicable
    { "variable": "tool_name", "operator": "equals", "value": "my_linter" },
    { "variable": "file_type", "operator": "equals", "value": ".py" }
  ],
  "recommendation": { // Actionable advice for the planner
    "action_type": "add_parameter | modify_step_order | use_alternative_tool",
    "details": {
      "parameter_name": "--fix-imports",
      "tool_to_use": "alternative_formatter"
      // ... other details
    }
  },
  "confidence_score": 0.85 // How confident the ReflexionService is in this feedback
}
```

### 2.6 外部依赖接口

#### 2.6.1 与OpenHands的集成接口
- **事件订阅**：Oppie-Core将订阅OpenHands事件总线上的相关事件（例如，任务开始、任务结束、错误事件）。
- **事件发布**：Oppie-Core将通过OpenHands事件总线发布自身的状态更新和关键事件。
- **服务发现**：利用OpenHands的服务注册和发现机制。
- **配置管理**：共享或适配OpenHands的配置管理方案。

#### 2.6.2 与UI-TARS-desktop的接口
- **命令与控制API**：用于触发GUI自动化操作。
- **状态查询API**：获取当前桌面或应用程序状态。
- **回调机制**：UI-TARS在完成操作或遇到事件时通知Oppie-Core。

#### 2.6.3 与billd-desk的接口
- **会话管理API**：启动、停止、查询远程桌面会话。
- **安全凭证管理**：集成billd-desk的认证授权机制。

## 3. 功能需求

### 3.1 核心功能
- [ ] ... (待补充详细功能点)

### 3.2 物理交互能力
- [ ] ... (待补充详细功能点)

## 4. 非功能需求

### 4.1 性能
- [ ] ...

### 4.2 可靠性
- **自动恢复率**：系统能够从95%以上的常见故障（如工具调用限制、网络错误）中自动恢复。
- **恢复精度**：从checkpoint恢复后，系统能够准确继续之前的任务，无数据丢失。

### 4.3 安全性
- [ ] ...

### 4.4 可扩展性
- [ ] ...

### 4.5 可用性
- [ ] ...

## 5. Phased Roadmap for Modular Architecture

This roadmap outlines the planned incremental rollout of the seven core Oppie-Core services. The goal is to transition from the current monolithic concept to a fully modular architecture by the end of Q4 2025. Each phase will focus on developing, testing, and integrating a subset of these services, allowing for iterative feedback and risk mitigation.

### Q3 2025: Foundational Services & Core Loop

**Goal:** Establish the basic infrastructure for modularity and implement the core task processing loop with initial versions of key services.

*   **Milestone 5.1: TaskManagementService v1 (Due: July 31, 2025)**
    *   **Specific:** Implement core task lifecycle management (create, queue, basic status tracking). Define API for task submission.
    *   **Measurable:** API endpoints for task creation and status query are functional. 90% unit test coverage.
    *   **Achievable:** Focus on essential CRUD operations and in-memory task queuing.
    *   **Relevant:** Foundational for all subsequent task processing.
    *   **Time-bound:** End of July 2025.
    *   **Dependencies:** None.

*   **Milestone 5.2: ContextManagementService v1 (Due: Aug 15, 2025)**
    *   **Specific:** Implement basic context storage (e.g., file paths, working directory) and retrieval for a single active task. Define initial API.
    *   **Measurable:** API for setting and getting basic task context. Can store and retrieve context for 5 concurrent simulated tasks.
    *   **Achievable:** Focus on string-based context data, no complex file snapshotting yet.
    *   **Relevant:** Essential for Planning and Execution services.
    *   **Time-bound:** Mid-August 2025.
    *   **Dependencies:** TaskManagementService v1 (for associating context with tasks).

*   **Milestone 5.3: PlanningService v1 (Due: Aug 31, 2025)**
    *   **Specific:** Implement a basic planner that can take a task description and generate a fixed, pre-defined sequence of steps (no dynamic planning). Integrate with TaskManagementService and ContextManagementService.
    *   **Measurable:** Can generate a plan for 3 predefined task types. Plan output adheres to a defined schema.
    *   **Achievable:** Leverage existing Codex CLI capabilities for plan generation logic if possible, focusing on service integration.
    *   **Relevant:** Core of the "Plan" phase.
    *   **Time-bound:** End of August 2025.
    *   **Dependencies:** TaskManagementService v1, ContextManagementService v1.

*   **Milestone 5.4: ExecutionService v1 (Due: Sep 15, 2025)**
    *   **Specific:** Implement an executor that can take a simple, pre-defined plan from PlanningService and execute a sequence of shell commands. Basic error reporting.
    *   **Measurable:** Can execute a plan of 3 shell commands successfully. Reports success/failure of each step.
    *   **Achievable:** Focus on direct command execution, no complex tool integration yet.
    *   **Relevant:** Core of the "Execute" phase.
    *   **Time-bound:** Mid-September 2025.
    *   **Dependencies:** PlanningService v1.

*   **Milestone 5.5: Initial Loop Integration (Due: Sep 30, 2025)**
    *   **Specific:** Demonstrate a basic end-to-end flow: Task submitted via TaskManagementService, planned by PlanningService (using ContextManagementService), and executed by ExecutionService.
    *   **Measurable:** Successful execution of one simple, predefined task (e.g., "create a file and write 'hello' into it").
    *   **Achievable:** Focus on successful path, minimal error handling.
    *   **Relevant:** Validates the core interoperability of foundational services.
    *   **Time-bound:** End of Q3 2025.
    *   **Dependencies:** All v1 services above.

### Q4 2025: Enhancing Core Loop & Adding Reflexion

**Goal:** Enhance the core loop with more sophisticated state management and tool integration, and introduce the learning capabilities of the ReflexionService.

*   **Milestone 5.6: StateTrackingService v1 & Checkpointing (Due: Oct 31, 2025)**
    *   **Specific:** Implement basic state tracking for task progress. Implement细粒度checkpointing after each plan step execution, storing to local disk. Basic recovery from the last checkpoint.
    *   **Measurable:** Checkpoints are created for each step. A task can be manually interrupted and resumed from the last checkpoint for one defined scenario.
    *   **Achievable:** Focus on local checkpoint storage and simple state variables.
    *   **Relevant:** Critical for reliability and resilience.
    *   **Time-bound:** End of October 2025.
    *   **Dependencies:** ExecutionService v1.

*   **Milestone 5.7: ExternalInterfaceService v1 (Due: Nov 15, 2025)**
    *   **Specific:** Integrate ExecutionService with at least one actual external tool (e.g., a linter via shell command, or a simplified Codex CLI call). Abstract tool interaction via this new service.
    *   **Measurable:** ExecutionService can successfully invoke one external tool via ExternalInterfaceService.
    *   **Achievable:** Start with simple, well-behaved tools.
    *   **Relevant:** Enables interaction with the broader development ecosystem.
    *   **Time-bound:** Mid-November 2025.
    *   **Dependencies:** ExecutionService v1.

*   **Milestone 5.8: ReflexionService v1 (Due: Nov 30, 2025)**
    *   **Specific:** Implement a basic ReflexionService that can analyze simple execution logs (success/failure of steps) from StateTrackingService and generate at least one type of simple feedback (e.g., "step X failed N times").
    *   **Measurable:** For a predefined execution trace with failures, ReflexionService generates a correct feedback report.
    *   **Achievable:** Focus on parsing structured log data, no complex learning algorithms yet.
    *   **Relevant:** Introduces the "Reflect" part of the cycle.
    *   **Time-bound:** End of November 2025.
    *   **Dependencies:** StateTrackingService v1.

*   **Milestone 5.9: Feedback Integration & Enhanced Planning (Due: Dec 15, 2025)**
    *   **Specific:** PlanningService v2 incorporates simple feedback from ReflexionService v1 to slightly modify a plan (e.g., retry a failed step).
    *   **Measurable:** PlanningService can adjust a plan based on one type of feedback from ReflexionService for a defined scenario.
    *   **Achievable:** Simple rule-based plan adjustment.
    *   **Relevant:** Closes the Plan-Execute-Reflect loop.
    *   **Time-bound:** Mid-December 2025.
    *   **Dependencies:** PlanningService v1, ReflexionService v1.

*   **Milestone 5.10: Q4 Review & Next Phase Planning (Due: Dec 31, 2025)**
    *   **Specific:** Comprehensive review of Q3-Q4 progress, system stability, and feature completeness against this roadmap. Plan for Phase 2 (H1 2026) focusing on advanced features, robustness, and wider tool integration.
    *   **Measurable:** Review meeting conducted, report produced, H1 2026 draft plan created.
    *   **Achievable:** Allocate dedicated time for review and planning.
    *   **Relevant:** Ensures continuous improvement and strategic alignment.
    *   **Time-bound:** End of Q4 2025.
    *   **Dependencies:** All Q3/Q4 milestones.

## 6. 路线图与里程碑

*(本节内容待ACTION 2中完成)*

## 7. 测试与验证策略

*(本节内容待ACTION 4中完成)*

## 8. 附录

### 7.1 术语表
- **Oppie-Core**: 系统的核心规划、执行、反思引擎。
- **Planner**: Oppie-Core中负责生成计划的组件 (模块化后为PlanningService)。
- **Executor**: Oppie-Core中负责执行计划的组件 (模块化后为ExecutionService)。
- **Reflexion**: Oppie-Core中负责从经验中学习的组件 (模块化后为ReflexionService)。
- **Checkpoint**: 系统在特定时间点的完整状态快照，用于恢复。
- **UI-TARS**: GUI自动化工具。
- **OpenHands**: 更广泛的AI协作和模块化执行框架。
- **billd-desk**: 远程桌面服务。

### 7.2 参考资料
- [NASA Opportunity Rover](https://www.nasa.gov/rovers/opportunity)
- [Codex CLI Documentation](...)
- [Cursor Documentation](...)
- [OpenHands GitHub](https://github.com/All-Hands-AI/OpenHands)

---
*PRD版本: 0.2.0*
*最后更新: 2025-05-08*
