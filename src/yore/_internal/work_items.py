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
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_ServiceKind = str

_SERVICE_KINDS: frozenset[str] = frozenset()
"""Yore kinds handled by this module."""

DEFAULT_SERVICE_URLS: dict[str, str] = {}
"""Default API roots for providers that have a canonical public service."""

_SERVICE_ENV_URLS: dict[str, tuple[str, ...]] = {}

_REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\Z")
_REPOSITORY_REFERENCE_PATTERN = re.compile(
    r"(?:"
    r"(?P<repository>[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)"
    r"(?P<repository_marker>[#!])"
    r"|(?P<short_marker>[#!])?"
    r")"
    r"(?P<number>[1-9]\d*)\Z",
)


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
    suffixes: dict[str, str] = {}
    if (suffix := suffixes.get(service)) and not path.endswith(suffix):
        url += suffix
    return url


def _headers(_service: str) -> dict[str, str]:
    return {"Accept": "application/json", "User-Agent": "yore"}


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
    env_names: dict[str, tuple[str, ...]] = {}
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
        raise ValueError(f"Invalid {service} reference {reference!r}; expected {expected}")
    marker = match.group("repository_marker") or match.group("short_marker")
    if marker == "!":
        raise ValueError(f"Invalid {service} reference {reference!r}; only # references are supported")
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


def _fetch_work_item(
    kind: _ServiceKind | str,
    reference: str,  # noqa: ARG001
    file: Path,  # noqa: ARG001
    *,
    service_urls: Mapping[str, str] | None = None,  # noqa: ARG001
) -> _WorkItem:
    """Fetch and normalize a non-GitHub/Radicle work item."""
    normalized_kind = kind.casefold()
    if normalized_kind not in _SERVICE_KINDS:
        raise ValueError(f"Unsupported work-item kind: {kind}")

    raise ValueError(f"Unsupported work-item kind: {kind}")


def _clear_work_item_caches() -> None:
    """Clear all provider and repository-inference caches."""
    _origin_remote.cache_clear()
