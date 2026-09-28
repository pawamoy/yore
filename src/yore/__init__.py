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

"""yore package.

Manage legacy code with comments.
"""

from __future__ import annotations

from yore._internal.cli import CommandCheck, CommandDiff, CommandFix, CommandMain, main
from yore._internal.config import Config, Unset, config_field
from yore._internal.lib import (
    COMMENT_PATTERN,
    COMMENT_PREFIXES,
    DEFAULT_EXCLUDE,
    DEFAULT_PREFIX,
    Scope,
    Versioned,
    YoreComment,
    YoreKind,
    get_pattern,
    lifecycle_dates,
    python_dates,
    rust_dates,
    yield_buffer_comments,
    yield_directory_comments,
    yield_file_comments,
    yield_files,
    yield_path_comments,
)
from yore._internal.work_items import DEFAULT_SERVICE_URLS

__all__: list[str] = [
    "COMMENT_PATTERN",
    "COMMENT_PREFIXES",
    "DEFAULT_EXCLUDE",
    "DEFAULT_PREFIX",
    "DEFAULT_SERVICE_URLS",
    "CommandCheck",
    "CommandDiff",
    "CommandFix",
    "CommandMain",
    "Config",
    "Scope",
    "Unset",
    "Versioned",
    "YoreComment",
    "YoreKind",
    "config_field",
    "get_pattern",
    "lifecycle_dates",
    "main",
    "python_dates",
    "rust_dates",
    "yield_buffer_comments",
    "yield_directory_comments",
    "yield_file_comments",
    "yield_files",
    "yield_path_comments",
]
