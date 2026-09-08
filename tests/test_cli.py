from __future__ import annotations

from pathlib import Path

from kubrick.cli import main
from kubrick.core import MediaClip, Project


def test_validate_project_command_accepts_valid_project(tmp_path: Path, capsys) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"placeholder")
    project_path = tmp_path / "edit.kubrick.json"
    Project(video=[MediaClip(str(source), 0, 2)]).save(project_path)

    assert main_args(["validate-project", str(project_path)], capsys) == 0
    output = capsys.readouterr().out
    assert "Valid project:" in output
    assert "Timeline duration: 2.000s" in output


def main_args(argv: list[str], capsys) -> int:
    # Keep the CLI's real parser while allowing the test to provide argv.
    import sys

    original = sys.argv
    sys.argv = ["kubrick", *argv]
    try:
        return main()
    finally:
        sys.argv = original
