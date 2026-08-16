"""Tests for the ``asa v1-smoke`` command (read-only live check)."""

from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from asa_api_client.cli.v1_smoke import app

TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"
V1 = "https://api.ads.apple.com/v1"
ME_URL = f"{V1}/me"
ACLS_URL = f"{V1}/acls"
CAMPAIGNS_URL = f"{V1}/campaigns/query"
REPORT_URL = f"{V1}/reports/apps/campaigns/query"
RECOMMENDATIONS_URL = f"{V1}/recommendations/target-cpas/query"
POPULARITY_URL = f"{V1}/insights/apps/search-term-popularity/query"
CHANGE_HISTORY_URL = f"{V1}/change-history/query"

STEP_NAMES = (
    "me/accounts",
    "campaigns",
    "campaign report",
    "recommendations",
    "search term popularity",
    "change history",
)

runner = CliRunner()


@pytest.fixture
def v1_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Set ASA_* credentials with a generated EC key and no ad account.

    Chdirs to a temp directory so a real ``.env`` in the repo root can
    never leak into ``AppleAdsClient.from_env()``.
    """
    monkeypatch.chdir(tmp_path)
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    monkeypatch.setenv("ASA_CLIENT_ID", "SEARCHADS.test")
    monkeypatch.setenv("ASA_TEAM_ID", "TEAM123")
    monkeypatch.setenv("ASA_KEY_ID", "KEY123")
    monkeypatch.setenv("ASA_PRIVATE_KEY", pem)
    monkeypatch.delenv("ASA_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("ASA_ORG_ID", raising=False)
    monkeypatch.delenv("ASA_AD_ACCOUNT_ID", raising=False)


@pytest.fixture
def v1_env_with_account(
    v1_env: None,  # noqa: ARG001 - fixture chaining, not a value
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extend ``v1_env`` with a preselected ``ASA_AD_ACCOUNT_ID``."""
    monkeypatch.setenv("ASA_AD_ACCOUNT_ID", "12345")


def _acls_json(*account_ids: int) -> dict[str, Any]:
    """Build a ``GET /acls`` response body with one entry per account ID."""
    return {
        "result": {
            "acls": [
                {
                    "adAccount": {"id": account_id, "name": f"Account {account_id}", "orgId": 999},
                    "roles": ["Admin"],
                }
                for account_id in account_ids
            ]
        }
    }


def _campaigns_json() -> dict[str, Any]:
    """Build a ``POST /campaigns/query`` response with one campaign."""
    return {
        "result": [
            {
                "id": 542370539,
                "name": "US Search",
                "status": "ENABLED",
                "promotedObjectType": "APPSTORE_APP",
                "promotedObjectId": "123456789",
            }
        ],
        "pagination": {"offset": 0, "pageSize": 10, "totalCount": 1},
    }


def _mock_identity(httpx_mock: HTTPXMock, *account_ids: int) -> None:
    """Mock the OAuth token, ``GET /me``, and ``GET /acls`` endpoints."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "tok", "token_type": "Bearer", "expires_in": 3600},
        is_optional=True,
        is_reusable=True,
    )
    httpx_mock.add_response(url=ME_URL, json={"result": {"userId": 1, "orgId": 999}})
    httpx_mock.add_response(url=ACLS_URL, json=_acls_json(*account_ids))


def _mock_gated_steps(httpx_mock: HTTPXMock, *, recommendations_status: int = 200) -> None:
    """Mock the report, recommendations, insights, and audit endpoints."""
    httpx_mock.add_response(
        url=REPORT_URL,
        json={
            "result": {"rows": [{"metadata": {"campaignId": 542370539, "campaignName": "US"}}]},
            "pagination": None,
        },
    )
    if recommendations_status == 200:
        httpx_mock.add_response(
            url=RECOMMENDATIONS_URL,
            json={"result": [{"id": "rec-tcpa-1", "recommendationType": "TCPA"}]},
        )
    else:
        httpx_mock.add_response(
            url=RECOMMENDATIONS_URL,
            status_code=recommendations_status,
            json={"error": {"code": "FORBIDDEN", "message": "feature not enabled"}},
        )
    httpx_mock.add_response(
        url=POPULARITY_URL,
        json={
            "result": {
                "rows": [
                    {
                        "week": "2026-08-09",
                        "countryOrRegion": "US",
                        "genre": "TRAVEL",
                        "searchTerm": "trip planner",
                    }
                ]
            }
        },
    )
    httpx_mock.add_response(
        url=CHANGE_HISTORY_URL,
        json={"result": [{"txnId": "txn-1", "userName": "api"}]},
    )


class TestV1Smoke:
    """End-to-end tests for the v1-smoke command over a mocked API."""

    @pytest.mark.usefixtures("v1_env_with_account")
    def test_happy_path_prints_all_steps_and_exits_zero(self, httpx_mock: HTTPXMock) -> None:
        """Test all mocked steps succeed, print, and exit with code 0."""
        _mock_identity(httpx_mock, 12345)
        httpx_mock.add_response(url=CAMPAIGNS_URL, json=_campaigns_json())
        _mock_gated_steps(httpx_mock)

        result = runner.invoke(app, [])

        assert result.exit_code == 0, result.output
        for name in STEP_NAMES:
            assert name in result.output
        assert "❌" not in result.output
        assert "⚠" not in result.output

    @pytest.mark.usefixtures("v1_env_with_account")
    def test_campaigns_403_exits_one(self, httpx_mock: HTTPXMock) -> None:
        """Test a 403 on the campaigns query fails the command with exit 1."""
        _mock_identity(httpx_mock, 12345)
        httpx_mock.add_response(
            url=CAMPAIGNS_URL,
            status_code=403,
            json={"error": {"code": "FORBIDDEN", "message": "not allowed"}},
        )

        result = runner.invoke(app, [])

        assert result.exit_code == 1
        assert "❌" in result.output
        assert "campaigns" in result.output

    @pytest.mark.usefixtures("v1_env_with_account")
    def test_recommendations_403_warns_but_exits_zero(self, httpx_mock: HTTPXMock) -> None:
        """Test a 403 on recommendations prints a warning row but exits 0."""
        _mock_identity(httpx_mock, 12345)
        httpx_mock.add_response(url=CAMPAIGNS_URL, json=_campaigns_json())
        _mock_gated_steps(httpx_mock, recommendations_status=403)

        result = runner.invoke(app, [])

        assert result.exit_code == 0, result.output
        assert "⚠" in result.output
        assert "❌" not in result.output
        for name in STEP_NAMES:
            assert name in result.output

    @pytest.mark.usefixtures("v1_env")
    def test_auto_selects_single_acl_account(self, httpx_mock: HTTPXMock) -> None:
        """Test the single accessible ACL account is auto-selected and used."""
        _mock_identity(httpx_mock, 12345)
        httpx_mock.add_response(url=CAMPAIGNS_URL, json=_campaigns_json())
        _mock_gated_steps(httpx_mock)

        result = runner.invoke(app, [])

        assert result.exit_code == 0, result.output
        assert "12345" in result.output
        campaigns_request = httpx_mock.get_requests(url=CAMPAIGNS_URL)[0]
        assert campaigns_request.headers["X-AP-Context"] == "adAccountId=12345"

    @pytest.mark.usefixtures("v1_env")
    def test_multiple_accounts_without_selection_exits_one(self, httpx_mock: HTTPXMock) -> None:
        """Test unset ad account with multiple ACL accounts lists them and exits 1."""
        _mock_identity(httpx_mock, 12345, 67890)

        result = runner.invoke(app, [])

        assert result.exit_code == 1
        combined = result.output + (result.stderr or "")
        assert "12345" in combined
        assert "67890" in combined

    def test_missing_credentials_exits_one(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test missing ASA_* configuration produces a clean exit 1."""
        monkeypatch.chdir(tmp_path)
        for name in (
            "ASA_CLIENT_ID",
            "ASA_TEAM_ID",
            "ASA_KEY_ID",
            "ASA_PRIVATE_KEY",
            "ASA_PRIVATE_KEY_PATH",
            "ASA_AD_ACCOUNT_ID",
            "ASA_ORG_ID",
        ):
            monkeypatch.delenv(name, raising=False)

        result = runner.invoke(app, [])

        assert result.exit_code == 1
