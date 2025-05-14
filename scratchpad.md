# Lessons Learned

## User Specified Lessons

- Include info useful for debugging in the program output.
- Read the file before you try to edit it.
- Due to Cursor's limit, when you use `git` and `gh` and need to submit a multiline commit message, first write the message in a file, and then use `git commit -F <filename>` or similar command to commit. And then remove the file. Include "[Cursor] " in the commit message and PR title.

## Engineering Best Practices

- For search results, ensure proper handling of different character encodings (UTF-8) for international queries
- Add debug information to stderr while keeping the main output clean in stdout for better pipeline integration
- When using seaborn styles in matplotlib, use 'seaborn-v0_8' instead of 'seaborn' as the style name due to recent seaborn version changes
- Use `chatgpt-4o-latest` as the model name for OpenAI. It is the latest GPT model and has vision capabilities as well. `o1` is the most advanced and expensive model from OpenAI. Use it when you need to do reasoning, planning, or get blocked.
- Use `claude-3.7-sonnet` as the model name for Claude. It is the latest Claude model and has vision capabilities as well.
- When encountering unexpected execution behavior (like hangs or wrong logic) with build tools (e.g., `./gradlew run`), double-check the build configuration file (e.g., `build.gradle`) for the correct entry point (`mainClass`) setting, as temporary changes or misconfigurations can lead to running unintended code.
- o3 and o4-mini are the most advanced models from OpenAI. Avoid using them for coding for now due to severe hallucinations.

## Distributed Systems Development

- 测试驱动开发（TDD）过程中，先创建失败的测试，然后实现最小的代码使测试通过，最后重构代码改进设计，这样可以确保代码的可靠性和质量。
- 在分布式系统中，使用纯数据结构（如dataclass）作为消息类型可以简化序列化和跨进程通信。
- 在实现监控和恢复机制时，要注意避免误触发（假阳性）和保持高响应性。
- 对于复杂的异步测试，可以考虑使用同步模拟（mock）替代，简化测试逻辑并提高测试的可靠性。
- 在分布式系统中处理状态同步时，应使用深拷贝而非浅拷贝，避免引用问题导致的意外状态更改。
- 事件处理机制（event handling）是实现松耦合组件间通信的有效方式，特别适用于分布式系统中的状态变化通知。
- 在高延迟网络环境下，使用批处理和自适应心跳可显著提高系统性能，批处理可减少30-40%的延迟。
- 性能测试应覆盖不同网络条件（延迟、抖动、丢包），以全面了解系统在各种环境下的表现。
- 使用配置驱动开发，可以轻松调整和优化系统行为，无需修改代码。
- 在设计无状态服务时应采用JWT等认证方式，可确保服务实例之间无需共享会话状态，提高系统的可伸缩性和可靠性。
- 消息队列是处理系统组件间通信的关键模式，尤其是在面对网络不稳定或组件临时不可用时，能提供可靠的消息传递保证。
- 在处理WebSocket长连接时，应实现心跳机制检测连接状态，并采用指数退避算法进行重连，提高系统的稳定性。
- JWT认证机制在分布式系统中特别有用，通过将令牌负载中包含必要的用户和会话信息，减少了对中心化状态存储的依赖。
- 在设计分布式消息系统时，消息元数据（如消息ID、时间戳、关联ID）与消息内容同等重要，它们确保消息可以被正确路由、去重和追踪。
- 在进行WebSocket和REST API测试时，使用pytest-asyncio和异步客户端模拟能显著简化测试代码，特别是对于并发场景的测试。

## Architecture & Documentation Practices

- 在实现WebSocket连接管理器时，为不同目标（会话、用户、设备）提供专门的消息发送方法可以简化上层应用逻辑，提高代码可读性。
- 设计模式中的"观察者模式"非常适合实现异步消息路由系统，路由器充当观察者通知中心，各个消息处理器作为观察者订阅特定类型的消息。
- 使用asyncio.Queue构建异步消息队列是处理并发WebSocket连接的高效方法，可以避免阻塞主事件循环，同时确保消息按顺序处理。
- 为JWT认证系统实现访问令牌/刷新令牌分离机制可以显著提高安全性，允许短期访问令牌降低风险，同时长期刷新令牌减少用户重新认证的频率。
- 使用半自动化架构决策记录(ADR)工作流，可以捕获关键技术决策的背景、选择和影响，有效提升项目的长期可维护性和知识传承。
- 将ADR集成到Plan-Execute循环中，可以确保所有重要决策的可追溯性，帮助新团队成员快速了解历史决策原因。
- 在多文档系统架构中保持文档一致性非常重要，应将共享常量和指标定义在单一来源，其他文档引用它们，避免文档漂移和不一致。
- 使用可追溯性矩阵确保每个需求都有对应的设计元素和测试，提高系统设计的完整性和可验证性。
- 在里程碑规划中，要确保各设计文档中的范围、优先级和交付内容保持一致，避免混淆或设置不切实际的期望。
- 在正则表达式处理结构化文本时，应当小心定义捕获组的边界，特别是对于多行文本，使用`[^\n]+`而非`[^\[]+`可以防止过度贪婪匹配导致的数据泄漏问题。
- 系统设计中的"混合恢复策略"是一种优雅的降级机制，通过支持新旧两种恢复途径（如OpenHands事件处理和传统的Agent S），实现平滑迁移，确保系统弹性。
- 在系统迁移过程中采用"陌生人模式"（Strangler Fig Pattern）可以降低风险，通过在保留旧系统的基础上，将新功能用新接口包装后逐步替换，实现平稳过渡。
- 特性标志（Feature Flags）是实现渐进式发布的关键工具，特别是"影子模式"（Shadow Mode）允许在不影响当前功能的情况下，验证新功能的正确性。
- 事件驱动架构中，使用中央事件总线（Event Bus）进行消息路由可以有效解耦组件，同时通过事件回放（Event Replay）简化测试并提高系统的可观测性。
- 平滑迁移策略应该包含四个关键部分：特性标志控制、结果比较机制、自动回退路径和可观测性工具。这样可以确保系统在迁移过程中保持稳定，同时提供足够的数据来评估新旧实现的差异。

# Multi-Agent Scratchpad

## 项目概述与目标

Oppie.xyz 是一个允许用户从手机启动并监控Cursor任务的系统。该系统需要能够自动恢复25工具调用限制或者网络错误等问题，无需人工干预。

主要目标：
- 创建一个能够自主执行代码开发任务的AI助手系统
- 实现Plan-Execute-Reflect循环工作模式，支持自我修正
- 提供远程监控和控制能力
- 支持循环中断恢复和checkpoint回滚
- 结合AI代码开发能力与GUI自动化（近期）和物理交互能力（远期）


## 关键挑战

- **工具调用限制**：克服25次工具调用限制，实现无缝恢复与继续执行
- **依赖服务稳定性**：应对UI-TARS、OpenHands等外部依赖可能的不稳定或不可用场景
- **状态一致性**：确保Plan-Execute-Reflect循环中的状态持久化和恢复机制可靠有效
- **错误恢复与自愈**：系统能够检测并从各种故障中自动恢复，包括网络错误、工具限制、代码执行错误等
- **模块化与解耦**：重构Oppie-Core为模块化架构，确保各组件职责单一与松耦合
- **Reflexion反馈循环**：建立有效的反馈机制，使系统能够从执行中学习并优化未来规划

## 可验证成功标准

- **自动恢复率**：系统能够从95%以上的常见故障（如工具调用限制、网络错误）中自动恢复
- **任务完成率**：80%以上的任务能够无需人工干预下自动完成
- **恢复精度**：从checkpoint恢复后，系统能够准确继续之前的任务，无数据丢失
- **响应时间**：系统对异常的检测和响应时间不超过5秒
- **用户满意度**：90%以上的用户反馈系统的可靠性和自主性令人满意


## 当前状态与进展

**当前状态**: PRD文档已经过多轮完善，当前处于最终审查和整合阶段，即将提交团队Review。

**最新进展**: 
- 完成了详细的失败处理和回滚用户故事，覆盖10类失败场景及自动恢复机制
- 定义了完整的Checkpoint和恢复策略，包括粒度、数据结构、存储和恢复流程
- 定义了Reflexion → Planner反馈循环的数据流和结构
- 重构了Oppie-Core为7个核心模块的模块化架构，明确了各模块职责和交互
- 为PlanningService和ExecutionService定义了详细接口契约
- 为Oppie与OpenHands的集成定义了详细接口契约及备选方案
- 创建了模块化架构的SVG可视化图表

**当前阻碍**:
- 尚未创建完整的可视化Oppie-Core架构示意图（SVG已创建，但需要转换为PNG）
- 缺少详细的路线图和里程碑定义，特别是模块化架构的实现阶段
- 缺少PRD中各部分的一致性和整体性验证
- 未定义详细的测试和验证策略
- 物理交互能力的近期和远期边界需要更明确的定义

**下一步计划**:
- 完成PRD的最终审查和整合，特别关注路线图定义、测试策略和整体一致性
- 解决架构图PNG格式转换问题
- 定义详细的实现路线图和里程碑
- 验证PRD各部分的一致性
- 准备团队Review环节


## 已完成的任务与里程碑

- ✅ 初始PRD草案评估
- ✅ 产出五大维度改进建议（愿景一致性、技术可行性、用户故事完整性、流程闭环、模块边界）
- ✅ 详细失败处理和回滚用户故事定义
- ✅ Checkpoint和恢复策略规范
- ✅ Reflexion → Planner反馈循环设计
- ✅ Oppie-Core模块化架构设计
- ✅ 核心服务接口契约定义
- ✅ 外部依赖接口定义

## 关键组件开发进度

| 组件名称 | 状态 | 完成度 | 详细说明 |
|---------|------|-------|---------|
| Oppie-Core | 设计阶段 | 75% | 完成模块化架构设计，接口契约定义；待完成路线图和测试策略 |
| Remote Desktop服务 | 需求分析 | 60% | 已定义基本接口和功能；待明确安全性要求和性能指标 |
| Computer Use Agent | 需求分析 | 70% | 已明确近期GUI自动化范围；待细化具体操作符和视觉识别能力 |
| OpenHands集成 | 设计阶段 | 85% | 已定义详细接口契约和备选方案；待验证与模块化架构的整合 |
| Trajectory Visualizer | 需求分析 | 50% | 基本功能已定义；需详细设计可视化指标和监控维度 |

## 优化成果

- **架构优化**：通过模块化设计，将Oppie-Core解耦为7个核心服务，降低了单点变更风险，提高了系统可维护性和可扩展性
- **错误处理**：设计了多层次的错误处理机制和自动恢复策略，预期将大幅提高系统在面对各类故障时的韧性
- **状态管理**：通过多粒度checkpoint策略，平衡了恢复精度和性能开销，增强了系统的可靠性
- **反馈学习**：设计了结构化的Reflexion反馈循环，使系统能够从经验中学习并持续优化

## 测试策略

### 测试层次结构
- **单元测试**：覆盖Oppie-Core和各组件的状态转换和边界条件
- **服务级集成测试**：验证组件间协作，
- **端到端测试**：模拟网络和工具限制条件下的完整流程测试
- **性能测试**：在不同网络条件下评估系统性能和优化效果

### 测试矩阵

| 组件 | 测试类型 | 测试场景 | 测试文件 | 状态 |
|------|---------|---------|---------|------|
|

### 后续里程碑


## ADR Hisotry (only for understand the heritage of system designs , dont need to follow)

## Multi-Agent Scratchpad

### 项目状态

我们正在开发oppie.xyz系统，这是一个集成了e2b-dev/desktop、Cursor IDE、OpenAI CodexCLI、e2b-dev/surf和Reflexion等组件的系统。该系统允许用户在本地主机中部署开源Sandbox Desktop，进行远程的Open Computer Use，并具有Plan-Execute-Reflect循环功能。

**当前核心任务**: 根据用户提供的项目文档规则序列，逐步生成项目相关文档。目前已完成 `@1.proj-interview-questionaire-generation.mdc` 的初步执行。

### 最近进展

1.  完成了对e2b-dev/desktop、e2b-dev/infra、e2b-dev/surf、Reflexion、OpenHands等关键组件的初步研究。
2.  创建并完善了项目需求访谈问卷 (`.cursor/proj_interview_qa.md`)，从最初的32个问题扩展到59个问题，涵盖了系统的多个关键方面。
3.  设计了初步的系统架构，包括基础层、应用层、核心层(oppie-core)、集成层、客户端层以及监控和控制层。
4.  **Cycle 0 执行**: Planner 尝试预填写 `.cursor/proj_interview_qa.md`，但因文件读取问题失败。
5.  **Cycle 1 执行**: Executor 向 Planner 报告了 Cycle 0 的失败。Planner 调整了策略，计划分步读取文件，并请求 Executor 提供文件内容。
6.  **Cycle 2 执行**: Executor 提供了 `.cursor/proj_interview_qa.md`, `.cursor/news_letter.md`, 和 `.cursor/product_market_fit.md` 的内容给 Planner。Planner 成功处理了这些内容，并生成了预填写的问卷。Executor 已将此更新后的问卷保存回 `.cursor/proj_interview_qa.md`。

### 当前阻碍

1.  缺乏直接的用户反馈，需要采用其他方法来确定系统需求和设计约束（此阻碍通过 Planner 预填写问卷得到部分缓解）。

### 下一步计划

1.  根据用户指定的项目文档生成顺序 (`@2.prd_generation.mdc`, `@3.backend_architecture_doc_generation.mdc`, 等)，准备启动下一个文档（即 `prd.md`，对应 `@2.prd_generation.mdc` 规则）的生成工作。
2.  **Cycle 3 启动**: Executor 将向 Planner 发出新请求，基于已完成的 `@proj_interview_qa.md` (现在包含了答案) 和相关的项目资料，指导 Planner 开始生成 `prd.md`。
3.  持续细化系统架构设计，并在后续文档生成过程中逐步完善。

### 关键决策与理由

1.  选择e2b-dev/desktop作为基础设施：提供了成熟的虚拟桌面环境和安全的沙箱隔离。
2.  集成Reflexion框架：通过语言反馈机制改进AI代理性能，无需更新模型权重。
3.  采用Plan-Execute-Reflect循环：结合CodexCLI、`drop-in_template_A` 和 Reflexion，创建一个能够从经验中学习的系统。
4.  **文档生成流程**: 遵循用户指定的文档生成规则序列，确保项目文档的系统性和完整性。

