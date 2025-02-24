"""yore package.

Manage legacy code with comments.
"""

from __future__ import annotations

from yore._internal.cli import CommandCheck, CommandFix, CommandMain, main
from yore._internal.lib import (
    COMMENT_PATTERN,
    DEFAULT_EXCLUDE,
    DEFAULT_PREFIX,
    Scope,
    YoreComment,
    YoreKind,
    python_dates,
    yield_buffer_comments,
    yield_directory_comments,
    yield_file_comments,
    yield_path_comments,
    yield_python_files,
)

__all__: list[str] = [
    "COMMENT_PATTERN",
    "DEFAULT_EXCLUDE",
    "DEFAULT_PREFIX",
    "CommandCheck",
    "CommandFix",
    "CommandMain",
    "Scope",
    "YoreComment",
    "YoreKind",
    "main",
    "python_dates",
    "yield_buffer_comments",
    "yield_directory_comments",
    "yield_file_comments",
    "yield_path_comments",
    "yield_python_files",
]
