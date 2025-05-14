# Oppie.xyz 系统项目需求访谈问卷

## 项目背景与目标

1. **oppie.xyz系统的主要目标和用途是什么？您期望它解决哪些具体问题？**
    Oppie.xyz的主要目标是提供一个移动优先的远程Cursor控制层（Remote Cursor Control），允许用户通过手机等移动设备可靠地执行代码开发和研究任务。它期望解决的核心问题是让开发者在离开键盘或主力开发设备后，其代码开发工作（如处理待办事项、运行测试、修复Bug、生成PR）仍能持续、自主地进行，实现无人值守的任务推进。系统通过"规划 → 执行 → 反思 → 自愈"的循环工作模式，确保任务的持续进展，就像一个不知疲倦的代码漫游车。

2. **您期望oppie.xyz系统与现有的AI代理系统相比有哪些独特的优势？**
    Oppie.xyz期望的独特优势包括：
    *   **强大的中断处理与自愈能力**：专为应对开发工作中常见的中断设计，具备Crash‑Safe特性（从检查点断点续传）、Checkpoints Protocol（执行后对比差异哈希，偏差大则回退重试），以及针对Cursor 25次工具调用限制或崩溃的自动恢复机制（Self-Recovery）。
    *   **移动优先的远程控制**：通过Mobile PWA（渐进式网络应用）和Sidecar Daemon（本地守护进程），用户可以从手机等移动设备下达指令、监控任务，打破对笔记本电脑的物理依赖。
    *   **与IDE的深度集成**：与Cursor IDE紧密集成，在其基础上提供远程代理能力，旨在增强而非替换用户已有的工作流。许多AI代理框架缺乏这种与IDE的紧密集成或稳健的远程接口。
    *   **企业级安全与合规扩展**：通过Guard-Rails SDK，企业团队可以将自身的安全与合规策略（如SOC-2 / HIPAA审计追踪）注入到每一个远程命令中。
    *   **持久化的状态与历史记录**：采用Raft-backed Vector Store来存储日志、代码嵌入和差异历史，确保数据在本地磁盘故障之外的持久性。
    *   **提升任务成功率与用户信任**：通过成熟的自愈能力和紧密的"规划-执行-反思"循环，旨在减少任务停滞，提高无人值守运行的可靠性，并可能降低GPU计算资源的使用成本。

3. **该系统的主要用户群体是谁？他们的技术背景和使用场景是什么？**
    该系统的主要用户群体包括：
    *   **OSS 维护者**：希望在非工作时间（如睡醒后）发现诸如 `good-first-issue` 之类的任务已自动处理完成并生成了通过CI的PR。
    *   **Indie Hacker / Bootstrapped SaaS 团队**：需要在夜间或开发者离开时自动运行测试，以加速MVP（最小可行产品）的迭代。
    *   **Agent 研究员**：需要可重放的日志和强大的恢复机制，以减少实验过程中的偶然性，确保实验结果的可靠性。
    *   **需要临时离开的开发者 / 数字游民 (Digital Nomads)**：在临时离开电脑时，希望Oppie能够接手继续修改Bug或执行其他开发任务。
    *   **轻装出行的工程师**：越来越多工程师仅携带iPad或手机出行，但仍需承担CI/CD等繁重的开发职责。

    他们的技术背景通常是具有一定经验的软件开发者或AI研究人员，熟悉IDE（特别是Cursor）和版本控制系统。
    使用场景主要是在开发者无法直接操作其主力开发设备时，能够通过移动设备远程启动、监控、并在必要时接管在家庭或办公室电脑上运行的编码、测试、研究或CI/CD相关任务。核心需求是"在我离开键盘时，从我的手机上启动、监控并合并一个通过测试的PR（或运行一份研究报告）"。

4. **您对系统成功的定义是什么？有哪些关键的成功指标？**
    系统成功的定义主要围绕任务执行的效率、成本效益和可靠性。
    关键成功指标包括：
    *   **Plan-Execute 循环效率**：目标是每5分钟完成一次有意义的Plan-Execute循环。 (Source: `news_letter.md`)
    *   **CI 通过率**：目标是CI通过率 ≥ 92%。 (Source: `news_letter.md`)
    *   **远程任务成本效益 (North-Star Metric)**：目标是每成功执行一个远程任务的成本 ≤ $15。 (Source: `product_market_fit.md`)
    *   **任务成功率 (SWE-Bench-Lite)**：在SWE-Bench-Lite基准测试上达到 ≥ 40% 的成功率（例如，在接下来的60天内通过内部测试实现此目标）。 (Source: `product_market_fit.md`)
    *   (Assumption: \"SWE-Bench-Lite success\" is a key indicator of overall system success, based on its prominence in the `product_market_fit.md` validation roadmap.)

5. **系统的核心价值主张是什么？用户通过oppie.xyz能够实现哪些他们现在难以完成的"工作"（Jobs-to-be-Done）？**
    系统的核心价值主张是：**提供一个可靠的、可通过移动设备远程控制的Cursor AI助手，能够在你离开键盘后自主、持续地执行开发和研究任务，并有效应对中断。** (Synthesized from `news_letter.md` and `product_market_fit.md`)

    用户通过Oppie.xyz能够实现的 "Jobs-to-be-Done" 包括：
    *   **远程启动、监控和管理开发任务**：例如，在通勤路上或外出时，通过手机启动代码修复、运行测试、处理GitHub Issue、合并已通过CI的PR，或执行研究报告的生成，而无需守在电脑前。 (Source: `product_market_fit.md`, `news_letter.md`)
    *   **实现无人值守的持续工作**：将周末的待办开发任务、夜间的测试运行等托付给Oppie，让AI助手在开发者休息或处理其他事务时继续推进工作。 (Source: `news_letter.md`)
    *   **提高应对工作中断的韧性**：即使遇到Cursor或操作系统休眠、工具调用次数限制等意外中断，系统也能从上一个检查点自动恢复并继续任务，减少人工干预的需要和时间损失。 (Source: `news_letter.md`)
    *   **加速产品迭代和问题修复**：例如，让Oppie在夜间运行测试以加速MVP的迭代周期，或者自动将 `good-first-issue` 转化为通过CI的PR。 (Source: `news_letter.md`)
    *   **摆脱"笔记本电脑的束缚"**：在火车上或其他不便使用笔记本电脑的场合，通过手机队列任务，让家中的台式机接力完成。 (Source: `product_market_fit.md`)

## 技术架构与集成

6. **在虚拟桌面环境中，您希望预装哪些特定版本的工具（Cursor IDE、OpenAI CodexCLI等）？这些工具是否有特定的配置要求？**
    Information not available in provided documents; requires further stakeholder input.
    (Assumption: While Cursor IDE and OpenAI CodexCLI are mentioned as components, specific versions or configuration requirements are not detailed in `news_letter.md` or `product_market_fit.md`.)

7. **您对集成e2b-dev/desktop和e2b-dev/infra有任何特定的要求或限制吗？例如，是否需要支持特定的云提供商？**
    Information not available in provided documents; requires further stakeholder input.
    (Assumption: `product_market_fit.md` mentions \"Edge-VM Runner\" as a future expansion which might relate to e2b-dev, but specific requirements or cloud provider preferences for the core integration are not detailed.)

8. **Reflexion框架如何与Plan-Execute循环具体集成？您期望的反馈机制和学习过程是怎样的？**
    Oppie.xyz采用紧密的"规划 (Plan) ⇄ 执行 (Execute) ⇄ 反思 (Reflect)"循环。Reflexion框架的角色体现在"Reflector"模块中。
    *   **集成方式**：Reflector模块在执行模块（Executor）完成任务后介入。
    *   **反馈机制**：Reflector负责"模板化总结结果、风险"。
    *   **学习过程**：这些总结和风险评估会"反馈 Planner 启动下一循环"。这意味着Planner会根据Reflector的输出调整后续的计划。
    (Source: `news_letter.md`, "工作原理：Plan ⇄ Execute ⇄ Reflect 循环" section)
    `news_letter.md` also mentions "高级规划算法 — Reflexion, ToT, SFS" in its future roadmap, implying a deeper integration or enhancement of Reflexion's capabilities in planning.

9. **将oppie-core集成到OpenHands时，您期望保留OpenHands的哪些功能，添加哪些新功能？**
    Information not available in provided documents; requires further stakeholder input.
    (Assumption: While Oppie.xyz is a system that includes various components, the specifics of integrating "oppie-core" into "OpenHands," including what functionalities to retain or add, are not detailed in `news_letter.md` or `product_market_fit.md`.)

10. **各核心组件（Cursor、OpenHands、Reflexion等）之间的详细交互模型和数据流是什么？这些组件如何协同工作？**
    基于 `news_letter.md` 的 "工作原理：Plan ⇄ Execute ⇄ Reflect 循环" 部分，一个高层次的交互模型可以描述如下：
    *   **Landing Context** (类比 TRN - 地形相对导航): 负责首次索引代码库，创建Raft Vector Store，确保系统在正确的上下文"着陆"。
    *   **Planner** (类比 JPL 任务控制中心): 接收任务，将其细分为带有检查点 (Checkpoints) 的执行计划。它会接收来自Reflector的反馈以启动下一个规划循环。
    *   **Executor** (类比 车体 + AutoNav): 严格按照Planner生成的计划，调用Cursor工具链执行任务，并实时记录diff（代码变更）。
    *   **Reflector** (类比 科学家分析回路): 对Executor的执行结果进行模板化总结，评估风险，并将这些信息反馈给Planner，以启动（或调整）下一个Plan-Execute循环。
    *   **Guard-rails** (类比 Hazard Detector): 通过静态分析和LLM策略进行风险监控，在遇到高风险情况时，可以触发回滚或重新规划。
    *   **Self-Recovery** (类比 深空延迟模型): 通过Watcher脚本监控系统状态，当遇到25次工具调用限制或系统崩溃等问题时，自动注入恢复提示以尝试继续任务。
    *   **Mobile PWA**: 用户通过手机PWA下达指令，这些指令可能被送往Planner，或者用于监控Executor的执行状态。
    *   **Raft Vector Store**: 用于存储代码库索引、日志、嵌入和diff历史，供多个组件访问。 (Source: `news_letter.md`, `product_market_fit.md`)

    Data flow primarily follows the Plan → Execute → Reflect loop, with Guard-rails and Self-Recovery acting as overarching monitors and intervention mechanisms. The Raft Vector Store serves as a central repository for contextual and historical data.
    Specifics about OpenHands' role in this direct component list from the newsletter are not detailed, though it's mentioned elsewhere as part of the broader Oppie.xyz vision.

11. **您对系统的内部事件总线有什么特定要求？事件类型、生产者/消费者模式和消息格式应该如何设计？**
    Information not available in provided documents; requires further stakeholder input.

## 功能需求

12. **在Plan-Execute-Reflect循环中，您期望系统能够处理的任务类型和复杂度是什么？**
    系统期望能够处理的任务类型包括：
    *   **代码开发任务**：如修复Bug、处理GitHub `good-first-issue`并将其转化为通过CI的PR。 (Source: `news_letter.md`)
    *   **测试任务**：如夜间运行测试以加速MVP迭代。 (Source: `news_letter.md`)
    *   **研究任务**：如运行研究报告。 (Source: `product_market_fit.md`)
    *   **常规开发待办**：能够处理开发者"周末待办"中的任务。 (Source: `news_letter.md`)

    关于复杂度：
    *   系统旨在通过"规划 → 执行 → 反思 → 自愈"循环不息地工作，暗示了其设计目标是能够处理需要多步骤、可能遇到中断并需要自我修正的复杂任务。
    *   The North-Star metric of "≥ 40 % success on SWE-Bench-Lite" (Source: `product_market_fit.md`) suggests an ambition to handle tasks of non-trivial complexity, as SWE-Bench typically involves resolving real-world GitHub issues.
    *   The goal of "每 5 分钟完成一次有意义的 Plan-Execute 循环" (Source: `news_letter.md`) suggests that individual cycles might be small, but chained together they can tackle larger problems.

13. **用户如何与系统交互？是否需要支持特定的交互方式（如自然语言、命令行、图形界面等）？**
    用户主要通过以下方式与系统交互：
    *   **Mobile PWA (渐进式网络应用)**：用户可以通过手机PWA下达指令（例如，提交一个Issue让Oppie处理）。这是主要的远程交互方式。 (Source: `news_letter.md`, `product_market_fit.md`)
    *   **Cursor 插件**：Oppie以 "Cursor 插件 + 本地守护进程" 形式提供，暗示用户也可能在Cursor IDE内部通过插件界面与系统进行配置或交互。 (Source: `news_letter.md`)
    *   Assumption: While "natural language" is not explicitly stated as an input method in the provided documents for task definition, the context of AI agents and LLMs (mentioned for Guard-rails) implies that task instructions given via the Mobile PWA might be in natural language. Further clarification would be beneficial. Command-line or specific GUI interactions beyond the PWA and Cursor plugin are not detailed.

14. **您对系统的实时监控和接管功能有哪些具体要求？如监控的粒度、接管的触发条件等。**
    *   **实时监控**：用户可以通过Mobile PWA监控任务。 (Source: `product_market_fit.md` - "Kick off, monitor, and merge...")
    *   **接管功能**: `product_market_fit.md` mentions "Turns Cursor into a remotely steerable agent that can be paused, resumed, or re-prompted from any device." This implies接管能力包括暂停、继续和重新提示（re-prompt）。
    *   The newsletter mentions "Autopause / Resume — 测试不通过？Oppie 暂停，反思，调整后继续。" This indicates one trigger for autopause is test failure.

    Specifics on监控的粒度 or other 接管的触发条件 are not detailed beyond these points.

15. **在系统出现错误或Plan-Execute循环中断时，您期望的恢复机制是什么？应该提供哪些回滚或检查点功能？**
    期望的恢复机制和功能包括：
    *   **Crash‑Safe断点续传**：如果Cursor或操作系统休眠导致中断，Oppie能从上次的检查点 (Checkpoint) 断点续传。 (Source: `news_letter.md`)
    *   **Checkpoints Protocol**：在每步执行后，系统会对比代码的差异哈希 (diff hash)。如果偏差较大，表明可能出现问题，此时系统会回退并重试。 (Source: `news_letter.md`)
    *   **Self-Recovery机制**：通过Watcher脚本监控系统状态。当遇到已知限制（如Cursor的25次工具调用限制）或工具崩溃时，系统会自动注入恢复提示，尝试让任务继续。 (Source: `news_letter.md`)
    *   **Autopause/Resume**：例如，当测试不通过时，Oppie会自动暂停，进行反思和调整，然后尝试继续。 (Source: `news_letter.md`)
    *   **Guard-rails触发的回滚/重规划**：当Guard-rails（通过静态分析+LLM策略）检测到高风险操作时，可以触发回滚或要求Planner重新规划。 (Source: `news_letter.md`)
    *   **针对特定风险的缓解措施**：
        *   对于移动网络不稳定导致的任务中断，采用离线队列 (Offline queue) 和Sidecar重试缓冲 (Sidecar retry buffer)。 (Source: `product_market_fit.md`, Risk Register)
        *   对于Cursor UI变更可能破坏自动化的问题，有双路径回退方案 (Dual-path fallback)，结合隐藏命令和GUI自动化。 (Source: `product_market_fit.md`, Risk Register)

16. **用户从手机端发起任务的完整流程是什么？他们需要提供哪些信息？系统应如何确认和验证这些任务？**
    *   **发起流程**：用户通过 Mobile PWA（渐进式网络应用）从手机端下达指令或任务。例如，用户可以提交一个Issue让Oppie在家中的电脑上执行处理。 (Source: `news_letter.md`, `product_market_fit.md`)
    *   **提供信息**: The documents imply tasks like "提 Issue" (submit an issue) or broader goals like "kick off, monitor, and merge a green PR (or run a research report)". The exact information schema required from the user isn't detailed. (Source: `news_letter.md`, `product_market_fit.md`)
    *   Assumption: Given the AI nature, users likely provide task descriptions in natural language, potentially with references to code or issues.
    *   **确认和验证**: Information not available in provided documents; requires further stakeholder input. (Specifics on task confirmation and validation mechanisms are not detailed). `product_market_fit.md` mentions "OTP gating for high-risk commands; diff approval via PWA" under Risk Register, which suggests a form of validation/approval for certain actions, but not a general task confirmation process.

17. **在任务执行过程中，用户应该能够看到哪些状态信息和进度指标？这些如何在移动端呈现？**
    *   **状态信息和进度指标**: Users can "monitor" tasks from their phone. (Source: `product_market_fit.md`)
    *   The newsletter mentions "实时记录 diff" (real-time recording of diffs) by the Executor. This could be a form of progress indicator.
    *   The target of "每 5 分钟完成一次有意义的 Plan-Execute 循环" and "CI 通过率 ≥ 92%" are key metrics, which could be surfaced to the user. (Source: `news_letter.md`)
    *   **移动端呈现**: Through the Mobile PWA. (Source: `news_letter.md`, `product_market_fit.md`)
    *   Specific details on *which* status information or *how* these are presented on the mobile PWA (beyond general monitoring capability) are not available in the provided documents.

18. **针对不同类型的故障（工具调用限制、网络中断、执行错误等），系统应该采取哪些具体的恢复策略？**
    *   **工具调用限制 (e.g., Cursor's 25-tool-call limit)**: The "Self-Recovery" module, via a Watcher script, automatically injects recovery prompts to attempt to continue the task. (Source: `news_letter.md`, `product_market_fit.md`)
    *   **网络中断 (Mobile network flakiness)**: An "Offline queue + Sidecar retry buffer" is planned as a mitigation. (Source: `product_market_fit.md`, Risk Register)
    *   **执行错误 / Crash (Cursor or OS休眠)**: "Crash‑Safe" functionality allows Oppie to resume from the last checkpoint. (Source: `news_letter.md`)
    *   **执行错误 / Test failures**: "Autopause / Resume" allows Oppie to pause, reflect, adjust, and then continue. (Source: `news_letter.md`)
    *   **执行错误 / Deviation from plan (偏差大)**: The "Checkpoints Protocol" involves comparing diff hashes after each step; large deviations trigger a rollback and retry. (Source: `news_letter.md`)
    *   **执行错误 / Cursor UI changes breaking automation**: A "Dual-path fallback (hidden command ✚ GUI automation)" is a mitigation strategy. (Source: `product_market_fit.md`, Risk Register)
    *   **执行错误 / High-risk commands**: "Guard-rails" can trigger rollback or re-planning. (Source: `news_letter.md`) "OTP gating for high-risk commands; diff approval via PWA" is also a mitigation for silent bugs introduced by agents. (Source: `product_market_fit.md`)

19. **checkpoint的粒度和频率应该如何设定？这些checkpoint应包含哪些具体信息以确保准确恢复？**
    *   **粒度和频率**: Checkpoints are made "每步执行后" (after each execution step) as per the "Checkpoints Protocol". (Source: `news_letter.md`) The system aims for a Plan-Execute cycle every 5 minutes, which might also inform checkpoint frequency in a broader sense.
    *   **包含信息**: The "Checkpoints Protocol" involves "对比差异哈希" (comparing diff hashes), implying that checkpoints capture at least the state necessary to compute and compare code diffs. (Source: `news_letter.md`) The "Self-Recovery" module also relies on these checkpoints for "断点续传" (resuming from breakpoint). (Source: `news_letter.md`) The "Raft-backed Vector Store stores logs, embeddings, and diff history" (Source: `product_market_fit.md`), suggesting these elements are crucial for context and recovery, and thus likely part of checkpoint data.
    *   Specific, exhaustive details of what a checkpoint must contain are not fully itemized beyond these implications.

20. **用户应该如何设置和管理自动恢复策略？有哪些配置选项应该提供给用户？**
    Information not available in provided documents; requires further stakeholder input. (While automatic recovery is a core feature, user configuration of these strategies is not mentioned.)

21. **系统应该如何记录和呈现Reflexion的反思结果？这些反思应该如何有效地用于改进后续计划？**
    *   **记录和呈现**: The "Reflector" module is responsible for "模板化总结结果、风险". (Source: `news_letter.md`) The "Raft-backed Vector Store stores logs, embeddings, and diff history" (Source: `product_market_fit.md`), which could include these reflection summaries. How these are *presented* to the user (if at all directly) is not specified.
    *   **用于改进后续计划**: The Reflector's "模板化总结结果、风险" are explicitly "反馈 Planner 启动下一循环". (Source: `news_letter.md`) This direct feedback loop is the primary mechanism for using reflections to improve subsequent plans. The system "行动前先反思" (reflects before acting) and if it "偏离时道歉并复位" (apologizes and resets when deviating), suggesting reflection is integral to its operational logic. (Source: `news_letter.md`)

## 非功能需求

22. **您对系统性能有哪些具体要求？例如，响应时间、并发用户数、资源使用限制等。**
    *   **响应时间/Loop Efficiency**: "每 5 分钟完成一次有意义的 Plan-Execute 循环" is a key performance target. (Source: `news_letter.md`)
    *   **Resource Use Limitation (GPU cost)**: A risk is "GPU cost overrun," mitigated by "Default to o4-mini; auto-kill loops after 15 min." (Source: `product_market_fit.md`, Risk Register) This implies a desire to manage resource costs.
    *   **Search Latency (for large repos)**: A trigger for the "Code-Atlas" (Raft Vector Store 2.0) expansion is "Repos > 1 M LOC & search latency > 400 ms," suggesting a performance concern for large codebases. (Source: `product_market_fit.md`, `news_letter.md`)
    *   Information on并发用户数 or other specific resource use limits is not available.

23. **安全性方面，除了e2b-dev/desktop提供的沙箱隔离外，还需要哪些额外的安全措施？**
    *   **Guard-Rails SDK**: This allows "Enterprise teams can inject security & compliance policies into every remote command." (Source: `product_market_fit.md`) The Guard-rails module uses "静态分析 + LLM 策略" and can trigger rollbacks or re-planning for high-risk situations. (Source: `news_letter.md`) This is a key additional security measure.
    *   **OTP gating for high-risk commands**: This is a mitigation for the risk of agents introducing silent bugs. (Source: `product_market_fit.md`, Risk Register)
    *   **Diff approval via PWA**: Also a mitigation for silent bugs, allowing for human oversight. (Source: `product_market_fit.md`, Risk Register)
    *   **Edge-VM Runner**: Mentioned as a future roadmap item for a "安全沙箱执行环境" (secure sandbox execution environment). (Source: `news_letter.md`)
    *   Assumption: The "Raft-backed Vector Store" which stores logs and diff history with durability (Source: `product_market_fit.md`) also contributes to auditability, which is a component of security.

24. **系统应该支持哪些扩展性功能？例如，是否需要支持添加新的工具、LLM模型或自定义工作流？**
    Yes, extensibility is planned:
    *   **Plug-in Mesh**: A future roadmap item is "Plug-in Mesh — 通过 `oppie.plugin.json` 轻松集成第三方工具." (Source: `news_letter.md`) This directly addresses adding new tools.
    *   **可插拔 Guard-rails**: The Guard-Rails concept itself, especially as an SDK, allows for "企业级安全合规注入," implying customizability and extension of rules/policies. (Source: `news_letter.md`, `product_market_fit.md`)
    *   **Advanced Planning Algorithms**: The roadmap includes "Reflexion, ToT, SFS," suggesting the system can evolve its core planning/reasoning capabilities, potentially by incorporating new models or techniques. (Source: `news_letter.md`)
    *   Support for new LLM models is implicitly suggested by the risk mitigation for GPU cost: "Default to o4-mini", implying other models could be used.
    *   Support for custom workflows is not explicitly stated, but the modular design (Planner, Executor, Reflector) and plugin architecture point towards a system designed for future flexibility.

25. **您对系统的可用性和容错性有哪些要求？例如，系统宕机时间、故障恢复时间等。**
    High availability and strong fault tolerance are core to the system's design and value proposition:
    *   **"为中断而生" / "Oppie 始终在线"**: This is a design philosophy. (Source: `news_letter.md`)
    *   **Crash‑Safe**: Ensures resumption from checkpoints after Cursor/OS休眠. (Source: `news_letter.md`)
    *   **Self-Recovery**: Handles 25-tool-call limit and crashes. (Source: `news_letter.md`)
    *   **Checkpoints Protocol**: Recovers from deviations by rolling back and retrying. (Source: `news_letter.md`)
    *   **Autopause / Resume**: Pauses on test failures, reflects, and continues. (Source: `news_letter.md`)
    *   **Guaranteed Progress**: "Guarantees progress even after hitting Cursor's 25-tool-call limit; lifts trust for unattended runs." (Source: `product_market_fit.md`)
    *   Specific metrics like acceptable downtime (e.g., 99.9%) or precise fault recovery times are not explicitly stated, but the emphasis on robust recovery ("fewer stalls, higher trust") is clear.

26. **在移动网络不稳定的情况下，系统应该如何确保任务指令的可靠传递和状态更新？**
    This is a recognized risk. The mitigation strategy is:
    *   **Offline queue + Sidecar retry buffer**: This mechanism is designed to handle task interruptions due to mobile network flakiness. (Source: `product_market_fit.md`, Risk Register)
    *   Assumption: The Sidecar Daemon, being a local process on the desktop, would manage the queue and retries for commands received from the mobile PWA, ensuring eventual consistency or execution once connectivity is restored or stable.

27. **对于长时间运行的任务，系统应该如何管理资源并防止性能下降？**
    *   **GPU Cost Management**: One aspect of resource management for potentially long-running (or inefficient) tasks is "auto-kill loops after 15 min" (this is a mitigation for GPU cost overrun, using o4-mini by default). (Source: `product_market_fit.md`, Risk Register) This acts as a hard stop for runaway processes.
    *   **Checkpointing**: The Checkpoints Protocol can help manage long tasks by saving progress. (Source: `news_letter.md`)
    *   The "Plan ⇄ Execute ⇄ Reflect" loop, with its target of a meaningful cycle every 5 minutes, suggests breaking down long tasks into manageable, iterative chunks, which can also help in managing resources and maintaining performance by allowing for re-planning and course correction. (Source: `news_letter.md`)
    *   Information on other specific strategies for managing resources (CPU, memory beyond GPU) or preventing performance degradation in long tasks is not detailed.

28. **系统应该如何处理多任务并发执行？是否需要任务优先级管理？**
    Information not available in provided documents; requires further stakeholder input. (The documents focus on the execution of individual tasks and their recovery, but concurrent task execution or prioritization is not discussed.)

## 部署与维护

29. **您计划如何部署该系统？是在本地环境、私有云还是公共云？**
    *   **Primary Deployment Model**: Oppie is provided as a "Cursor 插件 + 本地守护进程 (Sidecar Daemon)" which implies deployment on a user's local machine (e.g., home desktop). (Source: `news_letter.md`, `product_market_fit.md`) The user queues tasks on their mobile PWA, and "let the desktop work at home."
    *   **Future Cloud Runner**: `product_market_fit.md` mentions a "Cloud Runner compute add-on" as part of its monetization strategy and an "Edge-VM Runner" as an expansion lane for "disposable sandboxes". This indicates a future possibility of cloud-based execution environments. (Source: `product_market_fit.md`, `news_letter.md`)
    *   Whether the Raft-backed Vector Store is local or cloud-based for the initial deployment isn't explicitly stated, but "Managed cluster ($/GiB-mo)" is mentioned for "Code-Atlas" (which uses Raft Vector Store 2.0), suggesting a cloud option for that enhanced version.

30. **系统是否需要支持多用户环境？如果是，用户之间的资源隔离和权限管理有哪些要求？**
    *   **Monetization Tiers**: The monetization plan includes "$49 / seat / mo unlimited" (Source: `product_market_fit.md`), which implies support for multiple seats, typically seen in team or multi-user environments.
    *   **Enterprise Focus**: The "Guard-Rails SDK" for enterprise teams to inject security/compliance policies also suggests a context where multiple users or a central authority might manage settings. (Source: `product_market_fit.md`)
    *   However, specific requirements for resource isolation and permission management in a multi-user environment are not detailed in the provided documents.

31. **您对系统的监控和日志记录有哪些要求？需要记录哪些类型的事件和数据？**
    *   **Executor**: "实时记录 diff" (records diffs in real-time). (Source: `news_letter.md`)
    *   **Reflector**: Produces "模板化总结结果、风险". (Source: `news_letter.md`)
    *   **Raft-backed Vector Store**: "Stores logs, embeddings, and diff history with durability". (Source: `product_market_fit.md`) This indicates that logs, code embeddings, and diff history are key data types to be recorded.
    *   **Agent Researchers User Scenario**: Mentions "可重放日志" (replayable logs) as a benefit for agent researchers. (Source: `news_letter.md`)
    *   **Guard-Rails SDK for Audit Trails**: For teams demanding SOC-2 / HIPAA audit trails, Guard-Rails are relevant. (Source: `product_market_fit.md`) This implies logging relevant for compliance.
    *   Specific event types beyond these, or detailed schema for logs, are not available.

32. **您期望如何维护和更新系统？是否需要支持热更新或无缝升级？**
    Information not available in provided documents; requires further stakeholder input.

33. **系统部署的最小硬件要求是什么？在资源受限的环境中，系统应如何调整以保持核心功能？**
    Information not available in provided documents; requires further stakeholder input. (While GPU cost management is mentioned, overall minimum hardware specs or adjustments for resource-constrained environments are not.)

## 集成与兼容性

34. **除了已提到的组件外，系统是否需要与其他现有系统或工具集成？**
    *   **Plug-in Mesh**: The future roadmap includes "Plug-in Mesh — 通过 `oppie.plugin.json` 轻松集成第三方工具." (Source: `news_letter.md`) This explicitly states the intention to integrate with other third-party tools beyond the core components.
    *   No other specific systems or tools are mandated for integration in the provided documents.

35. **移动客户端dashboard（基于trajectory-visualizer）需要支持哪些具体功能？它是否需要与特定的移动平台兼容？**
    *   **Mobile PWA (Progressive Web App)**: This is the mobile client. (Source: `news_letter.md`, `product_market_fit.md`) PWAs are designed to be platform-agnostic, working across various mobile operating systems (iOS, Android) through a web browser.
    *   **Functionality**:
        *   "用手机下达指令 (如提 Issue)". (Source: `news_letter.md`)
        *   "Kick off, monitor, and merge a green PR (or run a research report) from my phone". (Source: `product_market_fit.md`)
        *   Allows tasks to be "paused, resumed, or re-prompted from any device." (Source: `product_market_fit.md`)
        *   "Diff approval via PWA" for mitigating silent bugs. (Source: `product_market_fit.md`)
    *   The term "trajectory-visualizer" is not present in `news_letter.md` or `product_market_fit.md`.
    *   Assumption: The question's mention of "trajectory-visualizer" might be from an external context or an older plan. Based *solely* on the provided `news_letter.md` and `product_market_fit.md`, the mobile client is a PWA with the functionalities listed above.

36. **系统是否需要支持国际化和本地化？如果是，需要支持哪些语言和地区？**
    Information not available in provided documents; requires further stakeholder input.

37. **对于API和数据格式，您是否有特定的要求或偏好？例如，REST vs GraphQL、JSON vs Protocol Buffers等。**
    Information not available in provided documents; requires further stakeholder input. (The `oppie.plugin.json` for the Plug-in Mesh is mentioned, implying a JSON-based configuration for plugins, but this doesn't cover broader API or data format choices.)

38. **移动客户端应该提供哪些具体的控制功能？例如，是否允许用户实时修改执行计划，或只提供暂停/继续选项？**
    The mobile client (PWA) should provide:
    *   **Task Initiation**: "Kick off" tasks / "下达指令". (Source: `product_market_fit.md`, `news_letter.md`)
    *   **Monitoring**: Ability to "monitor" tasks. (Source: `product_market_fit.md`)
    *   **Pause/Resume**: Tasks can be "paused, resumed". (Source: `product_market_fit.md`)
    *   **Re-prompt**: Tasks can be "re-prompted". (Source: `product_market_fit.md`)
    *   **Diff Approval**: "Diff approval via PWA". (Source: `product_market_fit.md`)
    *   The documents do not explicitly state whether users can "实时修改执行计划" (modify execution plans in real-time) beyond "re-prompting". The Planner module is responsible for generating execution plans, and the Reflector feeds back to the Planner for subsequent cycles, suggesting plan modification is more of an internal loop adjustment rather than direct user manipulation of an active plan via the PWA.

39. **移动客户端的通知系统应该如何设计？哪些事件应触发通知，通知应包含什么信息？**
    Information not available in provided documents; requires further stakeholder input. (While mobile interaction is key, specifics of a notification system are not detailed.)

## 用户体验与界面

40. **移动客户端的用户界面应遵循哪些设计原则？有哪些特定的UX/UI偏好？**
    Information not available in provided documents; requires further stakeholder input. (The client is a "Mobile PWA," but specific design principles or UX/UI preferences are not outlined.)

41. **对于新用户，系统应该提供什么样的入门体验？是否需要引导流程或教程？**
    Information not available in provided documents; requires further stakeholder input. (While there's a "Beta 等候名单" and plans to "Publish transparent blog + collect mobile demo videos," specific onboarding processes are not detailed.)

42. **用户应该如何查看和分析任务执行历史？需要哪些过滤、搜索或可视化功能？**
    *   **Raft-backed Vector Store**: "Stores logs, embeddings, and diff history with durability." (Source: `product_market_fit.md`) This suggests that the raw data for task execution history is available.
    *   **Agent Researchers User Scenario**: Mentions "可重放日志" (replayable logs) as a benefit. (Source: `news_letter.md`) This implies an ability to review execution in detail.
    *   How users view and analyze this history, or specific filtering, searching, or visualization features for the general user via the PWA, are not detailed beyond these points.

43. **如何设计界面使用户能够轻松监控多个并行任务？需要什么样的概览和详情视图？**
    Information not available in provided documents; requires further stakeholder input. (The documents do not currently discuss handling or monitoring multiple parallel tasks from the user's perspective.)

## 近期和远期功能规划

44. **在GUI自动化方面，近期的具体目标是什么？系统应该能够执行哪些类型的GUI操作？**
    *   `product_market_fit.md` mentions a mitigation for "Cursor UI changes break automation" as "Dual-path fallback (hidden command ✚ GUI automation)". This suggests some level of GUI automation capability is considered, at least as a fallback or part of the robustness strategy.
    *   However, specific *近期目标* for proactive GUI automation or the *types* of GUI operations Oppie should perform as a primary function are not detailed in the provided documents. The primary interaction seems to be via "Cursor工具链" (Cursor toolchain), which may or may not always involve GUI interaction directly controlled by Oppie.

45. **对于未来的物理交互能力，您有哪些初步设想和边界定义？这部分功能的优先级如何？**
    Information not available in provided documents; requires further stakeholder input. (The documents focus on code and software development tasks within a digital environment.)

46. **系统的近期MVP（最小可行产品）应该包含哪些核心功能？**
    Based on the documents, an MVP would likely focus on:
    *   **Core Plan ⇄ Execute ⇄ Reflect loop**: This is the fundamental working principle. (Source: `news_letter.md`)
    *   **Remote Task Initiation & Monitoring via Mobile PWA**: The "Job-to-be-done" for early adopters is to "Kick off, monitor, and merge a green PR (or run a research report) from my phone". (Source: `product_market_fit.md`)
    *   **Self-Recovery from Key Interruptions**: Especially the "25-tool-call limit" and basic crash recovery (Crash-Safe). This is a key differentiator ("Proven self-recovery"). (Source: `product_market_fit.md`, `news_letter.md`)
    *   **Basic Checkpoint System**: To enable recovery. (Source: `news_letter.md`)
    *   **Cursor Plugin + Local Sidecar Daemon**: The initial delivery form. (Source: `news_letter.md`)
    *   **Focus on SWE-Bench-Lite success**: The 60-day validation plan aims for "≥ 40 % success on SWE-Bench-Lite," indicating this capability is part of the early goals. (Source: `product_market_fit.md`)

47. **远期规划中，您希望系统能够支持哪些更高级的功能？**
    The "未来路线图" (Future Roadmap) in `news_letter.md` and "Expansion Lanes" in `product_market_fit.md` list several:
    *   **高级规划算法 (Advanced Planning Algorithms)**: Reflexion, ToT (Tree of Thoughts), SFS (Successive Filtering and Synthesis). (Source: `news_letter.md`)
    *   **可插拔 Guard-rails (Pluggable Guard-rails)**: For enterprise-grade security and compliance injection; Guard-Rails SDK. (Source: `news_letter.md`, `product_market_fit.md`)
    *   **Raft Vector Store 2.0 / Code-Atlas**: To support ultra-large codebases with incremental RAG (Retrieval Augmented Generation) and address search latency. (Source: `news_letter.md`, `product_market_fit.md`)
    *   **Edge-VM Runner**: For secure sandbox execution environments; per-minute VM billing. (Source: `news_letter.md`, `product_market_fit.md`)
    *   **Plug-in Mesh**: To easily integrate third-party tools via `oppie.plugin.json`. (Source: `news_letter.md`)

## 测试与验证

48. **您期望采用哪些测试策略来验证系统的各组件？包括单元测试、集成测试、端到端测试等。**
    Information not available in provided documents; requires further stakeholder input. (While validation goals like SWE-Bench success are mentioned, specific testing strategies like unit/integration/E2E tests are not detailed).

49. **对于自动恢复和错误处理功能，应该如何测试以确保其在各种异常情况下的可靠性？**
    *   **Dog-fooding on SWE-Bench-Lite**: The validation roadmap includes running "200 remote SWE-Bench-Lite tasks — hit ≥ 40 % success". This benchmark inherently tests recovery and error handling as it involves real-world scenarios that can lead to failures. (Source: `product_market_fit.md`)
    *   **Monitoring Self-Recovery**: The "Self-Recovery & Tight Loop" is a key asset, and its effectiveness in guaranteeing progress after hitting Cursor's 25-tool-call limit would be a focus of testing. (Source: `product_market_fit.md`)
    *   Specific methodologies for testing various exception types beyond this benchmark are not detailed.

50. **系统的主要风险点是什么？如何设计测试用例来充分探测这些风险点？**
    The `product_market_fit.md` "Risk Register" identifies several key risks and their mitigations. Test cases should be designed to verify these mitigations:
    *   **Risk: Mobile network flakiness interrupts tasks.**
        *   *Mitigation*: Offline queue + Sidecar retry buffer.
        *   *Test Case Idea*: Simulate network interruptions of varying durations during task submission and execution from the PWA; verify that tasks are eventually queued and processed by the Sidecar daemon once connectivity is restored.
    *   **Risk: Cursor UI changes break automation.**
        *   *Mitigation*: Dual-path fallback (hidden command ✚ GUI automation).
        *   *Test Case Idea*: Simulate a scenario where the primary (e.g., command-based) interaction with Cursor fails; verify that the system correctly falls back to GUI automation (or vice-versa) to complete the action.
    *   **Risk: Agents introduce silent bugs.**
        *   *Mitigation*: OTP gating for high-risk commands; diff approval via PWA.
        *   *Test Case Idea*: For defined high-risk operations, verify that OTP is required and that the PWA presents diffs for approval before changes are committed.
    *   **Risk: GPU cost overrun.**
        *   *Mitigation*: Default to o4-mini; auto-kill loops after 15 min.
        *   *Test Case Idea*: Run a task designed to loop or consume excessive GPU; verify it defaults to the o4-mini model (if applicable) and that the auto-kill mechanism triggers after 15 minutes.
    *   **Risk: Cheaper competitor undercuts price.** (This is a market risk, not directly testable via system test cases, but influences feature prioritization towards the "moat" features.)
    *   Assumption: Test cases should be designed to specifically trigger the conditions outlined in the Risk Register and validate the effectiveness of the corresponding mitigation strategies.

51. **应该建立哪些自动化测试流程来持续验证系统功能和性能？**
    *   **SWE-Bench-Lite**: Running SWE-Bench-Lite tasks is part of the validation roadmap ("run 200 remote SWE-Bench-Lite tasks"). This could be automated for continuous validation of core functionality and success rate. (Source: `product_market_fit.md`)
    *   **CI Pass Rate**: The target "CI 通过率 ≥ 92%" (Source: `news_letter.md`) for PRs generated by Oppie implies an automated CI process that tests Oppie's output.
    *   Further specifics on automated test flows are not detailed.

## 额外考虑因素

52. **您对系统的可持续性有哪些考虑？例如，长期维护、社区支持、开源贡献等。**
    *   **开源核心**: The "开源核心 (GPL-3) 即将发布" (Open source core (GPL-3) will be released soon). (Source: `news_letter.md`) This is a key aspect for community support and contributions.
    *   **Monetization for Sustainability**: The product has a clear monetization strategy (Starter/Pro tiers, Cloud Runner add-on, Guard-Rails SDK license, Code-Atlas managed cluster) aimed at financial sustainability. (Source: `product_market_fit.md`)
    *   **Long-term Vision**: The future roadmap items like Plug-in Mesh and advanced planning algorithms suggest a plan for ongoing development and relevance.
    *   Specifics on long-term maintenance plans beyond these are not detailed.

53. **您是否有任何特定的法规遵从要求（如GDPR、CCPA等）需要系统满足？**
    *   **Guard-Rails SDK for Compliance**: The Guard-Rails SDK is mentioned as a way for "Teams [to] demand SOC-2 / HIPAA audit trail". (Source: `product_market_fit.md`) This indicates an awareness and a mechanism to support enterprise compliance needs.
    *   No other specific regulations like GDPR or CCPA are explicitly mentioned as requirements in the provided documents.

54. **您对系统的文档和用户指南有哪些具体要求？**
    *   **Transparent Blog**: Part of the 60-day validation roadmap is to "Publish transparent blog". (Source: `product_market_fit.md`)
    *   **Mobile Demo Videos**: Also part of the validation roadmap is to "collect mobile demo videos". (Source: `product_market_fit.md`)
    *   These suggest a focus on clear communication and demonstration, but specific requirements for formal documentation or user guides are not detailed.

55. **现有技术组件（如e2b-dev/desktop、OpenAI CodexCLI、Reflexion等）的API和能力边界可能如何限制系统设计？有哪些潜在的替代方案？**
    *   **Cursor's 25-tool-call limit**: This is an explicitly acknowledged limitation of a key component (Cursor). Oppie's "Self-Recovery & Tight Loop" feature is designed specifically to mitigate this, turning a potential limitation into a showcase of Oppie's robustness. (Source: `news_letter.md`, `product_market_fit.md`)
    *   **Cursor UI changes breaking automation**: This is another acknowledged risk tied to a dependency on Cursor's UI. The mitigation is a "Dual-path fallback". (Source: `product_market_fit.md`)
    *   The documents do not detail other specific API/capability boundaries of other components or list potential alternative components. The approach seems to be building robustly around known limitations where possible.

56. **您对系统的初期使用场景和用户反馈收集有什么具体计划？**
    *   **Initial Use Cases (User Scenarios from Newsletter)**:
        *   OSS Maintainer: Waking up to find `good-first-issue` turned into a CI-passing PR.
        *   Indie Hacker: Using Oppie for overnight tests to speed up MVP iteration.
        *   Agent Researcher: Leveraging replayable logs and recovery for less experimental randomness.
        *   Developer stepping away: Oppie takes over bug fixing.
    *   **Early Adopters**: "Indie maintainers, bootstrapped SaaS teams, digital nomads." (Source: `product_market_fit.md`)
    *   **Validation Roadmap (Feedback Collection)**:
        *   **Dog-fooding**: Internally running SWE-Bench-Lite tasks.
        *   **Private beta**: "onboard 5 OSS maintainers; measure cost-per-merged-PR."
        *   **Retention probe**: "track repeat PWA usage & 'Run again' clicks."
        *   **Pricing test**: "$9 vs $49 tiers."
        *   "Publish transparent blog + collect mobile demo videos."
        (Source: `product_market_fit.md`)

57. **可能的问题场景：如果任务执行部分成功但遇到限制，系统应该如何确定保留哪些已完成工作并从何处重新开始？**
    *   **Checkpoints Protocol**: "每步执行后对比差异哈希，偏差大即回退重试." (After each execution step, compare diff hashes; if deviation is large, roll back and retry.) This implies that work is committed or understood at the granularity of an "execution step". (Source: `news_letter.md`)
    *   **Crash‑Safe**: "Oppie 从上次检查点断点续传." (Oppie resumes from the last checkpoint.) (Source: `news_letter.md`)
    *   **Real-time diff recording**: The Executor "实时记录 diff". (Source: `news_letter.md`)
    *   **Raft-backed Vector Store**: Stores "diff history". (Source: `product_market_fit.md`)
    *   These mechanisms suggest that the system tracks changes incrementally (diffs) and uses checkpoints to establish recovery points. If a limitation is hit, it would resume from the last known good checkpoint, effectively retaining work up to that point. The exact logic for determining "which work to keep" if a step is partially complete before a crash isn't minutely detailed but is based on the last successful checkpoint.

58. **您有哪些关于系统可扩展性的长期愿景？例如，未来是否计划支持更多类型的AI代理或任务类型？**
    The system is designed with extensibility in mind:
    *   **Plug-in Mesh**: For integrating third-party tools. (Source: `news_letter.md`)
    *   **Advanced Planning Algorithms**: Incorporating Reflexion, ToT, SFS implies evolving the AI capabilities, which could extend to different types of AI代理 or more complex tasks. (Source: `news_letter.md`)
    *   **Edge-VM Runner**: Secure sandbox environments could support a wider range of (potentially less trusted) tools or agents. (Source: `news_letter.md`)
    *   While not explicitly stating "more types of AI agents" or an exhaustive list of "task types," the architectural choices (modular design, plugin system, evolving planning algorithms) strongly suggest a vision for a broadly extensible and adaptable platform.

59. **还有其他任何我们尚未讨论但您认为重要的方面？**
    Based on the provided documents, the following are emphasized as important:
    *   **The "Oppy" Analogy and Brand Identity**: The inspiration from the Mars rover Opportunity (Oppy) – emphasizing autonomy, resilience, longevity, and even an emotional connection (trust, reliability) – is a significant aspect of the product's narrative and values ("传承 机遇号Opportunity 的坚韧与忠诚"). (Source: `news_letter.md`)
    *   **Trust and Reliability**: Repeated emphasis on "lifts trust for unattended runs," "fewer stalls, higher trust," and robust recovery mechanisms. (Source: `product_market_fit.md`, `news_letter.md`)
    *   **Pricing Strategy and Market Positioning**: The gap between Cursor's pricing and fully managed agents, and Oppie's positioning within that gap with specific tiers and add-ons. (Source: `product_market_fit.md`)
    *   **Open Source Core**: The plan to release the core as GPL-3. (Source: `news_letter.md`)

</rewritten_file> 