# Oppie Remote Cursor Control Mesh (M1) — High-Level Design  
*(Planner ⇄ Executor tight loop, mobile-triggered, with self-recovery — market brand **SoraSpark**, internal codename **oppie.xyz**)*

---

## 1 Executive Summary & MVP Goal

**M1**现在基于**OpenHands ACI**重构，Oppie的VS Code扩展主要作为适配器，在Cursor与OpenHands之间传递事件。移动PWA消费相同的轨迹流。

* **Primary job-to-be-done:**  Kick off a coding or research task from the phone (e.g. *Fix failing tests*) and watch it finish without human intervention, even if Cursor hits the 25 tool-call limit.
* **Success criteria:**  After the user taps the button on the phone, the plan is generated, executed, diffs streamed live, and the task completes or reports error.  Cursor limitations must never stall the loop for > 3 s; overall unattended success-rate ≥ 40 % and P95 push latency < 500 ms.

---

## 2 Requirements (snapshot)

| Category        | Must-have                                                                                                             |
|:----------------|:----------------------------------------------------------------------------------------------------------------------|
| **Functional**  | • Autonomous Planner ⇄ Executor loop inside Cursor.<br>• Remote trigger via SoraSpark PWA → Cloud Relay → Sidecar Daemon.<br>• Real-time progress & diff streaming back to the phone.<br>• Seamless self-recovery when Cursor reaches 25 tool-call limit **or** a Composer bubble misses **Template A**. |
| **Non-functional** | • ≤ 250 ms average overhead per recovery.<br>• ≥ 40 % unattended success-rate on SWE-Bench Lite.<br>• **P95 push latency < 500 ms** to mobile.<br>• < 1 % false-positive recoveries.<br>• No manual action required after the initial *Start Dev-Loop* VS Code task. |
| **Constraints** | • All core logic runs on the developer's workstation; cloud components are stateless.<br>• Use only languages that support true concurrency (Python 3.12, TypeScript, Go if needed). |

---

## 3 System Architecture

```mermaid
digraph G
  subgraph "Mobile & Cloud"
    PWA["📱 SoraSpark PWA"]
    Relay["🔄 Secure Relay\nWSS + JWT"]
  end
  subgraph "Host Workstation"
    Sidecar["🖥️ Sidecar Daemon\n(Python 3.12)"]
    Ext["🧩 Cursor Extension Core\n(TypeScript)"]
    OpenHands["🔄 OpenHands ACI Stack"]
    Planner["🤖 Codex Planner (o3)"]
    Executor["🛠️ Cursor Executor"]
    Watcher["👁️‍🗨️ Dev-Loop Watcher\n(Python)"]
  end
  PWA -> Relay -> Sidecar
  Sidecar -> Ext [label="IPC"]
  Ext -> OpenHands
  OpenHands -> Planner [label="plan →"]
  Planner -> Executor [label="Template A"]
  Executor -> Watcher [label="stdout / stderr"]
  Watcher -> Executor [label="recovery-prompt"]
  OpenHands -> Ext [label="events"]
  Ext -> PWA [label="progress / diff"]
```

*The **Dev-Loop Watcher** acts as an immune system that guarantees forward progress, while the **OpenHands ACI Stack** provides a comprehensive agent system with planning, execution, and reflection capabilities.*

---

## 4 Component Catalogue

| # | Component                         | Responsibility                                                                    | Key Tech                             |
|:-:|-----------------------------------|------------------------------------------------------------------------------------|--------------------------------------|
| 1 | **Cursor Extension Core**         | IPC server, exposes `Oppie:executePlan`, renders Webview timeline                  | VS Code Extension API                |
| 2 | **OpenHands ACI Stack**          | Agent planning, runtime execution, trajectory recording, function calling          | OpenHands CodeActAgent              |
| 3 | **OpenHands Adapter**            | 将Template A与OpenHands事件流互相转换，提供兼容层                                       | TypeScript/Python适配器              |
| 4 | **Sidecar Daemon**                | Bridges Cloud Relay & IPC; provides keystroke fallback when Extension fails       | `websockets`, `pyautogui`            |
| 5 | **Dev-Loop Watcher**              | Monitors Cursor Executor logs, fires recovery prompt when needed                  | Python 3.12                          |
| 6 | **Trajectory Visualizer**        | 实时可视化执行轨迹、事件流和文件变更                                                      | React + TailwindCSS                 |

---

## 5 Core Data & Control Flows

1. **Trigger** PWA sends `runPlan` over WSS to the Sidecar.
2. **Plan** Extension calls OpenHands ACI → CodeActAgent produces a structured plan.
3. **Execute** OpenHands Runtime执行计划，每个步骤产生事件流通过Extension传输到PWA。
4. **Recovery** 如果Executor logs中发现`Exceeded 25 native tool calls` **or** bubble缺失*Template A*，Watcher输入恢复指令；OpenHands的BudgetManager自动处理工具调用限制。
5. **Verify** OpenHands Reflection机制检查执行状态并学习失败模式。

---

## 6 Tech Stack (summary)

| Layer             | Choice                    | Justification                                               |
|-------------------|---------------------------|-------------------------------------------------------------|
| Language (Host)   | Python 3.12, TypeScript   | Rich stdlib + VS Code APIs                                  |
| Agent Framework   | OpenHands ACI             | 成熟的代理系统，内置事件流、运行时和向量存储                        |
| GUI Automation    | OpenHands Runtime / pyautogui | 主要通过OpenHands Runtime，保留pyautogui作为fallback           |
| Embeddings        | OpenHands VectorAdapter   | 支持多种后端（FAISS、Milvus等），统一API                          |
| Packaging         | `pnpm build` (extension), `pyinstaller` (watcher) | Single-file distribution                         |

---

## 7 Deployment & VS Code Tasks

```text
.vscode/tasks.json
└─ "Start Oppie Dev-Loop"  →  ./scripts/start_devloop.sh
```

`start_devloop.sh` 启动 **Codex Planner** 和 **OpenHands Server**，并启动 **Dev-Loop Watcher**。可使用 `OPENHANDS_ENABLED=true` 控制是否启用OpenHands。任务配置了 `"runOn": "folderOpen"` 以便打开项目时自动启动整个循环。

---

## 8 Alignment with .cursorrules & codex.md

重构后的设计仍保持了递归的 *Template A* 驱动的 **Planner ⇄ Executor** 循环，同时通过OpenHands扩展了其能力：

* **Watcher** 仍然负责强制执行 *Template A* 的存在，并在 25 工具调用后恢复（规则 `FINAL DOs AND DON'Ts`）。
* **OpenHands ACI** 运行在 Executor 的控制下，因此其步骤通过原生工具调用表达，保持在 Cursor 治理内（规则 `cursor_native_tooling`）。
* 所有组件仍在本地运行，遵守 **no cloud agent orchestration** 约束。
* 移动和云层仍是无状态中继；它们不违反规则限制，也不需要 Executor 工具调用。

---

## 9 Future Evolution (post-M1)

1. **OpenHands Function Library** 扩展OpenHands的function calling能力，支持更多Cursor特定操作。
2. **Reasoning Adapters** 利用OpenHands的插件机制添加推理增强（如ToT、Reflexion）。
3. **Fine-grained Usage Metering** JWT claims映射到Cursor使用事件，用于团队计费。

---

> **End of High-Level Design (M1).**  All further work must reference this file as the single source of truth.
