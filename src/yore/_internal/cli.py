# SPDX-License-Identifier: ISC
#
# ISC License
#
# Copyright (c) 2026, Timothée Mazzucotelli and contributors
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# Why does this file exist, and why not put this in `__main__`?
#
# You might be tempted to import things from `__main__` later,
# but that will cause problems: the code will get executed twice:
#
# - When you run `python -m yore` python will execute
#   `__main__.py` as a script. That means there won't be any
#   `yore.__main__` in `sys.modules`.
# - When you import `__main__` it will get executed again (as a module) because
#   there's no `yore.__main__` in `sys.modules`.

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import timedelta
from difflib import unified_diff
from functools import wraps
from inspect import cleandoc
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar
from typing import Annotated as An

import cappa
from typing_extensions import Doc

from yore._internal import debug
from yore._internal.config import Config, Unset
from yore._internal.lib import DEFAULT_PREFIX, yield_buffer_comments, yield_files, yield_path_comments

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


_NAME = "yore"

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _FromConfig(cappa.ValueFrom):
    def __init__(self, field: Unset | property, /) -> None:
        attr_name = field.fget.__name__ if isinstance(field, property) else field.name  # ty:ignore[unresolved-attribute]
        super().__init__(self._from_config, attr_name=attr_name)

    @staticmethod
    def _from_config(attr_name: str) -> Any:
        config = CommandMain._load_config()
        value = getattr(config, attr_name)
        return cappa.Empty if isinstance(value, Unset) else value


def _parse_timedelta(value: str) -> timedelta:
    """Parse a timedelta from a string."""
    number, unit = re.match(r" *(\d+) *([a-z])[a-z]* *", value).groups()  # ty:ignore[unresolved-attribute]
    multiplier = {"d": 1, "w": 7, "m": 31, "y": 365}[unit]
    return timedelta(days=int(number) * multiplier)


def _select_config(value: Any) -> Config:
    """Load an explicitly selected configuration during argument parsing."""
    return CommandMain._load_config(value)


@dataclass(kw_only=True)
class _ServiceOptions:
    """Shared work-item service URL options."""

    gitlab_url: An[
        str | None,
        cappa.Arg(
            long=True,
            value_name="URL",
            default=_FromConfig(Config.gitlab_url),  # ty: ignore[invalid-argument-type]
            show_default=f"{Config.gitlab_url}, GitLab environment, or GitLab.com",
        ),
        Doc("The GitLab instance or API URL."),
    ] = None

    forgejo_url: An[
        str | None,
        cappa.Arg(
            long=True,
            value_name="URL",
            default=_FromConfig(Config.forgejo_url),  # ty: ignore[invalid-argument-type]
            show_default=f"{Config.forgejo_url}, `FORGEJO_URL`, or Codeberg",
        ),
        Doc("The Forgejo instance or API URL."),
    ] = None

    def _service_urls(self) -> dict[str, str]:
        values = {
            "forgejo": self.forgejo_url,
            "gitlab": self.gitlab_url,
        }
        return {service: url for service, url in values.items() if url is not None}


@cappa.command(  # ty:ignore[call-non-callable]
    name="check",
    help="Check Yore comments.",
    description=cleandoc(
        """
        This command checks existing Yore comments in your code base against
        supported ecosystem lifecycle dates, external work-item states, or the
        provided next version of your project.
        """,
    ),
)
@dataclass(kw_only=True)
class CommandCheck(_ServiceOptions):
    """Command to check Yore comments."""

    paths: An[
        list[Path],
        cappa.Arg(),
        Doc("Path to files or directories to check."),
    ] = field(default_factory=list)

    bump: An[
        str | None,
        cappa.Arg(short=True, long=True, value_name="VERSION"),
        Doc("The next version of your project."),
    ] = None

    eol_within: An[
        timedelta | None,
        cappa.Arg(short="-E", long="--eol/--eol-within", parse=_parse_timedelta, value_name="TIMEDELTA"),
        Doc(
            """
            The time delta to start checking before the End of Life of an ecosystem version.
            It is provided in a human-readable format, like `2 weeks` or `1 month`.
            Spaces are optional, and the unit can be shortened to a single letter:
            `d` for days, `w` for weeks, `m` for months, and `y` for years.
            """,
        ),
    ] = None

    bol_within: An[
        timedelta | None,
        cappa.Arg(short="-B", long="--bol/--bol-within", parse=_parse_timedelta, value_name="TIMEDELTA"),
        Doc(
            """
            The time delta to start checking before the Beginning of Life of an ecosystem version.
            It is provided in a human-readable format, like `2 weeks` or `1 month`.
            Spaces are optional, and the unit can be shortened to a single letter:
            `d` for days, `w` for weeks, `m` for months, and `y` for years.
            """,
        ),
    ] = None

    prefix: An[
        str,
        cappa.Arg(
            short="-p",
            long=True,
            num_args=1,
            default=_FromConfig(Config.prefix),  # ty: ignore[invalid-argument-type]
            show_default=f"{Config.prefix} or `{DEFAULT_PREFIX}`",
        ),
        Doc("""The prefix for Yore comments."""),
    ] = DEFAULT_PREFIX

    def __call__(self) -> int:
        """Check Yore comments."""
        ok = True
        paths = self.paths or [Path()]
        for path in paths:
            for comment in yield_path_comments(path, prefix=self.prefix):
                ok &= comment.check(
                    bump=self.bump,
                    eol_within=self.eol_within,
                    bol_within=self.bol_within,
                    service_urls=self._service_urls(),
                )
        return 0 if ok else 1


@cappa.command(  # ty:ignore[call-non-callable]
    name="diff",
    help="See the diff you would get after fixing comments.",
    description=cleandoc(
        """
        This command fixes all relevant Yore comments, then computes and prints
        a Git-like diff in the console.
        """,
    ),
)
@dataclass(kw_only=True)
class CommandDiff(_ServiceOptions):
    """Command to diff Yore comments."""

    paths: An[
        list[Path],
        cappa.Arg(),
        Doc("Path to files or directories to diff."),
    ] = field(default_factory=list)

    bump: An[
        str | None,
        cappa.Arg(short=True, long=True, value_name="VERSION"),
        Doc("The next version of your project."),
    ] = None

    eol_within: An[
        timedelta | None,
        cappa.Arg(short="-E", long="--eol/--eol-within", parse=_parse_timedelta, value_name="TIMEDELTA"),
        Doc(
            """
            The time delta to start diffing before the End of Life of an ecosystem version.
            It is provided in a human-readable format, like `2 weeks` or `1 month`.
            Spaces are optional, and the unit can be shortened to a single letter:
            `d` for days, `w` for weeks, `m` for months, and `y` for years.
            """,
        ),
    ] = None

    bol_within: An[
        timedelta | None,
        cappa.Arg(short="-B", long="--bol/--bol-within", parse=_parse_timedelta, value_name="TIMEDELTA"),
        Doc(
            """
            The time delta to start diffing before the Beginning of Life of an ecosystem version.
            It is provided in a human-readable format, like `2 weeks` or `1 month`.
            Spaces are optional, and the unit can be shortened to a single letter:
            `d` for days, `w` for weeks, `m` for months, and `y` for years.
            """,
        ),
    ] = None

    highlight: An[
        str | None,
        cappa.Arg(
            short="-H",
            long="--highlight",
            num_args=1,
            default=_FromConfig(Config.diff_highlight),  # ty: ignore[invalid-argument-type]
            show_default=f"{Config.diff_highlight}",
        ),
        Doc("The command to highlight diffs."),
    ] = None

    prefix: An[
        str,
        cappa.Arg(
            short="-p",
            long=True,
            num_args=1,
            default=_FromConfig(Config.prefix),  # ty: ignore[invalid-argument-type]
            show_default=f"{Config.prefix} or `{DEFAULT_PREFIX}`",
        ),
        Doc("""The prefix for Yore comments."""),
    ] = DEFAULT_PREFIX

    def _diff(self, file: Path) -> Iterator[str]:
        try:
            old_lines = file.read_text().splitlines(keepends=True)
        except (OSError, UnicodeDecodeError):
            return
        new_lines = old_lines.copy()
        fixed = False
        for comment in sorted(
            yield_buffer_comments(file, new_lines, prefix=self.prefix),
            key=lambda c: c.lineno,
            reverse=True,
        ):
            fixed |= comment.fix(
                buffer=new_lines,
                bump=self.bump,
                eol_within=self.eol_within,
                bol_within=self.bol_within,
                service_urls=self._service_urls(),
            )
            if not new_lines:
                _logger.debug(f"no more lines in {file}, breaking early")
                break
        if fixed:
            yield from unified_diff(old_lines, new_lines, fromfile=str(file), tofile=str(file))

    def _diff_paths(self, paths: list[Path]) -> Iterator[str]:
        for path in paths:
            if path.is_file():
                yield from self._diff(path)
            else:
                for file in sorted(yield_files(path)):
                    yield from self._diff(file)

    def __call__(self) -> int:
        """Diff Yore comments."""
        lines = self._diff_paths(self.paths or [Path()])
        if self.highlight:
            process = subprocess.Popen(self.highlight, shell=True, text=True, stdin=subprocess.PIPE)  # noqa: S602
            for line in lines:
                process.stdin.write(line)  # ty:ignore[unresolved-attribute]
            process.stdin.close()  # ty:ignore[unresolved-attribute]
            process.wait()
            return int(process.returncode)
        for line in lines:
            print(line, end="")
        return 0


@cappa.command(  # ty:ignore[call-non-callable]
    name="fix",
    help="Fix Yore comments and the associated code lines.",
    description=cleandoc(
        """
        This command will fix your code by transforming it according to the Yore comments.
        """,
    ),
)
@dataclass(kw_only=True)
class CommandFix(_ServiceOptions):
    """Command to fix Yore comments."""

    paths: An[
        list[Path],
        cappa.Arg(),
        Doc("Path to files or directories to fix."),
    ] = field(default_factory=list)

    bump: An[
        str | None,
        cappa.Arg(short=True, long=True, value_name="VERSION"),
        Doc("The next version of your project."),
    ] = None

    eol_within: An[
        timedelta | None,
        cappa.Arg(short="-E", long="--eol/--eol-within", parse=_parse_timedelta, value_name="TIMEDELTA"),
        Doc(
            """
            The time delta to start fixing before the End of Life of an ecosystem version.
            It is provided in a human-readable format, like `2 weeks` or `1 month`.
            Spaces are optional, and the unit can be shortened to a single letter:
            `d` for days, `w` for weeks, `m` for months, and `y` for years.
            """,
        ),
    ] = None

    bol_within: An[
        timedelta | None,
        cappa.Arg(short="-B", long="--bol/--bol-within", parse=_parse_timedelta, value_name="TIMEDELTA"),
        Doc(
            """
            The time delta to start fixing before the Beginning of Life of an ecosystem version.
            It is provided in a human-readable format, like `2 weeks` or `1 month`.
            Spaces are optional, and the unit can be shortened to a single letter:
            `d` for days, `w` for weeks, `m` for months, and `y` for years.
            """,
        ),
    ] = None

    prefix: An[
        str,
        cappa.Arg(
            short="-p",
            long=True,
            num_args=1,
            default=_FromConfig(Config.prefix),  # ty: ignore[invalid-argument-type]
            show_default=f"{Config.prefix}",
        ),
        Doc("""The prefix for Yore comments."""),
    ] = DEFAULT_PREFIX

    def _fix(self, file: Path) -> None:
        try:
            lines = file.read_text().splitlines(keepends=True)
        except (OSError, UnicodeDecodeError):
            return
        count = 0
        for comment in sorted(
            yield_buffer_comments(file, lines, prefix=self.prefix),
            key=lambda c: c.lineno,
            reverse=True,
        ):
            if comment.fix(
                buffer=lines,
                bump=self.bump,
                eol_within=self.eol_within,
                bol_within=self.bol_within,
                service_urls=self._service_urls(),
            ):
                count += 1
                if not lines:
                    _logger.debug(f"no more lines in {file}, breaking early")
                    break
        if count:
            if lines:
                file.write_text("".join(lines))
                _logger.info(f"fixed {count} comment{'s' if count > 1 else ''} in {file}")
            else:
                file.unlink()
                _logger.info(f"removed {file}")

    def __call__(self) -> int:
        """Fix Yore comments."""
        paths = self.paths or [Path()]
        for path in paths:
            if path.is_file():
                self._fix(path)
            else:
                for file in yield_files(path):
                    self._fix(file)
        return 0


@cappa.command(  # ty:ignore[call-non-callable]
    name=_NAME,
    help="Manage legacy code in your code base with YORE comments.",
    description=cleandoc(
        """
        This tool lets you add `# YORE` comments (similar to `# TODO` comments)
        that will help you manage legacy code in your code base.

        A YORE comment follows a simple syntax that tells why this legacy code
        is here and how it can be checked, or fixed once it's time to do so.
        The syntax is as follows:

        ```python
        # <PREFIX>: <WHEN>: Remove <file|block|line>.
        # <PREFIX>: <WHEN>: replace <file|block|line> with line <LINENO>.
        # <PREFIX>: <WHEN>: replace <file|block|line> with lines <LINE-RANGE1[, LINE-RANGE2...]>.
        # <PREFIX>: <WHEN>: replace <file|block|line> with `<STRING>`.
        # <PREFIX>: <WHEN>: [regex-]replace `<PATTERN1>` with `<PATTERN2>` [within <file|block|line>].

        `<WHEN>` is `bump <VERSION>`, `<eol|bol> [<ECOSYSTEM> ]<VERSION>`, or
        an external work-item reference. Supported work-item tags are `GHI` and
        `GHP` (GitHub), `RDI` and `RDP` (Radicle), `GLI` and `GLM` (GitLab),
        and `FJI` and `FJP` (Forgejo).

        Trigger spellings are case-insensitive. GitHub, Radicle, GitLab,
        and Forgejo references accept compact tags or readable provider names.
        GitLab merge requests also accept `group/project!number` and `!number`.

        Supported lifecycle ecosystems are Python and Rust. When no ecosystem
        is given, Yore infers Rust from Cargo files and `.rs` files, and
        defaults to Python for other files. Repository-backed work items accept
        an explicit repository and number or a short `#number`/`number` form.
        Short references use CI metadata and then the Git `origin` remote.

        GitHub references accept `owner/repository#number`, `#number`, or
        `number`. Short references use `GITHUB_REPOSITORY`, then the Git
        `origin` remote. Authentication uses `GH_TOKEN` or `GITHUB_TOKEN` when
        available.
        Radicle references accept `rad:<RID>#<OBJECT-ID>` or `<OBJECT-ID>`.
        An object ID is the full 40-hex issue or patch ID. Short references
        infer the RID from the Git `rad` remote, then `rad inspect --rid`.
        Yore reads locally seeded COBs with `rad cob show`.

        Line references are one-based and ranges are inclusive. Either range
        endpoint can be omitted: `2-` means line 2 through the end of the
        selected scope, and `-5` means its start through line 5.
        Text and regex replacement default to `within line` when their
        `within <file|block|line>` suffix is omitted.
        ```

        Terms between `<` and `>` *must* be provided, while terms between `[` and `]` are optional.
        Uppercase terms are placeholders that you should replace with actual values,
        while lowercase terms are keywords that you should use literally.
        Everything except placeholders is case-insensitive.

        The default **prefix** is `YORE`. It is configurable through TOML, the CLI, or the Python API.

        Examples:

        *Replace a block of code when Python 3.8 reaches its End of Life.
        In this example, we want to replace the block with `from ast import unparse`.*

        ```python
        # YORE: EOL 3.8: Replace block with line 4.
        if sys.version_info < (3, 9):
            from astunparse import unparse
        else:
            from ast import unparse
        ```

        *Remove a compatibility line when Rust 1.72 reaches its End of Life.*

        ```rust
        // YORE: EOL Rust 1.72: Remove line.
        compatibility_workaround();
        ```

        *Remove a workaround when a GitHub issue is completed.*

        ```python
        # YORE: GitHub issue pawamoy/yore#123: Remove line.
        legacy_issue_workaround()
        ```

        *Remove a workaround when a GitLab merge request is merged.*

        ```python
        # YORE: GitLab merge request group/project!123: Remove line.
        legacy_merge_request_workaround()
        ```

        *Remove a workaround when a Radicle issue is solved.*

        ```rust
        // YORE: RDI 0123456789abcdef0123456789abcdef01234567: Remove line.
        legacy_issue_workaround();
        ```

        *Replace `lstrip` by `removeprefix` when Python 3.8 reaches its End of Life.*

        ```python
        # YORE: EOL 3.8: Replace `lstrip` with `removeprefix`.
        return [cpn.lstrip("_") for cpn in a.split(".")] == [cpn.lstrip("_") for cpn in b.split(".")]
        ```

        *Simplify union of accepted types when we bump the project to version 1.0.0.*

        ```python
        def load_extensions(
            # YORE: Bump 1.0.0: Replace ` | Sequence[LoadableExtension],` with ``.
            *exts: LoadableExtension | Sequence[LoadableExtension],
        ): ...
        ```
        """,
    ),
)
@dataclass(kw_only=True)
class CommandMain:
    """Command to manage legacy code in your code base with YORE comments."""

    subcommand: An[cappa.Subcommands[CommandCheck | CommandDiff | CommandFix], Doc("The selected subcommand.")]

    @staticmethod
    def _load_config(file: str | Path | None = None) -> Config:
        if file:
            path = Path(file)
            CommandMain._CONFIG = (
                Config.from_pyproject(path) if path.name == "pyproject.toml" else Config.from_file(path)
            )
        elif CommandMain._CONFIG is None:
            CommandMain._CONFIG = Config.from_default_locations()
        return CommandMain._CONFIG

    @staticmethod
    def _print_and_exit(
        func: An[Callable[[], str | None], Doc("A function that returns or prints a string.")],
        code: An[int, Doc("The status code to exit with.")] = 0,
    ) -> Callable[[], None]:
        """Argument action callable to print something and exit immediately."""

        @wraps(func)
        def _inner() -> None:
            raise cappa.Exit(func() or "", code=code)

        return _inner

    _CONFIG: ClassVar[Config | None] = None

    config: An[
        Config,
        cappa.Arg(
            short="-c",
            long=True,
            action=_select_config,
            propagate=True,
            show_default="`config/yore.toml`, `yore.toml`, or `pyproject.toml`",
        ),
        Doc("Path to the configuration file."),
    ] = field(default_factory=_load_config)

    version: An[
        bool,
        cappa.Arg(
            short="-V",
            long=True,
            action=_print_and_exit(debug._get_version),
            num_args=0,
            help="Print the program version and exit.",
        ),
        Doc("Version CLI option."),
    ] = False

    debug_info: An[
        bool,
        cappa.Arg(long=True, action=_print_and_exit(debug._print_debug_info), num_args=0),
        Doc("Print debug information."),
    ] = False


def main(
    args: An[list[str] | None, Doc("Arguments passed from the command line.")] = None,
) -> An[int, Doc("An exit code.")]:
    """Run the main program.

    This function is executed when you type `yore` or `python -m yore`.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    output = cappa.Output(error_format=f"[bold]{_NAME}[/]: [bold red]error[/]: {{message}}")
    completion_option: cappa.Arg = cappa.Arg(
        long=True,
        action=cappa.ArgAction.completion,
        choices=["complete", "generate"],
        help="Print shell-specific completion source.",
    )
    help_option: cappa.Arg = cappa.Arg(
        short="-h",
        long=True,
        action=cappa.ArgAction.help,
        help="Print the program help and exit.",
    )
    help_formatter = cappa.HelpFormatter(default_format="Default: {default}.")

    try:
        return cappa.invoke(  # ty:ignore[call-non-callable]
            CommandMain,
            argv=args,
            output=output,
            help=help_option,
            completion=completion_option,
            help_formatter=help_formatter,
        )
    except cappa.Exit as exit:
        return int(1 if exit.code is None else exit.code)
