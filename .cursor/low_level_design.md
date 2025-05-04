# Oppie Remote Cursor Control Mesh (M1) — Low-Level Design  
*(algorithms, utilities, tests — brand **SoraSpark**, codename **oppie.xyz**)*

---

## 1 Implementation Scope

This document breaks the **M1** milestone into concrete, testable units of work for the **Remote Cursor Control Mesh**.  It supersedes previous *Dev-Loop* notes and merges them with the new remote PWA surface.

| Component            | Status in M1 | Language | LOC target | Notes |
|----------------------|--------------|----------|-----------|-------|
| Cursor Extension Core| ✅ ship       | TS       | < 500     | IPC + Webview timeline |
| PocketFlow Orchestrator | ✅ ship    | TS       | < 150     | 3-step loop, adapters plug-in |
| ToolBroker / Plug-in Loader | ✅ ship | TS | < 200 | Dynamic `import()` of `*.plugin.js` |
| Sidecar Daemon       | ✅ ship       | Py 3.12  | < 400     | WSS bridge + keystroke fallback + push buffer |
| Dev-Loop Watcher     | ✅ ship       | Py 3.12  | < 250     | Regex + Agent S recovery |
| Agent S Helpers      | ✅ ship       | Py 3.12  | < 80      | focus + type utilities |
| Vector Store Client  | ✅ ship       | TS       | < 120     | Wraps rqlite HTTP |

---

## 2 IPC & Message Schema

```ts
// shared.ts (imported by Extension & Sidecar)
export type Msg =
  | { type: 'runPlan'; plan: Step[] }
  | { type: 'chat'; prompt: string }
  | { type: 'progress'; pct: number; log: string }
  | { type: 'diff'; patch: string }
  | { type: 'approve'; ok: boolean }
  | { type: 'recover'; ok: boolean; ts: number };  // NEW — push recovery status to PWA

export const IPC_PATH = process.platform === 'win32'
  ? r"\\.\\pipe\\oppie-ipc"
  : '/tmp/oppie-ipc.sock';
```

Push events of type `recover` allow the PWA to update its timeline and measure **P95 push latency** KPI.

*Transport*: UNIX domain socket (Windows named pipe) created by the **Extension Core** on activation.  The **Sidecar** reconnects with exponential backoff.

---

## 3 Cursor Extension Core (TypeScript)

### 3.1 Activation & IPC server

```ts
import { IPC_PATH, Msg } from './shared';
import * as vscode from 'vscode';
import net from 'net';

export function activate(ctx: vscode.ExtensionContext) {
  const server = net.createServer(socket => {
    socket.on('data', async (raw) => {
      const msg: Msg = JSON.parse(raw.toString());
      if (msg.type === 'runPlan') {
        await executePlan(msg.plan);
      } else if (msg.type === 'chat') {
        await invokeChat(msg.prompt);
      }
    });
  }).listen(IPC_PATH);

  ctx.subscriptions.push({ dispose() { server.close(); } });
}
```

### 3.2 `executePlan` & PocketFlow mini-loop

```ts
async function executePlan(plan: Step[]) {
  const pf = new PocketFlow({ adapters: loadReasoningAdapters() });
  for await (const evt of pf.run(plan)) {
    webviewPost(evt);            // stream to PWA
    sidecarNotify(evt);          // optional fallback
  }
}
```

### 3.3 Chat Invocation Strategy

1. Attempt dynamic command discovery (regex `^cursor\..*(chat|composer)`)
2. If found, `executeCommand` + clipboard paste + `type('\n')`.
3. Else, send `{ type: 'chat', prompt }` back to Sidecar which uses keystroke automation.

---

## 4 ToolBroker & Plug-in Loader

```ts
import glob from 'fast-glob';

export async function loadPlugins(): Promise<Plugin[]> {
  const files = await glob('plugins/**/*.plugin.js', { cwd: vscode.workspace.rootPath });
  return Promise.all(files.map(f => import(f)));
}
```

Each plug-in exposes:

```ts
export interface Plugin {
  name: string;
  version: string;
  apply(step: Step, ctx: ExecCtx): Promise<ExecResult>;
}
```

The **ToolBroker** iterates over steps and delegates to the first plug-in whose `apply` returns non-null.

---

## 5 Sidecar Daemon (Python 3.12)

```python
import asyncio, json, websockets, socket, os, sys, pathlib
from ipc_shared import IPC_PATH
WS_URL = os.environ.get('OPPIE_WSS') or 'wss://relay.oppie.xyz/session?jwt=…'

async def main():
    # connect IPC first
    reader, writer = await asyncio.open_unix_connection(IPC_PATH) if os.name != 'nt' else await asyncio.open_connection(path=IPC_PATH)
    async with websockets.connect(WS_URL) as ws:
        while True:
            data = await ws.recv()
            msg = json.loads(data)
            await handle(msg, writer)

def handle(msg, writer):
    writer.write(json.dumps(msg).encode())
```

### 5.1 Fallback keystroke path

```python
import pyautogui

def send_chat(prompt: str):
    pyautogui.hotkey('command', 'l')  # focus Composer
    pyautogui.write(prompt)
    pyautogui.press('enter')
```

This path is invoked when the Extension replies with `{ type: 'chat', prompt }`.

---

## 6 Dev-Loop Watcher (Python 3.12)

Most logic is unchanged from the legacy *Dev-Loop* but now listens to the real `cursor-executor` process spawned by the Extension.

```python
import re, subprocess, json, time
from agent_s_helpers import focus_cursor, type_and_enter

ERROR_RE  = re.compile(r"Exceeded 25 native tool calls")
TEMPLATE_RE = re.compile(r"### 🔄  Template A")

def tail_executor(cmd):
    with subprocess.Popen(cmd,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          text=True) as proc:
        for line in proc.stdout:
            handle_line(line, proc.pid)

def handle_line(line, pid):
    log("EXEC_LOG", line.rstrip(), pid)
    if ERROR_RE.search(line):
        recover("TOOL_LIMIT", pid)
    elif line.startswith("🪄 assistant_bubble_end"):
        if not TEMPLATE_RE.search(line):
            recover("MISSING_TEMPLATE", pid)

def recover(reason, pid):
    log("RECOVER_START", reason, pid)
    focus_cursor()
    type_and_enter(RECOVERY_PROMPT)
    log("RECOVER_DONE", reason, pid)
```

### 6.1 Recovery Prompt Constant

```python
RECOVERY_PROMPT = (
    "Cursor Executor, on top of @.cursorrules, @tech_stack.md and @scratchpad.md, "
    "strictly follow instructions from Codex Planner in the `Template Aₓ — Plan-and-Execute Loop` "
    "above to continue at where you stopped"
)
```

---

## 7 Testing & QA Matrix

| Level        | Tool / Framework   | Assertions |
|--------------|--------------------|------------|
| **Unit**     | `pytest`, `jest`   | IPC parse, regex match, plugin selection |
| **Contract** | `pact` (TS ↔ Py)   | Extension ↔ Sidecar message schema |
| **Integration** | `pexpect`, `vitest` | Fake executor → watcher recovers |
| **End-to-end** | Manual, screencast | Trigger from phone, watch loop for 1 h |

---

## 8 Packaging & Distribution

| Target            | Command |
|-------------------|---------|
| **Watcher Bin**   | `pyinstaller watcher.spec` |
| **Extension VSIX**| `pnpm package` |
| **Sidecar Zip**   | `pyinstaller sidecar.spec` |

`start_devloop.sh` spawns Planner (`codex -m o3 -a full-auto`) in a new iTerm tab **and** launches `watcher.bin` in the current shell.

---

## 9 Security & Privacy Notes

* **Accessibility** Agent S binaries are signed; first launch will request Assistive permission (macOS) — documented in README.
* **Sandbox** Sidecar and plugins run in separate processes, no shared memory.
* **Data** Only plan / diff metadata is sent to the relay; source code never leaves the workstation.

---

## 10 Performance Tuning

*Steady-state CPU* < 2 %, *RAM* < 120 MB per process.  Use non-blocking IO everywhere.  Profile with `py-spy` and `vscode-profiling`.

---

> **End of Low-Level Design (M1).**  Implementations must not diverge from the interfaces and constants defined here.