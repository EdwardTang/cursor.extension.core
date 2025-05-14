
# Available MCP Tools

## MCP服务器访问机制

所有MCP工具都通过`server pluggedin_proxy`机制访问，配置在`/Users/yongbingtang/.cursor/mcp.json`中。这使Cursor能连接到多种服务，包括搜索引擎、代码分析工具和数据库访问等。执行计划时，应考虑以下可用MCP服务器：

| MCP服务器 | 主要功能 | 适用场景 |
|----------|---------|---------|
| exa | 网络,Twitter,公司,学术的搜索与内容提取 | 需要外部信息、文档查询 |
| sequential-thinking | 任务分解与顺序规划 | 复杂问题分析、步骤计划 |
| my_sqlite_db | Cursor内部状态数据库访问 | 检查应用状态、配置 |
| Pieces | 长期记忆与上下文检索,和保存重要长期记忆文档 | 项目历史、之前工作恢复 |
| new-mcp (Gemini) | 深度分析当前代码库与思考链 | 架构评审、重构计划 |
| git | Git仓库管理 | 代码版本控制操作 |
| duckduckgo/mcp-server-serper | 替代搜索引擎,当exa/mcp-server-serper不可用时使用 | 网络搜索差异化 |
| mcp-deepwiki | GitHub 主要项目代码库的知识库访问,推荐研究探索解决方案时使用 | 文档和知识库查询 |
| context7-mcp | 实时更新当前技术栈相关知识库来增强上下文,减少LLM幻觉 | 扩展理解与分析 |

## Exa MCP

[Exa MCP Server](https://github.com/exa-labs/exa-mcp-server/)使AI助手能够通过Exa Search API执行实时网络搜索，提供安全可控的互联网访问。

**主要能力**：
* 优化的实时网络搜索结果，包含标题、URL和内容片段
* 支持多种专业搜索类型：网络、学术、社交媒体等

**核心工具**：
* `web_search`：通用网络搜索，适用于大多数信息获取需求
* `research_paper_search`：针对学术论文和研究内容的专业搜索
* `twitter_search`：查找Twitter/X上的推文、个人资料和对话
* `company_research`：通过爬取公司网站收集详细的企业信息
* `crawling`：从特定URL提取内容（文章、PDF、网页）
* `competitor_finder`：通过寻找提供类似产品的企业识别竞争对手

**启动方式**：
```bash
npx exa-mcp-server --tools=research_paper_search,company_research,crawling,competitor_finder,web_search,twitter_search
```

## Gemini Thinking Server MCP

`new-mcp`服务器包装了Google Gemini，生成**顺序的、可分支的"思考"和元评论**（置信度、替代路径），但**从不生成代码**。适用于需要深度分析的场景：架构评审、重构计划、风险审核等。使用Smithery CLI运行。

**核心参数概述**：
* `query`：要分析的问题
* `context`：额外上下文（对本项目，设置为'cloudkitchen_repo_mix.md'）
* `thought`：当前思考步骤（留空让Gemini生成）
* `thought_number`/`total_thoughts`：思考序列管理
* `is_revision`/`branch_id`：支持思考修改和分支
* `metaComments`/`confidenceLevel`/`alternativePaths`：元认知信息

> **使用提示**：此工具擅长分析，不生成代码。建议先运行'repomix'命令合并代码库上下文，设置context参数后让Gemini生成初始思考步骤，然后根据需要使用修改或分支功能。

**启动方式**：
```bash
npx -y @smithery/cli@latest run @bartekke8it56w2/new-mcp --key YOUR_KEY
```

## Sequential Thinking MCP Server

Sequential Thinking MCP通过结构化分解复杂问题，生成明确的执行计划，特别适合多步骤任务。基于Model Context Protocol标准，使用`@modelcontextprotocol/server-sequential-thinking`包实现。

**典型工作流**：
1. **任务分解**：将主任务拆分为自包含子任务
2. **步骤排序**：为每个子任务列出详细的执行顺序指令
3. **识别依赖关系**：明确子任务间的依赖，优化执行顺序
4. **网络搜索增强**：利用Exa或DuckDuckGo获取最新相关信息
5. **迭代优化**：整合搜索发现，根据需要重新分解和排序

**示例提示模板**：
"将以下`[任务]`分解为可管理的子任务。对每个子任务，提供详细的步骤说明，并明确识别子任务之间的依赖关系，以优化工作流程和任务优先级，实现高效完成。"

**启动方式**：
```bash
npx -y @modelcontextprotocol/server-sequential-thinking
```

## Git MCP Server

Git MCP Server提供对Git仓库的访问和操作能力，通过Node.js实现。本地配置指向`/Users/yongbingtang/Projects/git-mcp-server/dist/index.js`。

**主要功能**：
* 查询Git提交历史和代码更改
* 执行Git命令（例如clone、pull、push等）
* 分析代码库中的贡献者和活动
* 跟踪特定文件或分支的变更

**常用工具**：
* `git_history`：获取提交历史
* `git_diff`：比较不同版本的代码变更
* `git_blame`：查看特定文件各行的最后修改者
* `git_branch_info`：获取分支信息
* `git_execute`：执行指定的Git命令

**启动方式**：
```bash
node /Users/yongbingtang/Projects/git-mcp-server/dist/index.js
```

## MCP-DeepWiki

MCP-DeepWiki 服务器是一个为开发者和研究者设计的知识检索与文档分析平台，专注于 GitHub 主要项目的结构化知识获取与技术洞察。其底层实现基于 fastmcp 框架，支持通过 stdio 方式运行

MCP-DeepWiki服务器为开发者和研究者提供结构化的开源库检索与文档分析能力，特别适用于需要深入理解GitHub主流项目的技术细节和用法场景。其底层基于fastmcp框架，支持通过stdio方式运行，具备高效的库ID解析和文档获取工具。

**主要能力**：
* 解析库名为唯一的library ID（如mongodb/docs、vercel/nextjs等）
* 检索并获取指定开源库的最新文档、代码片段和技术说明
* 支持基于查询的文档聚焦（如“如何使用hooks？”、“如何配置路由？”）
* 结合GitHub指标（如star数、描述、语言）智能排序和推荐最相关的库
* 支持token限制，便于LLM上下文管理

**核心工具**：

- `resolve-library-id`  
  解析包名为唯一的library ID，并返回最相关的库列表。  
  **用法示例**：  
  ```
  {
    "tool": "resolve-library-id",
    "args": {
      "libraryName": "nextjs"
    }
  }
  ```
  返回内容包括最佳匹配的repo_name、描述、语言、star数等。必须先调用此工具获取library ID，再用于文档检索。

- `get-library-docs`  
  获取指定library ID的最新文档内容，可选支持查询聚焦和token长度限制。  
  **用法示例**：  
  ```
  {
    "tool": "get-library-docs",
    "args": {
      "libraryID": "vercel/nextjs",
      "query": "how to use routing?",
      "maxTokens": 2048
    }
  }
  ```
  返回内容为聚焦后的文档片段，便于LLM理解和回答技术问题。

**典型工作流**：
1. 先用`resolve-library-id`根据库名获取最优的library ID
2. 再用`get-library-docs`结合ID和具体查询获取高相关性的文档内容

**启动方式**：
```bash
node /path/to/mcp-deepwiki/dist/index.js
```

## Context7-MCP

Context7-MCP服务器使用Smithery CLI运行，提供实时更新的当前技术栈相关知识库，增强上下文理解并减少LLM幻觉。它使用Upstash作为后端。

**主要能力**：
* 提供最新的技术文档和指南
* 增强代码补全和建议的准确性
* 整合多源技术知识
* 上下文感知的问题解答

**核心工具**：
* `context_query`：基于当前工作上下文查询相关知识
* `tech_stack_info`：获取特定技术栈的最新信息
* `code_patterns`：获取特定编程问题的推荐模式
* `document_search`：搜索技术文档库

**启动方式**：
```bash
npx -y @smithery/cli@latest run @upstash/context7-mcp --key YOUR_KEY
```

## DuckDuckGo MCP Server

DuckDuckGo MCP服务器提供替代搜索引擎功能，当Exa或Serper不可用时特别有用。使用npx运行`duckduckgo-mcp-server`。

**主要能力**：
* 隐私保护的网络搜索结果
* 即时回答和摘要
* 特定领域知识查询

**核心工具**：
* `duckduckgo_search`：执行基本网络搜索
* `duckduckgo_instant_answer`：获取针对特定问题的即时回答
* `duckduckgo_news`：获取新闻相关搜索结果

**启动方式**：
```bash
npx -y duckduckgo-mcp-server
```

## Serper MCP Server

Serper MCP服务器(`mcp-server-serper`)是另一个替代搜索选项，使用Smithery CLI运行，通过Serper API提供Google搜索结果。

**主要功能**：
* 高质量的网络搜索结果
* 结构化数据提取
* 新闻、图片和视频搜索

**核心工具**：
* `serper_search`：执行基本网络搜索
* `serper_news`：获取新闻相关搜索结果
* `serper_images`：搜索图片
* `serper_videos`：搜索视频内容

**启动方式**：
```bash
npx -y @smithery/cli@latest run @marcopesani/mcp-server-serper --key YOUR_KEY
```

## SQLite DB Access (via mcp-alchemy)

此工具集通过`mcp-alchemy` MCP服务器提供对Cursor应用程序内部状态数据库的直接读取访问，位于`/Users/yongbingtang/Library/Application Support/Cursor//User/globalStorage/state.vscdb`。

**核心工具**：
* `mcp_my_sqlite_db_all_table_names`：获取所有表名
* `mcp_my_sqlite_db_filter_table_names`：按子字符串筛选表名
* `mcp_my_sqlite_db_schema_definitions`：获取指定表的架构信息
* `mcp_my_sqlite_db_execute_query`：执行任意SQL查询并返回结果

**启动方式**：
```bash
uvx --from mcp-alchemy==2025.04.16.110003 --refresh-package mcp-alchemy mcp-alchemy
```

**最佳实践**：先检查架构，再执行复杂查询；使用参数化查询防止SQL注入；注意查询对应用性能的潜在影响。

## Pieces MCP

[Pieces MCP](https://docs.pieces.app/products/mcp)允许通过自然语言查询Pieces长期记忆(LTM)系统，检索开发上下文和历史，并保存重要的长期记忆文档。

**关键功能**：
* 检索历史工作内容和上下文
* 支持时间范围、应用源和主题参数组合
* 保存和组织重要的代码片段和文档
* 能直接影响代理行为（检索+执行）

**高效查询技巧**：
* 明确指定时间范围（"昨天"、"4月2日至6日"）
* 包含应用源（"Chrome上访问的Stack Overflow页面"）
* 添加技术关键词（"API身份验证相关的JavaScript代码"）
* 引用打开的文件和后续问题

**主要使用场景**：
* 开发上下文（"显示React Context用法示例"）
* 项目历史（"追踪仪表板功能的演变"）
* 学习检索（"最近关于Kubernetes的书签"）
* 代码和协作（"显示与数据库索引相关的代码评审评论"）

**注意**：Pieces MCP运行不需要额外命令，但需要安装Pieces桌面应用作为后端服务。



## UML-MCP: 图表生成服务器

UML-MCP 是一个强大的图表生成服务器，它实现了模型上下文协议 (Model Context Protocol, MCP)，能够直接从 AI 助手和其他应用程序无缝创建图表。

**核心功能**：
*   **多种图表类型支持**：支持 UML 图（类图、序列图、活动图、用例图、状态图、组件图、部署图、对象图）、Mermaid、D2、Graphviz、ERD、BlockDiag、BPMN、C4 (使用 PlantUML) 等。
*   **MCP 集成**：与支持 MCP 的大语言模型 (LLM) 助手无缝集成。
*   **在线编辑器链接**：为每种图表类型提供直接链接到在线编辑器的功能。
*   **多种输出格式**：支持 SVG、PNG、PDF 等多种输出格式。
*   **灵活配置**：支持本地和远程图表渲染服务（如 Kroki, PlantUML）。
*   **模块化架构**：包括 MCP 服务器核心、图表生成器、MCP 工具接口和资源模板。

**核心工具 (Core Tools)**:
服务器实现了多种图表生成工具：

*   **通用UML生成器 (Universal UML Generator)**
    *   `generate_uml`: 生成任何支持的UML图表。
        *   参数: `diagram_type` (图表类型), `code` (图表定义代码), `output_dir` (可选, 输出目录)

*   **特定UML图表工具 (Specific UML Diagram Tools)**
    *   `generate_class_diagram`: 生成UML类图。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)
    *   `generate_sequence_diagram`: 生成UML序列图。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)
    *   `generate_activity_diagram`: 生成UML活动图。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)
    *   `generate_usecase_diagram`: 生成UML用例图。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)
    *   `generate_state_diagram`: 生成UML状态图。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)
    *   `generate_component_diagram`: 生成UML组件图。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)
    *   `generate_deployment_diagram`: 生成UML部署图。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)
    *   `generate_object_diagram`: 生成UML对象图。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)

*   **其他图表格式工具 (Other Diagram Formats)**
    *   `generate_mermaid_diagram`: 使用Mermaid语法生成图表。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)
    *   `generate_d2_diagram`: 使用D2语法生成图表。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)
    *   `generate_graphviz_diagram`: 使用Graphviz DOT语法生成图表。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)
    *   `generate_erd_diagram`: 生成实体关系图 (ERD)。
        *   参数: `code` (图表定义代码), `output_dir` (可选, 输出目录)

**可用资源 (MCP Resources)**:
服务器通过 `uml://` URI 协议提供以下资源：
*   `uml://types`: 可用的UML图表类型列表。
*   `uml://templates`: 用于创建UML图表的模板。
*   `uml://examples`: 用作参考的UML图表示例。
*   `uml://formats`: 支持的图表输出格式。
*   `uml://server-info`: 关于UML-MCP服务器的信息。

**辅助提示 (Helper Prompts)**:
服务器提供以下提示，以辅助创建常见的UML图表：
*   `class_diagram`: 创建一个UML类图，展示类、属性、方法和它们之间的关系。
*   `sequence_diagram`: 创建一个UML序列图，展示对象之间随时间变化的交互过程。
*   `activity_diagram`: 创建一个UML活动图，展示工作流程或业务流程的步骤。

**启动方式**：

通过 `smithery` CLI (推荐):
