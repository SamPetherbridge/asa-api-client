"""Tests for OAuth token refresh concurrency and caching."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import httpx
from pytest_httpx import HTTPXMock

from asa_api_client.auth import TOKEN_URL, Authenticator


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
