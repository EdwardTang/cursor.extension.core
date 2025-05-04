# Lessons

## User Specified Lessons

- Include info useful for debugging in the program output.
- Read the file before you try to edit it.
- Due to Cursor's limit, when you use `git` and `gh` and need to submit a multiline commit message, first write the message in a file, and then use `git commit -F <filename>` or similar command to commit. And then remove the file. Include "[Cursor] " in the commit message and PR title.

## Cursor learned

- For search results, ensure proper handling of different character encodings (UTF-8) for international queries
- Add debug information to stderr while keeping the main output clean in stdout for better pipeline integration
- When using seaborn styles in matplotlib, use 'seaborn-v0_8' instead of 'seaborn' as the style name due to recent seaborn version changes
- Use `chatgpt-4o-latest` as the model name for OpenAI. It is the latest GPT model and has vision capabilities as well. `o1` is the most advanced and expensive model from OpenAI. Use it when you need to do reasoning, planning, or get blocked.
- Use `claude-3.7-sonnet` as the model name for Claude. It is the latest Claude model and has vision capabilities as well.
- When encountering unexpected execution behavior (like hangs or wrong logic) with build tools (e.g., `./gradlew run`), double-check the build configuration file (e.g., `build.gradle`) for the correct entry point (`mainClass`) setting, as temporary changes or misconfigurations can lead to running unintended code.
- o3 and o4-mini are the most advanced models from OpenAI. Avoid using them for coding for now due to severe hallucinations. 
- 测试驱动开发（TDD）过程中，先创建失败的测试，然后实现最小的代码使测试通过，最后重构代码改进设计，这样可以确保代码的可靠性和质量。
- 在分布式系统中，使用纯数据结构（如dataclass）作为消息类型可以简化序列化和跨进程通信。
- 在实现监控和恢复机制时，要注意避免误触发（假阳性）和保持高响应性。

# Multi-Agent Scratchpad

## Background and Motivation

Oppie Remote Cursor Control Mesh (RCCM)是一个允许用户从手机启动并监控Cursor任务的系统。该系统需要能够自动恢复25工具调用限制和缺少Template A等问题，无需人工干预。

## Key Challenges and Analysis

- 确保系统在Cursor达到25工具调用限制时能自动恢复
- 监测Assistant Bubble缺少Template A的情况并恢复
- 支持从移动设备远程触发和监控任务
- 维持P95推送延迟<500ms的性能要求
- 实现≥40%的无人值守成功率
- 在多节点环境中保持状态一致性和解决冲突
- 设计松散耦合的组件以便于测试和扩展

## RCCM测试策略

### 测试层次结构
- **单元测试**：覆盖CursorCore和各组件的状态转换和边界条件
- **服务级集成测试**：验证组件间协作，特别是MeshAdapter节点间的同步
- **端到端测试**：模拟网络和工具限制条件下的完整流程测试

### 关键测试场景
1. **工具调用限制**：验证系统在达到25工具调用限制时能否正确检测并恢复
2. **模板缺失处理**：确保系统能检测到缺少Template A并采取适当行动
3. **网络故障恢复**：测试在网络中断后的重连和状态同步能力
4. **性能指标达成**：验证系统能否满足P95推送延迟<500ms的要求

### 测试工具和框架
- ToolProxy：包装所有MCP调用，计数并可预设"配额耗尽"响应
- 确定性事件总线：用于可重复的集成测试
- 模拟器/假对象：模拟网络层和MCP工具调用

### 测试矩阵

| 组件 | 测试类型 | 测试场景 | 测试文件 | 状态 |
|------|---------|---------|---------|------|
| CursorCore | 单元 | 激活和IPC服务器创建 | tests/unit/test_cursor_core.py | 绿色（已实现） |
| CursorCore | 单元 | 消息处理（runPlan, chat, recover）| tests/unit/test_cursor_core.py | 绿色（已实现） |
| CursorCore | 单元 | execute_plan调用PocketFlow | tests/unit/test_cursor_core.py | 绿色（已实现） |
| CursorCore | 单元 | 事件发送（webview, sidecar）| tests/unit/test_cursor_core.py | 绿色（已实现） |
| CursorCore | 单元 | 25工具调用限制处理 | tests/unit/test_cursor_core.py | 绿色（已实现） |
| ToolProxy | 单元 | 工具调用计数 | tests/unit/test_tool_proxy.py | 绿色（已实现） |
| ToolProxy | 单元 | 调用限制强制执行 | tests/unit/test_tool_proxy.py | 绿色（已实现） |
| ToolProxy | 单元 | 预设配额耗尽状态 | tests/unit/test_tool_proxy.py | 绿色（已实现） |
| ToolProxy | 单元 | 多代理共享计数 | tests/unit/test_tool_proxy.py | 绿色（已实现） |
| MeshAdapter | 集成 | 消息传播 | tests/integration/test_mesh_adapter.py | 黄色（基本框架实现） |
| MeshAdapter | 集成 | 节点断开重连 | tests/integration/test_mesh_adapter.py | 黄色（基本框架实现） |
| MeshAdapter | 集成 | 状态同步 | tests/integration/test_mesh_adapter.py | 黄色（基本框架实现） |
| MeshAdapter | 集成 | 冲突解决 | tests/integration/test_mesh_adapter.py | 黄色（基本框架实现） |
| MeshAdapter | 集成 | 心跳机制 | tests/integration/test_mesh_adapter.py | 黄色（基本框架实现） |
| 恢复机制 | E2E | 25工具调用限制恢复 | tests/e2e/test_recovery_mechanism.py | 绿色（已实现） |
| 恢复机制 | E2E | 缺少Template A恢复 | tests/e2e/test_recovery_mechanism.py | 黄色（基本框架实现） |
| 恢复机制 | E2E | 端到端恢复工作流 | tests/e2e/test_recovery_mechanism.py | 黄色（基本框架实现） |
| 恢复机制 | E2E | 恢复性能（<250ms） | tests/e2e/test_recovery_mechanism.py | 黄色（基本框架实现） |
| 恢复机制 | E2E | 假阳性率（<1%） | tests/e2e/test_recovery_mechanism.py | 绿色（已实现） |

### 已解决的问题与下一步计划

1. **共享类型定义**：已实现types.py，定义了Msg、Step、ExecResult等数据结构。
   - 下一步：根据实际使用情况扩展和优化类型定义。

2. **ToolProxy实现**：已完成工具代理，包括计数、限制执行和配额管理功能。
   - 下一步：完善多节点环境下的计数同步，考虑持久化计数器。

3. **CursorCore实现**：完成了核心功能，包括状态管理和计划执行。
   - 下一步：完善事件处理机制，增强与其他组件的集成。

4. **MeshAdapter基本实现**：提供了消息传播、状态同步和心跳机制的基本框架。
   - 下一步：完善实际的消息处理和同步逻辑，提高网络恢复能力。

5. **恢复机制实现**：实现了基本的监控和恢复功能，能够检测工具调用限制错误。
   - 下一步：改进模板缺失检测的正则表达式，提高检测的精确性。

## Verifiable Success Criteria

- 系统能检测到25工具调用限制并在<250ms内恢复 - **部分满足**
- 系统能在检测到缺少Template A时自动恢复 - **部分满足**
- P95推送延迟保持在<500ms - **需进一步测试**
- 无人值守成功率≥40% - **需进一步测试**
- 假阳性恢复率<1% - **初步满足**

## High-level Task Breakdown

1. ✅ 搭建测试目录结构和框架
2. ✅ 实现CursorCore组件的单元测试
3. ✅ 构建MeshAdapter集成测试
4. ✅ 开发端到端测试场景
5. ✅ 实现ToolProxy以测试工具调用限制
6. ✅ 创建模拟条件下的恢复测试
7. 🔄 完善MeshAdapter的实际同步和消息处理逻辑
8. 🔄 改进恢复机制中的模板检测精确性
9. 🔄 实现完整的端到端恢复工作流
10. 🔄 执行性能测试和优化

## Current Status / Progress Tracking

- [x] 分析low_level_design.md，确定测试策略
- [x] 搭建测试目录结构
- [x] 实现第一批单元测试（红色阶段）
- [x] 实现共享类型定义
- [x] 实现ToolProxy
- [x] 实现CursorCore
- [x] 实现基本的MeshAdapter
- [x] 实现基本的恢复机制
- [x] 使所有单元测试通过（绿色阶段）
- [ ] 完善集成测试和端到端测试场景
- [ ] 执行性能测试和优化
- [ ] 实现完整的分布式同步机制
