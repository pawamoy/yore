---
hide:
- navigation
---

# Usage

Yore lets you write `# YORE` comments in your code base to mark lines or blocks of code as legacy code: only there to support older ecosystem versions, pending external work, or backward compatibility with previous versions of your own project.

## Syntax

The syntax is as follows:

```text
<COMMENT> <PREFIX>: <WHEN>: remove <file|block|line>.
<COMMENT> <PREFIX>: <WHEN>: replace <file|block|line> with line <LINENO>.
<COMMENT> <PREFIX>: <WHEN>: replace <file|block|line> with lines <LINE-RANGE1[, LINE-RANGE2...]>.
<COMMENT> <PREFIX>: <WHEN>: replace <file|block|line> with `<STRING>`.
<COMMENT> <PREFIX>: <WHEN>: [regex-]replace `<PATTERN1>` with `<PATTERN2>` [within <file|block|line>].

<WHEN> = bump <VERSION>
       | <eol|bol> [<ECOSYSTEM> ]<VERSION>
       | ghi <GITHUB-REFERENCE>
       | ghp <GITHUB-REFERENCE>
       | rdi <RADICLE-REFERENCE>
       | rdp <RADICLE-REFERENCE>
       | gli <GITLAB-ISSUE-REFERENCE>
       | glm <GITLAB-MERGE-REQUEST-REFERENCE>
       | fji <FORGEJO-ISSUE-REFERENCE>
       | fjp <FORGEJO-PULL-REQUEST-REFERENCE>

<ECOSYSTEM> = python | rust
```

Terms between `<` and `>` *must* be provided, while terms between `[` and `]` are optional. Uppercase terms are placeholders that you should replace with actual values, while lowercase terms are keywords that you should use literally. Everything except placeholders is case-insensitive.

For literal and regex text replacement, omitting `within <SCOPE>` defaults to `within line`. Use `within block` or `within file` to search a larger scope.

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

Trigger spellings are case-insensitive. Work-item tags have readable aliases.
The following table is exhaustive:

| Compact tag | Meaning | Readable aliases |
| --- | --- | --- |
| `Bump` | Project version bump | — |
| `BOL` | Beginning of ecosystem life | — |
| `EOL` | End of ecosystem life | — |
| `GHI` | GitHub issue | `gh issue`, `github issue` |
| `GHP` | GitHub pull request | `gh pr`, `github pr`, `gh pull request`, `github pull request` |
| `RDI` | Radicle issue | `rd issue`, `rad issue`, `radicle issue` |
| `RDP` | Radicle patch | `rd patch`, `rad patch`, `radicle patch` |
| `GLI` | GitLab issue | `gl issue`, `gitlab issue` |
| `GLM` | GitLab merge request | `gl mr`, `gitlab mr`, `gl merge request`, `gitlab merge request` |
| `FJI` | Forgejo issue | `fj issue`, `forgejo issue` |
| `FJP` | Forgejo pull request | `fj pr`, `forgejo pr`, `fj pull request`, `forgejo pull request` |

For example, `GHI`, `gh issue`, and `GitHub Issue` select exactly the same
trigger. Readable aliases are normalized to their compact kind internally and
do not change reference parsing, completion rules, diagnostics, or fixes.

### Lifecycle triggers

For `eol` and `bol`, you can name the ecosystem explicitly, for example `EOL Rust 1.72`. An explicit qualifier overrides inference. Qualifiers are case-insensitive:

| Ecosystem | Accepted qualifiers |
| --- | --- |
| Python | `python` |
| Rust | `rust` |

When you omit the qualifier, Yore uses the filename or extension:

| Ecosystem | Inferred from |
| --- | --- |
| Python | `.py`, `.pyi`, `.pyw`, and `.pyx`; also the fallback for anything unrecognized |
| Rust | `.rs`, `Cargo.toml`, and `Cargo.lock` |

Python lifecycle dates come from the Python release-cycle data. Rust dates come from the [endoflife.date API](https://endoflife.date/docs/api/v1/). A release without a scheduled EOL date stays inactive for EOL checks and fixes. Rust version spellings such as `1.90.0` and `v1.90` resolve to the `1.90` series.

### GitHub triggers

GitHub references accept `owner/repository#number`, `#number`, or `number`. The two short forms use `GITHUB_REPOSITORY` when it is set (as it normally is in GitHub Actions), then fall back to the Git `origin` remote. `GHI` becomes actionable only when the issue is closed with reason `completed`; `GHP` becomes actionable only when the pull request is merged. During `check`, an issue closed for another reason and a pull request closed without merging emit warnings and make the check fail, but `diff` and `fix` leave their code untouched.

Yore reads public GitHub data without authentication. Set `GH_TOKEN` (preferred) or `GITHUB_TOKEN` to raise the rate limit and access private repositories. `GITHUB_API_URL` changes the API root for GitHub Enterprise; it defaults to `https://api.github.com`. A reference is fetched once per process. API, authentication, rate-limit, and malformed-response errors propagate instead of being treated as open work.

### Radicle triggers

Radicle references accept a full 40-hex issue or patch object ID, optionally prefixed with a repository and `#`:

- `0123456789abcdef0123456789abcdef01234567` or `#0123456789abcdef0123456789abcdef01234567` uses the current repository;
- `rad:z4TEkvLebGGXYE3pgxHGu1GGpUM94#0123456789abcdef0123456789abcdef01234567` names a RID explicitly;

For an ID-only reference, Yore first reads the conventional Git `rad` remote and then falls back to `rad inspect --rid`. A full object ID is required so the reference resolves consistently across nodes. `RDI` becomes actionable only for an issue whose state is `closed` with reason `solved`; a `closed`/`other` issue warns and remains untouched. `RDP` becomes actionable only for a `merged` patch; an `archived` patch warns and remains untouched. Open issues and open or draft patches are inactive.

Yore runs `rad cob show --repo <RID> --type xyz.radicle.issue --object <OBJECT-ID> --format json` for issues. It uses `xyz.radicle.patch` as the type for patches. Install `rad` and seed each referenced repository in local Radicle storage first. Yore reads the state available in that storage and fetches each object once per process. Missing objects, CLI failures, decoding errors, and unexpected states propagate.

### Other work-item services

GitLab and Forgejo use the same three-way policy: active work leaves the comment alone; fulfilled work makes `check` fail with an error and permits `diff`/`fix`; terminal work that did not fulfill the request makes `check` fail with a warning and is never edited. Yore requires an explicit success status or label before it edits code.

| Tag | Reference forms | Fulfilled when | Warns when |
| --- | --- | --- | --- |
| `GLI` | `group[/subgroup]/project#N`, `#N`, `N` | Closed with a `DONE` work-item status, or a completion label | Closed as duplicate, with a `CANCELED` status/rejection label, or without a completion marker |
| `GLM` | `group[/subgroup]/project!N`, `!N`, `#N`, `N` | Merged | Closed without merging |
| `FJI` | `owner/repository#N`, `#N`, `N` | Closed with a completion label | Closed without one |
| `FJP` | `owner/repository#N`, `#N`, `N` | Merged | Closed without merging |

Short repository references use the provider's CI repository variable, then infer the repository from the Git `origin` remote. GitLab uses `CI_PROJECT_PATH`; Forgejo uses `FORGEJO_REPOSITORY`.

For GitLab and Forgejo issues, the default completion labels are `yore:completed` and `yore/completed`. Default rejection labels are `yore:rejected`, `yore/rejected`, `wontfix`, `won't fix`, `duplicate`, and `invalid`. Override them with comma-separated `YORE_GITLAB_COMPLETED_LABELS` / `YORE_GITLAB_REJECTED_LABELS` or `YORE_FORGEJO_COMPLETED_LABELS` / `YORE_FORGEJO_REJECTED_LABELS`. A rejection label wins if both kinds are present.

Each resolved provider reference is fetched at most once per process. Requests have a three-second timeout. Connectivity, authentication, rate-limit, decoding, malformed-response, and unsupported-state errors propagate instead of being interpreted as active work.

Line references are one-based, and ranges are inclusive. Either endpoint can be omitted: `2-` selects line 2 through the end of the selected scope. `-5` selects the start through line 5. Line references are relative to the start of a block for `block` scope and absolute for `file` scope.

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
# YORE: EOL 3.8: Replace `lstrip` with `removeprefix`.
return [cpn.lstrip("_") for cpn in a.split(".")] == [cpn.lstrip("_") for cpn in b.split(".")]
```

*Remove a compatibility workaround when Rust 1.72 reaches its End of Life.*

```rust
// YORE: EOL Rust 1.72: Remove line.
compatibility_workaround();
```

*Remove a workaround after a GitHub issue is completed.*

```python
# YORE: GHI pawamoy/yore#123: Remove line.
legacy_issue_workaround()
```

*Remove temporary compatibility code after a pull request is merged.*

```python
# YORE: GHP #456: Remove line.
temporary_pr_compatibility()
```

*Remove a workaround after a Radicle issue is solved.*

```rust
// YORE: RDI 0123456789abcdef0123456789abcdef01234567: Remove line.
legacy_issue_workaround();
```

*Remove temporary code after a patch in another Radicle repository is merged.*

```rust
// YORE: RDP rad:z4TEkvLebGGXYE3pgxHGu1GGpUM94#89abcdef0123456789abcdef0123456789abcdef: Remove block.
if compatibility_required() {
    temporary_patch_compatibility();
}
```

*Simplify union of accepted types when we bump the project to version 1.0.0.*

```python
def load_extensions(
    # YORE: Bump 1.0.0: Replace ` | Sequence[LoadableExtension],` with ``.
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

### Work-item service URLs

GitLab and Forgejo use the same URL precedence. In the CLI, an explicit option overrides TOML; that resolved value overrides environment variables and then the public default. In Python, an entry in the `service_urls` mapping takes the place of the CLI/TOML value. An instance origin and the full API root are both accepted; Yore appends `/api/v4` or `/api/v1` where appropriate.

| Service | TOML key | CLI option | URL environment variables | Default |
| --- | --- | --- | --- | --- |
| GitLab | `gitlab.url` | `--gitlab-url` | `GITLAB_API_URL`, `CI_API_V4_URL`, `GITLAB_URL` | `https://gitlab.com/api/v4` |
| Forgejo | `forgejo.url` | `--forgejo-url` | `FORGEJO_API_URL`, `FORGEJO_SERVER_URL`, `FORGEJO_URL` | `https://codeberg.org/api/v1` |

For example, in `pyproject.toml`:

```toml
[tool.yore.gitlab]
url = "https://gitlab.example.com"
```

Or in `yore.toml` / `config/yore.toml`:

```toml
[gitlab]
url = "https://gitlab.example.com"
```

The adapters read credentials only from the environment:

| Service | Credential environment variables |
| --- | --- |
| GitLab | `GITLAB_TOKEN` or `PRIVATE_TOKEN`; `CI_JOB_TOKEN` is the fallback |
| Forgejo | `FORGEJO_TOKEN` |

Service URLs must use HTTP or HTTPS and cannot contain embedded credentials, a query, or a fragment. Prefer HTTPS whenever credentials are sent. A configured URL is trusted: pairing a secret with a malicious URL can disclose that secret.

## Commands

### `yore check`

Once you have written a few Yore comments in your code base, you can check them with the `yore check` command. If a comment is outdated, for example the current version of the project is equal to or higher than a `bump` comment, Yore will report it. The same applies when an ecosystem lifecycle date has arrived or an external work item is fulfilled. Terminal but unfulfilled work is reported as a warning instead. If you want to be warned before an EOL (End of Life) date, use the `-E`, `--eol`, `--eol-within` option. If you want to be warned before a BOL (Beginning of Life) date, use the `-B`, `--bol`, `--bol-within` option. To specify the upcoming project version, use the `-b`, `--bump` option.

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

Once you are ready, you can apply transformations to your code base with the `yore fix` command. It will apply what the comments instruct and remove or replace lines or blocks of code, but only when an ecosystem lifecycle date has been reached, an external work item is fulfilled, or the provided upcoming project version is equal to or higher than the one specified in the comments. Active and terminal-but-unfulfilled work is left untouched.

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
