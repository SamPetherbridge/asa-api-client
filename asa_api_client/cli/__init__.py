"""Console entry point for the ``asa`` CLI.

The CLI's dependencies (typer, rich, pandas, xlsxwriter) are an optional
extra.  ``main`` guards the import so a bare install gets a clean install
hint instead of a traceback.
"""

import sys

_INSTALL_HINT = 'Install the CLI extra: pip install "asa-api-client[cli]"'


def main() -> None:
    """Run the ``asa`` command-line interface."""
    try:
        from asa_api_client.cli.analyze import app
    except ImportError:
        sys.stderr.write(_INSTALL_HINT + "\n")
        raise SystemExit(1) from None
    app()
