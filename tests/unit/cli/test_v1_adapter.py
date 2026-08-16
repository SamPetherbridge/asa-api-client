"""Tests for the v1 fetch adapter and the ``--api-version`` flag.

Client touchpoints the adapter must cover (from ``cli/fetch.py`` and
``cli/analyze.py``):

- ``client.apps.search(query="", return_own_apps=True)`` yielding items
  with ``.adam_id`` / ``.app_name``.
- ``client.campaigns.list()`` yielding items with ``.id`` / ``.name`` /
  ``.adam_id`` / ``.daily_budget_amount`` / ``.budget_amount``.
- ``client.reports.campaigns_async(start, end, campaign_ids=..., timezone=...)``.
- ``client.reports.{ad_groups,keywords,search_terms,ads}_async(cid, start,
  end, timezone=...)`` — all returning a v5 ``ReportingResponse``.
- ``await client.aclose()`` (fetch) and ``client.close()`` (analyze).
"""

import asyncio
import json
import re
from datetime import date
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from asa_api_client.cli.analyze import app
from asa_api_client.cli.fetch import flatten_daily
from asa_api_client.cli.v1_adapter import V1FetchAdapter
from asa_api_client.client import AppleSearchAdsClient
from asa_api_client.models.reports import ReportingResponse
from asa_api_client.v1.client import AppleAdsClient

V1_BASE = "https://api.ads.apple.com/v1"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"

runner = CliRunner()


@pytest.fixture(scope="module")
def ec_private_key_pem() -> str:
    """Generate a throwaway EC P-256 private key in PEM format."""
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode()


@pytest.fixture
def v1_client(ec_private_key_pem: str) -> AppleAdsClient:
    """Build a real v1 AppleAdsClient with dummy credentials."""
    return AppleAdsClient(
        client_id="SEARCHADS.test",
        team_id="TEAM123",
        key_id="KEY123",
        ad_account_id="12345",
        private_key=ec_private_key_pem,
    )


@pytest.fixture
def adapter(v1_client: AppleAdsClient) -> V1FetchAdapter:
    """Wrap the v1 client in the fetch adapter."""
    return V1FetchAdapter(v1_client)


def mock_token(httpx_mock: HTTPXMock) -> None:
    """Register a reusable mocked OAuth token response."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
        is_reusable=True,
    )


def _granular(day: str, impressions: int, taps: int, installs: int, spend: str) -> dict[str, Any]:
    """Build one v1 granular-metrics entry."""
    return {
        "date": day,
        "impressions": impressions,
        "taps": taps,
        "totalInstalls": installs,
        "localSpend": {"amount": spend, "currency": "USD"},
        "cpt": {"amount": "0.50", "currency": "USD"},
    }


def _report_json(
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


class TestReportsShim:
    """Report conversion from v1 responses to v5 ReportingResponse."""

    def test_campaign_report_converts_to_v5_shape(
        self, httpx_mock: HTTPXMock, adapter: V1FetchAdapter
    ) -> None:
        """A v1 campaign report becomes a flattenable v5 ReportingResponse."""
        mock_token(httpx_mock)
        row = {
            "metadata": {"id": 1, "name": "Campaign One", "status": "ENABLED"},
            "totalMetrics": {
                "impressions": 300,
                "taps": 30,
                "totalInstalls": 5,
                "localSpend": {"amount": "15.00", "currency": "USD"},
            },
            "granularMetrics": [
                _granular("2026-08-01", 100, 10, 2, "5.00"),
                _granular("2026-08-02", 200, 20, 3, "10.00"),
            ],
        }
        httpx_mock.add_response(
            url=f"{V1_BASE}/reports/apps/campaigns/query", json=_report_json([row])
        )

        response = asyncio.run(
            adapter.reports.campaigns_async(
                date(2026, 8, 1), date(2026, 8, 2), campaign_ids=[1, 2], timezone="UTC"
            )
        )

        assert isinstance(response, ReportingResponse)
        body = json.loads(httpx_mock.get_requests(url=re.compile(r".*campaigns/query"))[0].content)
        assert body["filters"] == [{"field": "id", "operator": "IN", "value": ["1", "2"]}]
        assert body["timeRange"] == {
            "start": "2026-08-01",
            "end": "2026-08-02",
            "timeZone": "UTC",
            "granularity": "DAILY",
        }

        df = flatten_daily(response)
        assert len(df) == 2
        assert df["campaign_id"].tolist() == [1, 1]
        assert df["campaign_name"].tolist() == ["Campaign One", "Campaign One"]
        assert df["date"].tolist() == ["2026-08-01", "2026-08-02"]
        assert df["impressions"].tolist() == [100, 200]
        assert df["taps"].tolist() == [10, 20]
        assert df["total_installs"].tolist() == [2, 3]
        assert df["local_spend"].tolist() == ["5.00", "10.00"]
        assert df["avg_cpt"].tolist() == ["0.50", "0.50"]

    def test_ad_group_report_maps_metadata(
        self, httpx_mock: HTTPXMock, adapter: V1FetchAdapter
    ) -> None:
        """Ad-group rows carry campaign_id, ad_group_id, and ad_group_name."""
        mock_token(httpx_mock)
        row = {
            "metadata": {"id": 10, "campaignId": 1, "name": "AG One", "status": "ENABLED"},
            "granularMetrics": [_granular("2026-08-01", 100, 10, 2, "5.00")],
        }
        httpx_mock.add_response(
            url=f"{V1_BASE}/reports/apps/adgroups/query", json=_report_json([row])
        )

        response = asyncio.run(
            adapter.reports.ad_groups_async(1, date(2026, 8, 1), date(2026, 8, 1), timezone="UTC")
        )

        body = json.loads(httpx_mock.get_requests(url=re.compile(r".*adgroups/query"))[0].content)
        assert body["filters"] == [{"field": "campaignId", "operator": "EQUALS", "value": "1"}]
        df = flatten_daily(response)
        assert df["campaign_id"].tolist() == [1]
        assert df["ad_group_id"].tolist() == [10]
        assert df["ad_group_name"].tolist() == ["AG One"]

    def test_search_term_report_forces_ortz_and_maps_keyword(
        self, httpx_mock: HTTPXMock, adapter: V1FetchAdapter
    ) -> None:
        """Search-term rows use ORTZ and surface the nested keyword."""
        mock_token(httpx_mock)
        row = {
            "metadata": {
                "campaignId": 1,
                "adGroupId": 10,
                "searchTermText": "puzzle games",
                "searchTermSource": "AUTO",
                "keyword": {"id": 5, "text": "puzzle", "matchType": "BROAD"},
                "adGroup": {"name": "AG One"},
            },
            "granularMetrics": [_granular("2026-08-01", 100, 10, 2, "5.00")],
        }
        httpx_mock.add_response(
            url=f"{V1_BASE}/reports/apps/searchterms/query", json=_report_json([row])
        )

        response = asyncio.run(
            adapter.reports.search_terms_async(
                1, date(2026, 8, 1), date(2026, 8, 1), timezone="UTC"
            )
        )

        body = json.loads(
            httpx_mock.get_requests(url=re.compile(r".*searchterms/query"))[0].content
        )
        assert body["timeRange"]["timeZone"] == "ORTZ"
        df = flatten_daily(response)
        assert df["search_term_text"].tolist() == ["puzzle games"]
        assert df["ad_group_id"].tolist() == [10]
        assert df["keyword"].tolist() == ["puzzle"]
        assert df["keyword_id"].tolist() == [5]
        assert df["match_type"].tolist() == ["BROAD"]

    def test_keyword_report_maps_metadata(
        self, httpx_mock: HTTPXMock, adapter: V1FetchAdapter
    ) -> None:
        """Keyword rows carry keyword_id, keyword text, match type, and bid."""
        mock_token(httpx_mock)
        row = {
            "metadata": {
                "id": 5,
                "campaignId": 1,
                "adGroupId": 10,
                "text": "puzzle",
                "matchType": "EXACT",
                "status": "ACTIVE",
                "bid": {"amount": "1.25", "currency": "USD"},
            },
            "granularMetrics": [_granular("2026-08-01", 100, 10, 2, "5.00")],
        }
        httpx_mock.add_response(
            url=f"{V1_BASE}/reports/apps/keywords/query", json=_report_json([row])
        )

        response = asyncio.run(
            adapter.reports.keywords_async(1, date(2026, 8, 1), date(2026, 8, 1), timezone="UTC")
        )

        df = flatten_daily(response)
        assert df["keyword_id"].tolist() == [5]
        assert df["keyword"].tolist() == ["puzzle"]
        assert df["match_type"].tolist() == ["EXACT"]
        assert df["bid_amount"].tolist() == ["1.25"]

    def test_ad_report_maps_metadata(self, httpx_mock: HTTPXMock, adapter: V1FetchAdapter) -> None:
        """Ad rows carry ad_id, ad_name, and creative details."""
        mock_token(httpx_mock)
        row = {
            "metadata": {
                "id": 77,
                "campaignId": 1,
                "adGroupId": 10,
                "name": "Ad One",
                "displayStatus": "RUNNING",
                "creative": {
                    "id": 88,
                    "creativeType": "DEFAULT_PRODUCT_PAGE",
                    "creativeSpec": {"language": "en-US"},
                },
            },
            "granularMetrics": [_granular("2026-08-01", 100, 10, 2, "5.00")],
        }
        httpx_mock.add_response(url=f"{V1_BASE}/reports/apps/ads/query", json=_report_json([row]))

        response = asyncio.run(
            adapter.reports.ads_async(1, date(2026, 8, 1), date(2026, 8, 1), timezone="UTC")
        )

        df = flatten_daily(response)
        assert df["ad_id"].tolist() == [77]
        assert df["ad_name"].tolist() == ["Ad One"]
        assert df["ad_display_status"].tolist() == ["RUNNING"]
        assert df["creative_id"].tolist() == [88]

    def test_campaign_report_paginates(
        self, httpx_mock: HTTPXMock, adapter: V1FetchAdapter
    ) -> None:
        """The shim follows pagination and merges rows across pages."""
        mock_token(httpx_mock)

        def _row(cid: int) -> dict[str, Any]:
            return {
                "metadata": {"id": cid, "name": f"C{cid}"},
                "granularMetrics": [_granular("2026-08-01", 100, 10, 2, "5.00")],
            }

        url = f"{V1_BASE}/reports/apps/campaigns/query"
        httpx_mock.add_response(url=url, json=_report_json([_row(1)], offset=0, total_count=2))
        httpx_mock.add_response(url=url, json=_report_json([_row(2)], offset=1, total_count=2))

        response = asyncio.run(
            adapter.reports.campaigns_async(
                date(2026, 8, 1), date(2026, 8, 1), campaign_ids=None, timezone="UTC"
            )
        )

        requests = httpx_mock.get_requests(url=url)
        assert [json.loads(r.content)["pagination"]["offset"] for r in requests] == [0, 1]
        assert [row.metadata.campaign_id for row in response.row] == [1, 2]


class TestCampaignsShim:
    """Campaign listing via the v1 query endpoint."""

    def test_list_maps_promoted_object_to_adam_id(
        self, httpx_mock: HTTPXMock, adapter: V1FetchAdapter
    ) -> None:
        """APPSTORE_APP campaigns map promotedObjectId to an int adam_id."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{V1_BASE}/campaigns/query",
            json={
                "result": [
                    {
                        "id": 100,
                        "name": "App campaign",
                        "promotedObjectType": "APPSTORE_APP",
                        "promotedObjectId": "111",
                        "dailyBudget": {"value": {"amount": "100.00", "currency": "USD"}},
                    },
                    {
                        "id": 200,
                        "name": "Brand campaign",
                        "promotedObjectType": "BUSINESS_BRAND",
                        "promotedObjectId": "brand-1",
                    },
                ],
                "pagination": {"offset": 0, "pageSize": 500, "totalCount": 2},
            },
        )

        campaigns = list(adapter.campaigns.list())

        assert len(campaigns) == 1
        campaign = campaigns[0]
        assert campaign.id == 100
        assert campaign.name == "App campaign"
        assert campaign.adam_id == 111
        assert campaign.daily_budget_amount is not None
        assert campaign.daily_budget_amount.currency == "USD"
        assert campaign.budget_amount is None


class TestAppsShim:
    """App search mapping onto the v1 search endpoint."""

    def test_search_maps_own_apps(self, httpx_mock: HTTPXMock, adapter: V1FetchAdapter) -> None:
        """An empty-query own-apps search uses returnOwnedApps, no query."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=re.compile(rf"{re.escape(V1_BASE)}/search/apps\?.*"),
            json={
                "result": [
                    {
                        "adamId": 111,
                        "appName": "My App",
                        "developerName": "Me",
                        "countryOrRegionCodes": ["US"],
                    }
                ],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )

        apps = list(adapter.apps.search(query="", return_own_apps=True))

        request = httpx_mock.get_requests(url=re.compile(r".*search/apps.*"))[0]
        assert "returnOwnedApps=true" in str(request.url)
        assert "query=" not in str(request.url)
        assert apps[0].adam_id == 111
        assert apps[0].app_name == "My App"


class TestLifecycle:
    """close/aclose delegation to the wrapped v1 client."""

    def test_close_and_aclose_delegate(
        self, v1_client: AppleAdsClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Adapter close/aclose call through to the v1 client."""
        calls: list[str] = []
        monkeypatch.setattr(v1_client, "close", lambda: calls.append("close"))

        async def fake_aclose() -> None:
            calls.append("aclose")

        monkeypatch.setattr(v1_client, "aclose", fake_aclose)
        adapter = V1FetchAdapter(v1_client)

        adapter.close()
        asyncio.run(adapter.aclose())

        assert calls == ["close", "aclose"]


class TestAnalyzeFlag:
    """--api-version wiring in the analyze command."""

    def test_v1_flag_constructs_v1_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """--api-version v1 builds the client via AppleAdsClient.from_env."""
        sentinel = RuntimeError("v1-from-env-called")

        def boom(_cls: type[AppleAdsClient]) -> AppleAdsClient:
            raise sentinel

        monkeypatch.setattr(AppleAdsClient, "from_env", classmethod(boom))
        result = runner.invoke(app, ["analyze", "--api-version", "v1"])
        assert result.exception is sentinel

    def test_default_stays_on_v5(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without the flag, only AppleSearchAdsClient.from_env is used."""
        v5_sentinel = RuntimeError("v5-from-env-called")
        v1_sentinel = RuntimeError("v1-from-env-called")

        def v5_boom(_cls: type[AppleSearchAdsClient]) -> AppleSearchAdsClient:
            raise v5_sentinel

        def v1_boom(_cls: type[AppleAdsClient]) -> AppleAdsClient:
            raise v1_sentinel

        monkeypatch.setattr(AppleSearchAdsClient, "from_env", classmethod(v5_boom))
        monkeypatch.setattr(AppleAdsClient, "from_env", classmethod(v1_boom))
        result = runner.invoke(app, ["analyze"])
        assert result.exception is v5_sentinel
