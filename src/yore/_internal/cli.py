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
import sys
from dataclasses import dataclass, field
from datetime import timedelta
from functools import wraps
from inspect import cleandoc
from pathlib import Path
from typing import Annotated as An
from typing import Any, Callable

import cappa
from typing_extensions import Doc

from yore._internal import debug
from yore._internal.lib import yield_buffer_comments, yield_path_comments, yield_python_files

_NAME = "yore"

_logger = logging.getLogger(__name__)

# YORE: EOL 3.9: Remove block.
_dataclass_opts: dict[str, bool] = {}
if sys.version_info >= (3, 10):
    _dataclass_opts["kw_only"] = True


def _print_and_exit(
    func: An[Callable[[], str | None], Doc("A function that returns or prints a string.")],
    code: An[int, Doc("The status code to exit with.")] = 0,
) -> Callable[[], None]:
    """Argument action callable to print something and exit immediately."""

    @wraps(func)
    def _inner() -> None:
        raise cappa.Exit(func() or "", code=code)

    return _inner


def _parse_timedelta(value: str) -> timedelta:
    """Parse a timedelta from a string."""
    number, unit = re.match(r" *(\d+) *([a-z])[a-z]* *", value).groups()  # type: ignore[union-attr]
    multiplier = {"d": 1, "w": 7, "m": 31, "y": 365}[unit]
    return timedelta(days=int(number) * multiplier)


@cappa.command(
    name="check",
    help="Check Yore comments.",
    description=cleandoc(
        """
        This command checks existing Yore comments in your code base
        against Python End of Life dates or the provided next version of your project.
        """,
    ),
)
# YORE: EOL 3.9: Replace `**dataclass_opts` with `kw_only=True` within line.
@dataclass(**_dataclass_opts)
class CommandCheck:
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
            The time delta to start checking before the End of Life of a Python version.
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
            The time delta to start checking before the Beginning of Life of a Python version.
            It is provided in a human-readable format, like `2 weeks` or `1 month`.
            Spaces are optional, and the unit can be shortened to a single letter:
            `d` for days, `w` for weeks, `m` for months, and `y` for years.
            """,
        ),
    ] = None

    def __call__(self) -> Any:
        """Check Yore comments."""
        ok = True
        paths = self.paths or [Path(".")]
        for path in paths:
            for comment in yield_path_comments(path):
                ok &= comment.check(bump=self.bump, eol_within=self.eol_within, bol_within=self.bol_within)
        return 0 if ok else 1


@cappa.command(
    name="fix",
    help="Fix Yore comments and the associated code lines.",
    description=cleandoc(
        """
        This command will fix your code by transforming it according to the Yore comments.
        """,
    ),
)
# YORE: EOL 3.9: Replace `**dataclass_opts` with `kw_only=True` within line.
@dataclass(**_dataclass_opts)
class CommandFix:
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
            The time delta to start fixing before the End of Life of a Python version.
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
            The time delta to start fixing before the Beginning of Life of a Python version.
            It is provided in a human-readable format, like `2 weeks` or `1 month`.
            Spaces are optional, and the unit can be shortened to a single letter:
            `d` for days, `w` for weeks, `m` for months, and `y` for years.
            """,
        ),
    ] = None

    def _fix(self, file: Path) -> None:
        lines = file.read_text().splitlines(keepends=True)
        count = 0
        for comment in sorted(yield_buffer_comments(file, lines), key=lambda c: c.lineno, reverse=True):
            if comment.fix(buffer=lines, bump=self.bump, eol_within=self.eol_within, bol_within=self.bol_within):
                count += 1
        if count:
            file.write_text("".join(lines))
            _logger.info(f"fixed {count} comment{'s' if count > 1 else ''} in {file}")

    def __call__(self) -> Any:
        """Fix Yore comments."""
        paths = self.paths or [Path(".")]
        for path in paths:
            if path.is_file():
                self._fix(path)
            else:
                for file in yield_python_files(path):
                    self._fix(file)
        return 0


@cappa.command(
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
        # YORE: <eol|bump> <VERSION>: Remove <block|line>.
        # YORE: <eol|bump> <VERSION>: replace <block|line> with line <LINENO>.
        # YORE: <eol|bump> <VERSION>: replace <block|line> with lines <LINE-RANGE1[, LINE-RANGE2...]>.
        # YORE: <eol|bump> <VERSION>: replace <block|line> with `<STRING>`.
        # YORE: <eol|bump> <VERSION>: [regex-]replace `<PATTERN1>` with `<PATTERN2>` within <block|line>.
        ```

        Terms between `<` and `>` *must* be provided, while terms between `[` and `]` are optional.
        Uppercase terms are placeholders that you should replace with actual values,
        while lowercase terms are keywords that you should use literally.
        Everything except placeholders is case-insensitive.

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
        """,
    ),
)
# YORE: EOL 3.9: Replace `**dataclass_opts` with `kw_only=True` within line.
@dataclass(**_dataclass_opts)
class CommandMain:
    """Command to manage legacy code in your code base with YORE comments."""

    subcommand: An[cappa.Subcommands[CommandCheck | CommandFix], Doc("The selected subcommand.")]

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

    completion: An[
        bool,
        cappa.Arg(
            long=True,
            action=cappa.ArgAction.completion,
            choices=("complete", "generate"),
            help="Print shell-specific completion source.",
        ),
        Doc("Completion CLI option."),
    ] = False


def main(
    args: An[list[str] | None, Doc("Arguments passed from the command line.")] = None,
) -> An[int, Doc("An exit code.")]:
    """Run the main program.

    This function is executed when you type `yore` or `python -m yore`.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    output = cappa.Output(error_format=f"[bold]{_NAME}[/]: [bold red]error[/]: {{message}}")
    help_option: cappa.Arg = cappa.Arg(
        short="-h",
        long=True,
        action=cappa.ArgAction.help,
        help="Print the program help and exit.",
    )
    try:
        return cappa.invoke(
            CommandMain,
            argv=args,
            output=output,
            backend=cappa.backend,
            completion=False,
            help=help_option,
        )
    except cappa.Exit as error:
        return int(1 if error.code is None else error.code)
