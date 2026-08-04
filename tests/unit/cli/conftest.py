"""Shared fixtures for CLI tests: env credentials and report JSON builders."""

from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"
API = "https://api.searchads.apple.com/api/v5"


@pytest.fixture
def asa_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the client at fake credentials with a real EC P-256 key."""
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


def token_json() -> dict[str, Any]:
    """OAuth token response body."""
    return {"access_token": "tok", "token_type": "Bearer", "expires_in": 3600}


def campaigns_json() -> dict[str, Any]:
    """Two campaigns for two apps."""
    def campaign(cid: int, name: str, adam: int) -> dict[str, Any]:
        return {
            "id": cid,
            "orgId": 999,
            "name": name,
            "adamId": adam,
            "countriesOrRegions": ["US"],
            "status": "ENABLED",
            "servingStatus": "RUNNING",
            "modificationTime": "2026-08-01T00:00:00.000",
            "displayStatus": "RUNNING",
            "supplySources": ["APPSTORE_SEARCH_RESULTS"],
            "dailyBudgetAmount": {"amount": "100", "currency": "USD"},
        }

    data = [campaign(1, "Campaign One", 111), campaign(2, "Campaign Two", 222)]
    return {
        "data": data,
        "pagination": {"totalResults": 2, "startIndex": 0, "itemsPerPage": 2},
    }


def report_json(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap rows in the reporting response envelope."""
    return {"data": {"reportingDataResponse": {"row": rows, "grandTotals": {}}}}


def report_row(
    metadata: dict[str, Any], days: list[tuple[str, int, int, int, str]]
) -> dict[str, Any]:
    """Build a report row with a DAILY granularity breakdown.

    Args:
        metadata: The row metadata (campaignId etc.).
        days: Tuples of (date, impressions, taps, installs, spend).
    """
    granularity = [
        {
            "date": d,
            "impressions": imp,
            "taps": taps,
            "totalInstalls": installs,
            "localSpend": {"amount": spend, "currency": "USD"},
        }
        for d, imp, taps, installs, spend in days
    ]
    total = {
        "impressions": sum(g["impressions"] for g in granularity),
        "taps": sum(g["taps"] for g in granularity),
        "totalInstalls": sum(g["totalInstalls"] for g in granularity),
        "localSpend": {
            "amount": str(sum(float(g["localSpend"]["amount"]) for g in granularity)),
            "currency": "USD",
        },
    }
    return {"metadata": metadata, "total": total, "granularity": granularity}
