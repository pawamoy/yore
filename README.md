# yore

[![ci](https://github.com/pawamoy/yore/workflows/ci/badge.svg)](https://github.com/pawamoy/yore/actions?query=workflow%3Aci)
[![documentation](https://img.shields.io/badge/docs-zensical-FF9100.svg?style=flat)](https://pawamoy.github.io/yore/)
[![pypi version](https://img.shields.io/pypi/v/yore.svg)](https://pypi.org/project/yore/)
[![gitter](https://img.shields.io/badge/matrix-chat-4DB798.svg?style=flat)](https://app.gitter.im/#/room/#yore:gitter.im)

**Manage legacy code with comments.**

> In days of yore, ancients penned scripts of eld, their legacy code a relic of arcane lore. These venerable lines, cryptic and profound, whisper the wisdom of bygone masters, shaping our digital realm's very ground.
>
> — ChatGPT the Sage

With time, the code base of your project evolves. You add features, you fix bugs, and you generally reorganize code. Some of these changes might make your project's public API incompatible with previous versions. In that case, you usually have to "deprecate" previous usage in favor of the new usage. That means you have to support both usages, and emit deprecation warnings when old usage is detected.

Sometimes, you don't change anything in an incompatible way, but you want to support multiple versions of Python which provide different, incompatible APIs, or for which libraries you depend on provide different, incompatible APIs. In that case, you have to write multiple code branches to support the different Python versions. The code branches for versions of Python older than the latest one are what we call legacy code. Ideally you'd want to only use the API and features of the latest Python version, but your users are sometimes stuck with older versions, and you want to follow the official Python release cycle, which promises support for a certain amount of time after initial release for each minor version (3.11, 3.12, etc.). At the time of writing (2024, see [Python release cycle](https://devguide.python.org/versions/) for up-to-date information), each minor version is supported for approximately 5 years. There's a new minor version each year, so if you follow the release cycle, you maintain support for a window of 5 minor Python versions at any time. Sometimes you will have to support much older versions...

For these use-cases, Yore comes to the rescue.

Yore was born from the will of automating comments I had added along the evolution of my projects. I was usually writing comments such as `TODO: Remove once support for Python 3.8 is dropped`, or `TODO: Remove when we are ready for v1`. One day I decided to make these comments more formal, so I designed a very simple syntax and wrote a tool that would parse them and act on them.

Yore can therefore find comments in your code base, to warn you about upcoming end-of-life dates of Python versions, or outdated code based on the project version. It can also apply transformations to your code, to remove legacy blocks or lines of code or update them.

**Yore is language agnostic.** It works with many of the most popular languages. For now it only supports beginning/end of life dates for Python, but in the future it will likely support more.

## Quick usage

Write Yore comments:

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

## Sponsors

<!-- sponsors-start -->

<div id="premium-sponsors" style="text-align: center;">

<div id="silver-sponsors"><b>Silver sponsors</b><p>
<a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://raw.githubusercontent.com/tiangolo/fastapi/master/docs/en/docs/img/logo-margin/logo-teal.png" style="height: 200px; "></a><br>
</p></div>

<div id="bronze-sponsors"><b>Bronze sponsors</b><p>
<a href="https://www.nixtla.io/"><picture><source media="(prefers-color-scheme: light)" srcset="https://www.nixtla.io/img/logo/full-black.svg"><source media="(prefers-color-scheme: dark)" srcset="https://www.nixtla.io/img/logo/full-white.svg"><img alt="Nixtla" src="https://www.nixtla.io/img/logo/full-black.svg" style="height: 60px; "></picture></a><br>
</p></div>
</div>

---

<div id="sponsors"><p>
<a href="https://github.com/ofek"><img alt="ofek" src="https://avatars.githubusercontent.com/u/9677399?u=386c330f212ce467ce7119d9615c75d0e9b9f1ce&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/samuelcolvin"><img alt="samuelcolvin" src="https://avatars.githubusercontent.com/u/4039449?u=42eb3b833047c8c4b4f647a031eaef148c16d93f&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/tlambert03"><img alt="tlambert03" src="https://avatars.githubusercontent.com/u/1609449?u=922abf0524b47739b37095e553c99488814b05db&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/ssbarnea"><img alt="ssbarnea" src="https://avatars.githubusercontent.com/u/102495?u=c7bd9ddf127785286fc939dd18cb02db0a453bce&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/femtomc"><img alt="femtomc" src="https://avatars.githubusercontent.com/u/34410036?u=f13a71daf2a9f0d2da189beaa94250daa629e2d8&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/cmarqu"><img alt="cmarqu" src="https://avatars.githubusercontent.com/u/360986?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/kolenaIO"><img alt="kolenaIO" src="https://avatars.githubusercontent.com/u/77010818?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/ramnes"><img alt="ramnes" src="https://avatars.githubusercontent.com/u/835072?u=3fca03c3ba0051e2eb652b1def2188a94d1e1dc2&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/machow"><img alt="machow" src="https://avatars.githubusercontent.com/u/2574498?u=c41e3d2f758a05102d8075e38d67b9c17d4189d7&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/BenHammersley"><img alt="BenHammersley" src="https://avatars.githubusercontent.com/u/99436?u=4499a7b507541045222ee28ae122dbe3c8d08ab5&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/trevorWieland"><img alt="trevorWieland" src="https://avatars.githubusercontent.com/u/28811461?u=74cc0e3756c1d4e3d66b5c396e1d131ea8a10472&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/MarcoGorelli"><img alt="MarcoGorelli" src="https://avatars.githubusercontent.com/u/33491632?u=7de3a749cac76a60baca9777baf71d043a4f884d&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/analog-cbarber"><img alt="analog-cbarber" src="https://avatars.githubusercontent.com/u/7408243?u=fe0e7bf2882d1c9c901a341c2502e1518466527a&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/OdinManiac"><img alt="OdinManiac" src="https://avatars.githubusercontent.com/u/22727172?u=36ab20970f7f52ae8e7eb67b7fcf491fee01ac22&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/rstudio-sponsorship"><img alt="rstudio-sponsorship" src="https://avatars.githubusercontent.com/u/58949051?u=0c471515dd18111be30dfb7669ed5e778970959b&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/schlich"><img alt="schlich" src="https://avatars.githubusercontent.com/u/21191435?u=6f1240adb68f21614d809ae52d66509f46b1e877&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/butterlyn"><img alt="butterlyn" src="https://avatars.githubusercontent.com/u/53323535?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/livingbio"><img alt="livingbio" src="https://avatars.githubusercontent.com/u/10329983?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/NemetschekAllplan"><img alt="NemetschekAllplan" src="https://avatars.githubusercontent.com/u/912034?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/EricJayHartman"><img alt="EricJayHartman" src="https://avatars.githubusercontent.com/u/9259499?u=7e58cc7ec0cd3e85b27aec33656aa0f6612706dd&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/15r10nk"><img alt="15r10nk" src="https://avatars.githubusercontent.com/u/44680962?u=f04826446ff165742efa81e314bd03bf1724d50e&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/activeloopai"><img alt="activeloopai" src="https://avatars.githubusercontent.com/u/34816118?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/roboflow"><img alt="roboflow" src="https://avatars.githubusercontent.com/u/53104118?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/cmclaughlin"><img alt="cmclaughlin" src="https://avatars.githubusercontent.com/u/1061109?u=ddf6eec0edd2d11c980f8c3aa96e3d044d4e0468&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/RapidataAI"><img alt="RapidataAI" src="https://avatars.githubusercontent.com/u/104209891?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/rodolphebarbanneau"><img alt="rodolphebarbanneau" src="https://avatars.githubusercontent.com/u/46493454?u=6c405452a40c231cdf0b68e97544e07ee956a733&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/theSymbolSyndicate"><img alt="theSymbolSyndicate" src="https://avatars.githubusercontent.com/u/111542255?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/blakeNaccarato"><img alt="blakeNaccarato" src="https://avatars.githubusercontent.com/u/20692450?u=bb919218be30cfa994514f4cf39bb2f7cf952df4&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/ChargeStorm"><img alt="ChargeStorm" src="https://avatars.githubusercontent.com/u/26000165?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/Cusp-AI"><img alt="Cusp-AI" src="https://avatars.githubusercontent.com/u/178170649?v=4" style="height: 32px; border-radius: 100%;"></a>
</p></div>


*And 4 more private sponsor(s).*

<!-- sponsors-end -->
