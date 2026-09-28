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

"""Tests for the CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from yore import main
from yore._internal import cli, debug

if TYPE_CHECKING:
    from pathlib import Path

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


def test_service_url_options_are_documented(capsys: pytest.CaptureFixture) -> None:
    """Every network-backed operation exposes all service URL overrides."""
    options = {
        "--forgejo-url",
        "--gitlab-url",
    }
    for command in ("check", "diff", "fix"):
        assert main([command, "--help"]) == 0
        help_text = capsys.readouterr().out
        assert all(option in help_text for option in options)


def test_service_urls_from_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit service URLs reach work-item checks as one normalized mapping."""
    received: list[object] = []

    class _Comment:
        @staticmethod
        def check(**kwargs: object) -> bool:
            received.append(kwargs["service_urls"])
            return True

    monkeypatch.setattr(cli, "yield_path_comments", lambda *args, **kwargs: [_Comment()])
    assert (
        main(
            [
                "check",
                "--gitlab-url",
                "https://gitlab.example",
                "--forgejo-url",
                "https://forgejo.example",
            ],
        )
        == 0
    )
    assert received == [
        {
            "gitlab": "https://gitlab.example",
            "forgejo": "https://forgejo.example",
        },
    ]


def test_service_url_from_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nested provider configuration becomes the operation's URL mapping."""
    config_file = tmp_path / "yore.toml"
    config_file.write_text(
        '[gitlab]\nurl = "https://gitlab.example"\n',
        encoding="utf8",
    )
    received: list[object] = []

    class _Comment:
        @staticmethod
        def check(**kwargs: object) -> bool:
            received.append(kwargs["service_urls"])
            return True

    monkeypatch.setattr(cli.CommandMain, "_CONFIG", None)
    monkeypatch.setattr(cli, "yield_path_comments", lambda *args, **kwargs: [_Comment()])
    assert main(["-c", str(config_file), "check"]) == 0
    assert received == [{"gitlab": "https://gitlab.example"}]


def test_explicit_pyproject_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit pyproject path reads its tool.yore provider table."""
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text(
        '[tool.yore.gitlab]\nurl = "https://gitlab.example"\n',
        encoding="utf8",
    )
    received: list[object] = []

    class _Comment:
        @staticmethod
        def check(**kwargs: object) -> bool:
            received.append(kwargs["service_urls"])
            return True

    monkeypatch.setattr(cli.CommandMain, "_CONFIG", None)
    monkeypatch.setattr(cli, "yield_path_comments", lambda *args, **kwargs: [_Comment()])

    assert main(["-c", str(config_file), "check"]) == 0
    assert received == [{"gitlab": "https://gitlab.example"}]


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
