"""Tests for the ``asa-client`` console entry point."""

import tomllib
from pathlib import Path

import pytest


def test_project_scripts_owns_asa_client_not_asa() -> None:
    """Ensure asa-api-client exposes `asa-client` and never overwrites `asa` from asa-api-cli."""
    pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"
    scripts = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["scripts"]
    assert scripts == {"asa-client": "asa_api_client.cli:main"}
    assert "asa" not in scripts


def test_main_importable() -> None:
    """The entry point referenced by [project.scripts] must exist."""
    from asa_api_client.cli import main

    assert callable(main)


def test_missing_cli_extra_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing optional deps produce the install hint, not a traceback."""
    import builtins

    from asa_api_client import cli

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("typer") or name == "asa_api_client.cli.analyze":
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    assert excinfo.value.code == 1
    assert 'Install the CLI extra: pip install "asa-api-client[cli]"' in capsys.readouterr().err


def test_help_runs() -> None:
    """`asa-client --help` exits 0 and mentions analyze and smoke subcommands."""
    from typer.testing import CliRunner

    from asa_api_client.cli.analyze import app

    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "analyze" in result.output
    assert "smoke" in result.output

    # Hidden v1-smoke alias also resolves cleanly
    alias_help = CliRunner().invoke(app, ["v1-smoke", "--help"])
    assert alias_help.exit_code == 0
