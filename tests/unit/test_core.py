"""Unit tests for core logging and settings modules."""

import io
import logging
from collections.abc import Generator
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from asa_api_client.logging import configure_logging, get_logger
from asa_api_client.logging import logger as root_asa_logger
from asa_api_client.settings import Settings


@pytest.fixture(autouse=True)
def _restore_asa_logger() -> Generator[None]:
    """Reset the library logger to a quiet NullHandler after each test."""
    original_level = root_asa_logger.level
    original_propagate = root_asa_logger.propagate
    yield
    root_asa_logger.handlers.clear()
    root_asa_logger.addHandler(logging.NullHandler())
    root_asa_logger.setLevel(original_level)
    root_asa_logger.propagate = original_propagate


class TestLogging:
    """Tests for configure_logging() and get_logger()."""

    def test_configure_logging_stream_and_default_format(self) -> None:
        """configure_logging writes formatted records to the provided stream."""
        buf = io.StringIO()
        configured = configure_logging(level=logging.DEBUG, stream=buf)
        assert configured is root_asa_logger
        assert not configured.propagate

        child = get_logger("test_child")
        child.debug("hello debug")
        output = buf.getvalue()
        assert "asa_api.test_child" in output
        assert "DEBUG" in output
        assert "hello debug" in output

    def test_configure_logging_custom_handler_and_format(self) -> None:
        """Custom handler and format_string override defaults and clear prior handlers."""
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        configure_logging(
            level=logging.WARNING,
            handler=handler,
            format_string="[%(levelname)s] %(message)s",
        )
        assert root_asa_logger.handlers == [handler]

        child = get_logger("custom")
        child.info("ignored info")
        child.warning("loud warning")
        assert buf.getvalue().strip() == "[WARNING] loud warning"


class TestSettings:
    """Tests for Settings validation, normalization, and key loading."""

    def _clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for var in (
            "ASA_CLIENT_ID",
            "ASA_TEAM_ID",
            "ASA_KEY_ID",
            "ASA_ORG_ID",
            "ASA_AD_ACCOUNT_ID",
            "ASA_PRIVATE_KEY",
            "ASA_PRIVATE_KEY_PATH",
        ):
            monkeypatch.delenv(var, raising=False)

    def test_ad_account_id_normalization(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Numeric, padded, empty, and None account IDs normalize cleanly."""
        self._clean_env(monkeypatch)
        base = {
            "_env_file": None,
            "client_id": "SEARCHADS.abc",
            "team_id": "TEAM",
            "key_id": "KEY",
            "private_key": SecretStr("pem"),
        }
        assert Settings(**base, ad_account_id=None).ad_account_id is None  # type: ignore[arg-type]
        assert Settings(**base, ad_account_id="   ").ad_account_id is None  # type: ignore[arg-type]
        assert Settings(**base, ad_account_id=" 42 ").ad_account_id == "42"  # type: ignore[arg-type]
        assert Settings(**base, ad_account_id=42).ad_account_id == "42"  # type: ignore[arg-type]

    def test_private_key_exclusivity_validation(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Settings requires exactly one of private_key or private_key_path."""
        self._clean_env(monkeypatch)
        with pytest.raises(ValidationError, match="Must provide either"):
            Settings(
                _env_file=None,
                client_id="SEARCHADS.abc",
                team_id="TEAM",
                key_id="KEY",
            )

        with pytest.raises(ValidationError, match="not both"):
            Settings(
                _env_file=None,
                client_id="SEARCHADS.abc",
                team_id="TEAM",
                key_id="KEY",
                private_key=SecretStr("pem"),
                private_key_path=tmp_path / "key.pem",
            )

    def test_get_private_key_from_secret_and_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """get_private_key reads inline SecretStr or PEM file and maps file errors."""
        self._clean_env(monkeypatch)
        inline = Settings(
            _env_file=None,
            client_id="SEARCHADS.abc",
            team_id="TEAM",
            key_id="KEY",
            private_key=SecretStr("inline-pem"),
        )
        assert inline.get_private_key() == "inline-pem"

        key_file = tmp_path / "valid.pem"
        key_file.write_text("file-pem")
        from_path = Settings(
            _env_file=None,
            client_id="SEARCHADS.abc",
            team_id="TEAM",
            key_id="KEY",
            private_key_path=key_file,
        )
        assert from_path.get_private_key() == "file-pem"

        missing = Settings(
            _env_file=None,
            client_id="SEARCHADS.abc",
            team_id="TEAM",
            key_id="KEY",
            private_key_path=tmp_path / "missing.pem",
        )
        with pytest.raises(ValueError, match="not found"):
            missing.get_private_key()

        def deny_read(_self: Path, *_args: object, **_kwargs: object) -> str:
            raise PermissionError("denied")

        monkeypatch.setattr(Path, "read_text", deny_read)
        with pytest.raises(ValueError, match="Cannot read private key file"):
            from_path.get_private_key()
