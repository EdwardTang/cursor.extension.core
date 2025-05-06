# Oppie Remote Cursor Control Mesh (M1) — Low-Level Design  
*(algorithms, utilities, tests — brand **SoraSpark**, codename **oppie.xyz**)*

---

## 1 Implementation Scope

本文档重构了**M1**里程碑，采用**OpenHands ACI**作为核心Agent框架，并与**Remote Cursor Control Mesh**集成。它取代了之前的*Dev-Loop*方案，重点用OpenHands的现有能力取代自研组件。

| Component            | Status in M1 | Language | LOC target | Notes |
|----------------------|--------------|----------|-----------|-------|
| Cursor Extension Core| ✅ ship       | TS       | < 500     | IPC + Webview timeline |
| OpenHands Adapter    | ✅ ship       | TS/Py    | < 150     | 转换Template A和OpenHands事件 |
| OpenHands Config     | ✅ ship       | TOML/Py  | < 100     | OpenHands配置和扩展点 |
| Sidecar Daemon       | ✅ ship       | Py 3.12  | < 400     | WSS bridge + keystroke fallback + push buffer |
| Dev-Loop Watcher     | ✅ ship       | Py 3.12  | < 250     | 监控输出和触发恢复 |
| Trajectory Client    | ✅ ship       | TS       | < 120     | 封装trajectory-visualizer API |

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
  | { type: 'recover'; ok: boolean; ts: number }
  | { type: 'openhands_event'; payload: TimelineEntry }; // NEW - OpenHands事件

export const IPC_PATH = process.platform === 'win32'
  ? r"\\.\\pipe\\oppie-ipc"
  : '/tmp/oppie-ipc.sock';
```

`openhands_event`类型允许OpenHands的事件直接映射到UI timeline，支持实时可视化和监控。

*Transport*: UNIX domain socket (Windows named pipe) created by the **Extension Core** on activation. The **Sidecar** reconnects with exponential backoff.

---

## 3 Cursor Extension Core (TypeScript)

### 3.1 Activation & IPC server

```ts
import { IPC_PATH, Msg } from './shared';
import * as vscode from 'vscode';
import net from 'net';
import { OpenHandsAdapter } from './openhands-adapter';

export function activate(ctx: vscode.ExtensionContext) {
  const openHands = new OpenHandsAdapter();
  
  const server = net.createServer(socket => {
    socket.on('data', async (raw) => {
      const msg: Msg = JSON.parse(raw.toString());
      if (msg.type === 'runPlan') {
        await openHands.executePlan(msg.plan);
      } else if (msg.type === 'chat') {
        await invokeChat(msg.prompt);
      }
    });
  }).listen(IPC_PATH);

  ctx.subscriptions.push({ dispose() { server.close(); } });
}
```

### 3.2 OpenHands Adapter & Agent integration

```ts
class OpenHandsAdapter {
  constructor() {
    // 启动OpenHands实例或连接到现有服务
    this.initOpenHands();
  }

  async executePlan(plan: Step[]) {
    // 转换plan为OpenHands任务格式
    const task = this.convertToOpenHandsTask(plan);
    
    // 启动OpenHands Agent并监听事件
    this.openHandsClient.on('event', (event) => {
      webviewPost(event);
      sidecarNotify(event);
    });
    
    // 执行并等待结果
    await this.openHandsClient.execute(task);
  }

  private initOpenHands() {
    // 初始化OpenHands客户端
    // 可通过设置OPENHANDS_ENABLED环境变量控制是否启用
    const enabled = process.env.OPENHANDS_ENABLED === 'true';
    if (enabled) {
      // 连接到OpenHands服务
    } else {
      // 使用模拟实现
    }
  }

  private convertToOpenHandsTask(plan: Step[]): OpenHandsTask {
    // 将Oppie步骤转换为OpenHands任务
    return {
      type: 'code',
      instructions: plan.map(p => p.description).join('\n'),
      context: { template: 'A' }
    };
  }
}
```

### 3.3 Chat Invocation Strategy

保持不变，支持多种策略：
1. 尝试动态命令发现（regex `^cursor\..*(chat|composer)`）
2. 如果找到，通过`executeCommand` + 剪贴板粘贴 + `type('\n')`执行
3. 否则，发送`{ type: 'chat', prompt }`回给Sidecar使用键盘自动化

---

## 4 OpenHands Integration

### 4.1 OpenHands配置

OpenHands通过TOML文件配置，我们将创建一个Oppie特定的配置：

```toml
# oppie_openhands_config.toml
[core]
mode = "headless"  # 无UI模式，事件流通过API暴露
agent = "code_act_agent"  # 使用OpenHands的CodeActAgent

[llm]
provider = "openai"
model = "gpt-4"  # 与Codex o3兼容

[runtime]
type = "local"  # 本地执行环境
isolation = "minimal"  # 最小隔离以允许VS Code操作

[security]
allow_file_operations = true  # 允许文件操作
allow_command_execution = true  # 允许命令执行

[budget]
max_tool_calls = 24  # 低于Cursor 25工具调用限制
action_delay_ms = 100  # 操作间延迟以防止频繁调用

[vector_store]
type = "faiss"  # 使用FAISS作为向量存储
path = "./.openhands/vectors"  # 向量存储位置
```

### 4.2 OpenHands与Template A桥接

Template A需要转换为OpenHands能理解的任务格式：

```python
# openhands_adapter.py
from openhands.core import Agent, Task, Event
import re

TEMPLATE_A_REGEX = re.compile(r"## Template A(\d+)")

class TemplateAAdapter:
    def __init__(self, agent: Agent):
        self.agent = agent
    
    def convert_template_to_task(self, template_text: str) -> Task:
        """将Template A文本转换为OpenHands任务"""
        # 解析循环号
        cycle_match = TEMPLATE_A_REGEX.search(template_text)
        cycle = int(cycle_match.group(1)) if cycle_match else 0
        
        # 创建OpenHands任务
        return Task(
            type="code",
            instructions=template_text,
            metadata={
                "cycle": cycle,
                "type": "template_a",
                "executor": "cursor"
            }
        )
    
    def convert_events_to_template(self, events: list[Event]) -> str:
        """将OpenHands事件转换回Template A格式"""
        # 构建下一个Template A
        # ...实现省略...
        return template_text
```

---

## 5 Dev-Loop Watcher (Python 3.12)

保留当前监控Cursor输出的核心功能，但删除Agent S依赖，直接通过OpenHands函数调用或简化的文本输入实现恢复：

```python
import re, subprocess, json, time
from openhands.utils import input_text

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
    input_text(RECOVERY_PROMPT)  # 使用OpenHands的输入工具
    log("RECOVER_DONE", reason, pid)
```

### 5.1 Recovery Prompt Constant

```python
RECOVERY_PROMPT = (
    "Cursor Executor, on top of @.cursorrules, @tech_stack.md and @scratchpad.md, "
    "strictly follow instructions from Codex Planner in the `Template Aₓ — Plan-and-Execute Loop` "
    "above to continue at where you stopped"
)
```

---

## 6 Testing & QA Matrix

| Level        | Tool / Framework   | Assertions |
|--------------|--------------------|------------|
| **Unit**     | `pytest`, `jest`   | IPC parse, regex match, OpenHands Adapter |
| **Contract** | `pact` (TS ↔ Py)   | Extension ↔ Sidecar message schema |
| **Integration** | `openhands-test-client`, `vitest` | OpenHands task执行, 事件流产生和消费 |
| **End-to-end** | Manual, screencast | Trigger from phone, watch loop for 1 h |

---

## 7 Packaging & Distribution

| Target            | Command |
|-------------------|---------|
| **Watcher Bin**   | `pyinstaller watcher.spec` |
| **Extension VSIX**| `pnpm package` |
| **Sidecar Zip**   | `pyinstaller sidecar.spec` |
| **OpenHands**     | `poetry export -f requirements.txt --output openhands-requirements.txt` |

`start_devloop.sh`脚本将启动OpenHands服务、Codex Planner和Watcher。新增`--openhands`标志控制是否启用OpenHands功能。

---

## 8 Security & Privacy Notes

* **OpenHands沙箱** 配置为"minimal"隔离级别以允许文件系统和命令行访问，遵循最小权限原则。
* **Accessibility** 使用OpenHands Runtime的function calling替代大部分GUI自动化；仅在fallback时使用pyautogui。
* **Sandbox** OpenHands在单独进程中运行，与VS Code/Cursor隔离。
* **Data** 只有计划和差异元数据发送到中继服务；源代码永远不会离开工作站。

---

## 9 Performance Tuning

*内存优化*：
- 避免OpenHands和Cursor在内存中竞争 - 在OpenHands配置中设置`max_memory_mb`
- 使用事件流缓冲以防止在网络延迟时OOM

*CPU使用*：
- 稳态CPU < 2%, 内存 < 120 MB每进程
- Profile工具：OpenHands内置profiler + `py-spy` + `vscode-profiling`

---

## 10 Incremental Migration 

为确保平稳过渡，我们采用渐进式迁移策略：

1. **阶段1**：引入OpenHands适配器，同时保留现有组件；使用feature flag控制
2. **阶段2**：并行运行两个系统，比较成功率和性能
3. **阶段3**：当OpenHands稳定后，逐步弃用自研组件
4. **阶段4**：清理冗余代码，完成迁移

每个阶段都有明确的回退策略，确保关键功能不受影响。

---

> **End of Low-Level Design (M1).**  Implementations must not diverge from the interfaces and constants defined here.