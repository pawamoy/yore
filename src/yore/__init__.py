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
    YoreComment,
    YoreKind,
    get_pattern,
    python_dates,
    yield_buffer_comments,
    yield_directory_comments,
    yield_file_comments,
    yield_files,
    yield_path_comments,
)

__all__: list[str] = [
    "COMMENT_PATTERN",
    "COMMENT_PREFIXES",
    "DEFAULT_EXCLUDE",
    "DEFAULT_PREFIX",
    "CommandCheck",
    "CommandDiff",
    "CommandFix",
    "CommandMain",
    "Config",
    "Scope",
    "Unset",
    "YoreComment",
    "YoreKind",
    "config_field",
    "get_pattern",
    "main",
    "python_dates",
    "yield_buffer_comments",
    "yield_directory_comments",
    "yield_file_comments",
    "yield_files",
    "yield_path_comments",
]
