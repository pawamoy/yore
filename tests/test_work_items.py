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

"""Tests for external work-item providers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from yore._internal import lib
from yore._internal import work_items as wi


class _Response:
    def __init__(self, data: object) -> None:
        self.data = json.dumps(data).encode()

    def read(self) -> bytes:
        return self.data


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    wi._clear_work_item_caches()


@pytest.mark.parametrize(
    "value",
    ["file:///tmp/api", "gitlab.example", "https://user:secret@gitlab.example"],
)
def test_service_url_validation(value: str) -> None:
    """Service URLs are HTTP origins without embedded credentials."""
    with pytest.raises(ValueError, match="Invalid gitlab URL"):
        wi._normalize_service_url("gitlab", value)


def test_conflicting_issue_labels_are_not_completed() -> None:
    """A rejection label wins when an issue has contradictory labels."""
    completed, reason = wi._label_completion(
        "forgejo",
        {"labels": ["yore:completed", "yore:rejected"]},
    )
    assert not completed
    assert reason == "yore:rejected"


@pytest.mark.parametrize("kind", ["azi", "azp", "bbp", "bzi", "grc", "gti", "gtp", "jri", "lni"])
def test_removed_work_item_kinds_are_unsupported(kind: str) -> None:
    """Removed provider tags are absent from the public comment grammar."""
    comments = list(lib.yield_buffer_comments(Path("test.py"), [f"# YORE: {kind} 42: Remove line."]))

    assert comments == []
