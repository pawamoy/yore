"""Tests for the `cli` module."""

from __future__ import annotations

import pytest

from yore import lib


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

    def group(self, name: str) -> str:
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
    assert lib._match_to_lines(match) == expected_lines
