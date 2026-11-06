# python-floor-check

[![tests](https://github.com/maomao-1937/python-floor-check/actions/workflows/tests.yml/badge.svg)](https://github.com/maomao-1937/python-floor-check/actions/workflows/tests.yml)

Check which Python versions in a proposed CI matrix satisfy `project.requires-python` before running the jobs. The command uses Python 3.11 or newer and its standard library.

```sh
python python_floor_check.py fixtures/pyproject.toml 3.11 3.12.4
python python_floor_check.py fixtures/pyproject.toml 3.11 3.12.0 3.13
```

The fixture declares `>=3.11, <3.13, !=3.12.0`. The first command exits `0`. The second exits `1` and reports the exclusions by position.

```json
{"candidates":[{"ordinal":1,"match":true,"failed_clauses":[]},{"ordinal":2,"match":false,"failed_clauses":[3]},{"ordinal":3,"match":false,"failed_clauses":[2]}]}
```

Candidate and clause ordinals start at 1 and follow input order. A valid report contains only ordinals and match booleans. Invalid input or file I/O exits `2` with `{"error":"invalid_input"}`. A failed stdout write, including on `--help`, exits `2` quietly.

## Supported syntax

- Use 1–64 explicit candidate versions and 1–64 comma-separated clauses. Each candidate must satisfy every clause.
- Use stable `X.Y` or `X.Y.Z` releases with up to nine ASCII digits per component. Only `0` can start with zero. Ordinary comparisons pad a missing patch with zero.
- Use `<`, `<=`, `>`, `>=`, `==` or `!=`. For prefix matching, use `==X.Y.*` or `!=X.Y.*`. ASCII spaces may surround tokens.
- The profile covers these comparisons only. It excludes prereleases, epochs, `~=`, and other PEP 440 syntax. The command performs no interpreter selection or installation.

The TOML input must be a regular file of at most 256 KiB. Use a local relative or absolute path. The command rejects URI spellings, UNC paths, native Windows namespaces, reserved device stems, drive-relative paths, and alternate streams before accessing the file. Symlinks, junctions, and mounted or mapped drives can redirect an ordinary path. Choose paths on storage you trust.

## 中文

提交前检查 CI 计划测试的 Python 版本是否满足本地 `pyproject.toml` 声明的 `project.requires-python`。运行需要 Python 3.11 或更高版本，依赖仅为标准库。

```sh
python python_floor_check.py fixtures/pyproject.toml 3.11 3.12.0 3.13
```

示例范围是 `>=3.11, <3.13, !=3.12.0`。报告按输入顺序给出版本序号、是否匹配和未通过的子句序号，两类序号均从 1 开始。示例中第二个版本不满足第 3 条，第三个版本不满足第 2 条。

退出码 `0` 表示全部满足，`1` 表示至少一个版本超出范围，`2` 表示输入或 I/O 失败。无效输入和文件读取错误仅输出固定错误码。stdout 写入失败时安静退出 `2`，帮助输出也遵守这一规则。

版本与子句各支持 1–64 项。版本使用两段或三段 ASCII 数字，每段最多九位，除了 `0` 本身外禁止前导零。普通比较把缺失的补丁位视为零。支持 `<`、`<=`、`>`、`>=`、`==`、`!=` 及 `==X.Y.*`、`!=X.Y.*`，子句以逗号分隔，各项可有 ASCII 空格。此范围排除预发布、纪元、`~=` 等其他 PEP 440 写法。工具只检查显式提供的版本。

文件须为不超过 256 KiB 的普通文件。工具在访问前拒绝 URI、UNC、Windows 原生命名空间、设备名、驱动器相对路径及备用数据流。符号链接、目录联接、挂载点或映射盘仍可能改变路径指向，请使用可信存储中的文件。

See [TESTING.md](TESTING.md) for local verification and [RESEARCH.md](RESEARCH.md) for sources.
