MiniCoder
Git 仓库：https://github.com/sjx0921/MiniCoder.git

MiniCoder 是一个本地编程智能体（Coding Agent）。它通过 OpenAI 兼容的 Chat Completions / Tool Calling 接口与大语言模型交互，可在指定工作区内自主读取和搜索代码、修改文件、执行 PowerShell 命令、运行测试，并根据真实工具结果持续推进任务。

运行方式：需要 Python 3.10+，项目本体仅依赖标准库。复制 .env.example 为 .env，填写 MINICODER_API_KEY；如使用兼容网关，可设置 MINICODER_BASE_URL 和 MINICODER_MODEL。
PowerShell 启动：
python main.py --workspace .
也支持单次任务：
python main.py "检查项目测试失败原因并修复" --workspace .

特色功能：支持 list_files、read_file、search_text、write_file、replace_in_file、run_command、git_status、git_diff 和 update_plan；支持多轮 Agent 循环、上下文压缩、任务状态隔离与 /reset。用户明确要求“先制定计划”时，计划建立前仅允许 update_plan 执行。支持 auto / ask / strict 三种审批模式，高风险操作始终确认；支持“不修改 tests”“只修改指定文件”等任务级约束。框架记录修改版本与最近成功测试版本，代码在测试通过后再次修改时会要求重新验证，并在任务结束时给出 Git 状态与 Diff 事实。

安全边界：结构化文件工具限制在 workspace 内；run_command 从 workspace 启动，但不是 OS 级沙箱。

离线自动化测试：40 项全部通过，不需要 API Key。
