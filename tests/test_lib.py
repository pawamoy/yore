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

from datetime import date, timedelta
from pathlib import Path

import pytest

from yore._internal import lib


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


def test_lifecycle_date_provider_registry() -> None:
    """Every supported ecosystem has its own registered date-provider cache."""
    assert lib.lifecycle_dates == {
        "python": lib.python_dates,
    }


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
    ],
)
def test_supported_comments(comment: str) -> None:
    """Verify that supported comments are correctly identified."""
    assert list(lib.yield_buffer_comments(file=Path("test.txt"), lines=[f"# YORE: {comment}"]))
