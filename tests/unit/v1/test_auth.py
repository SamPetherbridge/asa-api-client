"""Tests for OAuth authentication, key loading, error mapping, and concurrency."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.auth import TOKEN_URL, Authenticator
from asa_api_client.exceptions import AuthenticationError, ConfigurationError, NetworkError


class TestAuthKeyLoadingAndSecrets:
    """Tests for key loading, JWT generation, and from_env construction."""

    def test_key_source_validation(self, ec_private_key_pem: str, tmp_path: Path) -> None:
        """Providing both or neither key source raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="not both"):
            Authenticator(
                client_id="SEARCHADS.test",
                team_id="TEAM123",
                key_id="KEY123",
                private_key=ec_private_key_pem,
                private_key_path=tmp_path / "key.pem",
            )

        with pytest.raises(ConfigurationError, match="Must provide either"):
            Authenticator(
                client_id="SEARCHADS.test",
                team_id="TEAM123",
                key_id="KEY123",
            )

    def test_load_private_key_from_path_and_errors(
        self, monkeypatch: pytest.MonkeyPatch, ec_private_key_pem: str, tmp_path: Path
    ) -> None:
        """Key file loads from str/Path and maps missing, permission, and OS errors."""
        key_file = tmp_path / "ec.pem"
        key_file.write_text(ec_private_key_pem)

        auth = Authenticator(
            client_id="SEARCHADS.test",
            team_id="TEAM123",
            key_id="KEY123",
            private_key_path=str(key_file),
        )
        # Second access hits the cached client_secret fast path
        secret_one = auth.client_secret
        secret_two = auth.client_secret
        assert secret_one == secret_two

        with pytest.raises(ConfigurationError, match="not found"):
            Authenticator(
                client_id="SEARCHADS.test",
                team_id="TEAM123",
                key_id="KEY123",
                private_key_path=tmp_path / "does-not-exist.pem",
            )

        # Passing a directory triggers IsADirectoryError (OSError)
        with pytest.raises(ConfigurationError, match="Error reading private key file"):
            Authenticator(
                client_id="SEARCHADS.test",
                team_id="TEAM123",
                key_id="KEY123",
                private_key_path=tmp_path,
            )

        def deny_read(_self: Path, *_args: object, **_kwargs: object) -> str:
            raise PermissionError("denied")

        monkeypatch.setattr(Path, "read_text", deny_read)
        with pytest.raises(ConfigurationError, match="Cannot read private key file"):
            Authenticator(
                client_id="SEARCHADS.test",
                team_id="TEAM123",
                key_id="KEY123",
                private_key_path=key_file,
            )

    def test_invalid_pem_raises_authentication_error(self) -> None:
        """Malformed PEM fails JWT signing with AuthenticationError."""
        auth = Authenticator(
            client_id="SEARCHADS.test",
            team_id="TEAM123",
            key_id="KEY123",
            private_key="not-a-valid-pem",
        )
        with pytest.raises(AuthenticationError, match="Failed to generate client secret"):
            _ = auth.client_secret

    def test_from_env_and_env_file(
        self, monkeypatch: pytest.MonkeyPatch, ec_private_key_pem: str, tmp_path: Path
    ) -> None:
        """Authenticator.from_env loads from env or custom .env and maps validation errors."""
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

        with pytest.raises(ConfigurationError, match="ASA_CLIENT_ID"):
            Authenticator.from_env(env_file=None)

        monkeypatch.setenv("ASA_CLIENT_ID", "SEARCHADS.env")
        monkeypatch.setenv("ASA_TEAM_ID", "TEAM")
        monkeypatch.setenv("ASA_KEY_ID", "KEY")
        with pytest.raises(ConfigurationError, match="Must provide either"):
            Authenticator.from_env(env_file=None)

        key_file = tmp_path / "auth.pem"
        key_file.write_text(ec_private_key_pem)
        env_file = tmp_path / ".env.custom"
        env_file.write_text(f"ASA_PRIVATE_KEY_PATH={key_file}\n")
        auth = Authenticator.from_env(env_file=env_file)
        assert auth.client_id == "SEARCHADS.env"
        assert auth.org_id == 0


class TestTokenExchangeErrors:
    """Tests for sync and async OAuth token endpoint failure modes."""

    def test_sync_oauth_error_and_network_error(
        self, httpx_mock: HTTPXMock, ec_private_key_pem: str
    ) -> None:
        """Non-200 OAuth response and transport failure raise typed errors."""
        auth = Authenticator(
            client_id="SEARCHADS.test",
            team_id="TEAM123",
            key_id="KEY123",
            private_key=ec_private_key_pem,
        )
        httpx_mock.add_response(
            url=TOKEN_URL,
            status_code=400,
            json={"error": "invalid_client", "error_description": "Bad secret"},
        )
        httpx_mock.add_exception(httpx.ConnectError("dns down"), url=TOKEN_URL)

        with httpx.Client() as client:
            with pytest.raises(AuthenticationError, match="Bad secret") as exc_info:
                auth.get_access_token(client)
            assert exc_info.value.status_code == 400

            with pytest.raises(NetworkError, match="Failed to request access token"):
                auth.get_access_token(client)

    async def test_async_oauth_error_and_network_error_and_invalidation(
        self, httpx_mock: HTTPXMock, ec_private_key_pem: str
    ) -> None:
        """Async OAuth errors map cleanly and invalidate_token clears cache."""
        auth = Authenticator(
            client_id="SEARCHADS.test",
            team_id="TEAM123",
            key_id="KEY123",
            private_key=ec_private_key_pem,
        )
        httpx_mock.add_response(
            url=TOKEN_URL,
            status_code=401,
            json={"error": "unauthorized_client"},
        )
        httpx_mock.add_exception(httpx.ConnectError("offline"), url=TOKEN_URL)
        httpx_mock.add_response(
            url=TOKEN_URL,
            status_code=200,
            json={"access_token": "tok-1", "token_type": "Bearer", "expires_in": 3600},
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(AuthenticationError, match="unauthorized_client"):
                await auth.get_access_token_async(client)

            with pytest.raises(NetworkError, match="Failed to request access token"):
                await auth.get_access_token_async(client)

            tok = await auth.get_access_token_async(client)
            assert tok.authorization_header == "Bearer tok-1"
            # Cached hit requires no additional HTTP mock
            assert (await auth.get_access_token_async(client)).token == "tok-1"

            auth.invalidate_token()
            assert auth._access_token is None


class TestAuthConcurrency:
    """Tests that concurrent token refreshes coalesce into a single OAuth POST."""

    async def test_async_concurrent_callers_issue_single_token_request(
        self, httpx_mock: HTTPXMock, ec_private_key_pem: str
    ) -> None:
        """Ten concurrent get_access_token_async calls issue only one OAuth POST."""

        async def slow_token(_request: httpx.Request) -> httpx.Response:
            await asyncio.sleep(0.01)
            return httpx.Response(
                200,
                json={
                    "access_token": "coalesced-async-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )

        httpx_mock.add_callback(slow_token, url=TOKEN_URL)
        auth = Authenticator(
            client_id="SEARCHADS.test",
            team_id="TEAM123",
            key_id="KEY123",
            org_id=111,
            private_key=ec_private_key_pem,
        )

        async with httpx.AsyncClient() as http_client:
            tokens = await asyncio.gather(
                *(auth.get_access_token_async(http_client) for _ in range(10))
            )

        assert len(httpx_mock.get_requests(url=TOKEN_URL)) == 1
        assert {t.token for t in tokens} == {"coalesced-async-token"}

    def test_sync_threaded_callers_issue_single_token_request(
        self, httpx_mock: HTTPXMock, ec_private_key_pem: str
    ) -> None:
        """Concurrent threads calling get_access_token share one OAuth POST."""
        import time

        def slow_token(_request: httpx.Request) -> httpx.Response:
            time.sleep(0.01)
            return httpx.Response(
                200,
                json={
                    "access_token": "coalesced-sync-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )

        httpx_mock.add_callback(slow_token, url=TOKEN_URL)
        auth = Authenticator(
            client_id="SEARCHADS.test",
            team_id="TEAM123",
            key_id="KEY123",
            org_id=111,
            private_key=ec_private_key_pem,
        )

        with httpx.Client() as http_client, ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(auth.get_access_token, http_client) for _ in range(8)]
            tokens = [f.result() for f in futures]

        assert len(httpx_mock.get_requests(url=TOKEN_URL)) == 1
        assert {t.token for t in tokens} == {"coalesced-sync-token"}
