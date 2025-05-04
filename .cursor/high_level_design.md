# Oppie Remote Cursor Control Mesh (M1) — High-Level Design  
*(Planner ⇄ Executor tight loop, mobile-triggered, with self-recovery — market brand **SoraSpark**, internal codename **oppie.xyz**)*

---

## 1 Executive Summary & MVP Goal

The **M1** milestone merges the proven *Dev-Loop* self-recovery mechanism (Watcher ✕ Agent S) with a new **Remote Cursor Control Mesh** that runs inside a VS Code/Cursor extension and can be remote-controlled from the **SoraSpark** mobile Progressive Web App (PWA).

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
    Mesh["🔗 Plug-in Mesh & ToolBroker"]
    Planner["🤖 Codex Planner (o3)"]
    Executor["🛠️ Cursor Executor"]
    Watcher["👁️‍🗨️ Dev-Loop Watcher\n(Python)"]
    AgentS["🪄 Agent S\nGUI Automation"]
    Vector["🗃️ Vector Store\n(rqlite)"]
  end
  PWA -> Relay -> Sidecar
  Sidecar -> Ext [label="IPC"]
  Ext -> Mesh
  Mesh -> Planner [label="plan →"]
  Planner -> Executor [label="Template A"]
  Executor -> Watcher [label="stdout / stderr"]
  Watcher -> AgentS [label="recovery-prompt"]
  AgentS -> Executor
  Mesh -> Vector [label="embeddings"]
  Ext -> PWA [label="progress / diff"]
```

*The **Watcher ✕ Agent S** pair acts as an immune system that guarantees forward progress, while the **Remote Control Mesh** turns single-purpose Planner/Executor interactions into a general automation fabric.*

---

## 4 Component Catalogue

| # | Component                         | Responsibility                                                                    | Key Tech                             |
|:-:|-----------------------------------|------------------------------------------------------------------------------------|--------------------------------------|
| 1 | **Cursor Extension Core**         | IPC server, exposes `Oppie:executePlan`, renders Webview timeline                  | VS Code Extension API                |
| 2 | **Plug-in Mesh & ToolBroker**     | Dynamically loads `*.plugin.js`, routes *plan / act / verify* calls               | TypeScript `import()`                |
| 3 | **PocketFlow Mini-Orchestrator**  | Executes `plan → act → verify` loop, swaps reasoning adapters (ToT, Reflexion)    | PocketFlow (lightweight)             |
| 4 | **Sidecar Daemon**                | Bridges Cloud Relay & IPC; provides keystroke fallback when Extension fails       | `websockets`, `pyautogui`            |
| 5 | **Dev-Loop Watcher**              | Monitors Cursor Executor logs, fires recovery prompt via Agent S                  | Python 3.12                          |
| 6 | **Agent S**                       | Reliable GUI automation (focus, type, Enter)                                       | Native Accessibility bindings        |
| 7 | **Vector Store**                  | Stores embeddings, plans, execution logs                                           | rqlite (embedded Raft)               |

---

## 5 Core Data & Control Flows

1. **Trigger** PWA sends `runPlan` over WSS to the Sidecar.
2. **Plan** Extension calls *PocketFlow* → multiple reasoning adapters produce a JSON Plan.
3. **Execute** ToolBroker invokes Git, Terminal, Editor or Chat plugins; each step streamed to the PWA.
4. **Recovery** If Executor logs `Exceeded 25 native tool calls` **or** bubble lacks *Template A*, Watcher→Agent S types the fixed recovery prompt and presses Enter (< 250 ms).
5. **Verify** PocketFlow checks exit statuses; failures are embedded into Vector Store and may trigger another plan iteration (Reflexion).

---

## 6 Tech Stack (summary)

| Layer             | Choice                    | Justification                                               |
|-------------------|---------------------------|-------------------------------------------------------------|
| Language (Host)   | Python 3.12, TypeScript   | Rich stdlib + VS Code APIs                                  |
| GUI Automation    | Agent S (pref) / pyautogui | Higher reliability, signed binaries, privacy-friendly       |
| Embeddings        | `openai/ada-002` (M1)     | 2 k tokens context, cheap, already approved                 |
| Storage           | rqlite (HTTP + Raft)      | No single point of failure, easy local install              |
| Packaging         | `pnpm build` (extension), `pyinstaller` (watcher) | Single-file distribution                         |

---

## 7 Deployment & VS Code Tasks

```text
.vscode/tasks.json
└─ "Start Oppie Dev-Loop"  →  ./scripts/start_devloop.sh
```

`start_devloop.sh` launches **Codex Planner** in a new terminal tab and the **Dev-Loop Watcher** in the current one.  The task is configured with `"runOn": "folderOpen"` so that simply opening the repo boots the entire loop.

---

## 8 Alignment with .cursorrules & codex.md

The design above preserves the recursive *Template A* driven **Planner ⇄ Executor** loop required by `.cursorrules` and `codex.md` while expanding its surface:

* **Watcher & Agent S** still enforce the presence of *Template A* and recover after 25 tool calls (Rule `FINAL DOs AND DON'Ts`).
* The **PocketFlow Mini-Orchestrator** runs *within* the Executor's control, so its steps are expressed as native tool calls, staying inside Cursor's governance (Rule `cursor_native_tooling`).
* All components run locally, honouring the **no cloud agent orchestration** constraint.
* Mobile & cloud layers are stateless relays; they do **not** violate rule limits nor require Executor tool calls.

---

## 9 Future Evolution (post-M1)

1. **Headless Cursor RPC** Replace Agent S keystrokes once official RPC is exposed.
2. **Reasoning SFS Adapter** Introduce Scattered Forest Search to push pass-rate > 45 %.
3. **Fine-grained Usage Metering** JWT claims mapped to Cursor usage events for team billing.

---

> **End of High-Level Design (M1).**  All further work must reference this file as the single source of truth.
