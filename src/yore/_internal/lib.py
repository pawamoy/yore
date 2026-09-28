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
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import date as Date  # noqa: N812
from datetime import datetime as DateTime  # noqa: N812
from datetime import timedelta as TimeDelta  # noqa: N812
from datetime import timezone as TimeZone  # noqa: N812
from functools import cache
from re import Pattern
from typing import TYPE_CHECKING, Literal, cast
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

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
    "fji",
    "fjp",
    "ghi",
    "ghp",
    "gli",
    "glm",
    "rdi",
    "rdp",
]
"""The supported kinds of Yore comments."""

_KIND_SPELLINGS: dict[YoreKind, tuple[str, ...]] = {
    "bol": ("bol",),
    "bump": ("bump",),
    "eol": ("eol",),
    "fji": ("fji", "fj issue", "forgejo issue"),
    "fjp": ("fjp", "fj pr", "forgejo pr", "fj pull request", "forgejo pull request"),
    "ghi": ("ghi", "gh issue", "github issue"),
    "ghp": ("ghp", "gh pr", "github pr", "gh pull request", "github pull request"),
    "gli": ("gli", "gl issue", "gitlab issue"),
    "glm": ("glm", "gl mr", "gitlab mr", "gl merge request", "gitlab merge request"),
    "rdi": ("rdi", "rd issue", "rad issue", "radicle issue"),
    "rdp": ("rdp", "rd patch", "rad patch", "radicle patch"),
}
"""Accepted case-insensitive spellings for each canonical Yore kind."""

_KIND_ALIASES: dict[str, YoreKind] = {
    spelling: kind for kind, spellings in _KIND_SPELLINGS.items() for spelling in spellings
}

_GitHubKind = Literal["ghi", "ghp"]
_RadicleKind = Literal["rdi", "rdp"]

Versioned = Literal["python", "rust"]
"""The versioned projects supported by lifecycle comments."""

_VERSIONED_ALIASES: dict[str, Versioned] = {
    "python": "python",
    "rust": "rust",
}

_FILENAME_VERSIONED: dict[str, Versioned] = {
    "cargo.lock": "rust",
    "cargo.toml": "rust",
}

_EXTENSION_VERSIONED: dict[str, Versioned] = {
    ".py": "python",
    ".pyi": "python",
    ".pyw": "python",
    ".pyx": "python",
    ".rs": "rust",
}

Scope = Literal["block", "file", "line"]
"""The scope of a comment."""

DEFAULT_PREFIX = "YORE"
"""The default prefix for Yore comments."""

DEFAULT_EXCLUDE = [".*", "__py*", "build", "dist", "target"]
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


_LineRange = tuple[int | None, int | None]


def _match_to_line_ranges(match: re.Match) -> list[_LineRange] | None:
    if matched_lines := match.group("lines"):
        line_ranges: list[_LineRange] = []
        matched_lines = re.sub(r" *- *", "-", matched_lines)
        matched_lines = matched_lines.replace(" ", ",").strip(",")
        matched_lines = re.sub(",+", ",", matched_lines)
        for line_range in matched_lines.split(","):
            if "-" in line_range:
                endpoints = line_range.split("-")
                if len(endpoints) != 2:  # noqa: PLR2004
                    raise ValueError(f"Invalid line range: {line_range}")
                start = int(endpoints[0]) if endpoints[0] else None
                end = int(endpoints[1]) if endpoints[1] else None
                if start is None and end is None:
                    raise ValueError("A line range must have at least one endpoint")
                line_ranges.append((start, end))
            else:
                line = int(line_range)
                line_ranges.append((line, line))
        return line_ranges
    return None


def _expand_line_ranges(
    line_ranges: list[_LineRange] | None,
    *,
    end: int | None = None,
) -> list[int] | None:
    if line_ranges is None:
        return None
    lines: list[int] = []
    for range_start, range_end in line_ranges:
        effective_end = range_end
        if effective_end is None:
            if end is None:
                return None
            effective_end = end
        lines.extend(
            range(1 if range_start is None else range_start, effective_end + 1),
        )
    return lines


def _match_to_lines(match: re.Match) -> list[int] | None:
    return _expand_line_ranges(_match_to_line_ranges(match))


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
    line_ranges = _match_to_line_ranges(match)
    comment = YoreComment(
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
        lines=_expand_line_ranges(line_ranges),
        string=match.group("string"),
        regex=bool(match.group("regex")),
        pattern1=match.group("pattern1"),
        pattern2=match.group("pattern2"),
        within=match.group("within"),
    )
    comment._line_ranges = line_ranges
    return comment


def _within(delta: TimeDelta, of: Date) -> bool:
    return DateTime.now(tz=TimeZone.utc).date() >= of - delta


def _delta(until: Date) -> TimeDelta:
    return until - DateTime.now(tz=TimeZone.utc).date()


def _past(date: Date) -> bool:
    return date <= DateTime.now(tz=TimeZone.utc).date()


_GITHUB_API_VERSION = "2022-11-28"
_GITHUB_REFERENCE_PATTERN = re.compile(
    r"(?:(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#)?#?(?P<number>[1-9]\d*)\Z",
)
_GITHUB_REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


@dataclass(frozen=True)
class _GitHubItem:
    repository: str
    number: int
    closed: bool
    completed: bool
    reason: str | None = None

    @property
    def reference(self) -> str:
        return f"{self.repository}#{self.number}"


def _repository_from_remote(remote: str) -> str:
    if "://" in remote:
        path = urlsplit(remote).path
    elif ":" in remote:
        _, _, path = remote.partition(":")
    else:
        path = remote
    parts = path.strip("/").removesuffix(".git").split("/")
    if len(parts) != 2:  # noqa: PLR2004
        raise ValueError(
            f"Cannot determine a GitHub repository from remote URL: {remote}",
        )
    repository = "/".join(parts)
    if not _GITHUB_REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError(f"Invalid GitHub repository from remote URL: {remote}")
    return repository


@cache
def _repository_from_git(directory: str) -> str:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],  # noqa: S607
        capture_output=True,
        cwd=directory,
        text=True,
        check=False,
    )
    if result.returncode or not result.stdout.strip():
        raise ValueError(
            "Cannot determine the GitHub repository: Git remote 'origin' is unavailable",
        )
    return _repository_from_remote(result.stdout.strip())


def _default_github_repository(file: Path) -> str:
    if repository := os.environ.get("GITHUB_REPOSITORY"):
        if not _GITHUB_REPOSITORY_PATTERN.fullmatch(repository):
            raise ValueError(f"Invalid GITHUB_REPOSITORY value: {repository}")
        return repository

    directory = file.resolve().parent
    while not directory.is_dir() and directory != directory.parent:
        directory = directory.parent
    return _repository_from_git(str(directory))


def _parse_github_reference(reference: str, file: Path) -> tuple[str, int]:
    if not (match := _GITHUB_REFERENCE_PATTERN.fullmatch(reference.strip())):
        raise ValueError(
            f"Invalid GitHub reference {reference!r}; expected NUMBER, #NUMBER, or OWNER/REPOSITORY#NUMBER",
        )
    repository = match.group("repository") or _default_github_repository(file)
    return repository, int(match.group("number"))


@cache
def _fetch_github_item(
    kind: _GitHubKind,
    repository: str,
    number: int,
    api_url: str,
) -> _GitHubItem:
    owner, repo = repository.split("/", 1)
    resource = "issues" if kind == "ghi" else "pulls"
    url = f"{api_url.rstrip('/')}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/{resource}/{number}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "yore",
        "X-GitHub-Api-Version": _GITHUB_API_VERSION,
    }
    if token := os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)  # noqa: S310
    data = json.loads(urlopen(request, timeout=3).read())  # noqa: S310

    if kind == "ghi":
        if "pull_request" in data:
            raise ValueError(
                f"GitHub reference {repository}#{number} is a pull request, not an issue",
            )
        closed = data["state"] == "closed"
        reason = data.get("state_reason")
        return _GitHubItem(
            repository=repository,
            number=number,
            closed=closed,
            completed=closed and reason == "completed",
            reason=reason,
        )

    merged = data.get("merged") is True or data.get("merged_at") is not None
    return _GitHubItem(
        repository=repository,
        number=number,
        closed=data["state"] == "closed",
        completed=merged,
    )


_RADICLE_RID_PATTERN = re.compile(r"rad:z[1-9A-HJ-NP-Za-km-z]+\Z")
_RADICLE_OBJECT_ID_PATTERN = r"[0-9A-Fa-f]{40}"
_RADICLE_REFERENCE_PATTERN = re.compile(
    rf"(?:(?P<repository>rad:z[1-9A-HJ-NP-Za-km-z]+)#)?"
    rf"#?(?P<object_id>{_RADICLE_OBJECT_ID_PATTERN})\Z",
)


@dataclass(frozen=True)
class _RadicleItem:
    repository: str
    object_id: str
    closed: bool
    completed: bool
    reason: str | None = None

    @property
    def reference(self) -> str:
        return f"{self.repository}#{self.object_id}"


def _repository_from_radicle_remote(remote: str) -> str:
    parsed = urlsplit(remote)
    if parsed.scheme != "rad" or not parsed.netloc:
        raise ValueError(
            f"Cannot determine a Radicle repository from remote URL: {remote}",
        )
    repository = f"rad:{parsed.netloc}"
    if not _RADICLE_RID_PATTERN.fullmatch(repository):
        raise ValueError(f"Invalid Radicle repository from remote URL: {remote}")
    return repository


@cache
def _repository_from_radicle_git(directory: str) -> str:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "rad"],  # noqa: S607
            capture_output=True,
            cwd=directory,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        pass
    else:
        if not result.returncode and result.stdout.strip():
            return _repository_from_radicle_remote(result.stdout.strip())

    try:
        result = subprocess.run(
            ["rad", "inspect", "--rid"],  # noqa: S607
            capture_output=True,
            cwd=directory,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        pass
    else:
        repository = result.stdout.strip()
        if not result.returncode and _RADICLE_RID_PATTERN.fullmatch(repository):
            return repository
    raise ValueError(
        "Cannot determine the Radicle repository: Git remote 'rad' and `rad inspect --rid` are unavailable",
    )


def _default_radicle_repository(file: Path) -> str:
    directory = file.resolve().parent
    while not directory.is_dir() and directory != directory.parent:
        directory = directory.parent
    return _repository_from_radicle_git(str(directory))


def _parse_radicle_reference(reference: str, file: Path) -> tuple[str, str]:
    if not (match := _RADICLE_REFERENCE_PATTERN.fullmatch(reference.strip())):
        raise ValueError(
            f"Invalid Radicle reference {reference!r}; expected OBJECT-ID or RADICLE-REPOSITORY#OBJECT-ID",
        )
    repository = match.group("repository") or _default_radicle_repository(file)
    if not _RADICLE_RID_PATTERN.fullmatch(repository):
        raise ValueError(f"Invalid Radicle repository: {repository}")
    return repository, match.group("object_id").lower()


@cache
def _fetch_radicle_item(
    kind: _RadicleKind,
    repository: str,
    object_id: str,
) -> _RadicleItem:
    noun = "issue" if kind == "rdi" else "patch"
    result = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "rad",
            "cob",
            "show",
            "--repo",
            repository,
            "--type",
            f"xyz.radicle.{noun}",
            "--object",
            object_id,
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise ValueError(  # noqa: TRY004
            f"Invalid Radicle {noun} response for {repository}#{object_id}",
        )
    state = data.get("state")
    if not isinstance(state, dict) or not isinstance(state.get("status"), str):
        raise ValueError(  # noqa: TRY004
            f"Invalid Radicle {noun} response for {repository}#{object_id}",
        )

    status = state["status"]
    if kind == "rdi":
        if status == "open":
            return _RadicleItem(repository, object_id, closed=False, completed=False)
        if status == "closed" and state.get("reason") in {"solved", "other"}:
            reason = state["reason"]
            return _RadicleItem(
                repository,
                object_id,
                closed=True,
                completed=reason == "solved",
                reason=reason,
            )
    elif status in {"draft", "open"}:
        return _RadicleItem(repository, object_id, closed=False, completed=False)
    elif status in {"archived", "merged"}:
        return _RadicleItem(
            repository,
            object_id,
            closed=True,
            completed=status == "merged",
            reason=status,
        )
    raise ValueError(
        f"Unsupported Radicle {noun} state {status!r} for {repository}#{object_id}",
    )


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
    _line_ranges: list[_LineRange] | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )
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
    def is_ghi(self) -> bool:
        """Whether the comment is a GitHub issue comment."""
        return self.kind.lower() == "ghi"

    @property
    def is_ghp(self) -> bool:
        """Whether the comment is a GitHub pull request comment."""
        return self.kind.lower() == "ghp"

    @property
    def is_rdi(self) -> bool:
        """Whether the comment is a Radicle issue comment."""
        return self.kind.lower() == "rdi"

    @property
    def is_rdp(self) -> bool:
        """Whether the comment is a Radicle patch comment."""
        return self.kind.lower() == "rdp"

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

    def _github_item(self) -> _GitHubItem:
        kind: _GitHubKind = "ghi" if self.is_ghi else "ghp"
        repository, number = _parse_github_reference(self.version, self.file)
        api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
        return _fetch_github_item(kind, repository, number, api_url)

    def _radicle_item(self) -> _RadicleItem:
        kind: _RadicleKind = "rdi" if self.is_rdi else "rdp"
        repository, object_id = _parse_radicle_reference(self.version, self.file)
        return _fetch_radicle_item(kind, repository, object_id)

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
        elif self.is_ghi or self.is_ghp:
            item = self._github_item()
            if item.completed:
                completed = "completed" if self.is_ghi else "merged"
                noun = "issue" if self.is_ghi else "pull request"
                _logger.error(
                    f"{msg_location} GitHub {noun} {item.reference} was {completed}: {self.comment}",
                )
            elif item.closed:
                if self.is_ghi:
                    reason = f" as {item.reason.replace('_', ' ')}" if item.reason else ""
                    _logger.warning(
                        f"{msg_location} GitHub issue {item.reference} was closed{reason}, not completed: {self.comment}",
                    )
                else:
                    _logger.warning(
                        f"{msg_location} GitHub pull request {item.reference} was closed without being merged: "
                        f"{self.comment}",
                    )
            else:
                return True
        elif self.is_rdi or self.is_rdp:
            item = self._radicle_item()
            if item.completed:
                completed = "solved" if self.is_rdi else "merged"
                noun = "issue" if self.is_rdi else "patch"
                _logger.error(
                    f"{msg_location} Radicle {noun} {item.reference} was {completed}: {self.comment}",
                )
            elif item.closed:
                if self.is_rdi:
                    _logger.warning(
                        f"{msg_location} Radicle issue {item.reference} was closed as other, not solved: "
                        f"{self.comment}",
                    )
                else:
                    _logger.warning(
                        f"{msg_location} Radicle patch {item.reference} was archived without being merged: "
                        f"{self.comment}",
                    )
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
        if not due and (self.is_ghi or self.is_ghp):
            due = self._github_item().completed
        if not due and (self.is_rdi or self.is_rdp):
            due = self._radicle_item().completed
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
                elif self._line_ranges is not None:
                    lines = _expand_line_ranges(self._line_ranges, end=end - start)
                    if lines is None:
                        raise RuntimeError("Could not resolve line ranges")
                    replacement = [buffer[start + line - 1] for line in lines]
                elif self.lines:
                    replacement = [buffer[start + line - 1] for line in self.lines]
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


class _LazyEndOfLifeDates(_LazyDates):
    EOL_DATA_URL = "https://endoflife.date/api/v1/products/{product}/"

    def __init__(self, product: str) -> None:
        super().__init__()
        self.product = product

    @property
    def data_url(self) -> str:
        return self.EOL_DATA_URL.format(product=self.product)

    def __getitem__(self, version: str) -> _ReleaseDates:
        if not self._dates and not self._fetched:
            self._fetch()
            self._fetched = True
        for candidate in self._version_candidates(version):
            if candidate in self._dates:
                return self._dates[candidate]
        raise KeyError(version)

    def _version_candidates(self, version: str) -> list[str]:
        candidates: list[str] = []

        def _add(candidate: str) -> None:
            if candidate and candidate not in candidates:
                candidates.append(candidate)

        normalized = version.strip()
        _add(normalized)
        if normalized.casefold().startswith("v"):
            normalized = normalized[1:]
            _add(normalized)
        if normalized.casefold().endswith(".x"):
            normalized = normalized[:-2]
            _add(normalized)
        while normalized.endswith(".0"):
            normalized = normalized[:-2]
            _add(normalized)
        return candidates

    def _fetch(self) -> None:
        data = json.loads(urlopen(self.data_url, timeout=3).read())  # noqa: S310
        dates: dict[str, _ReleaseDates] = {}
        for info in data["result"]["releases"]:
            bol_date = _LazyPythonDates._to_date(info["releaseDate"])
            eol_date = _LazyPythonDates._to_date(info["eolFrom"]) if info["eolFrom"] is not None else None
            dates[info["name"]] = (bol_date, eol_date)
        self._dates.update(dates)


rust_dates = _LazyEndOfLifeDates("rust")
"""A dictionary of Rust versions and their Beginning/End of Life dates."""

lifecycle_dates: dict[Versioned, _LazyDates] = {
    "python": python_dates,
    "rust": rust_dates,
}
"""The date providers for each supported versioned project."""
