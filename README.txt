MiniCoder
Git 仓库：https://github.com/sjx0921/MiniCoder.git

MiniCoder 是从零实现的本地编程智能体。它通过 OpenAI 兼容的 Chat Completions/Tool Calling 接口与大语言模型交互，可在指定工作区内读代码、改文件、运行命令并完成编程任务。未使用 LangChain、LlamaIndex、AutoGen、CrewAI、OpenAI Agents SDK 等 agent 框架，也不使用云端代码执行或文件工具；对话历史、工具调度、输出解析、循环控制和错误处理均由本仓库实现。

运行：需 Python 3.10+，仅依赖标准库。复制 .env.example 为 .env，填写 MINICODER_API_KEY；可选设置 MINICODER_BASE_URL（如 https://api.deepseek.com）和 MINICODER_MODEL（如 deepseek-chat）。PowerShell 中运行：
python main.py --workspace .
在 Task> 后输入自然语言任务；单次任务：
python main.py "检查项目并修复测试" --workspace .

特色：持久会话与 /reset；自动识别操作系统、PowerShell、绝对工作区和 unittest 测试线索；目录列举、文本搜索、读写/精确替换文件、命令执行、Git 状态与差异审查；文件工具限制在工作区；支持 auto/ask/strict 确认模式，高风险操作始终确认；支持任务计划、最大轮数、命令超时、UTF-8 输出、结构化上下文摘要和结束时 Git 改动报告。离线测试不需要 API Key。
