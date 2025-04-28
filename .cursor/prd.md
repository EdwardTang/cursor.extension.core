# Oppie.xyz — Simple PRD for Plan‑Execu Tight Loop and Self-Recovery MVP (v0.2)

---
## 1. Overview
Build a minimal, semi-autonomous *Planner ⇄ Executor* loop within the Cursor IDE. The **sole focus** of this MVP is to automatically detect when the Cursor Executor hits its "25 native tool calls" limit and immediately trigger a recovery mechanism via GUI automation to continue the loop.

## 2. Problem Statement
The current manual Planner-Executor workflow is interrupted when Cursor's tool call limit is reached, requiring human intervention to restart the process. This MVP aims to create a simple, automated recovery mechanism.

## 3. Guiding Principles
1.  **Simplicity First**: Implement only the core recovery logic.
2.  **Minimal Intrusion**: Interact with Cursor externally via GUI automation; avoid internal modifications.
3.  **Observability**: Log basic recovery actions (success/failure).

## 4. Functional Requirements
| ID      | Requirement                                                                         |
| :------ | :---------------------------------------------------------------------------------- |
| FR-S1   | Monitor Cursor Executor's stdout/stderr for the exact string `Exceeded 25 native tool calls`. |
| FR-S2   | Upon detection of the error string, immediately trigger a GUI automation script.    |
| FR-S3   | The GUI script must focus the Cursor Composer's new message input window.           |
| FR-S4   | The GUI script must type the following fixed recovery prompt and press Enter:       |
|         | `Cursor Executor, on top of @.cursorrules, @tech_stack.md and @scratchpad.md, strictly follow instructions from Codex Planner in the \`Template Aₓ — Plan-and-Execute Loop\` above to continue at where you stopped` |
| FR-S5   | Log a simple `RECOVER_TRIGGERED` message when the error is detected and `RECOVER_TYPED` when the GUI action completes. |

> **Note:** No backoff, retry logic, Reflexion, diffing, or alignment checks are included in this MVP.

## 5. Non‑Functional Requirements
*   **Reliability**: The GUI automation script should successfully type the prompt within ~5 seconds of error detection.
*   **Simplicity**: The recovery logic should reside in a small, standalone script (e.g., Python).
*   **Dependencies**: Minimal external dependencies (e.g., `pyautogui` or similar).

## 6. Success Metrics (MVP)
*   Successfully trigger and execute the recovery prompt insertion via GUI automation every time the "25 native tool calls" error is detected during testing.
*   Observe `RECOVER_TYPED` logs corresponding to each recovery event.

## 7. Stakeholders
*   **Eddie** — Product/Tech owner.

## 8. Scope
**Must‑have:** FR-S1, FR-S2, FR-S3, FR-S4, FR-S5.
**Out of Scope (for MVP):** Reflexion, diff analysis, alignment checks, complex error handling, backoff/retry mechanisms, persistent state tracking beyond basic logging.

---
## 9. High‑Level Architecture (Simplified)
```
┌─────────┐        plan text        ┌───────────┐
│ Codex   │ ──────────────────────▶ │  Cursor   │
│ Planner │ ◀────────────────────── │ Executor  │
└─────────┘                         └───────────┘
            ▲        error watch
            │          (stdout/stderr)
        ┌───────────────────────────────┐
        │ Tiny Watcher & Typer Script   │
        │ • Monitor executor output     │
        │ • Regex detect error          │
        │ • pyautogui.typewrite(...)    │
        │ • pyautogui.press('enter')    │
        └───────────────────────────────┘
```

### Data Flow (Simplified)
1.  Planner (e.g., via `codex` tool) generates a plan (Template Aₓ).
2.  User/Script pastes Plan into Cursor Executor.
3.  Executor runs, potentially hitting the 25-tool limit.
4.  The separate "Watcher & Typer" script monitors Executor's output.
5.  If the error string is detected, the script triggers GUI automation (FR-S2 to FR-S4).
6.  The recovery prompt restarts the Executor's process for the next step based on the *last* plan provided by the Planner (referenced implicitly in the prompt).
7.  The loop continues.

---
## 10. Key Components & Logic
| Component               | Tech             | Notes                                                                 |
| :---------------------- | :--------------- | :-------------------------------------------------------------------- |
| **Error Detection**     | Regex/String Match | Monitor stdout/stderr of the process running the Cursor interaction. |
| **GUI Automation**      | `pyautogui`      | Focuses Cursor window, types fixed prompt, presses Enter.             |
| **Watcher/Typer Script**| Python           | Orchestrates detection and triggering of GUI automation.              |

---
## 11. Tech‑Stack Choices (MVP)
| Layer            | Primary     | Notes                             |
| :--------------- | :---------- | :-------------------------------- |
| Language         | Python 3.x  | For the Watcher/Typer script.     |
| GUI Automation   | `pyautogui` | Cross-platform basic GUI control. |
| Core Loop Files  | Markdown    | `.cursorrules`, `*.mdc`, `*.md`   |

---
## 12. Deployment & Setup (via Cookiecutter)

To simplify setup in any user repository, a Cookiecutter template will be provided.

### Cookiecutter Template Structure
```
planexecu-cookiecutter/
├── cookiecutter.json                  # Defines default project_slug
├── {{cookiecutter.project_slug}}/     # Default: oppie.xyz/
│   ├── .cursorrules                   # Core Cursor rules for the loop
│   ├── drop-in_template_A.mdc         # Standard Planner -> Executor template
│   ├── codex.md                       # Planner instructions/guidelines
│   ├── scratchpad.md                  # Initial state/scratchpad file
│   └── README_PLANEXECU.md            # Quick start guide
└── hooks/
    └── post_gen_project.py            # Prints setup instructions after generation
```

### Cookiecutter Usage
1.  Install prerequisites: `pip install cookiecutter openai-codex`
2.  Set `OPENAI_API_KEY` environment variable.
3.  Install Cursor IDE.
4.  Run: `cookiecutter gh:your-org/planexecu-cookiecutter` (replace `your-org` appropriately)
5.  Accept the default `project_slug` ("oppie.xyz") or provide a custom name.
6.  Copy/merge the generated files (`.cursorrules`, `*.md`, `*.mdc`) into the root of the target repository.
7.  Follow instructions in `README_PLANEXECU.md` to start the loop.

*(The Watcher/Typer script itself is not part of the Cookiecutter template in this design but should be provided separately or documented for the user to implement/run).*

---
## 13. Security & Privacy
*   GUI automation script should be run locally by the user.
*   Ensure the script only interacts with the intended Cursor window if possible (e.g., via window title).

---
## 14. Open Questions
1.  Confirm the exact error string output by Cursor when the 25-tool limit is hit.
2.  Determine the most reliable way for `pyautogui` to find and focus the Cursor input window across different OS/setups.
3.  How will the Watcher/Typer script be distributed and run alongside Cursor/Codex? (Needs clear instructions in the main project README).
---

> **Next**: Implement the simple Watcher/Typer script and test the recovery mechanism end-to-end. Create the Cookiecutter template repository.

