# ADR-0005: 采用OpenHands ACI架构替代自研组件

## 状态

提议

## 日期

2025-05-06

## 背景

Oppie.xyz项目当前使用了多个自研组件（PocketFlow Mini-Orchestrator、Agent S、Vector Store）来实现Agent计划执行、GUI自动化和向量存储功能。这些组件增加了维护成本和系统复杂性。与此同时，我们发现开源社区中的OpenHands项目提供了成熟的Agent控制接口（ACI）以及全面的工具生态，可能适合替代我们的自研组件。

OpenHands提供了：
1. 成熟的Agent系统，支持planning、execution和reflection循环
2. 内置的轨迹可视化（trajectory-visualizer）
3. 可插拔的向量搜索（基于FAISS/Milvus）
4. 预构建的Runtime和Event系统
5. 计算机使用接口（Computer Use Interface）

## 决策

我们决定采用OpenHands ACI作为Oppie.xyz的核心Agent框架，具体替换以下组件：

1. 使用OpenHands的CodeActAgent替代PocketFlow Mini-Orchestrator
2. 使用OpenHands的Runtime和Function Calling替代Agent S的GUI自动化
3. 使用OpenHands内建的Trajectory系统和向量存储替代自研Vector Store

我们将保留现有的VS Code/Cursor扩展和移动PWA界面，通过轻量级适配器将它们与OpenHands集成。

## 后果

### 积极影响

1. 减少维护成本 - 不再需要自研和维护多个复杂组件
2. 获取更成熟的技术栈 - OpenHands已经在生产环境中验证
3. 丰富的功能集 - 直接获得LLM抽象、事件流、可视化等现成功能
4. 更快的开发迭代 - 可以专注于业务功能而非基础设施
5. 社区支持 - 获得更广泛的开发者社区支持

### 潜在风险

1. 学习成本 - 团队需要学习OpenHands的API和架构
2. 迁移成本 - 需要重写配置、重构测试、更新文档
3. 功能差异 - 可能需要开发兼容层以支持Oppie特有功能
4. 依赖外部项目 - 依赖OpenHands的开发节奏和版本更新

### 缓解措施

1. 创建精简的适配器层，隔离第三方依赖
2. 保持领域语言不变，在底层映射到OpenHands概念
3. 通过测试驱动迁移，确保功能完整性
4. 使用特性标志实现增量发布

## 相关循环

- Cycle 0: OpenHands集成设计
- PR: 待定

## 参考资料

- [OpenHands文档](https://deepwiki.com/All-Hands-AI/OpenHands)
- [Trajectory Visualizer](https://deepwiki.com/All-Hands-AI/trajectory-visualizer)
- [OpenHands ACI](https://github.com/All-Hands-AI/openhands-aci) 