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
import os
import re
import subprocess
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Literal, cast
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_ServiceKind = Literal["fji", "fjp", "gli", "glm"]

_SERVICE_KINDS: frozenset[str] = frozenset(
    {
        "fji",
        "fjp",
        "gli",
        "glm",
    },
)
"""Yore kinds handled by this module."""

DEFAULT_SERVICE_URLS: dict[str, str] = {
    "forgejo": "https://codeberg.org/api/v1",
    "gitlab": "https://gitlab.com/api/v4",
}
"""Default API roots for providers that have a canonical public service."""

_SERVICE_ENV_URLS: dict[str, tuple[str, ...]] = {
    "forgejo": ("FORGEJO_API_URL", "FORGEJO_SERVER_URL", "FORGEJO_URL"),
    "gitlab": ("GITLAB_API_URL", "CI_API_V4_URL", "GITLAB_URL"),
}

_REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\Z")
_REPOSITORY_REFERENCE_PATTERN = re.compile(
    r"(?:"
    r"(?P<repository>[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)"
    r"(?P<repository_marker>[#!])"
    r"|(?P<short_marker>[#!])?"
    r")"
    r"(?P<number>[1-9]\d*)\Z",
)
_GITLAB_STATUS_QUERY = """
query YoreWorkItemStatus($fullPath: ID!, $iid: String!) {
  workspace: namespace(fullPath: $fullPath) {
    workItem(iid: $iid) {
      widgets {
        ... on WorkItemWidgetStatus {
          status { name category }
        }
      }
    }
  }
}
""".strip()


@dataclass(frozen=True)
class _WorkItem:
    """A provider-neutral work item."""

    service: str
    noun: str
    reference: str
    closed: bool
    completed: bool
    completion: str = "completed"
    rejection: str = "was closed, not completed"


def _csv_env(name: str, default: str = "") -> set[str]:
    return {value.strip().casefold() for value in os.environ.get(name, default).split(",") if value.strip()}


def _service_url(
    service: str,
    service_urls: Mapping[str, str] | None,
) -> str:
    value = service_urls.get(service) if service_urls else None
    if not value:
        value = next(
            (env_value for name in _SERVICE_ENV_URLS[service] if (env_value := os.environ.get(name))),
            None,
        )
    if not value:
        value = DEFAULT_SERVICE_URLS.get(service)
    if not value:
        env_name = _SERVICE_ENV_URLS[service][0]
        raise ValueError(f"No {service} URL configured; set {env_name} or pass a service URL")
    return _normalize_service_url(service, value)


def _normalize_service_url(service: str, value: str) -> str:
    url = value.rstrip("/")
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Invalid {service} URL: {value}")

    path = parsed.path.rstrip("/")
    suffixes = {
        "forgejo": "/api/v1",
        "gitlab": "/api/v4",
    }
    if (suffix := suffixes.get(service)) and not path.endswith(suffix):
        url += suffix
    return url


def _headers(service: str) -> dict[str, str]:
    headers = {"Accept": "application/json", "User-Agent": "yore"}
    if service == "gitlab":
        if token := os.environ.get("GITLAB_TOKEN") or os.environ.get("PRIVATE_TOKEN"):
            headers["PRIVATE-TOKEN"] = token
        elif token := os.environ.get("CI_JOB_TOKEN"):
            headers["JOB-TOKEN"] = token
    elif service == "forgejo" and (token := os.environ.get("FORGEJO_TOKEN")):
        headers["Authorization"] = f"token {token}"
    return headers


def _request_json(
    url: str,
    *,
    headers: Mapping[str, str],
    body: object | None = None,
) -> dict[str, object]:
    data = None
    request_headers = dict(headers)
    if body is not None:
        data = json.dumps(body).encode()
        request_headers["Content-Type"] = "application/json"
    request = Request(url, headers=request_headers, data=data)  # noqa: S310
    raw = urlopen(request, timeout=3).read().decode()  # noqa: S310
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"Invalid {urlsplit(url).netloc} response")  # noqa: TRY004
    return parsed


def _file_directory(file: Path) -> str:
    directory = file.resolve().parent
    while not directory.is_dir() and directory != directory.parent:
        directory = directory.parent
    return str(directory)


@cache
def _origin_remote(directory: str) -> str:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],  # noqa: S607
        capture_output=True,
        cwd=directory,
        text=True,
        check=False,
    )
    if result.returncode or not result.stdout.strip():
        raise ValueError("Cannot infer a repository: Git remote 'origin' is unavailable")
    return result.stdout.strip()


def _remote_path(remote: str) -> list[str]:
    if "://" in remote:
        path = urlsplit(remote).path
    elif ":" in remote:
        _, _, path = remote.partition(":")
    else:
        path = remote
    return [part for part in path.strip("/").removesuffix(".git").split("/") if part]


def _default_repository(service: str, file: Path, *, nested: bool = False) -> str:
    env_names = {
        "forgejo": ("FORGEJO_REPOSITORY",),
        "gitlab": ("CI_PROJECT_PATH",),
    }
    for name in env_names[service]:
        if repository := os.environ.get(name):
            if not _REPOSITORY_PATTERN.fullmatch(repository):
                raise ValueError(f"Invalid {name} value: {repository}")
            return repository

    parts = _remote_path(_origin_remote(_file_directory(file)))
    if not nested and len(parts) >= 2:  # noqa: PLR2004
        parts = parts[-2:]
    repository = "/".join(parts)
    if not _REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError("Cannot infer a valid repository from the Git origin remote")
    return repository


def _parse_repository_reference(
    reference: str,
    file: Path,
    service: str,
    *,
    nested: bool = False,
) -> tuple[str, int]:
    if not (match := _REPOSITORY_REFERENCE_PATTERN.fullmatch(reference.strip())):
        expected = "NUMBER, #NUMBER, or REPOSITORY#NUMBER"
        if service == "gitlab":
            expected = "NUMBER, #NUMBER, !NUMBER, or REPOSITORY[#|!]NUMBER"
        raise ValueError(f"Invalid {service} reference {reference!r}; expected {expected}")
    marker = match.group("repository_marker") or match.group("short_marker")
    if marker == "!" and service != "gitlab":
        raise ValueError(f"Invalid {service} reference {reference!r}; only GitLab uses ! references")
    repository = match.group("repository") or _default_repository(service, file, nested=nested)
    if not nested and repository.count("/") != 1:
        raise ValueError(f"Invalid {service} repository: {repository}")
    return repository, int(match.group("number"))


def _label_names(data: Mapping[str, object]) -> set[str]:
    labels = data.get("labels", [])
    if not isinstance(labels, list):
        return set()
    names: set[str] = set()
    for label in labels:
        if isinstance(label, str):
            names.add(label.casefold())
        elif isinstance(label, dict):
            name = label.get("name")
            if isinstance(name, str):
                names.add(name.casefold())
    return names


def _label_completion(service: str, data: Mapping[str, object]) -> tuple[bool, str]:
    prefix = service.upper().replace("-", "_")
    completed = _csv_env(f"YORE_{prefix}_COMPLETED_LABELS", "yore:completed,yore/completed")
    rejected = _csv_env(
        f"YORE_{prefix}_REJECTED_LABELS",
        "yore:rejected,yore/rejected,wontfix,won't fix,duplicate,invalid",
    )
    labels = _label_names(data)
    if match := sorted(labels & rejected):
        return False, match[0]
    if match := sorted(labels & completed):
        return True, match[0]
    return False, "no completion status"


def _gitlab_graphql_url(api_url: str) -> str:
    return re.sub(r"/api/v4\Z", "/api/graphql", api_url)


def _gitlab_status(repository: str, number: int, api_url: str) -> tuple[str, str] | None:
    data = _request_json(
        _gitlab_graphql_url(api_url),
        headers=_headers("gitlab"),
        body={
            "query": _GITLAB_STATUS_QUERY,
            "variables": {"fullPath": repository, "iid": str(number)},
        },
    )
    root = data.get("data")
    if not isinstance(root, dict):
        return None
    workspace = root.get("workspace")
    if not isinstance(workspace, dict):
        return None
    work_item = workspace.get("workItem")
    if not isinstance(work_item, dict):
        return None
    widgets = work_item.get("widgets")
    if not isinstance(widgets, list):
        return None
    for widget in widgets:
        if not isinstance(widget, dict):
            continue
        status = widget.get("status")
        if not isinstance(status, dict):
            continue
        category = status.get("category")
        name = status.get("name")
        if isinstance(category, str) and isinstance(name, str):
            return category.upper(), name
    return None


@cache
def _fetch_gitlab_item(kind: Literal["gli", "glm"], repository: str, number: int, api_url: str) -> _WorkItem:
    resource = "issues" if kind == "gli" else "merge_requests"
    project = quote(repository, safe="")
    data = _request_json(
        f"{api_url}/projects/{project}/{resource}/{number}",
        headers=_headers("gitlab"),
    )
    state = data.get("state")
    if state not in {"opened", "closed", "merged", "locked"}:
        raise ValueError(f"Unsupported GitLab {resource[:-1]} state {state!r} for {repository}#{number}")
    marker = "#" if kind == "gli" else "!"
    reference = f"{repository}{marker}{number}"
    if kind == "glm":
        return _WorkItem(
            "GitLab",
            "merge request",
            reference,
            closed=state in {"closed", "merged"},
            completed=state == "merged" or data.get("merged_at") is not None,
            completion="merged",
            rejection="was closed without being merged",
        )

    if state != "closed":
        return _WorkItem(
            "GitLab",
            "issue",
            reference,
            closed=False,
            completed=False,
        )
    links = data.get("_links")
    if isinstance(links, dict) and links.get("closed_as_duplicate_of"):
        return _WorkItem(
            "GitLab",
            "issue",
            reference,
            closed=True,
            completed=False,
            rejection="was closed as duplicate, not completed",
        )
    if status := _gitlab_status(repository, number, api_url):
        category, name = status
        if category == "DONE":
            return _WorkItem(
                "GitLab",
                "issue",
                reference,
                closed=True,
                completed=True,
            )
        if category == "CANCELED":
            return _WorkItem(
                "GitLab",
                "issue",
                reference,
                closed=True,
                completed=False,
                rejection=f"was closed as {name}, not completed",
            )
    completed, reason = _label_completion("gitlab", data)
    return _WorkItem(
        "GitLab",
        "issue",
        reference,
        closed=True,
        completed=completed,
        rejection=f"was closed with {reason}, not completed",
    )


@cache
def _fetch_forge_item(
    service: Literal["forgejo"],
    kind: Literal["fji", "fjp"],
    repository: str,
    number: int,
    api_url: str,
) -> _WorkItem:
    owner, repo = repository.split("/", 1)
    data = _request_json(
        f"{api_url}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/issues/{number}",
        headers=_headers(service),
    )
    state = data.get("state")
    if state not in {"open", "closed"}:
        raise ValueError(f"Unsupported {service.title()} item state {state!r} for {repository}#{number}")
    pull_request = data.get("pull_request")
    is_pull = isinstance(pull_request, dict)
    wants_pull = kind == "fjp"
    if wants_pull != is_pull:
        expected = "pull request" if wants_pull else "issue"
        actual = "issue" if wants_pull else "pull request"
        article = "an" if actual == "issue" else "a"
        expected_article = "an" if expected == "issue" else "a"
        raise ValueError(
            f"{service.title()} reference {repository}#{number} is {article} {actual}, "
            f"not {expected_article} {expected}",
        )
    display = "Forgejo"
    reference = f"{repository}#{number}"
    if wants_pull:
        pull_data = cast("dict[str, object]", pull_request)
        merged = pull_data.get("merged") is True or pull_data.get("merged_at") is not None
        return _WorkItem(
            display,
            "pull request",
            reference,
            closed=state == "closed" or merged,
            completed=merged,
            completion="merged",
            rejection="was closed without being merged",
        )
    if state == "open":
        return _WorkItem(
            display,
            "issue",
            reference,
            closed=False,
            completed=False,
        )
    completed, reason = _label_completion(service, data)
    return _WorkItem(
        display,
        "issue",
        reference,
        closed=True,
        completed=completed,
        rejection=f"was closed with {reason}, not completed",
    )


def _fetch_work_item(
    kind: _ServiceKind | str,
    reference: str,
    file: Path,
    *,
    service_urls: Mapping[str, str] | None = None,
) -> _WorkItem:
    """Fetch and normalize a non-GitHub/Radicle work item."""
    normalized_kind = kind.casefold()
    if normalized_kind not in _SERVICE_KINDS:
        raise ValueError(f"Unsupported work-item kind: {kind}")

    if normalized_kind in {"gli", "glm"}:
        repository, number = _parse_repository_reference(reference, file, "gitlab", nested=True)
        return _fetch_gitlab_item(
            normalized_kind,
            repository,
            number,
            _service_url("gitlab", service_urls),
        )

    if normalized_kind in {"fji", "fjp"}:
        repository, number = _parse_repository_reference(reference, file, "forgejo")
        return _fetch_forge_item(
            "forgejo",
            normalized_kind,
            repository,
            number,
            _service_url("forgejo", service_urls),
        )

    raise ValueError(f"Unsupported work-item kind: {kind}")


def _clear_work_item_caches() -> None:
    """Clear all provider and repository-inference caches."""
    _origin_remote.cache_clear()
    _fetch_gitlab_item.cache_clear()
    _fetch_forge_item.cache_clear()
