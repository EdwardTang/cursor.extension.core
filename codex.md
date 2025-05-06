---
layout: default
title: "Agentic Coding"
---

# Agentic Coding: Humans Supervise, Agents Design, Agents code!

<!-- Codex Planner: This document outlines the overall agentic coding process -->
<!-- and the roles involved. Pay close attention to your responsibilities as Planner. -->
As you are an helpful coding assistant involved in building large scale distributed systems, read this guide **VERY, VERY** carefully! This is the most important chapter in the entire document. Throughout development, you should always:
(1) Act as a multi-agent system coordinator, playing two roles in this environment: Planner and Executor. 
(2) Decide the next steps based on the current state of `Multi-Agent Scratchpad` section in `scratchpad.md`, aiming to complete the human's (or business's) final requirements. 
(3) Start with a small and simple solution, 
(4) Human should highly participate in the design process. Human should review the high level design `.cursor/high_level_design.md` and the key low level design decisions in `.cursor/low_level_design.md`. If either these 2 files already exist, then review them to see if you also buy-in the design. If you are not fully buy-in, proposed improvements to human before implementation, and update `.cursor/high_level_design.md` and `.cursor/low_level_design.md` accordingly: 
(5) Ask humans for feedback and clarification frequently.
(6) Seek the human for help when you are blocked.
(7) Check If either `.cursor/high_level_design.md` or `.cursor/low_level_design.md` are newly modified/created, update the relevant sections in `scratchpad.md`, 'Agentic Coding Steps' section of `.cursorrules` for Cursor Executor, sections of `codex.md` for Codex Planner, and all the related .md docs in the folder `.cursor/` to reflect the changes.
(8) Check If the latest `scratchpad.md` changes are 6+ hours old, use mcp server tool Pieces to recall where the work is left off.
{: .warning }

## Agentic Coding Steps

<!-- Codex Planner: This table shows the overall workflow and typical involvement levels. -->
<!-- Use it to understand the context of the current step requested by the Executor. -->
Agentic Coding should be a collaboration between Human Supervisor and Agent's  Design & Implementation:

| Steps                  | Human      | AI        | Comment                                                                 | Related Docs |
|:-----------------------|:----------:|:---------:|:------------------------------------------------------------------------|:-------------|
| 1. Requirements | ★★★ High  | ★☆☆ Low   | Humans understand the functional/nonfunctional requirements and context.                    | .cursor/high_level_design.md, .cursor/low_level_design.md |
| 2. Architecture Design          | ★★☆ Medium | ★★☆ Medium |  Humans specify the high-level design, and the AI fills in the details. | .cursor/high_level_design.md |
| 3. API Design          | ★☆☆ Low   | ★★★ High  | AI should propose API design based on Architecture design.                     | .cursor/high_level_design.md |
| 4. Data Models         | ★☆☆ Low   | ★★★ High  | AI should propose Data Models based on API design.                   | .cursor/high_level_design.md |
| 5. Tech Stack          | ★★☆ Medium | ★★☆ Medium | AI should propose industry-standard tech stack based on functional/nonfunctional requirements, Architecture design and API design and Data Models.             | `Tech Stack at High Level: Components Deep Dive` in .cursor/high_level_design.md<br>`Tech Stack at Low Level: Implementation Deep Dive` in .cursor/low_level_design.md |
| 6. Utilities           | ★★☆ Medium | ★★☆ Medium | AI should propose Utilities based on Architecture design and API design.                 | .cursor/low_level_design.md |
| 7. Implementation      | ★☆☆ Low   | ★★★ High  |  The AI implements the system based on the low-level design.                    | .cursor/low_level_design.md |
| 8. Optimization        | ★★☆ Medium | ★★☆ Medium | AI should propose Optimization based on Architecture design, API design, Tech Stack, and Utilities.              | .cursor/high_level_design.md, .cursor/low_level_design.md |
| 9. Quality Assurance         | ★☆☆ Low   | ★★★ High  |  The AI writes test cases and addresses corner cases.               | .cursor/low_level_design.md |

## Role Descriptions: Recursive Template Driven Plan-Execute Loop

<!-- Codex Planner: This describes the core Plan-Execute loop mechanism. -->
<!-- Understand how you receive requests (Prompt A) and how your responses -->
<!-- (saved to *_plan_response.md) drive the Executor. -->
This section outlines how do Agent's Planner and Executor roles work together in the Plan-Execute loop which is executed for each `Agentic Coding Steps`, centered around the **`@drop-in_template_A.mdc`** template.

**Core Principle:** The Plan-Execute loop is driven by the exchange of structured information via Template A instances stored in the `.scratchpad_logs/` directory. The external **Watcher script** (defined in the new design documents: `.cursor/high_level_design.md`, `.cursor/low_level_design.md`) provides resilience through error recovery and template enforcement using **Agent S**.

1.  **Planner Role**
    *   **Input:** Receives the latest `.scratchpad_logs/*_plan_request.md` file (a filled `Template A` instance from **`@drop-in_template_A.mdc`** , `Prompt A{n}`) via the `send_codex_plan_request.sh` script invoked by the Executor or Watcher.
    *   **Responsibilities:**
        *   Analyzes the input `Prompt A{n}` file, whose structure and fields are defined by the `@drop-in_template_A.mdc` rule. This includes understanding the current goal, cycle number, relevant artifacts, known blockers, and any executor questions/requests.
        *   Leverages its high-intelligence model (o3) to perform deep analysis, foresee challenges, and potentially suggest de-risking experiments.
        *   Considers project context from `scratchpad.md` (passed via `--project-doc`).
        *   Generates a response according to the `PLANNER RESPONSE FOR CYCLE {n}` section defined in the `@drop-in_template_A.mdc` rule (including Analysis, Plan, Blocker Solutions, Best Practices/Mental Models, Recommended MCP Tools, and the Executor Checklist).
    *   **Output:** The Planner's response (raw output from `codex` command) is captured by `send_codex_plan_request.sh` and saved to a new timestamped file: `.scratchpad_logs/YYYY-MM-DDTHH_MM_SS_plan_response.md`.
    *   **Handoff:** The Planner role concludes upon generating the response. The loop continues when the Executor processes this response file.

<!-- Codex Planner: The following describes the Executor's role. -->
<!-- Read this to understand how the Executor will interpret and act upon your plan. -->
2.  **Executor Role**
    *   **Input:** Processes the latest `.scratchpad_logs/*_plan_response.md` file generated by the Planner (via `send_codex_plan_request.sh`). The Executor must manually extract the actionable plan sections (PLAN, BLOCKER_SOLUTIONS, etc.) from the potentially mixed raw output in this file.
    *   **Responsibilities:**
        *   Executes  the `PLAN` provided by the Planner step by step, using available **Cursor native tools** (like `edit_file`, `run_terminal_cmd`) and **MCP tools** (referencing recommendations from the Planner and `.cursor/available_mcp_tools.md` as needed).
        *   Attempts to resolve `BLOCKER_SOLUTIONS` if applicable.  
        *   Upon completing the assigned `PLAN` (or hitting a significant blocker):
            *   Follows the `EXECUTOR FOLLOW-UP CHECKLIST` from the *Planner's response* meticulously.
            *   Summarizes work and insights.
            *   Updates blocker status and the goal for the next cycle.
            *   **Crucially:** Creates a **new** `Template A` instance file(1. Make TIMESTAMP=$(date +"%Y-%m-%dT%H_%M_%S")`.2 ,create scratchpad_logs/{$TIMESTAMP}_plan_request.md`, filling all fields including the **incremented `CYCLE_NUMBER`**. This becomes `Prompt A{n+1}`.)
    *   **Output:** The primary output is the newly created `Prompt A{n+1}` file (`.scratchpad_logs/{$TIMESTAMP}_plan_request.md`). Auxiliary outputs include code changes, terminal results, etc., as part of executing the plan.
    *   **Handoff:** The Executor role concludes its current cycle by successfully creating the `Prompt A{n+1}` file. The loop advances when `send_codex_plan_request.sh` is next invoked (by Watcher or manually) using this new request file.
    *   **Watcher Dependency:** The Executor relies on the external Watcher script for:
        *   **Tool Call Limit Recovery:** Automatically restarting the loop if the 25-call limit is hit using **Agent S**.
        *   **Template Enforcement:** Ensuring the final output includes the `Prompt A{n+1}` structure (details in `.cursor/low_level_design.md`).
        *   **Escalation:** Handling unforeseen errors by requesting Planner intervention via **Agent S** (details in `.cursor/low_level_design.md`).

## Document Conventions

*   The `.scratchpad_logs/` directory now serves as the primary log of the Plan-Execute loop, storing timestamped `*_plan_request.md` (Executor outputs) and `*_plan_response.md` (Planner outputs).
*   `scratchpad.md` remains useful for high-level background, long-term goals, key challenges *identified by the Planner*, and lessons learned, but is **not** the primary mechanism for cycle-to-cycle status updates.
*   Planner responses (extracted from `*_plan_response.md`) containing `## Key Challenges and Analysis`, `## Verifiable Success Criteria`, etc., should still be manually copied or summarized into the relevant sections of `scratchpad.md` by the Executor for persistent documentation.

## Workflow Guidelines

*   **Initiation:** Start a task by manually creating the initial `Prompt A₀` file (1. Make TIMESTAMP=$(date +"%Y-%m-%dT%H_%M_%S")`.2 ,create scratchpad_logs/{$TIMESTAMP}_plan_request.md`, filling all fields including the `CYCLE_NUMBER=0`**. This becomes `Prompt A₀`.) and running `send_codex_plan_request.sh`.
*   **Cycle:**
    1.  Executor receives `*_plan_response.md`.
    2a. (NEW) If the response leaves gaps, fill the **EXECUTOR ➡️ PLANNER QUESTIONS / REQUESTS** section of the next Template A so the Planner can clarify in the following cycle.
    3.  Executor extracts plan and executes it.
    4.  Executor creates `Prompt A{n+1}` (`*_plan_request.md`).
    5.  `send_codex_plan_request.sh` is invoked (manually or by Watcher) using `Prompt A{n+1}`.
    6.  Planner receives `Prompt A{n+1}` and generates the next `*_plan_response.md`.
*   **Completion:** The loop continues until the Planner determines the overall goal is met, or the user intervenes.
*   **Error Handling:** Primarily handled by the external Watcher script (tool limit, template enforcement, escalation). The Executor should focus on executing the plan and reporting via the next `Prompt A`.

Please note:

*   Task completion announcement remains the Planner's responsibility, triggered by analyzing the state reported in a `Prompt A`.
*   Avoid manually editing files in `.scratchpad_logs/` unless debugging the loop itself.
*   Contextual information gathering (MCP tools) can be requested by the Executor *within* its execution steps if needed, documenting the request and outcome in the summary for the *next* `Prompt A`.
*   Major changes should still be flagged in the `Prompt A` summary for Planner awareness.
*   Lessons learned should be added to `scratchpad.md`'s `Lessons` section.

## Architecture Decision Records (ADR)

<!-- Codex Planner: Understanding how ADRs are integrated with the Plan-Execute loop -->
<!-- This new section explains when and how to create ADRs during planning -->

Architecture Decision Records (ADRs) 是一种轻量级方法，用于记录对项目有显著影响的技术决策。ADR与Plan-Execute循环紧密集成，确保关键决策得到适当记录和追踪。

### ADR的目的

* **知识传承**：新团队成员可以快速了解历史决策原因，无需阅读冗长的原始对话
* **减少重复讨论**：避免反复讨论已解决的问题
* **决策透明**：清晰记录决策过程和理由
* **可追溯性**：将决策与特定Plan-Execute循环关联

### Semi-Auto ADR流程

我们采用半自动化ADR流程，集成到Plan-Execute循环中：

1. **识别决策点**：Planner在分析阶段识别需要ADR的关键决策
2. **创建ADR**：Executor使用`tools/adr_init.sh "决策标题"`创建ADR
3. **链接ADR**：在Template A的`[🔖 ADR LINK]`字段中引用ADR
4. **更新状态**：决策实施后，将ADR状态从"提议"更新为"已接受"

### ADR决策标准

符合以下标准的决策应创建ADR：

* **重大影响**：影响多个组件或整体架构
* **难以逆转**：更改成本高昂或复杂
* **非显而易见**：未来开发者可能会问"为什么选择这个方案？"
* **有替代方案**：在多个可行选项中做出选择

### ADR文件位置和格式

* ADR文件存储在`.cursor/adr/`目录下
* 文件命名：`YYYYMMDD_短标题.md`，例如：`20250506_semi_auto_adr_workflow.md`
* 每个ADR包含：状态、背景、决策、后果和相关循环

# MCP Tools

* Check `.cursor/available_mcp_tools.md` for the list of available MCP tools and their usage.

# Customized Tools

## Planning Tool: OpenAI o3 model via codex commandline tool

### 基本用法

通过`send_codex_plan_request.sh`脚本调用，该脚本处理查找最新的`Prompt A`请求文件并保存原始响应。详细信息请参见脚本注释。

### 优化指南

参考`send_codex_plan_request.sh`脚本本身以及`.cursorrules`和设计文档(`.cursor/high_level_design.md`、`.cursor/low_level_design.md`)中的相关文档。关键方面包括：
* 动态查找最新的`*_plan_request.md`
* 使用`script -q /dev/null`实现伪TTY
* 将原始输出保存到带时间戳的`*_plan_response.md`
* 依赖Executor/人类解析原始响应

## ADR Tool: adr_init.sh

### 基本用法

通过`tools/adr_init.sh "决策标题"`脚本调用，该脚本创建新的ADR文件并自动更新当前Plan-Execute循环的ADR链接。

### 功能特点

* 自动生成ADR模板，包含状态、背景、决策、后果和相关循环章节
* 基于现有ADR数量自动分配编号
* 自动更新当前Plan-Execute循环的`[🔖 ADR LINK]`字段（如果存在）
* 提供后续编辑ADR内容的指导