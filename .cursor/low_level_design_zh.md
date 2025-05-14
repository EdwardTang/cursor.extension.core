# Oppie 远程光标控制网格（M1）——低层设计
*（算法、实用工具、测试——品牌 **SoraSpark**，代号 **oppie.xyz**）*

---

## 1 实现范围

本文档描述了**M1**里程碑的底层设计细节，专注于基于OpenHands ACI的Plan-Execute-Reflect循环、通过OpenHands Adapter实现的Template A集成、以及Dev-Loop Watcher驱动的恢复机制。此外，还包括VDI资源隔离、GUI流优化、偏轨检测、移动体验优化和人类接管协议的初步设计与模拟方案。

| 组件                         | M1 状态            | 语言              | 代码行数目标 | 备注                                                                                             |
|-----------------------------|--------------------|-------------------|--------------|-------------------------------------------------------------------------------------------------|
| OpenHands Adapter           | ✅ 初始实现        | Python/TypeScript | < 300        | 核心转换逻辑、事件处理、恢复任务构建。                                                              |
| OpenHands Config            | ✅ 定义与使用      | TOML/Python       | < 150        | Oppie特定配置，包括LLM、Runtime、Budget等，支持VDI模拟参数。                                        |
| Dev-Loop Watcher            | ✅ 为OH重构        | Python 3.12       | < 300        | 监控OpenHands Executor日志，通过Adapter触发恢复。                                                    |
| VDI/GUI 设计与模拟模型      | ✅ 设计与模拟逻辑  | Python/Markdown   | < 400        | 资源隔离、流优化、偏轨检测的算法设计和模拟代码/脚本。                                                   |
| 移动/接管协议设计           | ✅ 设计            | Markdown          | < 100        | 移动体验UX原则和人类接管协议定义。                                                                     |
| Template A 存储/处理        | ✅ 已有            | 文件系统          | -            | 使用 `.scratchpad_logs/` 存储Template A周期。                                                        |
| Cursor Ext. Core (接口)     | ✅ 最小更改        | TypeScript        | < 50         | 确保能通过Adapter与OpenHands通信（如果需要直接交互，否则Adapter处理）。                                 |

---

## 2 IPC & 消息模式（M1 重点）

主要的消息流通过 `OpenHands Adapter` 进行协调。`Template A` 文件作为高级别任务的载体。
OpenHands内部有其自身的事件和任务结构。Watcher和Adapter间的通信可能是简单的信号或结构化消息。

```python
# 示例：Watcher到Adapter的恢复通信
from dataclasses import dataclass

@dataclass
class RecoveryRequest:
    type: str  # 例如，"TOOL_LIMIT_EXCEEDED"，"TEMPLATE_A_MISSING"
    original_template_a_path: str
    details: dict # 额外上下文，如错误信息或周期号
```

VS Code扩展（如果直接与Adapter交互）的消息结构 `shared.ts` 中的 `openhands_event` 需要能够承载OpenHands产生的关键状态更新和结果，供未来可能的Webview展示。

---

## 3 OpenHands Adapter (Python/TypeScript)

### 3.1 职责
*   **Template A 解析：** 读取并解析 `.scratchpad_logs/*_plan_request.md` 文件。
*   **任务转换（A → OH）：** 将解析的 Template A 内容转换为结构化的 OpenHands 任务（例如，主要指令、上下文文件、元数据）。
*   **OpenHands 调用：** 使用 `oppie_openhands_config.toml` 启动 OpenHands 执行转换后的任务。
*   **事件处理（OH → A）：** 监听 OpenHands 事件流（动作、观察、代理状态变化、错误）。
*   **反思与响应生成：** 聚合相关的 OpenHands 事件和反思输出以填充新 `Template A` 文件的响应部分。
*   **恢复任务制定：** 接收到来自 Watcher 的 `RecoveryRequest` 时，构建一个新的 OpenHands 任务以从特定错误中恢复（例如，重新规划，澄清）。

### 3.2 核心工作流逻辑（伪代码）

```python
# openhands_adapter.py（概念性）
class OpenHandsAdapter:
    def __init__(self, config_path="oppie_openhands_config.toml"):
        # 加载 OpenHands 配置，初始化 OpenHands 客户端/运行器
        pass

    def process_latest_template_a(self):
        latest_request_path = find_latest_request_in_scratchpad_logs()
        template_a_content = parse_template_a_file(latest_request_path)
        
        openhands_task = self.convert_template_a_to_openhands_task(template_a_content)
        
        # 使用 OpenHands 执行任务（这是一个阻塞调用或异步管理）
        # OpenHands 内部处理规划、执行步骤、反思
        openhands_result_events = self.openhands_client.run_task(openhands_task)
        
        new_template_a_response_content = self.convert_openhands_results_to_template_a_response(
            template_a_content, # 原始请求用于上下文
            openhands_result_events
        )
        save_new_template_a_response(new_template_a_response_content)

    def trigger_recovery(self, recovery_request: RecoveryRequest):
        # 基于 recovery_request 创建一个专门的 OpenHands 任务
        # 例如，如果 TOOL_LIMIT_EXCEEDED，指示 OpenHands 重新规划剩余步骤
        # 来自 original_template_a_path
        recovery_task = self.formulate_recovery_openhands_task(recovery_request)
        openhands_result_events = self.openhands_client.run_task(recovery_task)
        # ... 转换并保存响应 ...

    def convert_template_a_to_openhands_task(self, template_a_data: dict) -> dict:
        # 从 Template A 中提取相关字段（NEXT_GOAL, RELEVANT_ARTIFACTS 等）
        # 映射到 OpenHands 任务结构（例如，指令、上下文文件、代理配置覆盖）
        # 确保 CYCLE_NUMBER 和其他关键元数据被传递
        instruction = template_a_data.get("NEXT_GOAL", "Proceed with the plan.")
        # 可能包括 RELEVANT_ARTIFACTS 的内容作为上下文
        return {
            "instruction": instruction,
            "metadata": {"template_a_cycle": template_a_data.get("CYCLE_NUMBER")}
            # ... 其他 OpenHands 特定任务字段 ...
        }

    def convert_openhands_results_to_template_a_response(self, original_request_data, events) -> str:
        # 分析 OpenHands 事件（计划、动作、观察、错误、最终反思）
        # 填充 Template A 的 PLANNER RESPONSE 部分：ANALYSIS, PLAN, BLOCKER_SOLUTIONS 等。
        # 这是一个复杂的步骤，可能涉及 LLM 调用，如果 OpenHands 反思不能直接使用。
        # 对于 M1，它可能是 OpenHands 反思到 ANALYSIS 的简单映射，以及动作总结到 PLAN。
        planner_response = {
            "ANALYSIS_JUSTIFICATION": "基于 OpenHands 执行和反思的分析...",
            "PLAN": "由 OpenHands 执行的计划：...（动作总结）...",
            "BLOCKER_SOLUTIONS": "由 OpenHands 识别的阻碍：...",
            # ... 等等 ...
        }
        # 使用 original_request_data 和 planner_response 构建完整的 Template A 响应字符串
        return construct_template_a_string(original_request_data, planner_response)
```

### 3.3 `adapter/mapping.py` 细节
*   为 `Template A` 中的所有字段定义明确的正则表达式模式以实现稳健解析。
*   实现 `parse_template_a_file(file_path) -> dict` 返回结构化字典。
*   实现 `construct_template_a_string(request_dict, planner_response_dict) -> str` 构建输出文件。
*   包含用于提取/格式化特定 Template A 部分的辅助函数。

---

## 4 OpenHands 配置（`oppie_openhands_config.toml`）

```toml
# oppie_openhands_config.toml（M1 重点）
[core]
mode = "headless"               # 无GUI，程序化控制
agent = "CodeActAgent"          # 或其他适合编码任务的OpenHands代理
max_iterations = 15             # 单次OpenHands任务运行的最大迭代次数

[llm]
# 配置OpenHands使用的LLM（例如，用于Planner和Reflector模块）
provider = "openai" # 或您的特定提供商
model = "gpt-4o-mini" # 示例，尽可能与Codex o3能力对齐
# api_key = "env:OPENAI_API_KEY" # 使用环境变量的示例

[runtime]
type = "local"                  # 本地执行命令
isolation = "minimal"           # 允许Cursor工具的必要系统访问
# working_directory = "/path/to/workspace" # 应动态设置或继承

[security]
allow_file_operations = true
allow_command_execution = true
# 如果需要，可能基于命令添加限制

[budget]
# OpenHands内部预算，与Cursor的25工具调用限制不同
# 这有助于管理OpenHands自身的工具调用，如果它使用复杂的内部工具。
max_tool_calls = 50 # 为OpenHands本身提供慷慨的内部预算

[logging]
level = "INFO"
file_path = ".scratchpad_logs/openhands_run.log" # 集中的OpenHands日志

# M1模拟参数（Oppie的自定义部分）
[oppie_simulation_m1]
enable_vdi_resource_contention_sim = false # 切换VDI多代理资源争用模拟
cpu_limit_per_agent_sim = "0.5" # 模拟的CPU核心限制
memory_limit_per_agent_sim = "512MB" # 模拟的内存限制

enable_gui_deviation_detection_sim = false # 切换GUI偏轨模拟
sim_deviation_type = "MISSING_ELEMENT" # 类型：MISSING_ELEMENT, WRONG_COLOR, TEXT_MISMATCH
sim_deviation_trigger_probability = 0.1 # 注入偏轨的概率
```
*   `[oppie_simulation_m1]` 部分是M1的自定义，用于控制模拟参数，如果OpenHands任务直接涉及这些模拟。否则，模拟逻辑存在于OpenHands调用的单独脚本中。

---

## 5 Dev-Loop Watcher (Python)

### 5.1 职责
*   **监控OpenHands输出：** 跟踪或持续读取 `oppie_openhands_config.toml` 中指定的日志文件（`logging.file_path`）或如果OpenHands由Adapter作为子进程运行，则直接读取 `stdout/stderr`。
*   **检测工具限制错误：** 使用正则表达式查找来自Cursor工具的确切"Exceeded 25 native tool calls"字符串（由OpenHands调用）。
*   **检测缺失的Template A：** 在Adapter写入响应后，Watcher（或Adapter在完成其周期前的后续检查）验证响应文件是否包含必要的 `PLANNER RESPONSE FOR CYCLE {n}` 结构，尤其是 `EXECUTOR FOLLOW-UP CHECKLIST`。
*   **触发恢复：** 如果检测到错误，向 `OpenHands Adapter` 发送 `RecoveryRequest`（例如，通过简单的IPC机制，如消息队列、文件信号或如果集成则直接函数调用）。

### 5.2 检测正则表达式
*   工具限制：`r"Exceeded 25 native tool calls"`（确保这与Cursor输出完全匹配）。
*   缺失的Template A结构：`r"EXECUTOR FOLLOW-UP CHECKLIST"`（存在性检查）。更稳健的检查可能会查找多个关键标题。

### 5.3 恢复逻辑

```python
# dev_loop_watcher.py（概念性）
import re
import time

class DevLoopWatcher:
    def __init__(self, adapter_client): # adapter_client 用于发送 RecoveryRequest
        self.adapter_client = adapter_client
        self.tool_limit_regex = re.compile(r"Exceeded 25 native tool calls")
        self.template_a_checklist_regex = re.compile(r"EXECUTOR FOLLOW-UP CHECKLIST")

    def monitor_openhands_execution(self, log_stream_or_file_path, current_template_a_req_path):
        # 持续读取 log_stream_or_file_path
        for line in read_stream_lines(log_stream_or_file_path):
            if self.tool_limit_regex.search(line):
                print("Watcher: 检测到工具限制！")
                self.adapter_client.trigger_recovery(
                    RecoveryRequest(
                        type="TOOL_LIMIT_EXCEEDED", 
                        original_template_a_path=current_template_a_req_path,
                        details={"error_line": line}
                    )
                )
                return # 停止监控此运行，恢复已启动
            # 如果需要，添加其他实时检查

    def check_planner_response_integrity(self, response_template_a_path):
        with open(response_template_a_path, 'r') as f:
            content = f.read()
        if not self.template_a_checklist_regex.search(content):
            print("Watcher: Planner响应缺少Template A清单！")
            self.adapter_client.trigger_recovery(
                RecoveryRequest(
                    type="TEMPLATE_A_MISSING", 
                    original_template_a_path=response_template_a_path, # 或导致此格式错误响应的请求
                    details={"error": "Missing EXECUTOR FOLLOW-UP CHECKLIST"}
                )
            )
            return False
        return True
```
*   **协调：** Adapter将在OpenHands运行期间调用 `monitor_openhands_execution`。在Adapter写入响应后，它（或主脚本）将调用 `check_planner_response_integrity`。

---

## 6 M1 设计与模拟细节（VDI/GUI/移动/接管）

### 6.1 VDI 资源隔离（设计与模拟）
*   **概念：** 使用Linux cgroups v2和命名空间（PID、挂载、网络、用户）在VDI中隔离假设的代理进程。
*   **M1 设计文档：** 详细描述cgroup层次结构（例如，VDI会话的系统切片，每个代理的子切片）。指定要使用的控制器（cpu.max、memory.high、memory.max、pids.max）。为每个代理记录命名空间设置。
*   **M1 模拟：** 
    *   使用 `subprocess` 启动简单子进程的Python脚本（`simulate_vdi_agents.py`）。
    *   使用 `cgcreate`、`cgset`（来自 `cgroup-tools`）或直接 `/sys/fs/cgroup` 操作程序化创建和分配cgroups给这些进程。
    *   子进程执行CPU密集型和内存分配任务。
    *   父脚本监控实际资源使用情况（例如，通过 `ps` 或 `/proc/[pid]/stat`）和cgroup统计信息以验证限制是否被强制执行。
    *   此脚本可以是OpenHands工具或由OpenHands动作调用。

### 6.2 GUI 流优化（设计）
*   **概念：** 基于估计的网络带宽和内容复杂度的自适应比特率（ABR）视频流（例如，H.264、AV1）。服务器端量化调整。
*   **M1 设计文档：** 
    *   算法：提出一个QoE（体验质量）模型。例如，基于缓冲的（如BOLA）或基于速率的（如PANDA）ABR算法草图。
    *   指标：定义带宽估计的指标（例如，吞吐量历史、RTT）和内容复杂度（例如，I帧大小、运动矢量）。
    *   量化：服务器如何根据ABR决策调整QP（量化参数）。
    *   **M1不模拟视频编码。** 重点在于决策逻辑。

### 6.3 GUI 流偏轨检测（设计与模拟）
*   **概念：** 检测GUI截图/帧序列中的意外变化或缺失元素。
*   **M1 设计文档：** 
    *   算法：提出一个简单的基于特征的比较。例如，对于定义的感兴趣区域（ROI）：
        1.  参考截图：提取关键特征（例如，SIFT/ORB关键点、颜色直方图、主色、通过模板匹配的模板图像存在）。
        2.  实时帧：提取相同特征。
        3.  比较特征集（例如，特征距离、直方图交集、颜色差异）。如果偏轨 > 阈值，标记。
    *   考虑OCR用于文本存在/缺失。
*   **M1 模拟：** 
    *   使用OpenCV的Python脚本（`simulate_gui_deviation.py`）。
    *   接受参考图像和测试图像（有/无模拟偏轨）。
    *   实现所选的特征提取和比较逻辑。
    *   输出偏轨分数或布尔标志。
    *   此脚本可以是OpenHands工具。

### 6.4 移动体验优化（设计）
*   **M1 设计文档：** 关注与长时间运行代理交互的PWA的UX原则。
    *   **信息层次：** 小屏幕上什么是关键的（当前步骤、阻碍、ETA、关键日志行）？
    *   **控件：** 必要的控件（暂停、恢复、中止、批准简化差异）。
    *   **通知：** 对关键事件（周期完成、错误、需要人类输入）进行非侵入性但信息丰富的推送通知。
    *   **数据最小化：** 设计状态更新的数据负载以适应移动网络。

### 6.5 人类接管协议（设计）
*   **M1 设计文档：** 定义状态、触发器和交互流程。
    *   **代理状态：** `AUTONOMOUS`，`BLOCKED_AWAITING_HUMAN`，`HUMAN_INTERVENING`，`TRANSITION_TO_AUTONOMOUS`。
    *   **等待人类的触发器：** 在一个步骤上反复失败，代理显式 `REQUEST_HUMAN_HELP` 动作，关键护栏违规。
    *   **界面（概念性）：** PWA显示当前代理状态、问题描述、相关工件。人类通过PWA提供输入（例如，新指令、文件编辑、跳过步骤）。
    *   **交接：** 代理如何整合人类输入并尝试自主恢复。

---

## 7 测试计划（M1 增加）

*   **OpenHands Adapter 测试：**
    *   `adapter/mapping.py` 的单元测试：`test_parse_valid_template_a`，`test_parse_malformed_template_a`，`test_construct_template_a_response`。
    *   `OpenHandsAdapter` 的单元测试（模拟OpenHands客户端）：`test_convert_template_a_to_oh_task_structure`，`test_convert_oh_events_to_template_a_analysis`，`test_formulate_tool_limit_recovery_task`。
    *   集成测试：完整循环 `Template A 请求文件 -> Adapter -> 模拟的OpenHands（返回预定义事件） -> Adapter -> Template A 响应文件`。
*   **Dev-Loop Watcher 测试：**
    *   单元测试（模拟Adapter客户端）：`test_detect_tool_limit_from_logs`，`test_detect_missing_checklist_from_response_file`，`test_correct_recovery_request_sent`。
*   **VDI/GUI 模拟测试：**
    *   `simulate_vdi_agents.py` 的单元测试：`test_cgroup_application_and_monitoring`（如果需要，模拟cgroup命令）。
    *   `simulate_gui_deviation.py` 的单元测试：`test_deviation_detection_logic` 使用示例图像。
*   **端到端（简化M1）：**
    *   场景：初始 Template A -> Adapter -> 模拟的OpenHands（模拟几个成功步骤然后在日志中发出工具限制）-> Watcher 检测 -> Adapter 触发恢复任务 -> 模拟的OpenHands（模拟成功重新规划）。

---

## 8 可追溯性矩阵（M1 重点）
确保 `low_level_design.md` 部分映射到 `high_level_design.md` 组件和 `prd.md` M1 需求。

| LLD 部分                        | HLD 组件覆盖                     | PRD M1 需求ID覆盖        |
|:--------------------------------|:--------------------------------|:-------------------------|
| 3. OpenHands Adapter            | OpenHands Adapter               | FR-C4, FR-PR2, FR-PR3    |
| 4. OpenHands 配置               | OpenHands ACI（配置方面）       | FR-C1, FR-C2, FR-C3      |
| 5. Dev-Loop Watcher             | Dev-Loop Watcher                | FR-C5, FR-PR2, FR-PR3    |
| 6.1 VDI 资源隔离               | VDI/GUI 设计文档                | FR-VDI1                  |
| 6.2 GUI 流优化                 | VDI/GUI 设计文档                | FR-GUI1                  |
| 6.3 GUI 流偏轨检测             | VDI/GUI 设计文档                | FR-GUI2                  |
| 6.4 移动体验优化               | 移动/接管设计文档               | FR-MOB1                  |
| 6.5 人类接管协议               | 移动/接管设计文档               | FR-HT1                   |
| 7. 测试计划（M1 增加）         | 所有M1组件                      | NFRs（可靠性、可测试性） |

---

> **低层设计（M1）结束。** 实现应遵循这些规范。