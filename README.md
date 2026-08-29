# MiniCoder

MiniCoder 是一个从零实现的本地编程智能体。它使用 OpenAI 兼容的模型 API 与模型原生 tool calling，在本机读取和修改项目文件、执行命令并完成编程任务。

它不封装 Claude Code、Codex 或其他现成 agent 产品，也不依赖 LangChain、LlamaIndex、OpenAI Agents SDK、AutoGen、CrewAI 等 agent 框架。对话循环、上下文、工具 schema、工具调度、本地执行、错误处理和终止条件均由本仓库代码实现。

## 功能

- OpenAI 兼容 `/chat/completions` 接口，可配置模型和网关地址
- 本地 `list_files`、`read_file`、`write_file`、`replace_in_file`、`run_command` 工具
- 工作区路径隔离：文件工具拒绝工作区以外的路径
- 自动感知操作系统、PowerShell/Shell、绝对工作区与测试框架，避免错误使用跨平台命令
- Windows 下显式使用 PowerShell 并统一 UTF-8 命令输出
- 命令超时、输出截断、工具错误回传模型
- 最大轮数限制，避免无限工具调用
- 上下文字符上限与本地压缩，避免会话无限膨胀
- 写文件、替换文本、执行命令前的人机确认；可用 `--auto-approve` 跳过低/中风险确认，高风险命令仍需确认
- 任务计划工具与结构化会话摘要，保留任务、进度及近期工具结果
- 用户明确要求“先制定计划”时，控制循环强制首个工具调用为 `update_plan`，否则拒绝执行其余工具
- 文本搜索、Git 状态和 diff 统计，以及任务结束时的本地改动审查
- 单次任务及持久上下文的交互式 CLI（支持 `/reset` 清空会话）

## 安装

需要 Python 3.10 或更高版本。项目只使用 Python 标准库。

```powershell
git clone https://github.com/sjx0921/MiniCoder.git
cd MiniCoder
Copy-Item .env.example .env
```

然后在本机环境变量或未提交的 `.env` 中配置：

```powershell
$env:MINICODER_API_KEY = "你的密钥"
$env:MINICODER_BASE_URL = "https://api.openai.com/v1" # 可选，支持兼容网关
$env:MINICODER_MODEL = "gpt-4o-mini"                 # 可选
```

MiniCoder 只从环境变量读取凭据；请勿将真实密钥写入仓库、README、截图或视频。

## 使用

在目标项目目录运行，或明确授予一个工作区：

```powershell
python main.py "检查测试失败原因并修复它" --workspace C:\path\to\project
python main.py --workspace .
```

可用参数：`--model`、`--base-url`、`--max-turns`、`--max-history-chars`、`--approval-mode` 和 `--auto-approve`。`--approval-mode ask`（默认）自动执行低风险命令，对写文件、安装依赖等中风险操作确认；`auto` 自动执行低、中风险操作；`strict` 对所有修改/命令确认。高风险操作始终确认。`--auto-approve` 是 `--approval-mode auto` 的兼容别名。例如：

```powershell
python main.py "为模块补充单元测试" --model gpt-4o-mini --max-turns 15
```

交互模式中，同一终端会话会保留先前的任务、模型回复和工具结果，因此可以继续追问“按刚才的方案修改”。输入 `/reset` 可清空会话并开始新任务；退出程序后历史不会落盘。

## 安全模型与限制

文件工具被限制在 `--workspace` 内。`run_command` 按模型请求在该工作区启动 shell 命令，因此仅应在可信项目中运行；默认会逐项请求确认。`--auto-approve` 会关闭这一确认，适合已审查的自动化任务。当前版本没有跨进程持久记忆，也不会使用任何云端代码执行或文件 API。

## 开发与测试

```powershell
python -m unittest discover -s tests -v
```

测试使用模拟模型客户端，不需要网络或 API Key。
