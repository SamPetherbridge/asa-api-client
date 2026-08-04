"""The ``asa analyze`` command."""

import typer

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def _root() -> None:
    """Apple Search Ads analysis toolkit."""


@app.command()
def analyze() -> None:
    """Generate an Excel performance analysis workbook."""
    raise typer.Exit(code=0)
