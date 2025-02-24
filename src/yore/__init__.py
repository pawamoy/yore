"""yore package.

Manage legacy code with comments.
"""

from __future__ import annotations

from yore._internal.cli import get_parser, main

__all__: list[str] = ["get_parser", "main"]
