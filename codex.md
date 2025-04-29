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
    *   **Input:** Receives the latest `.scratchpad_logs/*_plan_request.md` file (a filled `Template A` instance, `Prompt A{n}`) via the `send_codex_plan_request.sh` script invoked by the Executor or Watcher.
    *   **Responsibilities:**
        *   Analyzes the `[CURRENT GOAL]`, `[CYCLE_NUMBER]`, `[ARTIFACTS]`, and `[KNOWN BLOCKERS]` provided in the input `Prompt A{n}`.
        *   Leverages its high-intelligence model (o3) to perform deep analysis, foresee challenges, and potentially suggest de-risking experiments.
        *   Considers project context from `scratchpad.md` (passed via `--project-doc`).
        *   Generates a response containing the sections defined in Template A's `REQUEST FOR CODEX PLANNER` (Key Challenges, Plan, Blocker Solutions, Best Practices, Executor Checklist).
    *   **Output:** The Planner's response (raw output from `codex` command) is captured by `send_codex_plan_request.sh` and saved to a new timestamped file: `.scratchpad_logs/YYYY-MM-DDTHH_MM_SS_plan_response.md`.
    *   **Handoff:** The Planner role concludes upon generating the response. The loop continues when the Executor processes this response file.

<!-- Codex Planner: The following describes the Executor's role. -->
<!-- Read this to understand how the Executor will interpret and act upon your plan. -->
2.  **Executor Role** 
    *   **Input:** Processes the latest `.scratchpad_logs/*_plan_response.md` file generated by the Planner (via `send_codex_plan_request.sh`). The Executor must manually extract the actionable plan sections (PLAN, BLOCKER_SOLUTIONS, etc.) from the potentially mixed raw output in this file.
    *   **Responsibilities:**
        *   Executes the step-by-step `PLAN` provided by the Planner, using available Cursor native/mcp tools (code edits, terminal commands, file operations, etc.).
        *   Utilizes `BEST_PRACTICES / MENTAL_MODELS` during execution.
        *   Attempts to resolve `BLOCKER_SOLUTIONS` if applicable.  
        *   Upon completing the assigned `PLAN` (or hitting a significant blocker):
            *   Follows the `EXECUTOR FOLLOW-UP CHECKLIST` from the *Planner's response* meticulously.
            *   Summarizes work and insights.
            *   Updates blocker status and the goal for the next cycle.
            *   **Crucially:** Creates a **new** `Template A` instance file (`.scratchpad_logs/YYYY-MM-DDTHH_MM_SS_plan_request.md`), filling all fields including the **incremented `CYCLE_NUMBER`**. This becomes `Prompt A{n+1}`.
    *   **Output:** The primary output is the newly created `Prompt A{n+1}` file (`.scratchpad_logs/YYYY-MM-DDTHH_MM_SS_plan_request.md`). Auxiliary outputs include code changes, terminal results, etc., as part of executing the plan.
    *   **Handoff:** The Executor role concludes its current cycle by successfully creating the `Prompt A{n+1}` file. The loop advances when `send_codex_plan_request.sh` is next invoked (by Watcher or manually) using this new request file.
    *   **Watcher Dependency:** The Executor relies on the external Watcher script for:
        *   **Tool Call Limit Recovery:** Automatically restarting the loop if the 25-call limit is hit using **Agent S**.
        *   **Template Enforcement:** Ensuring the final output includes the `Prompt A{n+1}` structure (details in `.cursor/low_level_design.md`).
        *   **Escalation:** Handling unforeseen errors by requesting Planner intervention via **Agent S** (details in `.cursor/low_level_design.md`).

## Document Conventions

<!-- Codex Planner: Understand where information is stored and how it flows. -->
<!-- The `.scratchpad_logs/` directory is key for cycle-to-cycle state. -->
*   The `.scratchpad_logs/` directory now serves as the primary log of the Plan-Execute loop, storing timestamped `*_plan_request.md` (Executor outputs) and `*_plan_response.md` (Planner outputs).
*   `scratchpad.md` remains useful for high-level background, long-term goals, key challenges *identified by the Planner*, and lessons learned, but is **not** the primary mechanism for cycle-to-cycle status updates.
<!-- Codex Planner: Note that the Executor should copy key parts of your response -->
<!-- (like Key Challenges) into scratchpad.md for persistent documentation. -->
*   Planner responses (extracted from `*_plan_response.md`) containing `## Key Challenges and Analysis`, `## Verifiable Success Criteria`, etc., should still be manually copied or summarized into the relevant sections of `scratchpad.md` by the Executor for persistent documentation.

## Workflow Guidelines

<!-- Codex Planner: This details the flow of the Plan-Execute loop. -->
*   **Initiation:** Start a task by manually creating the initial `Prompt A₀` file (`*_plan_request.md` with `CYCLE_NUMBER=0`) and running `send_codex_plan_request.sh`.
*   **Cycle:**
    1.  Executor receives `*_plan_response.md`.
    2.  Executor extracts plan and executes it.
    3.  Executor creates `Prompt A{n+1}` (`*_plan_request.md`).
    4.  `send_codex_plan_request.sh` is invoked (manually or by Watcher) using `Prompt A{n+1}`.
    5.  Planner receives `Prompt A{n+1}` and generates the next `*_plan_response.md`.
*   **Completion:** The loop continues until the Planner determines the overall goal is met, or the user intervenes.
*   **Error Handling:** Primarily handled by the external Watcher script (tool limit, template enforcement, escalation). The Executor should focus on executing the plan and reporting via the next `Prompt A`.

Please note:

*   Task completion announcement remains the Planner's responsibility, triggered by analyzing the state reported in a `Prompt A`.
<!-- Codex Planner: These points describe Executor behavior and information flow. -->
*   Avoid manually editing files in `.scratchpad_logs/` unless debugging the loop itself.
*   Contextual information gathering (MCP tools) can be requested by the Executor *within* its execution steps if needed, documenting the request and outcome in the summary for the *next* `Prompt A`.
*   Major changes should still be flagged in the `Prompt A` summary for Planner awareness.
*   Lessons learned should be added to `scratchpad.md`'s `Lessons` section.

# Tools

<!-- Codex Planner: These are tools available within the environment. -->
<!-- Some are primarily for your use (Codex), others for the Executor (MCPs, GitMCP). -->
<!-- Understand the capabilities and limitations of each. -->

## OpenAI o3 model via codex commandline tool

<!-- Codex Planner: This describes how YOU are invoked. -->
### Basic Usage

Invoked via the `send_codex_plan_request.sh` script, which handles finding the latest `Prompt A` request file and saving the raw response. See script comments for details.

### Optimised guideline

Refer to the `send_codex_plan_request.sh` script itself and the surrounding documentation in `.cursorrules` and the design documents (`.cursor/high_level_design.md`, `.cursor/low_level_design.md`). Key aspects include:
*   Dynamic finding of the latest `*_plan_request.md`.
*   Use of `script -q /dev/null` for pseudo-TTY.
*   Saving raw output to timestamped `*_plan_response.md`.
*   Reliance on Executor/human to parse the raw response.

## Exa MCP

<!-- Codex Planner: This MCP tool is available to the EXECUTOR for web searches. -->
<!-- You might instruct the Executor to use this if external info is needed for the plan. -->
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

<!-- Codex Planner: This MCP tool is available to the EXECUTOR for deep analysis WITHOUT coding. -->
<!-- You might instruct the Executor to use this for complex pre-analysis before implementation. -->
### What the tool is for  
`geminithinking` lives on the Gemini Thinking Server, an MCP server that wraps Google Gemini to produce **sequential, branch‑able "thoughts" and meta‑commentary** (confidence, alternative paths) but **never generates code**. It shines when we need *analysis before action*—architecture reviews, refactor plans, risk audits, etc.

### When to call this tool (Executor Role)
<!-- Codex Planner: Note this section describes WHEN THE EXECUTOR should call this tool. -->
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
<!-- Codex Planner: Note this section describes HOW THE EXECUTOR should use this tool. -->
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

<!-- Codex Planner: This guidance is for the EXECUTOR when using the Sequential Thinking MCP. -->
<!-- You can incorporate these steps into your plans if sequential thinking is needed. -->
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

<!-- Codex Planner: This MCP tool is available to the EXECUTOR for accessing historical context via Pieces LTM. -->
<!-- You might instruct the Executor to use this if past context is needed for planning or execution. -->
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
    
3.  "Show the decisions made around UI updates for the onboarding flow."

### Controlling Agent Responses with Pieces MCP

You can also control the agent's actions directly through your prompts, allowing Pieces MCP to first retrieve relevant data from your context, then instruct the agent to perform specific tasks or updates.

Here's an example:
-   **Prompt:**_"What is the package version update that Mark asked me to make? Make the relevant update in my package manifest."_
    
-   **Outcome:** Pieces MCP retrieves Mark's requested package version update from your context, then automatically directs the agent to apply this update to your `package.json` manifest.    

## Effective Prompting Tips

<!-- Codex Planner: These tips are primarily for the USER/EXECUTOR when using Pieces MCP. -->
Sometimes, it can be challenging to create a prompt that gets you exactly what you need.

When using Pieces, especially with its large, on-device repository of personalized workflow data, it\'s best to use more specific prompts.

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
    
- What resources did I save recently related to Python decorators?
    
-   "Show notes taken about GraphQL in March."

Code & Collaboration

-   "Show code review comments related to database indexing."
    
-   "Did we finalize naming conventions for the latest API endpoints?"
    
-   "What feedback did I leave on recent pull requests?"

## SQLite DB Access (via mcp-alchemy)

<!-- Codex Planner: This describes tools available to the EXECUTOR for querying Cursor's internal SQLite DB. -->
<!-- Useful for inspecting internal state if needed, though likely less common for you to instruct directly. -->
This set of tools provides direct read access to the Cursor application\'s internal state database located at `/Users/yongbingtang/Library/Application Support/Cursor//User/globalStorage/state.vscdb` via the `mcp-alchemy` MCP server. This allows querying internal application state, configurations, or potentially historical data stored by Cursor.

**Database Connection Details:**
*   **Type:** SQLite (Version 3.49.1 based on typical system installs)
*   **Path:** `/Users/yongbingtang/Library/Application Support/Cursor//User/globalStorage/state.vscdb`
*   **User:** `None`

**Available Tools:**

*   **`mcp_my_sqlite_db_all_table_names`**
    *   **Purpose:** Retrieves a comma-separated list of all table names within the connected SQLite database.
    *   **When to use:** To get an initial overview of the database structure.

*   **`mcp_my_sqlite_db_filter_table_names`**
    *   **Purpose:** Filters table names based on a provided substring `q`.
    *   **Parameters:**
        *   `q`: Substring to filter table names by.
    *   **When to use:** When you know part of a table name and want to find matching tables.

*   **`mcp_my_sqlite_db_schema_definitions`**
    *   **Purpose:** Returns the schema (column names, types, constraints) and relation information for a list of specified table names.
    *   **Parameters:**
        *   `table_names`: A list of table names for which to retrieve schema information.
    *   **When to use:** To understand the structure and columns of specific tables before querying them.

*   **`mcp_my_sqlite_db_execute_query`**
    *   **Purpose:** Executes an arbitrary SQL query against the connected database and returns the results.
    *   **Parameters:**
        *   `query`: The SQL query string to execute.
        *   `params`: Optional dictionary of parameters to bind to the query (for parameterized queries, preventing SQL injection).
    *   **Output:** Results are returned in a readable format, truncated after 4000 characters.
    *   **When to use:** To fetch specific data, check values, or explore the contents of tables. Use parameterized queries (`params`) whenever possible, especially if incorporating external input into the query.
    *   **Caution:** This tool provides read-only access, but complex queries can still impact application performance if the database is actively used.

> **Note:** This tool interacts with an internal application database. Queries should be crafted carefully to avoid unintended consequences or performance issues. Always start with schema inspection before executing complex queries.

When you craft your response, recall that the Executor may send back **EXECUTOR ➡️ PLANNER QUESTIONS / REQUESTS** inside the next Template A. Treat that block as a priority inbox: answer those questions explicitly in your ANALYSIS, adjust the PLAN if needed, or acknowledge why certain requests are deferred.

