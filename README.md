# MiniCoder

> 一个面向本地工作区的 Coding Agent：能够读取与搜索代码、修改文件、执行命令、运行测试，并根据真实工具结果持续完成自然语言编程任务。

Git 仓库：<https://github.com/sjx0921/MiniCoder.git>

---

## 1. 项目简介

MiniCoder 是一个本地编程智能体。用户给出自然语言任务后，模型负责判断下一步行动，MiniCoder 的控制层负责解析 Tool Call、检查任务约束与审批策略、执行本地工具，并把真实执行结果重新回填给模型，形成多轮闭环。

典型流程：

```text
用户任务
   ↓
构建系统提示、运行环境与历史上下文
   ↓
调用大语言模型
   ↓
模型返回自然语言或 Tool Call
   ↓
控制层解析 Tool Call
   ↓
任务约束 / 风险 / 审批检查
   ↓
执行本地工具
   ↓
工具结果回填对话历史
   ↓
模型继续读取 / 修改 / 测试
   ↓
验证通过并输出最终总结
```

核心设计可以概括为：

```text
LLM 负责决策
工具负责执行
框架负责控制与验证
```

---

## 2. 核心能力

MiniCoder 当前支持：

- 自然语言编程任务
- OpenAI-compatible Chat Completions 接口
- 模型原生 Tool Calling
- 多轮自主 Agent Loop
- 本地文件读取、搜索、写入与精确替换
- Windows PowerShell 命令执行
- unittest / pytest / Cargo / Go / Node 测试线索识别
- 自动运行测试并读取真实结果
- Git status / diff / staged / unstaged / untracked 审查
- `update_plan` 任务计划
- plan-first 控制机制
- `auto / ask / strict` 三种审批模式
- 高风险操作强制确认
- workspace 文件路径隔离
- “不修改 tests”“只修改指定文件”等任务级约束
- 用户拒绝后的防重复执行与基础防绕过
- 修改版本与最近成功测试版本绑定
- 修改后重新验证
- 成功命令缓存，避免同一版本重复执行相同验证
- 会话历史保留与任务状态隔离
- 上下文压缩
- `/reset`
- 最大 Agent 轮数限制
- 命令 timeout
- 命令输出截断
- Windows UTF-8 输出
- 框架级执行事实总结
- 任务结束后的 Git 审查

---

## 3. 环境要求

```text
Python 3.10+
Windows / PowerShell
```

MiniCoder 本体只使用 Python 标准库。

克隆仓库：

```powershell
git clone https://github.com/sjx0921/MiniCoder.git
cd MiniCoder
```

复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

配置模型：

```text
MINICODER_API_KEY=你的 API Key
MINICODER_BASE_URL=https://api.openai.com/v1
MINICODER_MODEL=gpt-4o-mini
```

也可以连接支持 OpenAI-compatible Chat Completions + Tool Calling 的其他模型或网关，例如：

```text
MINICODER_BASE_URL=https://api.deepseek.com
MINICODER_MODEL=deepseek-chat
```

> **真实运行 MiniCoder 需要可用的模型 API 和 API Key。**
>
> **只有仓库中的离线自动化测试不需要 API Key。**

---

## 4. 什么是 OpenAI-compatible Chat Completions / Tool Calling？

MiniCoder 的 `llm.py` 自己实现了一个很小的 HTTP 客户端。

它向：

```text
{MINICODER_BASE_URL}/chat/completions
```

发送请求，主要包含：

```json
{
  "model": "...",
  "messages": [...],
  "tools": [...],
  "tool_choice": "auto"
}
```

这里的 **OpenAI-compatible** 指的是请求和响应格式兼容 OpenAI Chat Completions 协议，并不意味着必须使用 OpenAI 模型。

### Chat Completions

`messages` 保存系统消息、用户任务、模型回复以及工具结果。MiniCoder 每一轮都会把当前上下文交给模型，由模型生成下一步回复。

### Tool Calling

MiniCoder 会把本地工具的 schema 一并发给模型。模型需要执行工具时，可以返回类似：

```json
{
  "tool_calls": [
    {
      "id": "call_1",
      "type": "function",
      "function": {
        "name": "read_file",
        "arguments": "{\"path\":\"text_utils.py\"}"
      }
    }
  ]
}
```

MiniCoder 随后：

1. 解析 `tool_calls`
2. 解析函数参数 JSON
3. 检查任务约束、风险和审批状态
4. 在本地执行对应工具
5. 把结果以 `role: tool` 写回消息历史
6. 再次调用模型

因此模型本身并不直接操作文件系统；真正的文件和命令操作都由 MiniCoder 的本地工具完成。

---

## 5. 快速使用

### 5.1 交互模式

在仓库根目录：

```powershell
python main.py --workspace .
```

指定其他项目：

```powershell
python main.py --workspace C:\path\to\project
```

例如：

```powershell
python main.py --workspace .\minicoder_video_demo --approval-mode auto
```

启动后直接输入任务：

```text
任务> 先制定计划，运行当前完整测试，根据失败结果修复实现，不要修改 tests，最后重新测试并检查 Git diff。
```

退出：

```text
exit
quit
```

重置会话：

```text
/reset
```

### 5.2 单次任务

```powershell
python main.py "检查项目测试失败原因并修复" --workspace .
```

---

## 6. 本地工具

### `inspect_environment`

向模型提供当前运行环境的权威信息，包括：

- 操作系统
- Shell
- workspace 绝对路径
- Python
- 测试框架线索
- 推荐测试命令

### `list_files`

列出 workspace 中的文件和目录，并默认忽略 `.git`、`.venv`、`__pycache__`、`node_modules` 等生成目录。

### `read_file`

读取 workspace 内文本文件。

### `search_text`

在项目中搜索文本并返回匹配文件与位置。

### `write_file`

新建或完整覆盖文本文件。

### `replace_in_file`

对文件进行小范围精确替换。若待替换文本出现多次、存在歧义，会拒绝模糊修改。

### `run_command`

使用 Windows PowerShell 在 workspace 目录中执行命令，支持：

- 风险分类
- timeout
- 输出截断
- UTF-8 输出

### `git_status`

读取 Git 工作区状态，并区分：

- staged
- unstaged
- untracked

### `git_diff`

检查真实文件差异。

### `update_plan`

维护任务计划，状态包括：

```text
pending
in_progress
completed
```

---

## 7. Agent Loop

`agent.py` 是 MiniCoder 的核心控制层。

每轮主要执行：

```text
compact history（必要时）
        ↓
LLMClient.complete(messages, tools)
        ↓
读取 assistant_message.tool_calls
        ↓
解析 function name / arguments
        ↓
执行任务约束和审批检查
        ↓
ToolRegistry 执行本地工具
        ↓
role=tool 的结果写回 messages
        ↓
下一轮模型决策
```

如果模型不再返回 Tool Call，框架会判断当前任务是否满足结束条件。

如果达到 `max_turns`，Agent 会主动停止，防止无限循环。

---

## 8. Plan 与 plan-first

复杂任务可以使用：

```text
update_plan
```

例如：

```text
[in_progress] 运行完整测试
[pending] 根据失败结果定位实现
[pending] 修复代码
[pending] 重新验证
[pending] 检查 Git diff
```

当用户明确要求：

```text
先制定计划，然后……
```

MiniCoder 会进入 plan-first 状态。

**在计划成功建立之前，仅允许 `update_plan` 执行；其他工具调用都会被控制层阻止。**

如果模型一次返回多个 Tool Call，并且其中包含 `update_plan`，该轮只执行计划调用，其余调用等待后续模型轮次。

---

## 9. 会话历史与任务状态

交互模式中，同一进程会保留对话历史，因此用户可以继续说：

```text
只修刚才分析出来的第一个问题。
```

同时，每次新的 `任务>` 都会重置当前任务自己的执行状态，包括：

- Plan
- 任务级约束
- 拒绝记录
- 修改文件集合
- 修改版本
- 最近成功测试版本
- 成功命令缓存
- 当前任务活动记录

因此：

```text
会话上下文可以连续
任务执行状态不会串线
```

MiniCoder 当前**没有跨进程持久会话**；关闭程序后不会把聊天历史自动保存到磁盘。

---

## 10. `/reset`

输入：

```text
/reset
```

会清空：

- 对话历史
- Plan
- 任务约束
- 拒绝状态
- 修改 / 验证版本
- 成功命令缓存
- 当前任务活动状态

workspace 配置仍然保留。

---

## 11. 上下文压缩

MiniCoder 使用 `max_history_chars` 控制发送给模型的历史大小。

当历史过长时，会保留近期消息，并生成结构化摘要，摘要中保留：

- 最近任务
- 当前 Plan
- 当前任务约束
- 拒绝状态
- 修改版本
- 最近成功测试版本
- 近期工具活动

避免会话历史无限增长。

---

## 12. 任务级文件约束

MiniCoder 会从常见自然语言中提取部分可执行约束。

### 禁止修改测试

例如：

```text
不要修改 tests 下任何文件。
不要动测试文件。
do not modify tests.
```

控制层会在文件工具真正执行前直接拒绝 tests 写入。

### 只允许修改指定文件

例如：

```text
本任务只允许修改 text_utils.py。
只修改 text_utils.py。
only modify text_utils.py.
```

如果模型尝试通过 `write_file` 或 `replace_in_file` 修改其他文件，会被执行前拦截。

> 这类路径约束针对 MiniCoder 的结构化文件工具。`run_command` 不是完整文件权限沙箱。

---

## 13. 审批模式

MiniCoder 支持：

```text
--approval-mode auto
--approval-mode ask
--approval-mode strict
```

行为：

| 风险 | auto | ask | strict |
|---|---|---|---|
| 低风险命令 | 自动 | 自动 | 确认 |
| 中风险文件修改 | 自动 | 确认 | 确认 |
| 高风险操作 | 确认 | 确认 | 确认 |

### 用户拒绝

用户拒绝某项操作后，MiniCoder 会记录该操作。

同一任务中，如果模型没有收到用户明确的重试要求，不会反复请求同一个被拒绝操作。

对于被拒绝的文件修改，也会阻止部分明显试图通过 shell 绕过同一路径写入的行为。

---

## 14. 修改版本与测试验证

MiniCoder 不只依赖模型说“测试通过”，而是维护：

```text
当前修改版本
最近成功测试对应版本
```

结构化文件工具每发生一次成功 mutation，修改版本都会增加。

测试命令成功后，MiniCoder 记录：

```text
last_verified_mutation_version = current_mutation_version
```

如果出现：

```text
current_mutation_version > last_verified_mutation_version
```

表示：

> 最后一次测试成功以后，文件又发生了修改。

此时 Agent 不能直接以“验证成功”结束，而会要求重新运行相关测试。

例如：

```text
修改 text_utils.py
→ 测试 3/3 OK
→ 再修改 text_utils.py 的 docstring
→ 当前版本发生变化
→ 再次运行测试
→ 3/3 OK
→ 最近成功测试版本 == 当前修改版本
```

这样可以避免“测试通过后又改代码，却继续沿用旧测试结论”。

---

## 15. 成功命令缓存

如果相同命令已经在**当前修改版本**成功执行，且代码没有再次变化，框架可以复用该成功状态，避免模型无意义地反复运行相同命令。

一旦文件再次修改，版本变化，旧缓存不再代表当前状态。

---

## 16. Git 审查与框架执行事实

任务结束时，MiniCoder 可以补充 Git 状态与 Diff，帮助确认真实工作区状态。

同时，最终回复会附加框架自己维护的事实，例如：

```text
框架执行事实：
- 本任务会话内修改的文件：calculator.py, report.py, task_store.py, text_utils.py
- 最近成功测试对应代码版本：4
- 当前代码修改版本：4
- 当前计划：...
```

这些数据来自控制层状态，而不是模型自己回忆生成。

如果用户明确要求：

```text
不要执行任何工具
```

则工具调用以及框架自动 Git 审查都会被跳过。

---

## 17. 运行环境自动感知

MiniCoder 会把当前真实环境提供给模型，例如：

```text
Runtime environment (authoritative):
- Operating system: Windows 11
- Shell used by run_command: Windows PowerShell
- Workspace absolute path: ...
- Python: ...
- Test guidance: unittest-style tests detected
```

这样可以降低模型在 Windows 环境中错误使用：

```text
ls
pwd
tail
.venv/bin/python
```

等 Linux 风格操作的概率。

---

## 18. 测试框架线索

当前提供基础识别：

- Python unittest
- pytest
- Rust / Cargo
- Go
- Node

例如发现 `tests/test_*.py` 时，会优先建议：

```powershell
python -m unittest discover -s tests -v
```

这只是启发式运行环境提示，不是完整的构建系统解析器。

---

## 19. 离线自动化测试

运行：

```powershell
python -m unittest discover -s tests -v
```

当前最终测试结果：

```text
Ran 40 tests
OK
```

### 为什么这里不需要 API Key？

离线测试的目标是验证 **Agent 控制逻辑和本地工具**，不是测试真实大模型能力。

Agent 测试中使用 `FakeClient` 返回预先构造的模型消息和 `tool_calls`，因此不会向真实 `/chat/completions` 接口发送请求。

同时使用临时 workspace 验证文件操作、约束、版本状态等逻辑。

因此：

```text
运行 MiniCoder 真实任务 → 需要 API Key 和模型服务
运行 tests/ 离线测试 → 不需要 API Key，也不需要访问模型网络
```

当前测试覆盖包括但不限于：

- Tool Call 执行与结果回填
- 最大 Agent 轮数
- 会话历史与 `/reset`
- 上下文压缩
- 任务 Plan
- plan-first
- mixed tool-call batch 下的 plan-first
- 修改工具审批
- 用户拒绝后不重复请求
- 修改后强制重新验证
- no-tools
- tests 写保护
- only-file allowlist
- 路径归一化
- 新任务清理任务状态
- 修改文件去重与版本递增
- 中文任务提示
- Git untracked
- workspace 路径保护
- 模糊 replace 拒绝
- 命令风险分类
- timeout
- 输出截断
- PowerShell UTF-8
- CLI 参数
- 环境识别

---

## 20. 安全边界

MiniCoder 当前采用应用层多层控制：

```text
结构化文件工具 workspace 隔离
        +
任务级文件约束
        +
命令风险分类
        +
auto / ask / strict 审批
        +
高风险操作确认
        +
用户拒绝记录
        +
命令 timeout
        +
输出截断
```

最重要的边界是：

> **结构化文件工具受到 workspace 限制，但 `run_command` 不是操作系统级 sandbox。**

`run_command` 的工作目录虽然从 workspace 开始，但 PowerShell 本身仍可以访问系统允许访问的其他路径。

因此 MiniCoder 应在可信本地环境和可信代码库中运行。

---

## 21. 已知限制

1. `run_command` 不是 OS 级 sandbox。
2. PowerShell 风险分类基于规则，无法识别所有复杂等价命令。
3. “只改某文件”“不要修改 tests”等语义约束主要作用于结构化文件工具，无法完整分析任意 shell 命令的间接文件副作用。
4. 测试框架识别属于启发式检测。
5. timeout 能返回清晰超时结果，但复杂 Windows 子进程树还没有 OS Job Object 级管理。
6. 当前没有跨进程持久会话。
7. 不同 OpenAI-compatible 服务对 Tool Calling 的兼容程度可能不同。
8. LLM 的任务规划和代码理解质量仍取决于实际连接的模型能力。

---

## 22. 项目结构

```text
MiniCoder/
├── agent.py
├── config.py
├── llm.py
├── main.py
├── prompts.py
├── runtime.py
├── tools/
│   ├── __init__.py
│   ├── file_tools.py
│   ├── git_tools.py
│   ├── registry.py
│   └── shell_tool.py
├── tests/
│   ├── test_agent.py
│   ├── test_config.py
│   ├── test_git_tools.py
│   ├── test_main.py
│   ├── test_runtime.py
│   └── test_tools.py
├── .env.example
├── README.md
└── README.txt
```

主要职责：

| 文件 | 作用 |
|---|---|
| `agent.py` | Agent Loop、上下文、Plan、任务约束、审批与验证状态 |
| `llm.py` | OpenAI-compatible `/chat/completions` HTTP 客户端 |
| `runtime.py` | OS、Shell、workspace、Python、测试线索 |
| `prompts.py` | System Prompt |
| `tools/file_tools.py` | 文件操作与 workspace 路径保护 |
| `tools/shell_tool.py` | PowerShell、风险分类、timeout、输出截断 |
| `tools/git_tools.py` | Git status / diff / untracked |
| `tools/registry.py` | Tool schema、风险信息与本地 dispatcher |
| `main.py` | CLI、交互模式、参数解析、approval |
| `tests/` | 离线 Agent 与工具自动化测试 |

---

## 23. 一个完整任务示例

启动：

```powershell
python main.py --workspace .\minicoder_video_demo --approval-mode auto
```

输入：

```text
先制定计划。先运行当前项目的完整测试，在拿到真实失败结果之前不要读取具体实现文件；然后只根据失败信息读取直接相关的实现和测试，自主定位并修复所有实现问题。不要修改 tests 下任何文件，只做必要的最小修改。修复完成后重新运行完整测试确认全部通过，最后检查 Git 状态和 diff 并总结修改内容。
```

典型执行过程：

```text
update_plan
→ 运行完整 unittest
→ 得到真实失败
→ 读取相关测试与实现
→ 定位问题
→ replace_in_file 修改
→ 再次运行完整测试
→ 全部通过
→ git_status
→ git_diff
→ 输出总结与框架执行事实
```

这体现了 MiniCoder 的核心工作方式：

```text
获取真实状态
→ 决策
→ 本地执行
→ 观察工具结果
→ 再决策
→ 验证
```
