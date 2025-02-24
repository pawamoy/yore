"""Tests for the CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from yore import main
from yore._internal import debug

if TYPE_CHECKING:
    import pytest


def test_main() -> None:
    """Basic CLI test."""
    assert main([]) == 2


def test_show_help(capsys: pytest.CaptureFixture) -> None:
    """Show help.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    assert main(["-h"]) == 0
    captured = capsys.readouterr()
    assert "yore" in captured.out


def test_show_version(capsys: pytest.CaptureFixture) -> None:
    """Show version.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    assert main(["-V"]) == 0
    captured = capsys.readouterr()
    assert debug._get_version() in captured.out


def test_show_debug_info(capsys: pytest.CaptureFixture) -> None:
    """Show debug information.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    assert main(["--debug-info"]) == 0
    captured = capsys.readouterr().out.lower()
    assert "python" in captured
    assert "system" in captured
    assert "environment" in captured
    assert "packages" in captured
