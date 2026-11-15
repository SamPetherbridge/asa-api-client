"""Invariant: the package version is defined once, consistently."""

import tomllib
from pathlib import Path

import asa_api_client


def test_dunder_version_matches_pyproject() -> None:
    """Test __version__ agrees with pyproject.toml (release invariant).

    These drifted once (0.2.0 vs 0.2.1); this test makes the suite fail
    at bump time instead of at release time.
    """
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text())
    assert asa_api_client.__version__ == data["project"]["version"]


def test_pep561_py_typed_marker_present() -> None:
    """Test PEP 561 py.typed marker exists inside the package directory."""
    pkg_dir = Path(asa_api_client.__file__).resolve().parent
    assert (pkg_dir / "py.typed").is_file()
