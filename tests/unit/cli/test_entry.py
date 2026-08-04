"""Tests for the ``asa`` console entry point."""

import pytest


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
    """`asa --help` exits 0 and mentions the analyze subcommand."""
    from typer.testing import CliRunner

    from asa_api_client.cli.analyze import app

    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "analyze" in result.output
