"""Tests for the `cli` module."""

from __future__ import annotations

from datetime import timedelta
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
    assert lib._match_to_lines(match) == expected_lines  # type: ignore[arg-type]


def test_removing_file(tmp_path: Path) -> None:
    """Files are removed by "remove" comments and "file" scope."""
    file = tmp_path / "file1.py"
    file.write_text("# YORE: Bump 1: Remove file.")
    next(lib.yield_file_comments(file)).fix(bump="1")
    assert not file.exists()


def test_check_messages(caplog: pytest.LogCaptureFixture) -> None:
    """Verify contents of `check` messages."""
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
    "comment_syntax",
    ["# ", "// ", "-- ", ";", "% ", "'", "' ", "/* ", "<!-- ", "{# ", "{#- ", "(* "],
)
def test_supported_comment_syntax(comment_syntax: str) -> None:
    """Verify that supported comment syntax is correctly identified."""
    assert list(lib.yield_buffer_comments(file=Path("test.txt"), lines=[f"{comment_syntax}YORE: Bump 1: Remove line."]))


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
    ],
)
def test_supported_comments(comment: str) -> None:
    """Verify that supported comments are correctly identified."""
    assert list(lib.yield_buffer_comments(file=Path("test.txt"), lines=[f"# YORE: {comment}"]))
