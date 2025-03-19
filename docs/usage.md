# Usage

Yore lets you write `# YORE` comments in your code base to mark some lines of blocks of code as being legacy code: only there to support "old" versions of Python, or for backward compatibility with previous versions of your own project.

## Syntax

The syntax is as follows:

```text
<COMMENT> <PREFIX>: <eol|bol|bump> <VERSION>: remove <file|block|line>.
<COMMENT> <PREFIX>: <eol|bol|bump> <VERSION>: replace <file|block|line> with line <LINENO>.
<COMMENT> <PREFIX>: <eol|bol|bump> <VERSION>: replace <file|block|line> with lines <LINE-RANGE1[, LINE-RANGE2...]>.
<COMMENT> <PREFIX>: <eol|bol|bump> <VERSION>: replace <file|block|line> with `<STRING>`.
<COMMENT> <PREFIX>: <eol|bol|bump> <VERSION>: [regex-]replace `<PATTERN1>` with `<PATTERN2>` within <file|block|line>.
```

Terms between `<` and `>` *must* be provided, while terms between `[` and `]` are optional. Uppercase terms are placeholders that you should replace with actual values, while lowercase terms are keywords that you should use literally. Everything except placeholders is case-insensitive.

`COMMENT` is comment syntax, depending on the source file. Yore supports the following syntax:

- `#`: Nim, Perl, PHP, Python, R, Ruby, shell, YAML
- `//`: C, C++, Go, Java, Javascript, Rust, Swift
- `--`: Haskell, Lua, SQL
- `;`: Lisp, Scheme
- `%`: MATLAB
- `'`: VBA
- `/*`: C, C++, Java, Javascript, CSS
- `<!--`: HTML, Markdown, XML
- `{#`:  Jinja
- `(*`: OCaml

Trailing comments are not supported: comments must be preceded with spaces only. Yore comments are always written on a single line.

The default `PREFIX` is `YORE`. See [Configuration](#configuration).

Terms `eol`, `bol` and `bump` mean "End of Life", "Beginning of Life" and "version bump", respectively.

Line number and line ranges are relative to the start of blocks for the "block" scope, but absolute for the "file" scope.

## Examples

All the following examples are real-life examples extracted from another project ([Griffe](https://mkdocstrings.github.io/griffe/)).

*Remove the module-level `__getattr__` function when we bump the project to version 1.0.0.*

```python
# YORE: Bump 1.0.0: Remove block.
def __getattr__(name: str) -> Any:
    if name == "load_git":
        warnings.warn(
            f"Importing {name} from griffe.git is deprecated. Import it from griffe.loader instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        from griffe.loader import load_git

        return load_git
    raise AttributeError
```

*Simplify `ast.unparse` import when Python 3.8 reaches its End of Life.*

```python
# YORE: EOL 3.8: Replace block with line 4.
if sys.version_info < (3, 9):
    from astunparse import unparse
else:
    from ast import unparse
```

*Replace `lstrip` by `removeprefix` when Python 3.8 reaches its End of Life.*

```python
# YORE: EOL 3.8: Replace `lstrip` with `removeprefix` within line.
return [cpn.lstrip("_") for cpn in a.split(".")] == [cpn.lstrip("_") for cpn in b.split(".")]
```

*Simplify union of accepted types when we bump the project to version 1.0.0.*

```python
def load_extensions(
    # YORE: Bump 1.0.0: Replace ` | Sequence[LoadableExtension],` with `` within line.
    *exts: LoadableExtension | Sequence[LoadableExtension],
): ...
```

*Remove parameter from a signature when we bump the project to version 1.0.0.*

```python
def load(
    ...
    # YORE: Bump 1.0.0: Remove line.
    module: str | Path | None = None,
    ...
):
    ...
```

*Replace line with something else when we bump the project to version 1.0.0.*

```python
# YORE: Bump 1.0.0: Replace line with `return self.public`.
return _True if self.public else _False
```

## Blocks

A block is a list of consecutive non-blank or over-indented lines.

```python
# YORE: This is a block.
print("hello")
print("world")

# YORE: This is another block.
print("goodbye")
```

Here we see that the blank line marked the end of the first block. But if the lines following a blank lines are over-indented, they will still count as being part of the block:

```python
def function():
    # YORE: This is a block.
    print("hello")
    if some_condition:
        do_this()

        # Blank line above, but next lines are over-indented
        # compared to the first line of the block `print("hello")`.
        do_that()
```

If the indentation goes back to the initial level, but there is no blank line right before it, the block continues:

```python
def function():
    # YORE: This is a block.
    print("hello")
    if some_condition:
        do_this()

        do_that()
    if something_else:  # This is still part of the block!
        and_do_this()
```

If you don't want the `something_else` condition and code to be part of the block, separate it with a blank line:

```python
def function():
    # YORE: This is a block.
    print("hello")
    if some_condition:
        do_this()

        do_that()

    if something_else:  # This is not part of the first block anymore.
        and_do_this()
```

A line that is less indented that the initial line will also terminate a block.

```python
if something:
    # YORE: Start of a block. Initial indent = 4.
    print("hello")
if something_else:  # Indent = 0, not part of the block above.
    print("goodbye")
```

## Configuration

Configuration is read by default from one of the following files, in order:

- `config/yore.toml`
- `yore.toml`
- `pyproject.toml`

The path to the configuration can be specified with the CLI's `-c`, `--config` option:

```bash
yore -c path/to/config.toml
```

In `pyproject.toml`, the configuration must be added under `[tool.yore]`:

```toml
[tool.yore]
prefix = "YORE"
```

In other files, configuration is added at the top-level:

```toml
prefix = "YORE"
```

### `prefix`

Defines the prefix to match. Default is `YORE`.

```toml
prefix = "DUE"
```

### `diff.highlight`

Defines the shell command to run to highlight diffs (see [`yore diff` command](#yore-diff)). Default is none (no highlighting).

```toml
diff.highlight = "delta"
```

Example commands:

- `colordiff`, see https://www.colordiff.org/
- `delta`, see https://github.com/dandavison/delta
- `diff-so-fancy | less -RF`, see https://github.com/so-fancy/diff-so-fancy
- `python -m rich.syntax -x diff -`, see https://rich.readthedocs.io/en/latest/syntax.html#syntax-cli
- `vim -R -`

## Commands

### `yore check`

Once you have written a few Yore comments in your code base, you can check them with the `yore check` command. If a comment is outdated, for example the current version of the project is equal to or higher than a "bump" comment, Yore will warn you. Similarly, if a Python version has reached its end of life, and Yore finds an "eol" comment for this version, it will warn you. If you want to be warned before the EOL (End of Life) date of a Python version, use the `-E`, `---eol`,`--eol-within` option. If you want to be warned before the BOL (Beginning of Life) date of a Python version, use the `-B`, `--bol`, `--bol-within` option. To specify the upcoming project version, use the `-b`, `--bump` option.

```console
% yore check --eol '8 months' --bump 2.0
src/_griffe/agents/inspector.py:704: in ~7 months EOL 3.9: Replace block with lines 2-3
src/_griffe/agents/nodes/exports.py:19: version 2.0 >= Bump 2: Remove block
src/_griffe/encoders.py:186: version 2.0 >= Bump 2: Replace line with `members = obj_dict.get("members", {}).values()`
src/_griffe/encoders.py:188: version 2.0 >= Bump 2: Remove block
src/_griffe/encoders.py:209: version 2.0 >= Bump 2: Replace line with `members = obj_dict.get("members", {}).values()`
src/_griffe/encoders.py:211: version 2.0 >= Bump 2: Remove block
src/_griffe/expressions.py:78: in ~7 months EOL 3.9: Remove block
src/_griffe/expressions.py:178: in ~7 months EOL 3.9: Replace `**_dataclass_opts` with `slots=True` within line
src/_griffe/expressions.py:222: in ~7 months EOL 3.9: Replace `**_dataclass_opts` with `slots=True` within line
src/_griffe/expressions.py:854: in ~7 months EOL 3.9: Replace `**_dataclass_opts` with `slots=True` within line
src/griffe/__init__.py:180: version 2 >= Bump 2.0: Replace `ExportedName, ` with `` within line
src/griffe/__init__.py:432: version 2 >= Bump 2.0: Remove line
```

By default Yore will run `git ls-files` in the specified path (or current working directory) to know which files to scan. If the command fails, it will scan files recursively, excluding cache folders, virtualenvs, etc.. You can specify multiple paths on the command line:

```bash
yore check src scripts/this_module.py docs/*.py
# same thing for `yore diff` and `yore fix`
```

### `yore diff`

Like `yore fix`, but in dry-run mode (don't actually write on disk), and print the diff to the console. The diff can be syntax-highlighted with a shell command of your choice, thanks to the `-H`, `--highlight` CLI flag or the [`diff.highlight` configuration option](#diffhighlight).

```diff
% yore diff
--- pyproject.toml
+++ pyproject.toml
@@ -104,8 +104,6 @@
     "mkdocs-minify-plugin>=0.8",
     "mkdocs-section-index>=0.3",
     "mkdocstrings[python]>=0.29",
-    # DUE: EOL 3.10: Remove line.
-    "tomli>=2.0; python_version < '3.11'",
 ]

 [tool.uv]
--- scripts/gen_credits.py
+++ scripts/gen_credits.py
@@ -16,11 +16,7 @@
 from jinja2.sandbox import SandboxedEnvironment
 from packaging.requirements import Requirement

-# DUE: EOL 3.10: Replace block with line 2.
-if sys.version_info >= (3, 11):
-    import tomllib
-else:
-    import tomli as tomllib
+import tomllib

 project_dir = Path(os.getenv("MKDOCS_CONFIG_DIR", "."))
 with project_dir.joinpath("pyproject.toml").open("rb") as pyproject_file:
```

### `yore fix`

Once you are ready, you can apply transformations to your code base with the `yore fix` command. It will apply what the comments instruct and remove or replace line or blocks of code, but only when a Python version has reached its End of Life date or when the provided upcoming project version is equal to or higher than the one specified in the comments. All comments that would not emit warnings will be left untouched.

```console
% yore fix -f5m -b1
fixed 1 comment in ./src/griffe/encoders.py
fixed 4 comments in ./src/griffe/dataclasses.py
fixed 5 comments in ./src/griffe/mixins.py
fixed 1 comment in ./src/griffe/tests.py
fixed 1 comment in ./src/griffe/expressions.py
fixed 1 comment in ./src/griffe/agents/nodes/_runtime.py
fixed 1 comment in ./src/griffe/agents/nodes/_values.py
fixed 1 comment in ./src/griffe/git.py
fixed 3 comments in ./src/griffe/extensions/base.py
fixed 8 comments in ./src/griffe/loader.py
```

We recommend you run a formatting pass on the code after `yore fix`, for example using [Ruff](https://astral.sh/ruff) or [Black](https://github.com/psf/black).
