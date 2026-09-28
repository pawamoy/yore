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
    "when",
    [
        "GLI group/project#42",
        "GLM group/project!42",
    ],
)
def test_service_comment_kinds_are_parsed(when: str) -> None:
    """Supported external service kinds are part of the comment grammar."""
    parsed = list(lib.yield_buffer_comments(Path("test.py"), [f"# YORE: {when}: Remove line."]))

    assert len(parsed) == 1
    assert parsed[0].is_service_item


@pytest.mark.parametrize(
    ("service", "value", "expected"),
    [
        ("gitlab", "https://gitlab.example", "https://gitlab.example/api/v4"),
        ("gitlab", "https://gitlab.example/api/v4/", "https://gitlab.example/api/v4"),
    ],
)
def test_service_url_normalization(service: str, value: str, expected: str) -> None:
    """Instance origins and full API roots are both accepted."""
    assert wi._normalize_service_url(service, value) == expected


@pytest.mark.parametrize(
    "value",
    ["file:///tmp/api", "gitlab.example", "https://user:secret@gitlab.example"],
)
def test_service_url_validation(value: str) -> None:
    """Service URLs are HTTP origins without embedded credentials."""
    with pytest.raises(ValueError, match="Invalid gitlab URL"):
        wi._normalize_service_url("gitlab", value)


def test_service_url_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    """Python/CLI overrides beat environment values, which beat public defaults."""
    monkeypatch.setenv("GITLAB_API_URL", "https://environment.example")

    assert wi._service_url("gitlab", {"gitlab": "https://argument.example"}) == "https://argument.example/api/v4"
    assert wi._service_url("gitlab", None) == "https://environment.example/api/v4"

    monkeypatch.delenv("GITLAB_API_URL")

    assert wi._service_url("gitlab", None) == "https://gitlab.com/api/v4"


@pytest.mark.parametrize(
    ("service", "environment", "header", "expected"),
    [
        ("gitlab", {"GITLAB_TOKEN": "secret"}, "PRIVATE-TOKEN", "secret"),
        ("gitlab", {"CI_JOB_TOKEN": "job-secret"}, "JOB-TOKEN", "job-secret"),
    ],
)
def test_service_authentication_headers(
    service: str,
    environment: dict[str, str],
    header: str,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each adapter translates its conventional credentials into request headers."""
    for name in ("GITLAB_TOKEN", "PRIVATE_TOKEN", "CI_JOB_TOKEN", "FORGEJO_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    headers = wi._headers(service)

    assert headers[header] == expected


@pytest.mark.parametrize(
    ("service", "reference", "expected"),
    [
        ("gitlab", "group/project!42", ("group/project", 42)),
        ("gitlab", "!42", ("default/project", 42)),
        ("gitlab", "#42", ("default/project", 42)),
    ],
)
def test_repository_reference_markers(
    service: str,
    reference: str,
    expected: tuple[str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitLab accepts its native bang notation and short references."""
    monkeypatch.setenv("CI_PROJECT_PATH", "default/project")

    assert wi._parse_repository_reference(reference, Path("test.py"), service, nested=service == "gitlab") == expected


@pytest.mark.parametrize(
    ("kind", "state", "merged_at", "expected"),
    [
        ("glm", "opened", None, (False, False)),
        ("glm", "locked", None, (False, False)),
        ("glm", "closed", None, (True, False)),
        ("glm", "merged", "2026-01-01", (True, True)),
    ],
)
def test_gitlab_merge_request_states(
    kind: str,
    state: str,
    merged_at: str | None,
    expected: tuple[bool, bool],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitLab merge requests preserve merged versus merely closed."""
    seen: list[str] = []

    def _request(url: str, **_kwargs: object) -> dict[str, object]:
        seen.append(url)
        return {"state": state, "merged_at": merged_at}

    monkeypatch.setattr(wi, "_request_json", _request)
    item = wi._fetch_gitlab_item(
        kind,
        "group/sub/project",
        42,
        "https://gitlab.example/api/v4",
    )
    assert (item.closed, item.completed) == expected
    assert item.reference == "group/sub/project!42"
    assert seen == ["https://gitlab.example/api/v4/projects/group%2Fsub%2Fproject/merge_requests/42"]


@pytest.mark.parametrize(
    ("rest", "graphql_status", "expected"),
    [
        ({"state": "opened"}, None, (False, False, "was closed, not completed")),
        (
            {
                "state": "closed",
                "_links": {"closed_as_duplicate_of": "https://example/1"},
            },
            None,
            (True, False, "duplicate"),
        ),
        (
            {"state": "closed"},
            ("DONE", "Shipped"),
            (True, True, "was closed, not completed"),
        ),
        (
            {"state": "closed"},
            ("CANCELED", "Won't do"),
            (True, False, "Won't do"),
        ),
        (
            {"state": "closed", "labels": ["yore:completed"]},
            None,
            (True, True, "yore:completed"),
        ),
        (
            {"state": "closed", "labels": []},
            None,
            (True, False, "no completion status"),
        ),
    ],
)
def test_gitlab_issue_states(
    rest: dict[str, object],
    graphql_status: tuple[str, str] | None,
    expected: tuple[bool, bool, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitLab issues use status categories, duplicate data, then safe labels."""
    monkeypatch.setattr(wi, "_request_json", lambda *args, **kwargs: rest)
    monkeypatch.setattr(wi, "_gitlab_status", lambda *args: graphql_status)
    item = wi._fetch_gitlab_item("gli", "group/project", 42, "https://gitlab.example/api/v4")
    assert (item.closed, item.completed) == expected[:2]
    assert expected[2] in item.rejection


def test_conflicting_issue_labels_are_not_completed() -> None:
    """A rejection label wins when an issue has contradictory labels."""
    completed, reason = wi._label_completion(
        "forgejo",
        {"labels": ["yore:completed", "yore:rejected"]},
    )
    assert not completed
    assert reason == "yore:rejected"


@pytest.mark.parametrize(
    ("closed", "completed", "expected", "level"),
    [
        (False, False, True, None),
        (True, True, False, "ERROR"),
        (True, False, False, "WARNING"),
    ],
)
def test_service_comment_check_and_fix(
    *,
    closed: bool,
    completed: bool,
    expected: bool,
    level: str | None,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All adapters share diagnostics and transformation gating."""
    item = wi._WorkItem(
        "GitLab",
        "merge request",
        "group/project!42",
        closed,
        completed,
        completion="merged",
        rejection="was closed without being merged",
    )
    monkeypatch.setattr(lib, "_fetch_work_item", lambda *args, **kwargs: item)
    lines = [
        "# YORE: GLM group/project!42: Remove line.\n",
        "legacy()\n",
    ]
    parsed = next(lib.yield_buffer_comments(Path("test.py"), lines))

    with caplog.at_level(0):
        assert parsed.check() is expected
    assert (caplog.records[-1].levelname if caplog.records else None) == level
    assert parsed.fix(lines) is completed
    assert lines == (
        []
        if completed
        else [
            "# YORE: GLM group/project!42: Remove line.\n",
            "legacy()\n",
        ]
    )


@pytest.mark.parametrize("kind", ["azi", "azp", "bbp", "bzi", "grc", "gti", "gtp", "jri", "lni"])
def test_removed_work_item_kinds_are_unsupported(kind: str) -> None:
    """Removed provider tags are absent from the public comment grammar."""
    comments = list(lib.yield_buffer_comments(Path("test.py"), [f"# YORE: {kind} 42: Remove line."]))

    assert comments == []
