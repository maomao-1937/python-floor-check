# Research notes

The PyPA specification treats comma-separated version clauses as a conjunction. For release comparisons it zero-pads release segments as needed. It defines prefix matching with `.*` for equality and inequality. This tool takes those rules for two- and three-component stable releases and bounds the accepted syntax. [PyPA version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/)

The uv documentation describes how project commands use `requires-python` and how an explicit request can influence interpreter choice. uv 0.13.0 changed the default stable download from 3.14 to 3.15, so an unpinned download and a project's declared range can evolve separately. [uv Python versions](https://docs.astral.sh/uv/concepts/python-versions/#project-python-versions), [uv 0.13.0 changelog](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md#0130)

In an April 2026 uv issue, a user reported a missing-`requires-python` warning despite using `.python-version`. The discussion distinguishes the development interpreter pin from the supported range. The report documents one user's experience. [uv issue #19043](https://github.com/astral-sh/uv/issues/19043)

An explicit matrix check can surface candidate versions outside a project's declared range before jobs start. That is the tool's design assumption. The report represents a comparison against the declaration, so running the actual jobs is still how to establish runtime behavior.

## 中文

PyPA 规定逗号连接的版本条件必须同时满足，比较发布版本时会在末尾补零，并为等于和不等于定义了 `.*` 前缀匹配。本工具从中取两段或三段稳定版本的比较规则，并限定输入规模。 [PyPA 版本规范](https://packaging.python.org/en/latest/specifications/version-specifiers/)

uv 文档说明了项目范围与显式解释器请求的作用。uv 0.13.0 将默认下载的稳定版从 3.14 调整到 3.15。2026 年 4 月还有用户报告，在使用 `.python-version` 时依然收到缺少 `requires-python` 的提示。讨论区分了开发环境版本与项目支持范围。 [uv 文档](https://docs.astral.sh/uv/concepts/python-versions/#project-python-versions)、[uv 更新记录](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md#0130)、[uv 用户报告](https://github.com/astral-sh/uv/issues/19043)

据此，本工具检查显式 CI 候选版本是否符合项目声明。运行兼容性仍由实际测试验证。
