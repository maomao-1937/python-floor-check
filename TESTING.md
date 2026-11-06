# Testing

The native namespace regression checks the raw and normalized root before filesystem access. It covers a namespace spelling followed by a parent segment.

Run the standard-library test suite from the repository root with Python 3.11 or newer.

```sh
python -m unittest discover -s tests -v
python python_floor_check.py --help
```

The suite runs the CLI in child processes. It exercises all six comparison operators, patch zero-padding, wildcard prefixes, whole-input validation, and the limits on file bytes, candidates, clauses, and digits. It checks fixed reports for malformed TOML and I/O errors. A guarded child process verifies rejected paths do not reach file access. Separate child processes write into an actual pipe with its reader already closed to test help and each report outcome.

Run the example commands from `checks.json` and compare their exit codes.

| Command arguments after the script | Exit |
| --- | --- |
| `fixtures/pyproject.toml 3.11 3.12.4` | 0 |
| `fixtures/pyproject.toml 3.11 3.12.0 3.13` | 1 |
| `fixtures/unsupported.toml 3.11` | 2 |

## 中文

在仓库根目录运行 `python -m unittest discover -s tests -v`。测试启动真实 CLI 进程，覆盖比较运算、补零、通配前缀、整份输入校验、文件与输入数量上限及报告内容。路径测试拦截文件访问以确认危险拼写会提前拒绝，管道测试提前关闭真实读取端，检查帮助和结果输出都能安静退出。

表中三组命令也是 `checks.json` 的快速验证用例，分别覆盖全部匹配、部分不匹配和输入无效。
