# agent_acceptance_project

一道用于验收编码代理（coding agent）的基础测试项目。它由四个标准库实现模块
和对应的 `unittest` 测试组成，分别覆盖分数统计、文本规范化、任务存储与任务
报告这几类常见逻辑。

## 项目用途

本项目内**故意保留**了若干逻辑 Bug，用于验收代理能否正确诊断故障、针对性地
修改实现、并通过测试确认修复。任务要求是：让全部测试通过，但**不要改动任何
测试文件中的断言**，只能修改实现模块（`score_tracker.py`、`text_utils.py`、
`task_store.py`、`report.py`）。

### 各模块与预期修复点

| 模块                 | 保留的 Bug                                                               |
|----------------------|--------------------------------------------------------------------------|
| `score_tracker.py`   | 添加分数时没有校验 0~100 范围；平均分错误地使用整数除法                  |
| `text_utils.py`      | 只去除首尾空格，没有正确合并连续空格                                      |
| `task_store.py`      | 完成任务时没有规范化标题；找不到任务时返回错误值（应为失败）              |
| `report.py`          | 统计未完成任务数量时存在 off-by-one 错误                                  |

全部实现只依赖 Python 标准库，测试框架使用 `unittest`。

## 目录结构

```
agent_acceptance_project/
├── score_tracker.py
├── text_utils.py
├── task_store.py
├── report.py
├── tests/
│   ├── test_score_tracker.py
│   ├── test_text_utils.py
│   ├── test_task_store.py
│   └── test_report.py
└── README.md
```

## 运行测试

在 `agent_acceptance_project` 目录下执行：

```bash
python -m unittest discover -s tests -v
```

该命令会发现 `tests/` 下的所有 `test_*.py` 文件并逐个执行。因为实现中保留了
上述 Bug，当前会有一部分测试失败；修复实现模块后，所有测试应通过。
