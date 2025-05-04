# Oppie.xyz — Agentic Coding Assistant PRD (v0.5)

---

## 1  Overview
Inspired by the resilience and autonomy of NASA's Mars rover Opportunity (Oppy), Oppie.xyz is envisioned as an **agentic coding assistant** native to the Cursor IDE. It acts as your "code rover," capable of navigating complex codebases and executing development tasks autonomously, even when you're away from the keyboard. Oppie operates on a core **Plan ⇄ Execute ⇄ Reflect** loop, enhanced with robust self-recovery and persistence mechanisms. This document outlines the requirements for building Oppie.xyz, evolving from the initial remote control/recovery MVP towards the full vision.

A Sidecar Daemon bridges a mobile PWA interface to the local Cursor instance, enabling remote monitoring and control, while also facilitating rapid self-recovery from limitations like the tool call cap.

---

## 2  Goals & Success Metrics
| KPI | Target | Notes |
| --- | --- | --- |
| **Plan-Execute Cycle Time (P95)** | < 5 minutes | Time for one meaningful iteration on a typical task. |
| **Autonomous Task Success Rate** | ≥ 40 % on SWE-Bench-Lite | Unattended execution, measured by CI pass / functional correctness. |
| **Recovery Success Rate** | 100 % | Of detected "25 native tool calls" limit errors. |
| **P95 Recovery Latency** | < 150 ms | From stderr detection to recovery prompt injection. |
| **Mobile Push Latency (P95)** | < 500 ms | From desktop event (e.g., diff generated) to phone UI update. |
| **CI Pass Rate on Generated PRs** | ≥ 92% | For tasks completed autonomously by Oppie. |
| **User NPS (Pilot Group)** | ≥ +30 | After 2 weeks of using core loop + remote features. |

---

## 3  Problem Statement
Developers need a reliable agent that can persistently work on coding tasks (e.g., fixing bugs, implementing features, running tests, refactoring) even through interruptions like IDE/OS restarts, network issues, or hitting platform limits (like Cursor's tool call cap). Current workflows require significant human supervision, especially for longer tasks. Oppie.xyz aims to provide this persistent autonomy, allowing developers to confidently delegate tasks and stay informed remotely via a mobile interface.

---

## 4  Guiding Principles
1.  **Autonomy & Resilience:** Oppie should strive to complete tasks independently and recover gracefully from common interruptions.
2.  **Plan-Execute-Reflect Cycle:** The core loop drives iterative progress and adaptation.
3.  **Checkpoint-driven Persistence:** State is saved frequently, enabling crash recovery and rollback.
4.  **Mobile-first Interaction (for Remote):** Critical status updates and controls are accessible via the PWA.
5.  **Observability:** Clear logging and metrics for understanding agent behavior.
6.  **Isolation & Safety:** Minimize direct modification of Cursor internals; use official APIs or GUI automation cautiously. Implement guardrails.
7.  **Simplicity (for Components):** Keep individual components (Sidecar, PWA) focused and maintainable.

---

## 5  Functional Requirements
| ID      | Module / Feature          | Requirement                                                                                                | Priority | Notes |
| :------ | :------------------------ | :--------------------------------------------------------------------------------------------------------- | :------- | :---- |
| **Core Loop** |                       |                                                                                                            |          |       |
| FR-C1   | Planner                   | Analyze user requests & project context; break down tasks into executable steps with checkpoints.        | P0       | Uses LLM (e.g., Codex o3). |
| FR-C2   | Executor                  | Execute planned steps using Cursor native tools & MCP tools; capture diffs/outputs accurately.           | P0       | Wraps Cursor's execution. |
| FR-C3   | Reflector                 | Summarize execution results, identify deviations/blockers, format feedback for the Planner's next cycle. | P0       | Template-driven communication. |
| FR-C4   | Landing Context           | On first run or context change, index the relevant codebase into a persistent Vector Store (Raft).        | P1       | For efficient RAG. |
| **Persistence & Recovery** |        |                                                                                                            |          |       |
| FR-PR1  | Checkpoint Protocol       | Save execution state (code diffs, tool outputs, logs) at each checkpoint defined by the Planner.          | P0       | Enables resume/rollback. |
| FR-PR2  | Crash Recovery            | On restart (IDE/OS/Sidecar), automatically resume execution from the last successful checkpoint.           | P0       | "Crash-Safe". |
| FR-PR3  | Tool Limit Detection      | Monitor Cursor Executor's stdout/stderr for the exact `Exceeded 25 native tool calls` string.            | P0       | Via Sidecar Daemon. |
| FR-PR4  | Tool Limit Recovery       | Trigger GUI automation (via Sidecar) to inject the recovery prompt into Cursor Composer input.            | P0       | Target <150ms latency. |
| FR-PR5  | Recovery Logging          | Log `RECOVER_TRIGGERED` and `RECOVER_ACTION_SENT` events with timestamps and plan context hash.            | P0       | For observability. |
| **Remote Interface (PWA)** |        |                                                                                                            |          |       |
| FR-RI1  | Live Progress Push        | Sidecar pushes key events (plan start, step execution, diff generated, errors, recovery) to PWA via Relay. | P0       | WSS connection. |
| FR-RI2  | PWA Display               | PWA displays current status, recent logs, generated diffs, and active plan.                              | P0       | React + Vite PWA. |
| FR-RI3  | PWA Controls              | PWA provides controls to Pause / Resume execution, Approve/Reject Diffs (if guardrail requires).           | P1       | Sends commands back via Relay. |
| FR-RI4  | Remote Task Initiation    | Allow initiating predefined or simple tasks (e.g., "run tests", "fix this issue #123") from PWA.       | P2       | Future enhancement. |
| **Safety & Monitoring** |            |                                                                                                            |          |       |
| FR-SM1  | Basic Guard-rails         | Implement simple checks (e.g., excessive file changes, shell command risk) before execution.            | P1       | Can pause & request PWA approval. |
| FR-SM2  | Autopause                 | Automatically pause execution if tests fail or significant deviations from plan occur.                     | P1       | Requires Reflector analysis. |
| FR-SM3  | Health Endpoint           | Sidecar exposes `/healthz` HTTP endpoint reporting status (running, last checkpoint time, recovery status). | P1       | For external monitoring. |
| FR-SM4  | Metrics Exposure          | Sidecar exposes Prometheus metrics (cycle times, errors, recovery counts, etc.).                           | P1       | `/metrics` endpoint. |
| FR-SM5  | Secure Remote Actions     | Optional OTP confirmation in PWA for potentially high-risk actions (e.g., `git push`, complex shell commands). | P2       | Security enhancement. |

---

## 6  Non-Functional Requirements
*   **Latency:** P95 Recovery < 150 ms; P95 Mobile Push < 500 ms; P95 Plan-Execute Cycle < 5 minutes.
*   **Scalability:** Sidecar handles high volume stderr/stdout; Raft Vector Store scales with codebase size.
*   **Security:** Sidecar runs locally; Relay uses JWT auth; Optional OTP for sensitive remote commands.
*   **Reliability:** High success rate for recovery; persistent state survives restarts.
*   **Extensibility:** Pluggable Guard-rails; potentially support different Planner/Reflector models.

---

## 7  High-Level Architecture
```mermaid
graph TD
    subgraph "Local Workstation"
        subgraph "Core Oppie Loop (Cursor Context)"
            Planner[Planner
(LLM via API)]
            Executor[Executor
(Cursor Tools)]
            Reflector[Reflector
(Template Engine)]
            VDB[(Raft Vector Store
Code Context)]
            StateDB[(Checkpoint State
File/DB)]

            Planner -- Plan --> Executor
            Executor -- Raw Results --> Reflector
            Reflector -- Formatted Feedback --> Planner
            Executor -- Reads/Writes --> StateDB
            Planner -- Reads --> VDB
            Executor -- Reads --> VDB
            Reflector -- Reads --> StateDB
        end

        SD[Sidecar Daemon
(Python)]
        CE[Cursor Executor PTY]

        CE -- stdout/stderr --> SD
        SD -- Keystrokes (Recovery/Control) --> CE
        SD -- Monitors/Controls --> Core Oppie Loop
        SD -- Reads/Writes --> StateDB  // For remote control state
    end

    subgraph "Cloud"
        Relay[Relay WSS]
    end

    subgraph "Phone"
        PWA[Mobile PWA]
    end

    SD -- WSS --> Relay
    Relay -- WSS --> PWA
    PWA -- Commands via WSS --> Relay
    Relay -- Commands via WSS --> SD
    SD -. Metrics .-> Prometheus[(Prometheus)]
```
**Flow:**
1.  User initiates task (locally or via PWA).
2.  Planner gets context (Code from VDB, State from StateDB), generates plan.
3.  Executor runs plan steps using Cursor tools, saving state/diffs to StateDB at checkpoints.
4.  Reflector summarizes results, sends feedback to Planner. Loop continues.
5.  Sidecar monitors PTY for errors (tool limit) and triggers recovery keystrokes.
6.  Sidecar pushes status/diffs via Relay to PWA.
7.  User monitors/controls via PWA (Pause/Resume/Approve).

---

## 8  Tech Stack
| Layer                 | Choice                | Notes                                                    |
| :-------------------- | :-------------------- | :------------------------------------------------------- |
| **Core Loop**         |                       |                                                          |
| Planner               | **Codex API (o3)**    | High-intelligence model for planning & reflection.         |
| Executor              | **Cursor Native Tools** | `edit_file`, `run_terminal_cmd`, etc.                    |
| Reflector             | **Jinja2/Templates**  | Structured communication between Executor and Planner.     |
| Vector Store          | **LanceDB / ChromaDB**| Local, persistent vector storage for code context (RAG). |
| Checkpoint Store      | **Filesystem / SQLite**| Storing execution state, diffs, logs per checkpoint.     |
| **Sidecar & Remote** |                       |                                                          |
| Sidecar Language      | **Python 3.12**       | Packaged via PyInstaller/Ruff.                           |
| GUI Automation        | **pyautogui**         | Cross-platform for recovery keystrokes (fallback).       |
| Mobile UI             | **React + Vite PWA**  | For remote monitoring and control.                       |
| Real-time Comm        | **WebSocket (Node `ws`)**| Sidecar ⇄ Relay ⇄ PWA communication.                   |
| **Monitoring**        |                       |                                                          |
| Metrics               | **prometheus-client** | Python library for exposing metrics.                     |
| Logging               | **JSONL Files**       | Structured logging for audit and debugging.              |

---

## 9  Milestones
| ID | Scope                                       | ETA        | Status      |
| ---| :------------------------------------------ | :--------- | :---------- |
| M1 | Core Loop Foundation (Plan-Exec-Reflect)    | 2025-05-20 | To Do       |
| M2 | Checkpoint Persistence & Basic Recovery     | 2025-05-30 | To Do       |
| M3 | Sidecar Daemon + Tool Limit Recovery (FR-PR3/4/5) | 2025-06-10 | In Progress |
| M4 | PWA Interface + Live Progress (FR-RI1/2)    | 2025-06-20 | To Do       |
| M5 | Landing Context (Vector Store Integration)  | 2025-06-30 | To Do       |
| M6 | Basic Guard-rails & PWA Controls (FR-SM1/RI3)| 2025-07-10 | To Do       |
| M7 | Pilot with 3 repos; hit KPIs              | 2025-07-25 | To Do       |

---

## 10  Risk Register
| Risk                             | Impact | Likelihood | Mitigation                                                  |
| :------------------------------- | :----- | :--------- | :---------------------------------------------------------- |
| Planner Complexity/Hallucination | High   | Medium     | Iterative planning, strong Reflector feedback, guardrails.  |
| State Management Bugs            | High   | Medium     | Robust checkpointing, atomic writes, validation.            |
| Context Window Limits            | Medium | High       | Efficient RAG via Vector Store, context pruning strategies. |
| Cursor UI/API Changes            | Medium | Medium     | Adapt Sidecar/Executor; prefer stable APIs over GUI.      |
| GUI Automation Flakiness         | Medium | Medium     | Hidden command discovery; image fallback; robust selectors. |
| Mobile Network Flakiness         | Medium | Medium     | Local buffering in Sidecar, resumable WSS connections.      |
| OS Privacy Blocks `pyautogui`    | High   | Low        | Documented setup script to pre-grant permissions.         |
| Security of Remote Control       | High   | Medium     | Local-only Sidecar option, Relay auth, optional OTP.        |

---

## 11  Open Questions
1.  Optimal strategy for representing/saving execution state for checkpoints?
2.  How to effectively manage context for the Planner LLM in very large codebases?
3.  Best practices for designing Guard-rails without being overly restrictive?
4.  Reliability of background WSS push notifications on iOS/Android PWA?
5.  How to handle complex merge conflicts if Oppie modifies files concurrently with user?

---

> **Next**: Complete Sidecar Daemon + Tool Limit Recovery (M3), then build PWA Interface (M4).

