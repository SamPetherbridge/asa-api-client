"""Shared fixtures for CLI tests: env credentials and v1 JSON builders."""

import re
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pytest_httpx import HTTPXMock

TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"
V1_API = "https://api.ads.apple.com/v1"


@pytest.fixture
def asa_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point the client at fake credentials with a real EC P-256 key.

    Also chdirs to a temp directory so a real ``.env`` in the repo root
    can never leak into tests that call ``from_env()`` with defaults.
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
    monkeypatch.setenv("ASA_ORG_ID", "999")
    monkeypatch.setenv("ASA_PRIVATE_KEY", pem)
    monkeypatch.delenv("ASA_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("ASA_AD_ACCOUNT_ID", raising=False)


def token_json() -> dict[str, Any]:
    """OAuth token response body."""
    return {"access_token": "tok", "token_type": "Bearer", "expires_in": 3600}


def acls_json(account_id: int = 999, name: str = "Test Org") -> dict[str, Any]:
    """Single-account ACL discovery response body."""
    return {
        "result": {
            "acls": [
                {
                    "adAccount": {"id": account_id, "name": name, "orgId": account_id},
                    "roles": ["Admin"],
                }
            ]
        }
    }


def campaigns_json() -> dict[str, Any]:
    """Two App Store campaigns for two apps (plus one Apple Maps campaign to skip)."""
    return {
        "result": [
            {
                "id": 1,
                "name": "Campaign One",
                "status": "ENABLED",
                "promotedObjectType": "APPSTORE_APP",
                "promotedObjectId": "111",
                "dailyBudget": {"value": {"amount": "100", "currency": "USD"}},
            },
            {
                "id": 2,
                "name": "Campaign Two",
                "status": "ENABLED",
                "promotedObjectType": "APPSTORE_APP",
                "promotedObjectId": "222",
                "dailyBudget": {"value": {"amount": "100", "currency": "USD"}},
            },
            {
                "id": 999,
                "name": "Brand Campaign",
                "status": "ENABLED",
                "promotedObjectType": "BUSINESS_BRAND",
                "promotedObjectId": "brand-1",
            },
        ],
        "pagination": {"offset": 0, "pageSize": 500, "totalCount": 3},
    }


def report_json(
    rows: list[dict[str, Any]], *, offset: int = 0, total_count: int | None = None
) -> dict[str, Any]:
    """Wrap v1 report rows in the ``{result, pagination}`` envelope."""
    return {
        "result": {"rows": rows},
        "pagination": {
            "offset": offset,
            "pageSize": 5000,
            "totalCount": total_count if total_count is not None else len(rows),
        },
    }


def report_row(
    metadata: dict[str, Any], days: list[tuple[str, int, int, int, str]]
) -> dict[str, Any]:
    """Build a v1 report row with a DAILY ``granularMetrics`` breakdown."""
    granular: list[dict[str, Any]] = [
        {
            "date": d,
            "impressions": imp,
            "taps": taps,
            "totalInstalls": installs,
            "localSpend": {"amount": spend, "currency": "USD"},
            "cpt": {"amount": "0.50", "currency": "USD"},
        }
        for d, imp, taps, installs, spend in days
    ]
    total = {
        "impressions": sum(g["impressions"] for g in granular),
        "taps": sum(g["taps"] for g in granular),
        "totalInstalls": sum(g["totalInstalls"] for g in granular),
        "localSpend": {
            "amount": str(sum(float(g["localSpend"]["amount"]) for g in granular)),
            "currency": "USD",
        },
    }
    return {"metadata": metadata, "totalMetrics": total, "granularMetrics": granular}


def mock_v1_api(httpx_mock: HTTPXMock) -> None:
    """Register reusable mocks for a full ``asa analyze`` happy-path run."""
    httpx_mock.add_response(url=TOKEN_URL, json=token_json(), is_reusable=True)
    httpx_mock.add_response(url=f"{V1_API}/acls", json=acls_json(), is_reusable=True)
    httpx_mock.add_response(
        url=f"{V1_API}/campaigns/query", json=campaigns_json(), is_reusable=True
    )
    httpx_mock.add_response(
        url=re.compile(rf"{re.escape(V1_API)}/search/apps\?.*"),
        json={"result": [], "pagination": {"offset": 0, "pageSize": 500, "totalCount": 0}},
        is_reusable=True,
    )
    rows = [
        report_row(
            {"id": 1, "name": "Campaign One", "status": "ENABLED"},
            [("2026-07-01", 1000, 100, 10, "50.0")],
        )
    ]
    httpx_mock.add_response(
        url=f"{V1_API}/reports/apps/campaigns/query",
        json=report_json(rows),
        is_reusable=True,
    )
    for entity in ("adgroups", "keywords", "searchterms", "ads"):
        httpx_mock.add_response(
            url=f"{V1_API}/reports/apps/{entity}/query",
            json=report_json([]),
            is_reusable=True,
        )
