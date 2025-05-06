# 迭代待办列表 (Backlogs)

## Feature: 正统 ADR 流程

### 背景 (Context)
在现有的 Plan-Execu 循环中，决策记录主要依赖 `.scratchpad_logs/` 的原始对话文件。这导致新成员或后期维护者需要翻阅大量噪声信息才能了解一次关键技术／架构决策的来龙去脉。为了提升可追溯性与团队协作效率，需要引入 **Architecture Decision Record (ADR)** 正统流程。

### 目标 (Goal)
为 oppie.xyz 项目建立一套轻量、结构化、可版本控制的 ADR 体系，使每一项关键决策都可以快速定位、检索，并附带背景与影响分析。

### 描述 (Description)
1. 在仓库根目录新增 `docs/adr/` 目录，存放 Markdown 格式的 ADR 文件。
2. 采用经典 ADR 模板（Status / Date / Context / Decision / Consequences）。
3. Executor 在完成一项显著架构或技术决策时：
   - 创建新的 ADR 文件，文件名格式 `NNNN-title.md`，其中 `NNNN` 为 4 位递增序号。
   - 在文件中填写决策详情，并在 `Status` 字段标记 `Proposed` 或 `Accepted`。
4. 在 Pull Request / Plan-Execu Review 阶段，由人类或 Planner 确认并将 `Status` 更新为 `Accepted`。
5. 在 CI 阶段增加 lint/hook：若代码中检测到新增高风险依赖或目录结构调整，但未伴随 ADR，则提醒作者补全。
6. 在 README 或 `docs/index.md` 中增加 **ADR 索引**，自动列出已有 ADR 并链接。

### 权重 (Priority / Effort)
- **优先级**：中（提升长期可维护性）
- **预估工时**：2–3 人日

### 子任务 (Sub-tasks)
- [ ] 创建 `docs/adr/` 目录并提交初始空 README
- [ ] 添加 `0001-adr-template.md` 模板示例
- [ ] 在 `.pre-commit-config.yaml` 中配置 ADR 文件名 lint (可选)
- [ ] 编写 Git hook 检查脚本（缺 ADR 时警告）
- [ ] 更新 `README.md` 的决策索引章节
- [ ] 为现有重大决策补写至少 1 条 ADR 作为示范

### 依赖 (Dependencies)
- 需要 CI 环境支持自定义脚本或 lint。
- 团队成员需学习 ADR 流程（可制作指南）。

### 风险 (Risks)
- 过度文档化导致维护负担；需保持模板简洁、聚焦关键决策。
- 如果流程执行不严格，ADR 与实际代码可能出现偏差。

### 验收标准 (Acceptance Criteria)
1. 仓库根目录可以看到 `docs/adr/`，其中包含模板示例。
2. 合并重要变更的 PR 必须附带或者引用对应 ADR。
3. README 或文档站点自动生成 ADR 索引且可点击跳转。
4. 团队成员能够在 2 分钟内通过索引找到某项决策的背景与影响。 