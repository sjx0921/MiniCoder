# MiniCoder Video Demo

这是一个只使用 Python 标准库和 `unittest` 的 MiniCoder Coding Agent 视频演示项目。

正确需求：

- `average` 在空列表时返回 `0.0`，在非空列表时返回真实算术平均值。
- `normalize_text` 保留 `None`，去除首尾空白，并将内部连续空白归一为一个普通空格。
- `TaskStore` 维护 `todo` 与 `done`；完成任务时忽略输入标题首尾空白，并将任务从 `todo` 移到 `done`。
- `incomplete_count` 返回实际未完成任务数量，空任务列表返回 `0`。

运行测试：

```powershell
python -m unittest discover -s tests -v
```
