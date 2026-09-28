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

"""Tests for the `cli` module."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from typing import TYPE_CHECKING

import pytest

from yore._internal import lib

if TYPE_CHECKING:
    from urllib.request import Request


class _Response:
    def __init__(self, data: object) -> None:
        self.data = data

    def read(self) -> bytes:
        return json.dumps(self.data).encode()


_RADICLE_RID = "rad:z4TEkvLebGGXYE3pgxHGu1GGpUM94"
_RADICLE_OBJECT_ID = "0123456789abcdef0123456789abcdef01234567"


@pytest.mark.parametrize(
    ("block", "expected_size"),
    [
        (["a", "b", "c"], 3),
        (["a", " b", "c"], 3),
        ([" a", " b", "c"], 2),
        (["a", "", "c"], 1),
        (["a", " b", "", "d"], 2),
        (["a", " b", "", " d"], 4),
        (["a", " b", "", " d", "e"], 5),
    ],
)
def test_block_size(block: list[str], expected_size: int) -> None:
    """Assert that `_block_size` returns the expected size."""
    assert lib._block_size(block, 0) == expected_size


def test_ecosystem_build_directories_are_excluded_by_default() -> None:
    """Rust build directories are excluded from recursive scans."""
    assert "target" in lib.DEFAULT_EXCLUDE


class _Match:
    def __init__(self, lines: str) -> None:
        self.lines = lines

    def group(self, name: str) -> str:  # noqa: ARG002
        return self.lines


@pytest.mark.parametrize(
    ("lines", "expected_lines"),
    [
        ("1", [1]),
        ("1 2", [1, 2]),
        ("1,2", [1, 2]),
        (",, ,1,, ,,,,  2 ,,", [1, 2]),
        ("1-3", [1, 2, 3]),
        ("1-2", [1, 2]),
        ("1-1", [1]),
        ("1-2, 3, 5-7", [1, 2, 3, 5, 6, 7]),
    ],
)
def test_match_to_lines(lines: str, expected_lines: list[int]) -> None:
    """Assert that `_match_to_lines` returns the expected lines."""
    match = _Match(lines)
    assert lib._match_to_lines(match) == expected_lines  # ty: ignore[invalid-argument-type]


def test_removing_file(tmp_path: Path) -> None:
    """Files are removed by "remove" comments and "file" scope."""
    file = tmp_path / "file1.py"
    file.write_text("# YORE: Bump 1: Remove file.", encoding="utf8")
    next(lib.yield_file_comments(file)).fix(bump="1")
    assert not file.exists()


def test_check_messages(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify contents of `check` messages."""
    monkeypatch.setattr(
        lib.python_dates,
        "_dates",
        {"3.8": (date(2019, 10, 14), date(2024, 10, 7))},
    )
    with caplog.at_level(0):
        lib.YoreComment(
            file=Path("test.txt"),
            lineno=1,
            raw="hello",
            prefix="YORE",
            suffix="",
            kind="eol",
            version="3.8",
            remove="line",
        ).check(eol_within=timedelta(days=0))
        message = caplog.messages[0]
    assert " since " in message
    assert " in " not in message


@pytest.mark.parametrize(
    ("file", "content", "expected"),
    [
        (Path("test.py"), [], "python"),
        (Path("test.PY"), [], "python"),
        (Path("test.rs"), [], "rust"),
        (Path("test.RS"), [], "rust"),
        (Path("Cargo.toml"), [], "rust"),
        (Path("Cargo.lock"), [], "rust"),
        (Path("test.js"), [], "python"),
        (Path("test.go"), [], "python"),
        (Path("manage.py"), ["from django.db import models"], "python"),
        (Path("migration.sql"), [], "python"),
        (Path("kustomization.yaml"), ["apiVersion: apps/v1", "kind: Deployment"], "python"),
        (Path("test.txt"), [], "python"),
    ],
)
def test_infer_versioned_project(
    file: Path,
    content: list[str],
    expected: lib.Versioned,
) -> None:
    """Lifecycle comments infer their versioned project from path and content."""
    parsed = next(
        lib.yield_buffer_comments(
            file=file,
            lines=[*content, "# YORE: EOL 1: Remove line."],
        ),
    )
    assert parsed.versioned == expected


@pytest.mark.parametrize(
    ("qualifier", "expected"),
    [
        ("Python", "python"),
        ("Rust", "rust"),
    ],
)
def test_explicit_versioned_project(qualifier: str, expected: lib.Versioned) -> None:
    """Explicit ecosystem qualifiers are case-insensitive and normalized."""
    parsed = next(
        lib.yield_buffer_comments(
            file=Path("test.txt"),
            lines=[f"# YORE: EOL {qualifier} 1: Remove line."],
        ),
    )
    assert parsed.versioned == expected


def test_explicit_versioned_project_overrides_inference() -> None:
    """An explicit qualifier takes precedence over the inferred ecosystem."""
    parsed = next(
        lib.yield_buffer_comments(
            file=Path("test.rs"),
            lines=["// YORE: EOL Python 3.8: Remove line."],
        ),
    )
    assert parsed.versioned == "python"


@pytest.mark.parametrize("kind", ["GHI", "GHP"])
def test_github_repository_owner_is_not_an_ecosystem_qualifier(kind: str) -> None:
    """GitHub repository owners can have the same name as an ecosystem."""
    parsed = next(
        lib.yield_buffer_comments(
            file=Path("test.py"),
            lines=[f"# YORE: {kind} rust/project#42: Remove line."],
        ),
    )
    assert parsed.version == "rust/project#42"


@pytest.mark.parametrize(
    "remote",
    [
        "git@github.com:octocat/example.git",
        "https://github.com/octocat/example.git",
        "ssh://git@github.com/octocat/example.git",
        "git://github.com/octocat/example.git",
    ],
)
def test_repository_from_remote(remote: str) -> None:
    """Common GitHub remote URL forms resolve to an owner/repository pair."""
    assert lib._repository_from_remote(remote) == "octocat/example"


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("octocat/example#42", ("octocat/example", 42)),
        ("#42", ("default/project", 42)),
        ("42", ("default/project", 42)),
    ],
)
def test_parse_github_reference(
    reference: str,
    expected: tuple[str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub references support explicit and current-repository forms."""
    monkeypatch.setenv("GITHUB_REPOSITORY", "default/project")
    assert lib._parse_github_reference(reference, Path("test.py")) == expected


def test_parse_github_reference_from_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """Short GitHub references fall back to the origin remote outside Actions."""
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(
        lib,
        "_repository_from_git",
        lambda directory: "octocat/example",
    )
    assert lib._parse_github_reference("#42", Path("test.py")) == (
        "octocat/example",
        42,
    )


@pytest.mark.parametrize(
    "reference",
    ["", "#0", "octocat/example", "https://github.com/octocat/example/issues/42"],
)
def test_invalid_github_reference(reference: str) -> None:
    """Invalid GitHub references fail with a useful error."""
    with pytest.raises(ValueError, match="Invalid GitHub reference"):
        lib._parse_github_reference(reference, Path("test.py"))


@pytest.mark.parametrize(
    ("kind", "resource", "payload", "expected"),
    [
        (
            "ghi",
            "issues",
            {"state": "open", "state_reason": None},
            (False, False, None),
        ),
        (
            "ghi",
            "issues",
            {"state": "closed", "state_reason": "completed"},
            (True, True, "completed"),
        ),
        (
            "ghi",
            "issues",
            {"state": "closed", "state_reason": "not_planned"},
            (True, False, "not_planned"),
        ),
        (
            "ghi",
            "issues",
            {"state": "closed", "state_reason": "duplicate"},
            (True, False, "duplicate"),
        ),
        (
            "ghi",
            "issues",
            {"state": "closed", "state_reason": None},
            (True, False, None),
        ),
        (
            "ghp",
            "pulls",
            {"state": "open", "merged": False, "merged_at": None},
            (False, False, None),
        ),
        (
            "ghp",
            "pulls",
            {"state": "closed", "merged": True, "merged_at": "2026-01-01"},
            (True, True, None),
        ),
        (
            "ghp",
            "pulls",
            {"state": "closed", "merged": False, "merged_at": "2026-01-01"},
            (True, True, None),
        ),
        (
            "ghp",
            "pulls",
            {"state": "closed", "merged": False, "merged_at": None},
            (True, False, None),
        ),
    ],
)
def test_fetch_github_item(
    kind: lib._GitHubKind,
    resource: str,
    payload: dict[str, object],
    expected: tuple[bool, bool, str | None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub API responses map to open, completed, and rejected states."""
    requests: list[Request] = []

    def _urlopen(request: Request, timeout: int) -> _Response:
        requests.append(request)
        assert request.full_url == f"https://github.example/api/v3/repos/octocat/example/{resource}/42"
        assert timeout == 3
        headers = {name.casefold(): value for name, value in request.header_items()}
        assert headers["accept"] == "application/vnd.github+json"
        assert headers["authorization"] == "Bearer test-token"
        assert headers["user-agent"] == "yore"
        assert headers["x-github-api-version"] == "2022-11-28"
        return _Response(payload)

    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_TOKEN", "ignored-token")
    monkeypatch.setattr(lib, "urlopen", _urlopen)
    lib._fetch_github_item.cache_clear()

    item = lib._fetch_github_item(
        kind,
        "octocat/example",
        42,
        "https://github.example/api/v3",
    )
    assert (item.closed, item.completed, item.reason) == expected
    assert (
        lib._fetch_github_item(
            kind,
            "octocat/example",
            42,
            "https://github.example/api/v3",
        )
        is item
    )
    assert len(requests) == 1


@pytest.mark.parametrize(
    ("github_token", "expected_authorization"),
    [("actions-token", "Bearer actions-token"), (None, None)],
)
def test_fetch_github_item_authentication_fallback(
    github_token: str | None,
    expected_authorization: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GITHUB_TOKEN is the fallback, while public requests can be anonymous."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    if github_token is None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    else:
        monkeypatch.setenv("GITHUB_TOKEN", github_token)

    def _urlopen(request: Request, timeout: int) -> _Response:
        headers = {name.casefold(): value for name, value in request.header_items()}
        assert timeout == 3
        assert headers.get("authorization") == expected_authorization
        return _Response({"state": "open", "state_reason": None})

    monkeypatch.setattr(lib, "urlopen", _urlopen)
    lib._fetch_github_item.cache_clear()
    lib._fetch_github_item("ghi", "octocat/example", 42, "https://api.github.com")


def test_github_issue_rejects_pull_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """GHI does not silently treat a pull request as an issue."""
    monkeypatch.setattr(
        lib,
        "urlopen",
        lambda request, timeout: _Response(
            {"state": "closed", "state_reason": "completed", "pull_request": {}},
        ),
    )
    lib._fetch_github_item.cache_clear()
    with pytest.raises(ValueError, match="is a pull request, not an issue"):
        lib._fetch_github_item("ghi", "octocat/example", 42, "https://api.github.com")


@pytest.mark.parametrize(
    ("kind", "closed", "completed", "reason", "expected", "level", "message"),
    [
        ("GHI", False, False, None, True, None, None),
        (
            "GHI",
            True,
            True,
            "completed",
            False,
            "ERROR",
            "GitHub issue octocat/example#42 was completed",
        ),
        (
            "GHI",
            True,
            False,
            "not_planned",
            False,
            "WARNING",
            "was closed as not planned, not completed",
        ),
        ("GHI", True, False, None, False, "WARNING", "was closed, not completed"),
        ("GHP", False, False, None, True, None, None),
        (
            "GHP",
            True,
            True,
            None,
            False,
            "ERROR",
            "GitHub pull request octocat/example#42 was merged",
        ),
        ("GHP", True, False, None, False, "WARNING", "was closed without being merged"),
    ],
)
def test_check_github_comment(
    *,
    kind: str,
    closed: bool,
    completed: bool,
    reason: str | None,
    expected: bool,
    level: str | None,
    message: str | None,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checking GitHub comments distinguishes open, completed, and rejected work."""
    item = lib._GitHubItem("octocat/example", 42, closed, completed, reason)
    monkeypatch.setattr(lib, "_fetch_github_item", lambda *args: item)
    parsed = next(
        lib.yield_buffer_comments(
            file=Path("test.py"),
            lines=[f"# YORE: {kind} octocat/example#42: Remove line."],
        ),
    )

    with caplog.at_level(0):
        assert parsed.check() is expected
    if level is None:
        assert not caplog.records
    else:
        assert message is not None
        assert caplog.records[-1].levelname == level
        assert message in caplog.messages[-1]


@pytest.mark.parametrize(
    ("kind", "closed", "completed", "expected"),
    [
        ("GHI", True, True, True),
        ("GHI", True, False, False),
        ("GHP", True, True, True),
        ("GHP", True, False, False),
    ],
)
def test_fix_github_comment(
    kind: str,
    closed: bool,
    completed: bool,
    expected: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only completed issues and merged pull requests activate transformations."""
    item = lib._GitHubItem("octocat/example", 42, closed, completed)
    monkeypatch.setattr(lib, "_fetch_github_item", lambda *args: item)
    lines = [f"# YORE: {kind} octocat/example#42: Remove line.\n", "legacy()\n"]
    parsed = next(lib.yield_buffer_comments(file=Path("test.py"), lines=lines))

    assert parsed.fix(lines) is expected
    assert lines == ([] if expected else [f"# YORE: {kind} octocat/example#42: Remove line.\n", "legacy()\n"])


@pytest.mark.parametrize(
    "remote",
    [
        "rad://z4TEkvLebGGXYE3pgxHGu1GGpUM94",
        "rad://z4TEkvLebGGXYE3pgxHGu1GGpUM94/z6MkkPv9fC13uHwdqd3V6sfL4YH7HUaA1",
    ],
)
def test_repository_from_radicle_remote(remote: str) -> None:
    """Radicle fetch and push remote URLs resolve to their repository ID."""
    assert lib._repository_from_radicle_remote(remote) == _RADICLE_RID


@pytest.mark.parametrize(
    "remote",
    ["https://seed.example/rad:z123.git", "rad://invalid0rid", "rad:"],
)
def test_invalid_radicle_remote(remote: str) -> None:
    """Non-Radicle and malformed remotes cannot identify a repository."""
    with pytest.raises(ValueError, match="Radicle repository"):
        lib._repository_from_radicle_remote(remote)


def test_repository_from_radicle_git_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    """The conventional Git remote is preferred for current-repository inference."""
    calls: list[list[str]] = []

    def _run(args: list[str], **kwargs: object) -> object:  # noqa: ARG001
        calls.append(args)
        return type(
            "Result",
            (),
            {"returncode": 0, "stdout": f"rad://{_RADICLE_RID.removeprefix('rad:')}\n"},
        )()

    monkeypatch.setattr(lib.subprocess, "run", _run)
    lib._repository_from_radicle_git.cache_clear()

    assert lib._repository_from_radicle_git("/project") == _RADICLE_RID
    assert calls == [["git", "remote", "get-url", "rad"]]


def test_repository_from_radicle_inspect(monkeypatch: pytest.MonkeyPatch) -> None:
    """Radicle inspection is the fallback when the Git remote is unavailable."""
    calls: list[list[str]] = []

    def _run(args: list[str], **kwargs: object) -> object:  # noqa: ARG001
        calls.append(args)
        if args[0] == "git":
            return type("Result", (), {"returncode": 2, "stdout": ""})()
        return type("Result", (), {"returncode": 0, "stdout": f"{_RADICLE_RID}\n"})()

    monkeypatch.setattr(lib.subprocess, "run", _run)
    lib._repository_from_radicle_git.cache_clear()

    assert lib._repository_from_radicle_git("/project") == _RADICLE_RID
    assert calls == [["git", "remote", "get-url", "rad"], ["rad", "inspect", "--rid"]]


def test_repository_from_radicle_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing Git and Radicle commands produce a domain-specific error."""

    def _run(*_args: object, **_kwargs: object) -> object:
        raise FileNotFoundError

    monkeypatch.setattr(lib.subprocess, "run", _run)
    lib._repository_from_radicle_git.cache_clear()
    with pytest.raises(ValueError, match="Cannot determine the Radicle repository"):
        lib._repository_from_radicle_git("/project")


@pytest.mark.parametrize(
    ("reference", "expected_repository"),
    [
        (f"{_RADICLE_RID}#{_RADICLE_OBJECT_ID}", _RADICLE_RID),
        (_RADICLE_OBJECT_ID.upper(), _RADICLE_RID),
        (f"#{_RADICLE_OBJECT_ID}", _RADICLE_RID),
    ],
)
def test_parse_radicle_reference(
    reference: str,
    expected_repository: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Radicle references support explicit repositories and current-repository forms."""
    monkeypatch.setattr(
        lib,
        "_repository_from_radicle_git",
        lambda directory: _RADICLE_RID,
    )
    assert lib._parse_radicle_reference(reference, Path("test.py")) == (
        expected_repository,
        _RADICLE_OBJECT_ID,
    )


@pytest.mark.parametrize(
    "reference",
    [
        "",
        "0123456",
        f"rad:invalid0rid#{_RADICLE_OBJECT_ID}",
        f"https://seed.example/{_RADICLE_RID}#{_RADICLE_OBJECT_ID}",
        f"heartwood#{_RADICLE_OBJECT_ID}",
    ],
)
def test_invalid_radicle_reference(reference: str) -> None:
    """Invalid Radicle references fail before invoking the CLI."""
    with pytest.raises(ValueError, match="Invalid Radicle reference"):
        lib._parse_radicle_reference(reference, Path("test.py"))


@pytest.mark.parametrize("kind", ["RDI", "RDP"])
def test_parse_radicle_comment_with_explicit_rid(kind: str) -> None:
    """The trigger separator remains unambiguous when a reference contains `rad:`."""
    parsed = next(
        lib.yield_buffer_comments(
            file=Path("test.py"),
            lines=[f"# YORE: {kind} {_RADICLE_RID}#{_RADICLE_OBJECT_ID}: Remove line."],
        ),
    )
    assert parsed.version == f"{_RADICLE_RID}#{_RADICLE_OBJECT_ID}"


@pytest.mark.parametrize(
    ("kind", "state", "expected"),
    [
        ("rdi", {"status": "open"}, (False, False, None)),
        ("rdi", {"status": "closed", "reason": "solved"}, (True, True, "solved")),
        ("rdi", {"status": "closed", "reason": "other"}, (True, False, "other")),
        ("rdp", {"status": "draft"}, (False, False, None)),
        ("rdp", {"status": "open"}, (False, False, None)),
        ("rdp", {"status": "merged"}, (True, True, "merged")),
        ("rdp", {"status": "archived"}, (True, False, "archived")),
    ],
)
def test_fetch_radicle_item(
    kind: lib._RadicleKind,
    state: dict[str, str],
    expected: tuple[bool, bool, str | None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local COB JSON maps to active, completed, and rejected states."""
    calls: list[list[str]] = []

    def _run(args: list[str], **kwargs: object) -> CompletedProcess[str]:
        calls.append(args)
        assert kwargs == {"capture_output": True, "text": True, "check": True, "timeout": 10}
        return CompletedProcess(args, 0, json.dumps({"state": state}), "")

    monkeypatch.setattr(lib.subprocess, "run", _run)
    lib._fetch_radicle_item.cache_clear()

    item = lib._fetch_radicle_item(kind, _RADICLE_RID, _RADICLE_OBJECT_ID)

    noun = "issue" if kind == "rdi" else "patch"
    assert calls == [
        [
            "rad",
            "cob",
            "show",
            "--repo",
            _RADICLE_RID,
            "--type",
            f"xyz.radicle.{noun}",
            "--object",
            _RADICLE_OBJECT_ID,
            "--format",
            "json",
        ],
    ]
    assert (item.closed, item.completed, item.reason) == expected
    assert lib._fetch_radicle_item(kind, _RADICLE_RID, _RADICLE_OBJECT_ID) is item
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("kind", "state"),
    [
        ("rdi", {}),
        ("rdi", {"status": "closed", "reason": "unknown"}),
        ("rdp", {"status": "unknown"}),
    ],
)
def test_invalid_radicle_item_state(
    kind: lib._RadicleKind,
    state: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected COB states fail before Yore can apply a fix."""
    monkeypatch.setattr(
        lib.subprocess,
        "run",
        lambda args, **kwargs: CompletedProcess(args, 0, json.dumps({"state": state}), ""),
    )
    lib._fetch_radicle_item.cache_clear()

    with pytest.raises(ValueError, match="Radicle"):
        lib._fetch_radicle_item(kind, _RADICLE_RID, _RADICLE_OBJECT_ID)


def test_invalid_radicle_item_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-object COB response is rejected explicitly."""
    monkeypatch.setattr(
        lib.subprocess,
        "run",
        lambda args, **kwargs: CompletedProcess(args, 0, "[]", ""),
    )
    lib._fetch_radicle_item.cache_clear()

    with pytest.raises(ValueError, match="Invalid Radicle issue response"):
        lib._fetch_radicle_item("rdi", _RADICLE_RID, _RADICLE_OBJECT_ID)


def test_radicle_cli_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing or inaccessible local COB cannot silently appear active."""
    error = CalledProcessError(1, ["rad", "cob", "show"], stderr="object not found")

    def _run(args: list[str], **kwargs: object) -> CompletedProcess[str]:  # noqa: ARG001
        raise error

    monkeypatch.setattr(lib.subprocess, "run", _run)
    lib._fetch_radicle_item.cache_clear()

    with pytest.raises(CalledProcessError):
        lib._fetch_radicle_item("rdi", _RADICLE_RID, _RADICLE_OBJECT_ID)


@pytest.mark.parametrize(
    ("kind", "closed", "completed", "reason", "expected", "level", "message"),
    [
        ("RDI", False, False, None, True, None, None),
        ("RDI", True, True, "solved", False, "ERROR", "Radicle issue"),
        (
            "RDI",
            True,
            False,
            "other",
            False,
            "WARNING",
            "was closed as other, not solved",
        ),
        ("RDP", False, False, None, True, None, None),
        ("RDP", True, True, "merged", False, "ERROR", "Radicle patch"),
        (
            "RDP",
            True,
            False,
            "archived",
            False,
            "WARNING",
            "was archived without being merged",
        ),
    ],
)
def test_check_radicle_comment(
    *,
    kind: str,
    closed: bool,
    completed: bool,
    reason: str | None,
    expected: bool,
    level: str | None,
    message: str | None,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checking Radicle comments distinguishes active, completed, and rejected work."""
    item = lib._RadicleItem(_RADICLE_RID, _RADICLE_OBJECT_ID, closed, completed, reason)

    def _fetch(
        _kind: lib._RadicleKind,
        _repository: str,
        _object_id: str,
    ) -> lib._RadicleItem:
        return item

    monkeypatch.setattr(lib, "_fetch_radicle_item", _fetch)
    parsed = next(
        lib.yield_buffer_comments(
            file=Path("test.py"),
            lines=[f"# YORE: {kind} {_RADICLE_RID}#{_RADICLE_OBJECT_ID}: Remove line."],
        ),
    )

    with caplog.at_level(0):
        assert parsed.check() is expected
    if level is None:
        assert not caplog.records
    else:
        assert message is not None
        assert caplog.records[-1].levelname == level
        assert message in caplog.messages[-1]
        assert f"{_RADICLE_RID}#{_RADICLE_OBJECT_ID}" in caplog.messages[-1]


@pytest.mark.parametrize(
    ("kind", "completed", "expected"),
    [
        ("RDI", True, True),
        ("RDI", False, False),
        ("RDP", True, True),
        ("RDP", False, False),
    ],
)
def test_fix_radicle_comment(
    kind: str,
    completed: bool,
    expected: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only solved issues and merged patches activate transformations."""
    item = lib._RadicleItem(
        _RADICLE_RID,
        _RADICLE_OBJECT_ID,
        closed=True,
        completed=completed,
    )
    monkeypatch.setattr(lib, "_fetch_radicle_item", lambda *args: item)
    comment = f"# YORE: {kind} {_RADICLE_RID}#{_RADICLE_OBJECT_ID}: Remove line.\n"
    lines = [comment, "legacy()\n"]
    parsed = next(lib.yield_buffer_comments(file=Path("test.py"), lines=lines))

    assert parsed.fix(lines) is expected
    assert lines == ([] if expected else [comment, "legacy()\n"])


def test_python_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Python adapter loads its dedicated release-cycle feed."""

    class _Response:
        @staticmethod
        def read() -> bytes:
            return b'{"3.13":{"first_release":"2024-10-07","end_of_life":"2029-10"}}'

    dates = lib._LazyPythonDates()

    def _urlopen(url: str, timeout: int) -> _Response:
        assert url == "https://peps.python.org/api/release-cycle.json"
        assert timeout == 3
        return _Response()

    monkeypatch.setattr(lib, "urlopen", _urlopen)

    assert dates["3.13"] == (date(2024, 10, 7), date(2029, 11, 1))


def test_endoflife_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    """The generic adapter loads concrete and unscheduled lifecycle dates."""

    class _Response:
        @staticmethod
        def read() -> bytes:
            return (
                b'{"result":{"releases":['
                b'{"name":"1.26","releaseDate":"2026-02-10","eolFrom":"2027-02-01"},'
                b'{"name":"1.27","releaseDate":"2026-08-19","eolFrom":null}'
                b"]}}"
            )

    dates = lib._LazyEndOfLifeDates("rust")

    def _urlopen(url: str, timeout: int) -> _Response:
        assert url == "https://endoflife.date/api/v1/products/rust/"
        assert timeout == 3
        return _Response()

    monkeypatch.setattr(lib, "urlopen", _urlopen)

    assert dates["1.26"] == (date(2026, 2, 10), date(2027, 2, 1))
    assert dates["1.27.0"] == (date(2026, 8, 19), None)


@pytest.mark.parametrize(
    ("product", "stored", "requested"),
    [
        ("rust", "1.90", "1.90.0"),
        ("rust", "1.90", "v1.90"),
    ],
)
def test_endoflife_date_version_normalization(
    product: str,
    stored: str,
    requested: str,
) -> None:
    """Common ecosystem-specific version spellings resolve to release series."""
    dates = lib._LazyEndOfLifeDates(product)
    dates._dates[stored] = (date(2020, 1, 1), date(2021, 1, 1))
    assert dates[requested] == dates._dates[stored]


def test_lifecycle_date_provider_registry() -> None:
    """Every supported ecosystem has its own registered date-provider cache."""
    assert lib.lifecycle_dates == {
        "python": lib.python_dates,
        "rust": lib.rust_dates,
    }
    assert lib.rust_dates.data_url == "https://endoflife.date/api/v1/products/rust/"


@pytest.mark.parametrize(
    ("file", "comment", "expected"),
    [
        (Path("test.rs"), "EOL 1: Remove line.", "rust"),
    ],
)
def test_fix_versioned_comment(
    file: Path,
    comment: str,
    expected: lib.Versioned,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inferred lifecycle comments use the matching provider when fixing."""
    eol = None if comment.startswith("BOL") else date(2021, 1, 1)
    monkeypatch.setattr(
        lib.lifecycle_dates[expected],
        "_dates",
        {"1": (date(2020, 1, 1), eol)},
    )
    lines = [f"// YORE: {comment}\n", "old_api();\n"]
    parsed = next(lib.yield_buffer_comments(file=file, lines=lines))

    assert parsed.versioned == expected
    assert parsed.fix(lines)
    assert not lines


def test_unscheduled_or_unknown_eol_is_inactive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checks and fixes skip unscheduled and unknown ecosystem EOL dates."""
    monkeypatch.setattr(lib.rust_dates, "_dates", {"1.27": (date(2026, 8, 19), None)})

    for version in ("1.27", "unknown"):
        lines = [f"// YORE: EOL Rust {version}: Remove line.\n", "supported();\n"]
        parsed = next(lib.yield_buffer_comments(file=Path("test.rs"), lines=lines))

        assert parsed.check()
        assert not parsed.fix(lines)
        assert len(lines) == 2


@pytest.mark.parametrize(
    "comment_syntax",
    ["# ", "// ", "-- ", ";", "% ", "'", "' ", "/* ", "<!-- ", "{# ", "{#- ", "(* "],
)
def test_supported_comment_syntax(comment_syntax: str) -> None:
    """Verify that supported comment syntax is correctly identified."""
    assert list(lib.yield_buffer_comments(file=Path("test.txt"), lines=[f"{comment_syntax}YORE: Bump 1: Remove line."]))


@pytest.mark.parametrize(
    ("kind", "spellings"),
    [
        ("bol", ("bol",)),
        ("bump", ("bump",)),
        ("eol", ("eol",)),
        ("ghi", ("ghi", "gh issue", "github issue")),
        (
            "ghp",
            ("ghp", "gh pr", "github pr", "gh pull request", "github pull request"),
        ),
        ("gli", ("gli", "gl issue", "gitlab issue")),
        (
            "glm",
            ("glm", "gl mr", "gitlab mr", "gl merge request", "gitlab merge request"),
        ),
        ("rdi", ("rdi", "rd issue", "rad issue", "radicle issue")),
        ("rdp", ("rdp", "rd patch", "rad patch", "radicle patch")),
    ],
)
def test_kind_aliases(kind: lib.YoreKind, spellings: tuple[str, ...]) -> None:
    """Every documented trigger spelling parses to the same canonical kind."""
    assert lib._KIND_SPELLINGS[kind] == spellings

    for spelling in spellings:
        parsed = next(
            lib.yield_buffer_comments(
                file=Path("test.txt"),
                lines=[f"# YORE: {spelling} 1: Remove line."],
            ),
        )
        assert parsed.kind.casefold() == kind
        if spelling != kind:
            assert parsed.kind == kind


def test_kind_aliases_are_case_insensitive_and_preserve_compact_tag_spelling() -> None:
    """Readable aliases normalize while legacy compact tags retain their spelling."""
    readable = next(
        lib.yield_buffer_comments(
            file=Path("test.py"),
            lines=["# YORE: GitHub Issue octocat/example#42: Remove line."],
        ),
    )
    compact = next(
        lib.yield_buffer_comments(
            file=Path("test.py"),
            lines=["# YORE: GHI octocat/example#42: Remove line."],
        ),
    )

    assert readable.kind == "ghi"
    assert compact.kind == "GHI"


@pytest.mark.parametrize(
    "comment",
    [
        "Bump 1: Remove line.",
        "Bump 1: Remove block.",
        "Bump 1: Remove file.",
        "Bump 1: Replace `a` with `` within line.",
        "Bump 1: Replace `a` with `` within block.",
        "Bump 1: Replace `a` with `` within file.",
        "Bump 1: Regex-replace `a` with `` within line.",
        "Bump 1: Regex-replace `a` with `` within block.",
        "Bump 1: Regex-replace `a` with `` within file.",
        "Bump 1: Replace block with line 2.",
        "Bump 1: Replace file with line 2.",
        "Bump 1: Replace block with lines 2-10.",
        "Bump 1: Replace file with line 2-10.",
        "BOL 3.8: Remove line.",
        "EOL 3.8: Remove line.",
        "BOL Python 3.8: Remove line.",
        "EOL Rust 1.72: Remove line.",
        "GHI octocat/example#42: Remove line.",
        "GHP #42: Remove line.",
        f"RDI {_RADICLE_OBJECT_ID}: Remove line.",
        f"RDP {_RADICLE_RID}#{_RADICLE_OBJECT_ID}: Remove line.",
        "GLI group/project#42: Remove line.",
        "GLM group/project!42: Remove line.",
    ],
)
def test_supported_comments(comment: str) -> None:
    """Verify that supported comments are correctly identified."""
    assert list(lib.yield_buffer_comments(file=Path("test.txt"), lines=[f"# YORE: {comment}"]))
