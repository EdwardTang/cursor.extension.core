# Plan‑Execu Tight Loop — PRD & Technical System Design (v0.1)

Source: https://chatgpt.com/share/680c6a03-f8d4-8006-9bc4-0dfc28804a1e

---
## 1. Overview
Build a self‑running *Planner ⇄ Executor* loop that leverages **Reflexion‑Aligned templates**, GUI automation (Agent S or AppleScript), rate‑limit resilience, and an asynchronous diff‑driven Tracker so the system can operate autonomously while remaining aligned with human values and safe‑guards.

## 2. Problem Statement
Today Codex Planner and Cursor Executor require human copy/paste to exchange *Plan* and *PlanRequest* and manual oversight for hallucinations and Cursor tool‑call limits. We need a closed loop that:
* Runs for hours without human intervention.
* Surfaces deviations or value mis‑alignments immediately.
* Recovers gracefully from Cursor’s 25 native‑tool hard limit.

## 3. Guiding Principles
1. **Alignment‑first** — every cycle embeds diagnosis, corrective actions, and alignment check.
2. **Human‑in‑the‑loop Escalation** — loop pauses only on clearly defined guard‑rails.
3. **Minimal Intrusion** — no brittle hacks inside Cursor; interact via GUI automation layer.
4. **Observability** — checkpoints, diffs, reflections, and alerts are persisted and queryable.

## 4. Functional Requirements
| ID | Requirement |
|----|-------------|
| **FR‑1** | Enforce **Reflexion‑Aligned Template** with fields: diagnosis, action_items, alignment_check. |
| **FR‑2** | Automate Planner⇄Executor hand‑off via Agent S (default) or AppleScript fallback. |
| **FR‑3** | Detect Cursor native‑tool limits; apply exponential back‑off and *continue* re‑runs. |
| **FR‑4** | Compute high‑efficiency diffs (Myers + diff‑match‑patch) and map to probability_class. |
| **FR‑5** | Trigger LLM Reflexion when probability_class ≤ MEDIUM or after checkpoint restore. |
| **FR‑6** | Provide three pause conditions: repeat‑error≥3, fatal executor error, deviation alert. |
| **FR‑7** | Human operator can *resume_episode(ckpt_id)* or *restore_checkpoint*. |

## 5. Non‑Functional Requirements
* **Reliability:** ≥ 99% successful iterations without manual nudge.
* **Latency:** < 3 s added by Tracker per cycle.
* **Security & Privacy:** no raw customer code leaves host; only diff‑hashes logged.
* **Extensibility:** Planner/Executor interchangeable; GUI layer replaceable.

## 6. Success Metrics (MVP)
* MTTA (mean‑time‑to‑alert) on deviation < 60 s.
* < 1 human intervention per 100 valid iterations over 8‑hour run.
* ≥ 95 % Reflection JSON parsed without error.

## 7. Stakeholders
* **Eddie** — Product/Tech owner.  
* **AI Engineering** — owns Codex Planner & Tracker.  
* **Dev‑Tools Team** — maintains Cursor integration.

## 8. Scope
**Must‑have:** FR‑1 … FR‑4.  
**Should‑have:** FR‑5, FR‑6.  
**Future:** cloud sandbox mode, multi‑Planner ensemble.

---
## 9. High‑Level Architecture
```
┌─────────┐   send_message   ┌───────────┐
│ Codex   │ ───────────────▶ │ Cursor    │
│ Planner │ ◀─────────────── │ Executor  │
└─────────┘    Outbox &      └───────────┘
      ▲          GUI                    ▲
      │       automation               │
      │                                 │
      │  checkpoints / diffs / alerts   │
┌──────────────────────────────────────────────┐
│           PlanExecu Tracker (MCP)            │
│  • Checkpoint DB (SQLite)                   │
│  • Diff Engine (Myers+dmp)                  │
│  • Reflexion Worker (LLM)                   │
│  • Alignment Rubric                         │
└──────────────────────────────────────────────┘
```

### Data Flow
1. Planner outputs **Plan Aₙ** → `send_message` tool inserts into *Outbox*.
2. Agent S detects Outbox event, focuses Cursor, pastes Plan, presses ⏎.
3. Executor runs → returns **PR‑Aₙ₊₁**, same path back.
4. Tracker records checkpoints, computes diff, classifies probability_class.
5. If `MEDIUM/LOW`, Reflexion Worker generates JSON and loop may pause.

---
## 10. Data Contracts
### 10.1 Template Fields (Markdown)
```markdown
[📂 PROJECT]        …
[🗺️ CURRENT GOAL]   …
…
[🪞 REFLECTION]
  diagnosis: "…"
  action_items:
    - Step 1
    - Step 2
[✅ ALIGNMENT_CHECK] yes | no  // + rationale
```

### 10.2 MCP Tools
| Tool | Params | Response |
|------|--------|----------|
| `record_checkpoint` | iteration, role, scratchpad | ckpt_id |
| `diff_and_classify` | from_id, to_id | {patch, probability_class} |
| `send_message` | target, message | ack |
| `pause_episode` | reason | episode_id |
| `resume_episode` | ckpt_id | ack |

### 10.3 SQLite Schema (excerpt)
```sql
CREATE TABLE checkpoints(...);
CREATE TABLE diffs(...);
CREATE TABLE reflections(...);
CREATE TABLE outbox(id INTEGER, target TEXT, payload TEXT);
```

---
## 11. Algorithms & Workers
| Component | Tech | Notes |
|-----------|------|-------|
| **Diff Engine** | `difflib.unified_diff` (line) + `diff-match-patch` (char) | ratio→MEDIUM/LOW thresholds 0.6/0.4 |
| **Reflexion Worker** | LLM (o3 / gpt‑4o) | Prompt returns JSON `{diagnosis, action_items}` |
| **GUI Automation** | Agent S (pyautogui) **or** AppleScript (`osascript`) | fallback chosen by host‑capability |
| **Rate‑limit Handler** | Regex detect "Exceeded 25 native tool calls" → `backoff = min(2ⁿ × 800 ms, 60 s)` | after 3 fails → pause |

---
## 12. Tech‑Stack Choices
| Layer | Primary | Alt / Notes |
|-------|---------|-------------|
| Language | Python 3.11 |  |
| Tracker API | FastAPI + MCP‑Python‑SDK | runs over stdio or HTTP |
| Storage | SQLite 3.45 | future: DuckDB / Postgres |
| Queue | RQ (Redis) | Celery if scaling out |
| Diff libs | `difflib`, `diff-match-patch` | Rust port for perf |
| LLM | OpenAI o3 | Claude 3 as backup |
| GUI Bot | Agent S 0.2 | AppleScript fallback |
| Observability | OpenTelemetry + Grafana | exporters in Tracker |

---
## 13. Deployment & Ops
* **Single‑host dev:** Docker Compose: `tracker`, `redis`, optional `worker`.
* **Prod:** K8s; `tracker` HPA, workers as Job.
* GUI bot runs on macOS workstation where Cursor is installed.
* Secrets via 1Password Connect.

---
## 14. Security & Privacy
* GUI bot limited to `Cursor` window via window title regex.
* Reflection JSON scrubbed of PII before log.
* All MCP traffic over Unix socket or WireGuard.

---
## 15. Open Questions
1. Formal schema of Cursor Outbox key/value — need to confirm field names per latest release.
2. Should back‑pressure propagate to Planner or Executor when pause occurs?
3. Might `Agent S` GUI actions need computer‑vision fine‑tuning for theme changes (dark / light)?
4. Decide on grounding LLM for alignment rubric — static rules vs policy LM.

---
### Appendix A. Alignment Rubric (draft)
* Data privacy respected?
* Legal / license compliance?
* Not causing irreversible workspace damage?
* Resource cost reasonable (<10 min CPU per iteration)?

> **Next**: validate Outbox insertion with a local Cursor build, plus run an end‑to‑end smoke test of Planner→GUI bot→Executor.

