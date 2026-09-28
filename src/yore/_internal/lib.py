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

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from datetime import date as Date  # noqa: N812
from datetime import datetime as DateTime  # noqa: N812
from datetime import timedelta as TimeDelta  # noqa: N812
from datetime import timezone as TimeZone  # noqa: N812
from functools import cache
from re import Pattern
from typing import TYPE_CHECKING, Literal, cast
from urllib.request import urlopen

from humanize import naturaldelta
from packaging.version import Version

from yore._internal.work_items import (
    _SERVICE_KINDS,
    _fetch_work_item,
    _WorkItem,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path

YoreKind = Literal[
    "bol",
    "bump",
    "eol",
]
"""The supported kinds of Yore comments."""

_KIND_SPELLINGS: dict[YoreKind, tuple[str, ...]] = {
    "bol": ("bol",),
    "bump": ("bump",),
    "eol": ("eol",),
}
"""Accepted case-insensitive spellings for each canonical Yore kind."""

_KIND_ALIASES: dict[str, YoreKind] = {
    spelling: kind for kind, spellings in _KIND_SPELLINGS.items() for spelling in spellings
}


Versioned = Literal["python"]
"""The versioned projects supported by lifecycle comments."""

_VERSIONED_ALIASES: dict[str, Versioned] = {
    "python": "python",
}

_FILENAME_VERSIONED: dict[str, Versioned] = {}

_EXTENSION_VERSIONED: dict[str, Versioned] = {
    ".py": "python",
    ".pyi": "python",
    ".pyw": "python",
    ".pyx": "python",
}

Scope = Literal["block", "file", "line"]
"""The scope of a comment."""

DEFAULT_PREFIX = "YORE"
"""The default prefix for Yore comments."""

DEFAULT_EXCLUDE = [".*", "__py*", "build", "dist"]
"""The default patterns to exclude when scanning directories."""

_logger = logging.getLogger(__name__)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _block_size(buffer: list[str], start: int) -> int:
    size = 0
    consecutive_blank = 0
    indent = _indent(buffer[start])
    for line in buffer[start:]:
        if line.strip():
            line_indent = _indent(line)
            if line_indent < indent:
                break
            if _indent(line) == indent and consecutive_blank:
                break
            consecutive_blank = 0
        else:
            consecutive_blank += 1
        size += 1
    return size - consecutive_blank


def _scope_range(replace: Scope, buffer: list[str], start: int) -> tuple[int, int]:
    if replace == "line":
        return start, start + 1
    if replace == "block":
        return start, start + _block_size(buffer, start)
    if replace == "file":
        return 0, len(buffer)
    raise ValueError(f"Invlid replace scope: {replace}")


def _reindent(lines: list[str], indent: int) -> list[str]:
    common = min(_indent(line) for line in lines)
    new = indent * " "
    return [f"{new}{line[common:]}" for line in lines]


def _match_to_line(match: re.Match) -> int | None:
    if matched_line := match.group("line"):
        return int(matched_line)
    return None


def _match_to_lines(match: re.Match) -> list[int] | None:
    if matched_lines := match.group("lines"):
        lines: list[int] = []
        matched_lines = matched_lines.replace(" ", ",").strip(",")
        matched_lines = re.sub(",+", ",", matched_lines)
        for line_range in matched_lines.split(","):
            if "-" in line_range:
                start, end = line_range.split("-")
                lines.extend(range(int(start), int(end) + 1))
            else:
                lines.append(int(line_range))
        return lines
    return None


def _infer_versioned(file: Path) -> Versioned:
    name = file.name.casefold()
    if versioned := _FILENAME_VERSIONED.get(name):
        return versioned
    suffix = file.suffix.casefold()
    return _EXTENSION_VERSIONED.get(suffix, "python")


def _match_to_versioned(match: re.Match, inferred: Versioned) -> Versioned:
    if matched_versioned := match.group("versioned"):
        return _VERSIONED_ALIASES[matched_versioned.casefold()]
    return inferred


def _match_to_kind(match: re.Match) -> YoreKind:
    spelling = match.group("kind")
    canonical = _KIND_ALIASES[spelling.casefold()]
    # Preserve the established spelling/capitalization behavior for compact
    # tags. Readable aliases normalize to the canonical compact kind so the
    # rest of the evaluator needs no alias-specific branches.
    if spelling.casefold() == canonical:
        return cast("YoreKind", spelling)
    return canonical


def _match_to_comment(match: re.Match, file: Path, lineno: int, inferred: Versioned) -> YoreComment:
    return YoreComment(
        file=file,
        lineno=lineno,
        raw=match.group(0),
        prefix=match.group("prefix"),
        suffix=match.group("suffix"),
        kind=_match_to_kind(match),
        version=match.group("version"),
        versioned=_match_to_versioned(match, inferred),
        remove=match.group("remove"),
        replace=match.group("replace"),
        line=_match_to_line(match),
        lines=_match_to_lines(match),
        string=match.group("string"),
        regex=bool(match.group("regex")),
        pattern1=match.group("pattern1"),
        pattern2=match.group("pattern2"),
        within=match.group("within"),
    )


def _within(delta: TimeDelta, of: Date) -> bool:
    return DateTime.now(tz=TimeZone.utc).date() >= of - delta


def _delta(until: Date) -> TimeDelta:
    return until - DateTime.now(tz=TimeZone.utc).date()


def _past(date: Date) -> bool:
    return date <= DateTime.now(tz=TimeZone.utc).date()


@dataclass(kw_only=True)
class YoreComment:
    """A Yore comment."""

    file: Path
    """The file containing comment."""
    lineno: int
    """The line number of the comment."""
    raw: str
    """The raw comment."""
    prefix: str
    """The prefix of the comment."""
    suffix: str
    """The suffix of the comment."""
    kind: YoreKind
    """The kind of comment."""
    version: str
    """The lifecycle/bump version or external work-item reference."""
    versioned: Versioned = "python"
    """The versioned project for BOL/EOL comments."""
    remove: Scope | None = None
    """The removal scope."""
    replace: Scope | None = None
    """The replacement scope."""
    line: int | None = None
    """The line to replace."""
    lines: list[int] | None = None
    """The lines to replace."""
    string: str | None = None
    """The string to replace."""
    regex: bool = False
    """Whether to use regex for replacement."""
    pattern1: str | None = None
    """The pattern to replace."""
    pattern2: str | None = None
    """The replacement pattern."""
    within: Scope | None = None
    """The scope to replace within."""

    @property
    def is_bol(self) -> bool:
        """Whether the comment is an End of Life comment."""
        return self.kind.lower() == "bol"

    @property
    def is_eol(self) -> bool:
        """Whether the comment is an End of Life comment."""
        return self.kind.lower() == "eol"

    @property
    def is_bump(self) -> bool:
        """Whether the comment is a bump comment."""
        return self.kind.lower() == "bump"

    @property
    def is_service_item(self) -> bool:
        """Whether the comment targets another supported work-item service."""
        return self.kind.lower() in _SERVICE_KINDS

    @property
    def bol(self) -> Date:
        """The Beginning of Life date for the versioned project."""
        return lifecycle_dates[self.versioned][self.version][0]

    @property
    def eol(self) -> Date | None:
        """The End of Life date for the versioned project."""
        return lifecycle_dates[self.versioned][self.version][1]

    @property
    def comment(self) -> str:
        """The comment without the prefix."""
        return self.raw.removeprefix(self.prefix).removesuffix(self.suffix)

    def _service_item(self, service_urls: Mapping[str, str] | None = None) -> _WorkItem:
        return _fetch_work_item(
            self.kind,
            self.version,
            self.file,
            service_urls=service_urls,
        )

    def check(
        self,
        *,
        bump: str | None = None,
        eol_within: TimeDelta | None = None,
        bol_within: TimeDelta | None = None,
        service_urls: Mapping[str, str] | None = None,
    ) -> bool:
        """Check the comment.

        Parameters:
            bump: The next version of the project.
            eol_within: The time delta to start warning before the End of Life of a versioned project.
            bol_within: The time delta to start warning before the Beginning of Life of a versioned project.
            service_urls: Optional API URL overrides keyed by service name.

        Returns:
            True when there is nothing to do, False otherwise.
        """
        msg_location = f"{self.file}:{self.lineno}:"
        if self.is_eol:
            try:
                eol = self.eol
            except KeyError:
                # Unknown version, skip.
                return True
            if eol is None:
                # No EOL date has been scheduled, skip.
                return True
            if eol_within and _within(eol_within, eol):
                delta = f"since {eol}" if _past(eol) else f"in ~{naturaldelta(_delta(eol))}"
                _logger.warning(f"{msg_location} {delta} {self.comment}")
            elif _within(TimeDelta(days=0), eol):
                _logger.error(f"{msg_location} since {eol} {self.comment}")
            else:
                return True
        elif self.is_bol:
            try:
                bol = self.bol
            except KeyError:
                # Unknown version, skip.
                return True
            if bol_within and _within(bol_within, bol):
                delta = f"since {bol}" if _past(bol) else f"in ~{naturaldelta(_delta(bol))}"
                _logger.warning(f"{msg_location} {delta} {self.comment}")
            elif _within(TimeDelta(days=0), bol):
                _logger.error(f"{msg_location} since {bol} {self.comment}")
            else:
                return True
        elif self.is_service_item:
            item = self._service_item(service_urls)
            if item.completed:
                _logger.error(
                    f"{msg_location} {item.service} {item.noun} {item.reference} was {item.completion}: {self.comment}",
                )
            elif item.closed:
                _logger.warning(
                    f"{msg_location} {item.service} {item.noun} {item.reference} {item.rejection}: {self.comment}",
                )
            else:
                return True
        elif self.is_bump and bump and Version(bump) >= Version(self.version):
            _logger.error(f"{msg_location} version {self.version} >= {self.comment}")
        else:
            return True
        return False

    def fix(
        self,
        buffer: list[str] | None = None,
        *,
        bump: str | None = None,
        eol_within: TimeDelta | None = None,
        bol_within: TimeDelta | None = None,
        service_urls: Mapping[str, str] | None = None,
    ) -> bool:
        """Fix the comment and code below it.

        Parameters:
            buffer: The buffer to fix. If not provided, read from and write to the file.
            bump: The next version of the project.
            eol_within: The time delta to start fixing before the End of Life of a versioned project.
            bol_within: The time delta to start fixing before the Beginning of Life of a versioned project.
            service_urls: Optional API URL overrides keyed by service name.

        Returns:
            Whether the comment was fixed.
        """
        write = buffer is None
        buffer = buffer or self.file.read_text(encoding="utf8").splitlines(keepends=True)

        # Check if the fix should be applied.
        due = False
        try:
            if self.is_eol and (eol := self.eol) is not None:
                due = (eol_within is not None and _within(eol_within, eol)) or _within(
                    TimeDelta(),
                    eol,
                )
            elif self.is_bol:
                bol = self.bol
                due = (bol_within is not None and _within(bol_within, bol)) or _within(
                    TimeDelta(),
                    bol,
                )
        except KeyError:
            # Unknown version, skip.
            pass
        if not due and self.is_bump and bump:
            due = Version(bump) >= Version(self.version)
        if not due and self.is_service_item:
            due = self._service_item(service_urls).completed

        if due:
            # Start at the commnent line, immediately remove it.
            start = self.lineno - 1
            del buffer[start]

            if self.remove:
                start, end = _scope_range(self.remove, buffer, start)
                del buffer[start:end]
                if write and self.remove == "file":
                    self.file.unlink()

            elif self.replace:
                # Line numbers/ranges are relative to block starts, absolute for the "file" scope.
                start, end = _scope_range(self.replace, buffer, start)
                if self.line:
                    replacement = [buffer[start + self.line - 1]]
                elif self.lines:
                    replacement = [buffer[start + line] for line in self.lines]
                elif self.string:
                    replacement = [self.string + "\n"]
                else:
                    raise RuntimeError("No replacement specified")
                replacement = _reindent(replacement, _indent(buffer[start]))
                buffer[start:end] = replacement

            elif self.within:
                # Line numbers/ranges are relative to block starts, absolute for the "file" scope.
                start, end = _scope_range(self.within, buffer, start)
                block = buffer[start:end]
                if self.regex:
                    pattern1: Pattern = re.compile(self.pattern1)  # ty: ignore[no-matching-overload]
                    replacement = [pattern1.sub(self.pattern2, line) for line in block]
                else:
                    replacement = [line.replace(self.pattern1, self.pattern2) for line in block]  # ty: ignore[no-matching-overload]
                replacement = _reindent(replacement, _indent(buffer[start]))
                buffer[start:end] = replacement

            if write and buffer:
                self.file.write_text("".join(buffer))

            return True
        return False


COMMENT_PREFIXES: set[str] = {
    r"\#\ ",  # Nim, Perl, PHP, Python, R, Ruby, shell, YAML
    r"//\ ",  # C, C++, Go, Java, Javascript, Rust, Swift
    r"--\ ",  # Haskell, Lua, SQL
    r";",  # Lisp, Scheme
    r"%\ ",  # MATLAB
    r"'\ ?",  # VBA
    r"/\*\ ",  # C, C++, Java, Javascript, CSS
    r"<!--\ ",  # HTML, Markdown, XML
    r"\{\#-?\ ",  # Jinja
    r"\(\*\ ",  # OCaml
}
"""The supported comment prefixes."""

_PATTERN_PREFIX = rf"^(?P<prefix>\s*(?:{'|'.join(sorted(COMMENT_PREFIXES))})PREFIX:\ )"
_PATTERN_SUFFIX = r"(?P<suffix>\.?.*)$"
_VERSIONED_PATTERN = "|".join(re.escape(alias) for alias in sorted(_VERSIONED_ALIASES, key=len, reverse=True))
_LIFECYCLE_KIND_PATTERN = "|".join(
    re.escape(spelling)
    for spelling in sorted(
        (spelling for kind in ("bol", "eol") for spelling in _KIND_SPELLINGS[kind]),
        key=len,
        reverse=True,
    )
)
_OTHER_KIND_PATTERN = "|".join(
    re.escape(spelling)
    for spelling in sorted(
        (
            spelling
            for kind, spellings in _KIND_SPELLINGS.items()
            if kind not in {"bol", "eol"}
            for spelling in spellings
        ),
        key=len,
        reverse=True,
    )
)

COMMENT_PATTERN: str = rf"""
    (?P<kind>(?P<lifecycle>{_LIFECYCLE_KIND_PATTERN})|{_OTHER_KIND_PATTERN})\ (?(lifecycle)(?:(?P<versioned>{_VERSIONED_PATTERN})\ )?)(?P<version>.+?):\ (?:
        remove\ (?P<remove>block|file|line)
        |
        replace\ (?P<replace>block|file|line)\ with\ (?:
            line\ (?P<line>\d+)
            |
            lines\ (?P<lines>[\d, -]+)
            |
            `(?P<string>.+?)`
        )
        |
        (?P<regex>regex-)?replace\ `(?P<pattern1>.+?)`\ with\ `(?P<pattern2>.*?)`\ within\ (?P<within>block|file|line)
    )
"""
"""The Yore comment pattern, as a regular expression."""


@cache
def get_pattern(prefix: str = DEFAULT_PREFIX) -> Pattern:
    """Get the Yore comment pattern with a specific prefix.

    Parameters:
        prefix: The prefix to use in the pattern.

    Returns:
        The Yore comment pattern.
    """
    return re.compile(
        _PATTERN_PREFIX.replace("PREFIX", prefix) + COMMENT_PATTERN + _PATTERN_SUFFIX,
        re.VERBOSE | re.IGNORECASE,
    )


@cache
def _get_prematching_pattern(prefix: str = DEFAULT_PREFIX) -> Pattern:
    return re.compile(_PATTERN_PREFIX.replace("PREFIX", prefix), re.VERBOSE | re.IGNORECASE)


def yield_files(directory: Path, exclude: list[str] | None = None) -> Iterator[Path]:
    """Yield all files in a directory."""
    exclude = DEFAULT_EXCLUDE if exclude is None else exclude
    _logger.debug(f"{directory}: scanning...")
    try:
        git_files = subprocess.run(
            ["git", "ls-files", "-z"],  # noqa: S607
            capture_output=True,
            cwd=directory,
            text=True,
            check=False,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        for path in directory.iterdir():
            if path.is_file():
                yield path
            elif path.is_dir() and not any(path.match(pattern) for pattern in exclude):
                yield from yield_files(path, exclude=exclude)
    else:
        for filepath in git_files.strip("\0").split("\0"):
            yield directory / filepath


def yield_buffer_comments(file: Path, lines: list[str], *, prefix: str = DEFAULT_PREFIX) -> Iterator[YoreComment]:
    """Yield all Yore comments in a buffer.

    Parameters:
        file: The file to check.
        lines: The buffer to check (pre-read lines).
        prefix: The prefix to look for in the comments.

    Yields:
        Yore comments.
    """
    prepattern = _get_prematching_pattern(prefix)
    pattern = get_pattern(prefix)
    inferred = _infer_versioned(file)
    for lineno, line in enumerate(lines, 1):
        if prepattern.match(line):
            if match := pattern.match(line):
                yield _match_to_comment(match, file, lineno, inferred)
            else:
                _logger.error(f"{file}:{lineno}: invalid Yore comment")


def yield_file_comments(file: Path, *, prefix: str = DEFAULT_PREFIX) -> Iterator[YoreComment]:
    """Yield all Yore comments in a file.

    Parameters:
        file: The file to check.
        prefix: The prefix to look for in the comments.

    Yields:
        Yore comments.
    """
    try:
        lines = file.read_text(encoding="utf8").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    yield from yield_buffer_comments(file, lines, prefix=prefix)


def yield_directory_comments(directory: Path, *, prefix: str = DEFAULT_PREFIX) -> Iterator[YoreComment]:
    """Yield all Yore comments in a directory.

    Parameters:
        directory: The directory to check.
        prefix: The prefix to look for in the comments.

    Yields:
        Yore comments.
    """
    for file in yield_files(directory):
        yield from yield_file_comments(file, prefix=prefix)


def yield_path_comments(path: Path, *, prefix: str = DEFAULT_PREFIX) -> Iterator[YoreComment]:
    """Yield all Yore comments in a file or directory.

    Parameters:
        path: The file or directory to check.
        prefix: The prefix to look for in the comments.

    Yields:
        Yore comments.
    """
    if path.is_dir():
        yield from yield_directory_comments(path, prefix=prefix)
    else:
        yield from yield_file_comments(path, prefix=prefix)


_ReleaseDates = tuple[Date, Date | None]


class _LazyDates:
    def __init__(self) -> None:
        self._dates: dict[str, _ReleaseDates] = {}
        self._fetched = False

    def __getitem__(self, version: str) -> _ReleaseDates:
        if not self._dates and not self._fetched:
            self._fetch()
            self._fetched = True
        return self._dates[version]

    def _fetch(self) -> None:
        raise NotImplementedError


class _LazyPythonDates(_LazyDates):
    EOL_DATA_URL = "https://peps.python.org/api/release-cycle.json"

    @staticmethod
    def _to_date(date: str) -> Date:
        parts = [int(part) for part in date.split("-")]
        if len(parts) == 2:  # noqa: PLR2004
            # Without a day, assume date to be the first of the next month.
            year, month = parts
            if month == 12:  # noqa: PLR2004
                month = 1
                year += 1
            else:
                month += 1
            day = 1
        else:
            year, month, day = parts
        return Date(year, month, day)

    def _fetch(self) -> None:
        data = json.loads(urlopen(self.EOL_DATA_URL, timeout=3).read())  # noqa: S310
        dates: dict[str, _ReleaseDates] = {}
        for version, info in data.items():
            bol_date = self._to_date(info["first_release"])
            eol_date = self._to_date(info["end_of_life"])
            dates[version] = (bol_date, eol_date)
        self._dates.update(dates)


python_dates = _LazyPythonDates()
"""A dictionary of Python versions and their Beginning/End of Life dates."""


lifecycle_dates: dict[Versioned, _LazyDates] = {
    "python": python_dates,
}
"""The date providers for each supported versioned project."""
