# yore

[![ci](https://github.com/pawamoy/yore/workflows/ci/badge.svg)](https://github.com/pawamoy/yore/actions?query=workflow%3Aci)
[![documentation](https://img.shields.io/badge/docs-mkdocs-708FCC.svg?style=flat)](https://pawamoy.github.io/yore/)
[![pypi version](https://img.shields.io/pypi/v/yore.svg)](https://pypi.org/project/yore/)
[![gitter](https://badges.gitter.im/join%20chat.svg)](https://app.gitter.im/#/room/#yore:gitter.im)

Manage legacy code with comments.

> In days of yore, ancients penned scripts of eld, their legacy code a relic of arcane lore. These venerable lines, cryptic and profound, whisper the wisdom of bygone masters, shaping our digital realm's very ground.
>
> — ChatGPT the Sage

With time, the code base of your project evolves. You add features, you fix bugs, and you generally reorganize code. Some of these changes might make your project's public API incompatible with previous versions. In that case, you usually have to "deprecate" previous usage in favor of the new usage. That means you have to support both usages, and emit deprecation warnings when old usage is detected.

Sometimes, you don't change anything in an incompatible way, but you want to support multiple versions of Python which provide different, incompatible APIs, or for which libraries you depend on provide different, incompatible APIs. In that case, you have to write multiple code branches to support the different Python versions. The code branches for versions of Python older than the latest one are what we call legacy code. Ideally you'd want to only use the API and features of the latest Python version, but your users are sometimes stuck with older versions, and you want to follow the official Python release cycle, which promises support for a certain amount of time after initial release for each minor version (3.11, 3.12, etc.). At the time of writing (2024, see [Python release cycle](https://devguide.python.org/versions/) for up-to-date information), each minor version is supported for approximately 5 years. There's a new minor version each year, so if you follow the release cycle, you maintain support for a window of 5 minor Python versions at any time. Sometimes you will have to support much older versions...

For these use-cases, Yore comes to the rescue. 

Yore was born from the will of automating comments I had added along the evolution of my projects. I was usually writing comments such as `TODO: Remove once support for Python 3.8 is dropped`, or `TODO: Remove when we are ready for v1`. One day I decided to make these comments more formal, so I designed a very simple syntax and wrote a tool that would parse them and act on them.

Yore can therefore find comments in your code base, to warn you about upcoming end-of-life dates of Python versions, or outdated code based on the project version. It can also apply transformations to your code, to remove legacy blocks or lines of code or update them.

## Quick usage

Write Yore-comments:

```python
# YORE: EOL 3.8: Replace block with line 4.
if sys.version_info < (3, 9):
    from astunparse import unparse
else:
    from ast import unparse
```

Check your code base:

```console
$ yore check --eol-within '5 months'
./src/griffe/agents/nodes/_values.py:11: Python 3.8 will reach its End of Life within approx. 4 months
```

Fix your code base:

```console
$ yore fix --eol-within '5 months'
fixed 1 comment in ./src/griffe/agents/nodes/_values.py
```

```diff
diff --git a/src/griffe/agents/nodes/_values.py b/src/griffe/agents/nodes/_values.py
index 59bfacac..2f6eaa88 100644
--- a/src/griffe/agents/nodes/_values.py
+++ b/src/griffe/agents/nodes/_values.py
@@ -8,11 +8,7 @@ from typing import TYPE_CHECKING
 
 from griffe.logger import get_logger
 
-# YORE: EOL 3.8: Replace block with line 4.
-if sys.version_info < (3, 9):
-    from astunparse import unparse
-else:
-    from ast import unparse
+from ast import unparse
 
 if TYPE_CHECKING:
     from pathlib import Path
```

See the [usage documentation](https://pawamoy.github.io/yore/usage).

## Installation

```bash
pip install yore
```

With [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install yore
```
