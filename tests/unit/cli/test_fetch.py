"""Tests for v1 scope resolution, row flattening, and chunked async report fetching."""

import json
import re
from datetime import date, timedelta
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from asa_api_client import AppleAdsClient
from asa_api_client.cli.dates import SEARCH_TERM_LOOKBACK, prior_window
from asa_api_client.cli.fetch import (
    LevelFetchError,
    ScopeError,
    _ad_group_metadata,
    _ad_metadata,
    _campaign_metadata,
    _keyword_metadata,
    _search_term_metadata,
    fetch_all,
    flatten_rows,
    resolve_scope,
)
from asa_api_client.v1.models.reports import (
    AppsAdGroupReportRow,
    AppsAdReportRow,
    AppsCampaignReportRow,
    AppsKeywordReportRow,
    AppsSearchTermReportRow,
)
from tests.unit.cli.conftest import (
    TOKEN_URL,
    V1_API,
    campaigns_json,
    report_json,
    report_row,
    token_json,
)

START, END = date(2026, 7, 1), date(2026, 7, 2)
TODAY = date(2026, 8, 5)


def _client() -> AppleAdsClient:
    client = AppleAdsClient.from_env(env_file=None)
    client.ad_account_id = "999"
    return client


def _mock_common(httpx_mock: HTTPXMock, *, apps: list[dict[str, Any]] | None = None) -> None:
    httpx_mock.add_response(url=TOKEN_URL, json=token_json(), is_reusable=True)
    httpx_mock.add_response(
        url=f"{V1_API}/campaigns/query", json=campaigns_json(), is_reusable=True
    )
    httpx_mock.add_response(
        url=re.compile(rf"{re.escape(V1_API)}/search/apps\?.*"),
        json={
            "result": apps or [],
            "pagination": {"offset": 0, "pageSize": 500, "totalCount": len(apps or [])},
        },
        is_reusable=True,
    )


class TestFlattenRows:
    """flatten_rows: one row per entity-day across all five v1 report row types."""

    def test_campaign_rows_explode_granularity(self) -> None:
        """Two granular days become two rows carrying campaign metadata and avg_cpt."""
        row = AppsCampaignReportRow.model_validate(
            report_row(
                {"id": 1, "name": "One", "status": "ENABLED"},
                [("2026-07-01", 100, 10, 1, "5.0"), ("2026-07-02", 200, 20, 2, "10.0")],
            )
        )
        df = flatten_rows([row], _campaign_metadata)
        assert len(df) == 2
        assert df["date"].tolist() == ["2026-07-01", "2026-07-02"]
        assert df["local_spend"].tolist() == ["5.0", "10.0"]
        assert df["avg_cpt"].tolist() == ["0.50", "0.50"]
        assert df["campaign_id"].tolist() == [1, 1]
        assert df["campaign_status"].tolist() == ["ENABLED", "ENABLED"]

    def test_ad_group_keyword_search_term_and_ad_metadata(self) -> None:
        """All sub-entity metadata helpers map nested v1 fields to flat snake_case columns."""
        days = [("2026-07-01", 50, 5, 1, "2.50")]

        ag_row = AppsAdGroupReportRow.model_validate(
            report_row({"id": 10, "campaignId": 1, "name": "AG One", "status": "ENABLED"}, days)
        )
        ag_df = flatten_rows([ag_row], _ad_group_metadata)
        assert ag_df["ad_group_id"].tolist() == [10]
        assert ag_df["ad_group_name"].tolist() == ["AG One"]

        kw_row = AppsKeywordReportRow.model_validate(
            report_row(
                {
                    "id": 5,
                    "campaignId": 1,
                    "adGroupId": 10,
                    "text": "puzzle",
                    "matchType": "EXACT",
                    "status": "ENABLED",
                    "bid": {"amount": "1.25", "currency": "USD"},
                },
                days,
            )
        )
        kw_df = flatten_rows([kw_row], _keyword_metadata)
        assert kw_df["keyword_id"].tolist() == [5]
        assert kw_df["keyword"].tolist() == ["puzzle"]
        assert kw_df["match_type"].tolist() == ["EXACT"]
        assert kw_df["bid_amount"].tolist() == ["1.25"]

        st_row = AppsSearchTermReportRow.model_validate(
            report_row(
                {
                    "campaignId": 1,
                    "adGroupId": 10,
                    "searchTermText": "puzzle games",
                    "searchTermSource": "AUTO",
                    "keyword": {"id": 5, "text": "puzzle", "matchType": "BROAD"},
                    "adGroup": {"name": "AG One"},
                },
                days,
            )
        )
        st_df = flatten_rows([st_row], _search_term_metadata)
        assert st_df["search_term_text"].tolist() == ["puzzle games"]
        assert st_df["keyword"].tolist() == ["puzzle"]
        assert st_df["match_type"].tolist() == ["BROAD"]

        ad_row = AppsAdReportRow.model_validate(
            report_row(
                {
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
                days,
            )
        )
        ad_df = flatten_rows([ad_row], _ad_metadata)
        assert ad_df["ad_id"].tolist() == [77]
        assert ad_df["ad_name"].tolist() == ["Ad One"]
        assert ad_df["ad_display_status"].tolist() == ["RUNNING"]
        assert ad_df["creative_id"].tolist() == [88]

    def test_empty_rows(self) -> None:
        """Empty row sequence produces an empty DataFrame."""
        assert flatten_rows([], _campaign_metadata).empty


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
@pytest.mark.usefixtures("asa_env")
class TestResolveScope:
    """resolve_scope: App Store campaign metadata map + currency."""

    def test_all_apps_skips_brand_campaigns(self, httpx_mock: HTTPXMock) -> None:
        """Without --app, App Store campaigns are included and BUSINESS_BRAND skipped."""
        _mock_common(
            httpx_mock,
            apps=[
                {
                    "adamId": 111,
                    "appName": "My App",
                    "developerName": "Dev",
                    "countryOrRegionCodes": ["US"],
                }
            ],
        )
        with _client() as client:
            meta, currency = resolve_scope(client, None)
        assert sorted(meta["campaign_id"]) == [1, 2]
        assert currency == "USD"
        assert meta.loc[meta["adam_id"] == 111, "app_name"].iloc[0] == "My App"
        assert meta.loc[meta["adam_id"] == 222, "app_name"].iloc[0] == "App 222"

        app_req = httpx_mock.get_requests(url=re.compile(r".*search/apps.*"))[0]
        assert "returnOwnedApps=true" in str(app_req.url)
        assert "query=" not in str(app_req.url)

    def test_app_filter(self, httpx_mock: HTTPXMock) -> None:
        """--app filters campaigns by adam_id."""
        _mock_common(httpx_mock)
        with _client() as client:
            meta, _ = resolve_scope(client, [111])
        assert meta["campaign_id"].tolist() == [1]

    def test_no_match_raises(self, httpx_mock: HTTPXMock) -> None:
        """An adam_id with no campaigns raises ScopeError."""
        _mock_common(httpx_mock)
        with _client() as client, pytest.raises(ScopeError):
            resolve_scope(client, [999])


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
@pytest.mark.usefixtures("asa_env")
class TestFetchAll:
    """fetch_all: five levels + prior period, pagination, lookback clipping, failure tolerance."""

    def _mock_reports(self, httpx_mock: HTTPXMock, *, exclude: set[str] | None = None) -> None:
        excluded = exclude or set()
        if "campaigns" not in excluded:
            httpx_mock.add_response(
                url=f"{V1_API}/reports/apps/campaigns/query",
                json=report_json(self._campaign_rows()),
                is_reusable=True,
            )
        self._mock_sublevel_reports(httpx_mock, exclude=excluded)

    def _mock_sublevel_reports(
        self, httpx_mock: HTTPXMock, *, exclude: set[str] | None = None
    ) -> None:
        excluded = exclude or set()
        days = [("2026-07-01", 100, 10, 1, "5.0"), ("2026-07-02", 100, 10, 1, "5.0")]
        if "adgroups" not in excluded:
            httpx_mock.add_response(
                url=f"{V1_API}/reports/apps/adgroups/query",
                json=report_json([report_row({"id": 10, "campaignId": 1, "name": "AG"}, days)]),
                is_reusable=True,
            )
        if "keywords" not in excluded:
            httpx_mock.add_response(
                url=f"{V1_API}/reports/apps/keywords/query",
                json=report_json(
                    [report_row({"id": 5, "campaignId": 1, "adGroupId": 10, "text": "kw"}, days)]
                ),
                is_reusable=True,
            )
        if "searchterms" not in excluded:
            httpx_mock.add_response(
                url=f"{V1_API}/reports/apps/searchterms/query",
                json=report_json(
                    [report_row({"campaignId": 1, "adGroupId": 10, "searchTermText": "st"}, days)]
                ),
                is_reusable=True,
            )
        if "ads" not in excluded:
            httpx_mock.add_response(
                url=f"{V1_API}/reports/apps/ads/query",
                json=report_json(
                    [report_row({"id": 7, "campaignId": 1, "adGroupId": 10, "name": "Ad"}, days)]
                ),
                is_reusable=True,
            )

    @staticmethod
    def _campaign_rows() -> list[dict[str, Any]]:
        return [
            report_row(
                {"id": 1, "name": "One", "status": "ENABLED"},
                [("2026-07-01", 100, 10, 1, "5.0"), ("2026-07-02", 100, 10, 1, "5.0")],
            )
        ]

    async def test_happy_path(self, httpx_mock: HTTPXMock) -> None:
        """All five levels populated; prior campaigns fetched; names merged."""
        _mock_common(httpx_mock)
        self._mock_reports(httpx_mock)
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            result = await fetch_all(client, meta, START, END, today=TODAY)
        assert set(result.levels) == {"campaigns", "ad_groups", "keywords", "search_terms", "ads"}
        camp = result.levels["campaigns"].daily
        assert "app_name" in camp.columns
        assert not result.prior_campaigns.empty
        assert result.warnings == []

        camp_body = json.loads(
            httpx_mock.get_requests(url=f"{V1_API}/reports/apps/campaigns/query")[0].content
        )
        assert camp_body["filters"] == [{"field": "id", "operator": "IN", "value": ["1", "2"]}]

    async def test_progress_callback(self, httpx_mock: HTTPXMock) -> None:
        """on_progress fires with (key, done, total) and reaches total."""
        _mock_common(httpx_mock)
        self._mock_reports(httpx_mock)
        seen: dict[str, tuple[int, int]] = {}
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            await fetch_all(
                client,
                meta,
                START,
                END,
                today=TODAY,
                on_progress=lambda key, done, total: seen.__setitem__(key, (done, total)),
            )
        assert seen["campaigns"] == (2, 2)
        assert seen["keywords"] == (2, 2)

    async def test_chunk_failure_warns_and_continues(self, httpx_mock: HTTPXMock) -> None:
        """A failing per-campaign chunk becomes a warning + note, not a crash."""
        _mock_common(httpx_mock)

        def kw_callback(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            if body["filters"][0]["value"] == "2":
                return httpx.Response(status_code=400, json={"error": {"message": "boom"}})
            days = [("2026-07-01", 100, 10, 1, "5.0")]
            return httpx.Response(
                status_code=200,
                json=report_json(
                    [report_row({"id": 5, "campaignId": 1, "adGroupId": 10, "text": "kw"}, days)]
                ),
            )

        httpx_mock.add_callback(
            kw_callback, url=f"{V1_API}/reports/apps/keywords/query", is_reusable=True
        )
        self._mock_reports(httpx_mock, exclude={"keywords"})
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            result = await fetch_all(client, meta, START, END, today=TODAY)
        assert any("Keywords" in w for w in result.warnings)
        assert result.levels["keywords"].notes
        assert not result.levels["keywords"].daily.empty

    async def test_prior_campaign_window_failure_warns_and_continues(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """A failing prior-period campaign fetch degrades to a warning."""
        _mock_common(httpx_mock)
        prior_start, _ = prior_window(START, END)

        def campaigns_callback(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            if body["timeRange"]["start"] == prior_start.isoformat():
                return httpx.Response(
                    status_code=400,
                    json={"error": {"message": "lookback exceeded"}},
                )
            return httpx.Response(status_code=200, json=report_json(self._campaign_rows()))

        httpx_mock.add_callback(
            campaigns_callback, url=f"{V1_API}/reports/apps/campaigns/query", is_reusable=True
        )
        self._mock_sublevel_reports(httpx_mock)
        seen: dict[str, tuple[int, int]] = {}
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            result = await fetch_all(
                client,
                meta,
                START,
                END,
                today=TODAY,
                on_progress=lambda key, done, total: seen.__setitem__(key, (done, total)),
            )
        assert result.prior_campaigns.empty
        assert any("Prior period" in w for w in result.warnings)
        assert not result.levels["campaigns"].daily.empty
        assert seen["campaigns"] == (2, 2)

    async def test_whole_level_failure_raises(self, httpx_mock: HTTPXMock) -> None:
        """Every chunk of a level failing aborts the run with context."""
        _mock_common(httpx_mock)
        httpx_mock.add_response(
            url=f"{V1_API}/reports/apps/ads/query",
            status_code=400,
            json={"error": {"message": "no ads"}},
            is_reusable=True,
        )
        self._mock_reports(httpx_mock, exclude={"ads"})
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            with pytest.raises(LevelFetchError, match="Ads"):
                await fetch_all(client, meta, START, END, today=TODAY)

    async def test_search_terms_clipped_to_90_days_and_forced_ortz(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Long ranges clip search terms to trailing 90 days and always request ORTZ."""
        _mock_common(httpx_mock)
        self._mock_reports(httpx_mock)
        clipped_start = TODAY - timedelta(days=SEARCH_TERM_LOOKBACK)
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            result = await fetch_all(client, meta, date(2025, 8, 6), date(2026, 8, 4), today=TODAY)
        assert any("90" in n for n in result.levels["search_terms"].notes)

        st_requests = httpx_mock.get_requests(url=f"{V1_API}/reports/apps/searchterms/query")
        kw_requests = httpx_mock.get_requests(url=f"{V1_API}/reports/apps/keywords/query")
        assert len(st_requests) == 2
        assert len(kw_requests) == 10
        for req in st_requests:
            tr = json.loads(req.content)["timeRange"]
            assert tr["start"] == clipped_start.isoformat()
            assert tr["timeZone"] == "ORTZ"

    async def test_search_terms_entirely_outside_lookback(self, httpx_mock: HTTPXMock) -> None:
        """A range entirely older than the 90-day lookback yields no data, not a crash."""
        _mock_common(httpx_mock)
        self._mock_reports(httpx_mock)
        seen: dict[str, tuple[int, int]] = {}
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            result = await fetch_all(
                client,
                meta,
                date(2025, 1, 1),
                date(2025, 1, 31),
                today=TODAY,
                on_progress=lambda key, done, total: seen.__setitem__(key, (done, total)),
            )

        st = result.levels["search_terms"]
        assert st.daily.empty
        assert any("no search-term data is available" in n for n in st.notes)
        would_be_st_start = TODAY - timedelta(days=SEARCH_TERM_LOOKBACK)
        assert not any(str(would_be_st_start) in n for n in st.notes)
        assert seen["search_terms"] == (0, 0)
        assert not httpx_mock.get_requests(url=f"{V1_API}/reports/apps/searchterms/query")
