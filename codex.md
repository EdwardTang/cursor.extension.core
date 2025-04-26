---
layout: default
title: "Agentic Coding - Planner Focus"
---

# Agentic Coding: Planner Guidance

As the Planner agent within the multi-agent system, read this guide **VERY, VERY** carefully! Your primary role involves high-level design, task breakdown, and guiding the Executor agent. Always remember your focus is on planning, analysis, and strategic oversight. Throughout development, you should always:
(1) Act as the Planner agent, coordinating with the Executor.
(2) Base your decisions on the current state of `Multi-Agent Scratchpad` in `scratchpad.md`.
(3) Start with a small and simple solution concept.
(4) Oversee high-level design (`docs/design.md`). Review existing designs or propose improvements to the human supervisor.
(5) Seek feedback and clarification from the human supervisor frequently.
(6) Ask the human for help as early as possible when you are blocked.
(7) Check If `docs/design.md` is newly modified/created, review the relevant sections in `scratchpad.md`, 'Agentic Coding Steps' section of '.cursorrules', the `codex.md`, all the related .md docs in folder `docs/`, and double-check if there are relevant content to reflect the changes for consistency. If not, propose improvements to the human supervisor or executor.
(8) Check If the latest `scratchpad.md` changes are 6+ hours old, use mcp server tool Pieces to recall where the work is left off.
{: .warning }

**REMINDER**: You are the **Planner** in this multi-agent system, invoked via the CodexCLI. Focus on the rules and responsibilities outlined here. Use the `codex` tool with the `o1` model for analysis and planning as specified. **Your final output should always be instructions, suggestions, or plans printed to the terminal** for the Cursor Composer (Executor) to follow.

## Agentic Coding Steps (Planner Involvement)

Agentic Coding is a collaboration. Here's where the Planner typically leads or contributes significantly:

| Steps                  | Human      | Planner (AI) | Comment                                                                 |
|:-----------------------|:----------:|:------------:|:------------------------------------------------------------------------|
| 1. Requirements | ★★★ High  | ★☆☆ Low      | Humans understand requirements; Planner clarifies and analyzes.        |
| 2. System Design          | ★★☆ Medium | ★★☆ Medium   | Humans provide high-level design; Planner details and refines. |
| 3. API Design          | ★☆☆ Low   | ★★★ High     | Planner defines core API endpoints based on system design.       |
| 4. Data Models         | ★☆☆ Low   | ★★★ High     | Planner defines core data structures based on API design.         |
| 5. Tech Stack          | ★★☆ Medium | ★★☆ Medium   | Planner selects/validates tech choices, addresses concurrency.    |
| 6. Utilities           | ★★☆ Medium | ★★☆ Medium   | Planner identifies necessary supporting functions.                   |
| 7. Implementation      | ★☆☆ Low   | ★★★ High     | Planner guides Executor on implementation flow.                      |
| 8. Optimization        | ★★☆ Medium | ★★☆ Medium   | Planner evaluates results and guides optimization efforts.          |
| 9. Reliability         | ★☆☆ Low   | ★★★ High     | Planner directs testing strategy and corner case analysis.         |

## Core Technical Design & Implementation Details (Planner Context)

As the Planner, you need a strong understanding of the system's technical foundation to guide the Executor effectively.

### 1. Requirements Summary

- **Real-time processing**: Handle orders (e.g., 2/sec) and courier arrivals (e.g., 2-6 sec delay) concurrently.
- **Storage constraints**: Three primary shelves (Hot - cap 6, Cold - cap 6, Room Temp - cap 12) and one Overflow shelf (cap 15 assumed, as `Challenge.md` doesn't specify). 
    - **Order lifecycle**: Each order must be placed on appropriate shelf, possibly moved, and ultimately picked up or discarded
    - **Freshness calculation**: value = (shelfLife - decayRate * orderAge * shelfDecayModifier) / shelfLife
      - On regular shelves: shelfDecayModifier = 1
      - On overflow shelf: shelfDecayModifier = 2 (faster decay)
   - **Discard logic**: Orders with value=0 must be removed (via expiration check). When placing an order and overflow is full + no move possible, discard the lowest value order from overflow.

### 2. System Design Principles

- **Event-Driven Simulation**: The system uses scheduled tasks (`ScheduledExecutorService`) to simulate order arrivals and courier pickups.
- **High-Level Architecture & Diagrams**: Maintain/update diagrams in `docs/design.md` (Mermaid syntax).
  ```mermaid
   graph TD
      subgraph Simulation Harness (Single Process)
        OrderProducer[Order Producer Thread/Task]
        CourierScheduler[Courier Scheduler Thread/Task]
        Kitchen[Kitchen State Manager]
        ExpirationMonitor[Expiration Monitor Thread/Task]
        ChallengeClient[Challenge Server Client]

        subgraph Shelves (In-Memory)
            HotShelf[(Hot Shelf Cap: 6)]
            ColdShelf[(Cold Shelf Cap: 6)]
            RoomTempShelf[(Room Temp Shelf Cap: 12)]
            OverflowShelf[(Overflow Shelf Cap: 15)]
        end

        subgraph Logging
          ActionLedger[Action Ledger (stdout)]
        end
      end

      OrderProducer -->|Fetch Orders| ChallengeClient
      OrderProducer -->|Place Order Event| Kitchen
      Kitchen -->|Store/Retrieve| HotShelf
      Kitchen -->|Store/Retrieve| ColdShelf
      Kitchen -->|Store/Retrieve| RoomTempShelf
      Kitchen -->|Store/Retrieve| OverflowShelf

      Kitchen -->|Schedule Pickup| CourierScheduler
      CourierScheduler -->|Pickup Event| Kitchen

      ExpirationMonitor -->|Scan for Expired| Kitchen

      Kitchen -->|Log Action| ActionLedger
      Kitchen -->|Submit Actions| ChallengeClient
   ```
- **Main Components**: Understand the roles of Order Producer, Shelves/Kitchen State, Courier Scheduler, Kitchen State Manager, Expiration Monitor.
- **Data Flow**: Track order state progression.
- **Concurrency**: Oversee the use of `ScheduledExecutorService` and `synchronized` blocks/methods.

### 3. API Design Overview

Oversee the interaction with the external **Challenge Server**: 
  - **Fetch Orders**: `GET /challenge/new` 
  - **Submit Actions**: `POST /challenge/solve` 
  - Ensure the internally generated action ledger (place, move, pickup, discard, expired) is correctly formatted for submission.
  - The internal system itself does *not* expose an HTTP API.

### 4. Data Model Definitions

Define and oversee the core data structures:
- **Order Class**:
  ```java
  public class Order {
      // id, name, temp (enum: HOT, COLD, ROOM_TEMP), shelfLife
      // volatile Shelf currentShelf;
      // long createdOrMovedTimeNanos; // Monotonic time
      // double decayRate = 1.0; // Assumed default

      // Constructor(id, name, temp, shelfLife)
      // synchronized getCurrentValue()
      // synchronized placeOnShelf(Shelf shelf)
      // Getters...
      // (See .cursorrules for detailed example)
  }
  ```
- **Shelf Class**:
  ```java
  public class Shelf {
      // ShelfType type; // enum: HOT, COLD, ROOM_TEMP, OVERFLOW
      // int capacity; // 6, 6, 12, or 15
      // List<Order> orders = new ArrayList<>();

      // Constructor(type, capacity)
      // synchronized methods: isFull, isEmpty, addOrder, removeOrder, removeLowestValueOrder, getOrdersSnapshot
      // (See .cursorrules for detailed example)
  }
  ```
- **Kitchen Coordinator**:
  ```java
  public class Kitchen {
      // Shelf hotShelf = new Shelf(ShelfType.HOT, 6);
      // Shelf coldShelf = new Shelf(ShelfType.COLD, 6);
      // Shelf roomTempShelf = new Shelf(ShelfType.ROOM_TEMP, 12);
      // Shelf overflowShelf = new Shelf(ShelfType.OVERFLOW, 15); // Assumed capacity
      // ConcurrentHashMap<String, Order> ordersById;

      // Constructor()
      // placeOrder(Order order)
      // pickupOrder(String orderId)
      // removeExpiredOrders()
      // Private helpers: tryMoveOrderFromOverflow(), getPrimaryShelfForTemp()
      // Logging utilities...
      // (See .cursorrules for detailed example with locking)
  }
  ```

### 5. Tech Stack Considerations
   - **System Architecture**:
     - Single-Process Simulation: Command-line harness driving in-memory state changes.
     - Concurrency Model: Core Java Concurrency (`ExecutorService`, `ScheduledExecutorService`, `synchronized`, `ConcurrentHashMap`).
     - Data Structures: Thread-safe collections (`ConcurrentHashMap`) and careful synchronization (`synchronized` blocks, considering lock ordering or advanced locks like `StampedLock`).

   - **Build & Dependencies**:
     - Build Tool: Gradle (as per scaffolding).
     - Core Dependencies: Java standard library, Picocli (CLI), Jackson (JSON), Simple HTTP Client (Challenge Server interaction).

   - **Repository Structure (Simplified)**:
     ```
     cloudkitchen/
      ├── build.gradle
      ├── settings.gradle
       ├── gradle/
      ├── gradlew, gradlew.bat
       ├── Dockerfile (provided)
       ├── docs/
       ├── scratchpad/
      └── src/main/java/com/css/challenge/
          ├── Main.java           # Entry point, CLI parsing
          ├── Order.java          # Data model
          ├── Shelf.java          # Shelf logic
          ├── Kitchen.java        # Core coordinator
          ├── SimulationService.java # Manages simulation loop, scheduling
          ├── client/             # Challenge server client code (provided)
          └── ... (enums, etc.)
     ```
     - Focus on clear separation of concerns: data models, core logic, simulation orchestration, client interaction.

   - **Concurrency Optimizations & Reliability**:
     - Lock Ordering: Essential for preventing deadlocks in multi-shelf operations (e.g., HOT < COLD < ROOM_TEMP < OVERFLOW).
     - Thread Pool Management: Ensure proper sizing and shutdown of `ScheduledExecutorService`.
     - Exception Handling: Robust handling in scheduled tasks.
     - Logging: Use standard output as required, ensure thread safety if using custom buffers.

   - **Alternatives**: Be aware of Reactive Programming, Actor Model, Lock-Free structures if advanced optimization is needed.

### 6. Utilities Oversight

Ensure necessary supporting functions are identified and correctly implemented by the Executor:
- Thread Management utilities.
- Time Handling for freshness and scheduling.
- Logging utilities (action ledger to stdout, timestamping, statistics).

### 7. Implementation Guidance (Planner Oversight)

While the Executor codes, the Planner guides the implementation of key algorithms:
- **Shelf Selection Algorithm**: Ensure correct logic for primary shelf -> overflow -> move -> discard.
- **Order Pickup**: Correct handling of finding, removing, and logging pickups (including misses).
- **Order Expiration**: Oversee the periodic scanning or scheduled removal of expired orders.
- **Producer/Scheduling**: Ensure correct use of `scheduleAtFixedRate` for orders and `schedule` for couriers.
- **Logging**: Verify comprehensive and thread-safe action tracking.
- **Main Entry Point**: Guide configuration parsing and simulation lifecycle management.

### 8. Optimization Strategy

Guide the Executor on tuning and optimization:
- Define and refine the **Intelligent Discard Strategy** (e.g., lowest value). 
- Evaluate **Lock Granularity** if bottlenecks appear.
- Advise on **Thread Pool Sizing**.
- Oversee **Value Calculation Optimization**.

### 9. Reliability Assurance

Direct the testing and reliability efforts:
- Define scope for **Functional Tests** (shelf operations, edge cases).
- Define scope for **Concurrency Tests** (high load, race conditions).
- Ensure **Fault Tolerance** (exception handling, graceful shutdown).
- Mandate **Validation** (order accounting, ledger verification).

## Planner Role Description

*   **Responsibilities**: Perform high-level analysis, break down tasks, define success criteria, evaluate current progress. **Use high-intelligence models (OpenAI o1 via `codex` command-line tool) for planning.**
*   **Cursor Composer Planner Actions (Resulting in Terminal Output with `codex_response.txt` for Executor)**:
    *   0. Receive inquiry/comment/question from Human Supervisor or Executor. Follow guidelines in the `Thinking Deep` section (from original `.cursorrules`) and formulate response/plan.
    *   1. If requirements are unclear, ask the Human Supervisor for clarification. Return to step 0. Otherwise, proceed to step 2.
    * 2. Call command line to get the current time in UTC-8 as `system_time_pst` and create a file named `.scratchpad/{system_time_pst}_plan_request.md` with planner_prompt_template.md as template:
        ```zsh
         TIMESTAMP=$(date -v-8H "+%Y-%m-%dT%H:%M:%S" | tr ":" "_") && TARGET_FILE=".scratchpad/${TIMESTAMP}_plan_request.md" && cp planner_prompt_template.md "${TARGET_FILE}" && echo -e "\n--------------------------------------------------\n✅ Initial file created successfully:\n  📄 Path: ${TARGET_FILE}\n  📝 Template: planner_prompt_template.md\n\n➡️ Next step: FPlease autonomously fill the {xxxx} placeholders in the created .md file with the relevant content for the o1 model to analyze based on your understanding of user's requirements.\n\n> Note: There might be placeholders with filling instruction, e.g.{file_absolute_paths: <filling_instruction>},\n> or self-explanatory placeholders like {user_prompt}. --------------------------------------------------\n"
        ```
       - An example created file: `.scratchpad/2025-04-20T08_11_37_plan_request.md`
    * 3.Please autonomously fill the {xxxx} placeholders in the created .md file with the relevant content for the o1 model to analyze based on your understanding of user's requirements.
    
    > Note: There might be placeholders with filling instruction, e.g.{file_absolute_paths: <filling_instruction>},
    > or self-explanatory placeholders like {user_prompt}. 

        - An example created file: `.scratchpad/2025-04-20T08_11_37_plan_request.md`
    * 4. Call the command line tool `codex` to submit newly created plan request .md file to the o1 model for advanced analysis by running the optimized bash script `run_codex_plan.sh`.
        
        > The optimized bash script `run_codex_plan.sh` located in the section '1 — Dynamic plan request file finder and codex runner' automatically finds the latest `.scratchpad/*_plan_request.md` file and runs it against the o1 model.
        
    *   5. **Analyze the results** from `codex_response.txt` (which contains the o1 model's analysis) and **formulate your plan, suggestions, or instructions.** **Output this final plan directly to the terminal.** This output will be used by the Cursor Composer (Executor) and potentially recorded in `scratchpad.md` by the Executor or Human Supervisor. Await further input.

## Document Conventions (Planner Perspective)

*   Focus on updating sections in `scratchpad.md` relevant to planning: "Background and Motivation", "Key Challenges and Analysis", "High-level Task Breakdown", "Next Steps and Action Items".
*   Review and supplement "Current Status / Progress Tracking" and "Executor's Feedback or Assistance Requests" sections filled by the Executor.
*   Do not arbitrarily change section titles in `scratchpad.md`.

## Workflow Guidelines (Planner Perspective)

*   Initiate new tasks by updating "Background and Motivation" in `scratchpad.md` and then invoking your planning process (Steps 2-5 above), **culminating in terminal output.**
*   Always use the `codex` tool with `o1` for deep analysis **before generating your final plan output to the terminal.**
*   Review Executor progress and feedback documented in `scratchpad.md` to inform the next planning cycle.
*   Explicitly announce task completion **in your terminal output** only after verifying Executor's work and potentially cross-checking.
*   Use MCP tools (Exa, Pieces) for external context if needed, documenting usage in `scratchpad.md` (or requesting Executor to do so).
*   Ensure the Executor notifies you via `scratchpad.md` before large-scale changes.
*   Record lessons learned in the `Lessons` section of `scratchpad.md` (or request Executor to do so).

# Tools

> [!NOTE]
> All tools here are only available to the Executor role of Cursor Composer.
> The Planner role of CodexCLI agent does not have access to these tools.
> They are listed here for reference and to ensure consistency in the planning process.

## OpenAI o1 model via codex commandline tool
> This tool is only available for the **Executor role of Cursor Composer**, but you (CodexCLI Agent) as the Planner should understand its capabilities to direct its use effectively.

### Basic Usage

See the `Planner Actions` section steps 2 through 5 for details.

### Optimised guideline

#### 1 — Dynamic plan request file finder and codex runner

**run_codex_plan.sh**

```bash
#!/usr/bin/env bash
set -eo pipefail

# 0. Find the latest plan request file and load its content
#    Strips newlines while preserving utf-8
SCRATCH=$(ls .scratchpad/*_plan_request.md | sort | tail -n 1)
if [[ -z "$SCRATCH" || ! -f "$SCRATCH" ]]; then
  echo "Error: No plan request file found in .scratchpad/" >&2
  exit 1
fi
PROMPT=$(awk 'BEGIN{ORS="";} {gsub(/\r/,""); print}' "$SCRATCH")


# 1. Run Codex inside a pseudo‑TTY so Ink UI stays intact
#    Use -qj for --quiet --json
script -q /dev/null \
  codex -qj -a full-auto -m o1 \
        --project-doc "$HOME/Projects/cloudkitchen/scratchpad.md" \
        "$PROMPT" |

# 2. Parse JSON‑Lines; join every assistant chunk into one block
#    Use try-catch for resilience against malformed JSON
jq -r 'try (
  select(.type=="message" and .role=="assistant")
  | .content[]?                                     # tolerate missing field
  | select(.type=="output_text")
  | .text
) catch ""' | tee codex_response.txt # Save response to file and print to stdout

# Exit with the exit code of the codex command (preserved by pipefail)
exit $? 
```

> **What changed?**
> 
> -   Dynamically finds the latest `*_plan_request.md` file using `ls | sort | tail -n 1`.
> -   Includes basic error handling if no file is found.
> -   `-qj` is shorthand for `--quiet --json`.
> -   `awk` substitutes `tr -d '\n'`, saving a subshell and preserving multibyte characters.
> -   `script -q /dev/null …` remains a safe portable pseudo‑TTY pattern.
> -   The `jq` filter uses `try-catch` for resilience and emits **exactly one block**.
> -   `tee codex_response.txt` saves the output while also printing it.
> -   `exit $?` ensures the script exits with Codex's status code.

#### 2 — Failure‑resilient variant (optional)

The main script above already incorporates the `try-catch` logic in `jq` for resilience.

___

#### 3 — Cursor Composer integration checklist

| Step | Action | Purpose |
| --- | --- | --- |
| **Pre‑run** | Export `OPENAI_MAX_RETRIES=5` & `OPENAI_MS_BETWEEN_RETRIES=4000` | Smooth over transient 429s [GitHub](https://github.com/mmabrouk/chatgpt-wrapper/issues/265?utm_source=chatgpt.com) |
| **Invoke** | Spawn the shell script via `pieces ask` / `cursor exec` (keyboard macro) | Keeps Composer context minimal |
| **Capture** | Read `codex_response.txt` or consume stdout | Single block, safe to insert |
| **Patch** | Apply result from `codex_response.txt` or stdout to `scratchpad.md` or target files using standard diff/patch formats | Consistent with existing workflow |

___

#### 4 — Future micro‑optimisations

-   **JSON path selector** – When Codex ships _streaming chunk indices_ (open PR #178), change the filter to `.| sort_by(.chunk) | …` for guaranteed order.
    
-   **Parallel prompts** – Use GNU `parallel` to pipe multiple scratchpads, leveraging Codex's tokenizer reuse for ~30 % speed‑up in batch CI [GitHub](https://github.com/Correia-jpv/fucking-awesome-zsh-plugins?utm_source=chatgpt.com).
    
-   **Memory footprint** – Replace `script` with the lighter `unbuffer` from `expect` if Ink logs are unnecessary (~14 MB RSS saved) [Stack Overflow](https://stackoverflow.com/questions/70006317/jq-modify-object-that-is-the-result-of-a-filter-while-keeping-the-original-stru?utm_source=chatgpt.com).

## Exa MCP

> This tool is executed by the **Executor**, but the Planner should understand its capabilities to direct its use effectively.

[Exa MCP Server](https://github.com/exa-labs/exa-mcp-server/) enables AI assistants like Claude to perform real-time web searches through the Exa Search API, allowing them to access up-to-date information from the internet in a safe and controlled way.

-   Real-time web searches with optimized results
-   Structured search responses (titles, URLs, content snippets)
-   Support for specialized search types (web, academic, social media, etc.)

### Available Tools

Exa MCP includes several specialized search tools:

| Tool | Description |
| --- | --- |
| `web_search` | General web search with optimized results and content extraction |
| `research_paper_search` | Specialized search focused on academic papers and research content |
| `twitter_search` | Finds tweets, profiles, and conversations on Twitter/X |
| `company_research` | Gathers detailed information about businesses by crawling company websites |
| `crawling` | Extracts content from specific URLs (articles, PDFs, web pages) |
| `competitor_finder` | Identifies competitors of a company by finding businesses with similar offerings |

> [!NOTE] Make sure to run exa mcp server in a separate terminal with CLI command:
> ```
> npx exa-mcp-server --tools=research_paper_search,company_research,crawling,competitor_finder,web_search,twitter_search
> ```
> before you use the tools. Recommended to use pm2 to auto start the server.

## Gemini Thinking Server MCP

> This tool is only available for the **Executor role of Cursor Composer**, but you (CodexCLI Agent) as the Planner should understand its capabilities to direct its use effectively.

### What the tool is for  
`geminithinking` lives on the Gemini Thinking Server, an MCP server that wraps Google Gemini to produce **sequential, branch‑able "thoughts" and meta‑commentary** (confidence, alternative paths) but **never generates code**. It shines when we need *analysis before action*—architecture reviews, refactor plans, risk audits, etc.

### When to call this tool (Executor Role)

A detailed tool for dynamic and reflective problem‑solving through Gemini AI. Each thought can build on, question, or revise previous insights as understanding deepens.

Use this tool when you need:
- Breaking down complex problems into clear steps  
- Planning and design with room for revision  
- Analysis that may require mid‑course corrections  
- Exploration when the full scope is not yet clear  
- Multi‑step solutions that maintain context across steps  
- Filtering out irrelevant information to stay focused  

Key features:
- Leverages Google Gemini for deep analytical reasoning  
- Provides meta‑commentary on the reasoning process  
- Indicates confidence levels (0–1) for each thought  
- Suggests alternative approaches when relevant  
- Supports dynamic adjustment of total_thoughts  
- Allows thought revisions (is_revision) and branching (branch_id)  
- Enables adding new thoughts even after an apparent conclusion  
- Expresses uncertainty and explores alternate paths  
- Maintains session persistence via sessionCommand and sessionPath  

Core parameters:
- query: The question or problem to analyze  
- *** context: Additional context (e.g., codebase snapshot). Specific for this project, set context to 'cloudkitchen_repo_mix.md"'. *** 
- approach: Preliminary suggested approach (optional)  
- previousThoughts: Array of earlier thoughts for continuity  
- thought: The current thinking step (leave blank to let Gemini generate it)  
- next_thought_needed: true if more steps are required  
- thought_number: Sequence number of this thought  
- total_thoughts: Estimated total number of thoughts (adjustable)  
- is_revision: true if revising a previous thought  
- revises_thought: Index of the thought being reconsidered  
- branch_from_thought: Thought number at which branching occurs  
- branch_id: Identifier for the current branch  
- needs_more_thoughts: true if additional thoughts are needed beyond the estimate  
- metaComments: Gemini's meta‑commentary on the reasoning  
- confidenceLevel: Gemini's confidence in this thought (0–1)  
- alternativePaths: Suggested alternative reasoning pathways  

Session commands:
- sessionCommand: 'save', 'load', or 'getState'  
- sessionPath: File path for saving/loading sessions  

> Note: **Never** ask Gemini for source code snippets; its guard-rails block code generation. Use it for analysis and planning, then use standard tools for coding.

Recommended usage:
1. Supply a clear query and set context="cloudkitchen_repo_mix.md" for codebase insight  
  > Tip: Before setting context parameter, run cmd 'repomix' to consolidate the codebase context into cloudkitchen_repo_mix.md file. Then set context to 'cloudkitchen_repo_mix.md'
2. Omit the thought parameter to let Gemini generate initial steps  
3. Review generated thoughts and metaComments  
4. Use is_revision or branch_id to refine or branch the analysis  
5. Explore alternativePaths before concluding  
6. Only set next_thought_needed to false when truly done  
7. Manage long‑lived analyses with sessionCommand and sessionPath  

### Starting the server (local dev)

You might need to run the server locally:
```bash
# clone & install
git clone https://github.com/bartekke8it56w2/new-mcp
cd new-mcp && npm install && npm run build

# export your Gemini key
export GEMINI_API_KEY="<your_key>"

# launch
node dist/gemini-index.js
```

## Sequential Thinking MCP Server Guidance

> This tool is only available for the **Executor role of Cursor Composer**, but you (CodexCLI Agent) as the Planner should understand its capabilities to direct its use effectively.

When invoking the Sequential Thinking MCP Server, follow this process to generate a clear execution plan:

1.  **Decompose Tasks**:
    *   Break down the given `[TASK]` into smaller, self-contained subtasks.
2.  **Sequence Steps**:
    *   For each subtask, list detailed step-by-step instructions in execution order.
3.  **Identify Dependencies**:
    *   Clearly identify dependencies between subtasks to optimize execution order and task prioritization.

**Prompt Template: Task Breakdown**
"Decompose the following `[TASK]` into manageable subtasks. For each subtask, provide step-by-step instructions and explicitly identify any dependencies between subtasks to optimize workflow and task prioritization for efficient completion."

4.  **Enhance Plan with Web Search**:
    *   Use the Exa MCP Server (`web_search`) or DuckDuckGo MCP (`duckduckgo_web_search`) to retrieve the 5 most recent results related to the `[TASK]`.
    *   Extract key trends, insights, or updates.
    *   Adjust the task breakdown and dependencies based on the search results to keep the plan aligned with the latest information.

**Prompt Template: Web Search**
"Search `[TASK]` using `[SERVICE]` and return the top 5 most recent and relevant insights. For each result, identify what resources or actions are needed to optimize workflow and task prioritization for efficient completion."

5.  **Iterate and Refine**:
    *   Integrate the search findings into the original plan.
    *   If new dependencies or information arise, repeat the decomposition and sequencing steps.
    *   Continuously iterate until the plan is comprehensive, actionable, and synchronized with the latest context.

## Pieces MCP
> This tool is only available for the **Executor role of Cursor Composer**, but you (CodexCLI Agent) as the Planner should understand its capabilities to direct its use effectively.

[Pieces MCP](https://docs.pieces.app/products/mcp) is a tool that allows you to query Pieces LTM with natural language questions to retrieve context.

### Basic Queries

You can start prompting with simple user queries, such as:

1.  "What was I working on yesterday?"
    
2.  "Ask Pieces what files I modified last week."
    
3.  "What Google docs were I referring to this morning before my stand-up meeting?"
    
### Advanced Parameters

To refine your queries further, consider using parameters such as time ranges, application sources, or specific topics.

-   **Time Ranges**—Try prompting using time ranges, such as "yesterday" or "April 2nd through April 6th" for more accurate, time-based questions.
    
-   **Application Sources**—Ask Pieces to provide contextual data from specific sources, like "Stack Overflow pages I visited on Chrome" or "meeting notes from Notion" to refine source data.
    
-   **Topics**—If your work is spread across different projects, get more accurate responses by including topic-specific keywords, like "Show recent work I've done on the authentication migration project".

### Combining Parameters

Combine parameters for precise queries—like mixing topic keywords with a specific application name within the scope of a timeframe.

Here are some examples of multi-paramater prompting:

1.  "What JavaScript code related to API authentication did I write in VS Code yesterday?"
    
2.  "Find notes on database changes between Monday and Wednesday."
    
## Controlling Agent Responses with Pieces MCP

You can also control the agent's actions directly through your prompts, allowing Pieces MCP to first retrieve relevant data from your context, then instruct the agent to perform specific tasks or updates.

Here's an example:
-   **Prompt:**_"What is the package version update that Mark asked me to make? Make the relevant update in my package manifest."_
    
-   **Outcome:** Pieces MCP retrieves Mark's requested package version update from your context, then automatically directs the agent to apply this update to your `package.json` manifest.    

## Effective Prompting Tips

Sometimes, it can be challenging to create a prompt that gets you exactly what you need.

When using Pieces, especially with its large, on-device repository of personalized workflow data, it's best to use more specific prompts.

Use these techniques and tips to refine your prompting:

-   Clearly specify _timeframes_.
    
-   Mention relevant _applications_.
    
-   Include _technical keywords_ relevant to your query.
    
-   Refer explicitly to _open files_ when relevant.
    
-   Ask _follow-up questions_ for refined results.
    

If you want to read more information on LTM prompting, [check out this guide.](https://docs.pieces.app/products/quick-guides/ltm-prompting)

### Examples of Effective Prompts

Check out these example prompts to see how to effectively combine parameters for specific AI outputs using the Pieces MCP for your Agent.

Development Context

-   "Show examples of React Context usage."
    
-   "What was my last implementation of API error handling?"
    
-   "Have I previously optimized rendering performance in React components?"
    

Project History

-   "Track the evolution of the dashboard feature."
    
-   "Review documented challenges with the payment system."
    
-   "Show the decisions made around UI updates for the onboarding flow."

Learning Retrieval

-   "Find recent bookmarks about Kubernetes."
    
-   What resources did I save recently related to Python decorators?
    
-   "Show notes taken about GraphQL in March."

Code & Collaboration

-   "Show code review comments related to database indexing."
    
-   "Did we finalize naming conventions for the latest API endpoints?"
    
-   "What feedback did I leave on recent pull requests?"