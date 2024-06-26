# yore

[![ci](https://github.com/pawamoy/yore/workflows/ci/badge.svg)](https://github.com/pawamoy/yore/actions?query=workflow%3Aci)
[![documentation](https://img.shields.io/badge/docs-mkdocs-708FCC.svg?style=flat)](https://pawamoy.github.io/yore/)
[![pypi version](https://img.shields.io/pypi/v/yore.svg)](https://pypi.org/project/yore/)
[![gitpod](https://img.shields.io/badge/gitpod-workspace-708FCC.svg?style=flat)](https://gitpod.io/#https://github.com/pawamoy/yore)
[![gitter](https://badges.gitter.im/join%20chat.svg)](https://app.gitter.im/#/room/#yore:gitter.im)

Manage legacy code with comments.

---

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
$ yore check --warn-before-eol '5 months'
./src/griffe/agents/nodes/_values.py:11: Python 3.8 will reach its End of Life within approx. 4 months
```

Fix your code base:

```console
$ yore fix --fix-before-eol '5 months'
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

With `pip`:

```bash
pip install yore
```

With [`pipx`](https://github.com/pipxproject/pipx):

```bash
python3.8 -m pip install --user pipx
pipx install yore
```
