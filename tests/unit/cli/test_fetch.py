"""Tests for scope resolution and chunked async report fetching."""

import re
from datetime import date

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client import AppleSearchAdsClient
from asa_api_client.cli.fetch import (
    LevelFetchError,
    ScopeError,
    fetch_all,
    flatten_daily,
    resolve_scope,
)
from asa_api_client.models.reports import ReportingResponse
from tests.unit.cli.conftest import (
    API,
    TOKEN_URL,
    campaigns_json,
    report_json,
    report_row,
    token_json,
)

START, END = date(2026, 7, 1), date(2026, 7, 2)
TODAY = date(2026, 8, 5)


def _client() -> AppleSearchAdsClient:
    return AppleSearchAdsClient.from_env(env_file=None)


def _mock_common(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=TOKEN_URL, json=token_json(), is_reusable=True)
    httpx_mock.add_response(
        url=f"{API}/campaigns?limit=1000&offset=0", json=campaigns_json(), is_reusable=True
    )
    httpx_mock.add_response(
        url=re.compile(rf"{API}/search/apps\?.*"), json={"data": []}, is_reusable=True
    )


class TestFlattenDaily:
    """flatten_daily: one row per entity-day from the granularity array."""

    def test_explodes_granularity(self) -> None:
        """Two days become two rows carrying metadata and date."""
        resp = ReportingResponse.model_validate(
            report_json(
                [
                    report_row(
                        {"campaignId": 1, "campaignName": "One"},
                        [("2026-07-01", 100, 10, 1, "5.0"), ("2026-07-02", 200, 20, 2, "10.0")],
                    )
                ]
            )["data"]["reportingDataResponse"]
        )
        df = flatten_daily(resp)
        assert len(df) == 2
        assert df["date"].tolist() == ["2026-07-01", "2026-07-02"]
        assert df["local_spend"].tolist() == ["5.0", "10.0"]
        assert df["campaign_id"].tolist() == [1, 1]

    def test_empty_response(self) -> None:
        """No rows → empty frame."""
        resp = ReportingResponse.model_validate({"row": []})
        assert flatten_daily(resp).empty


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
@pytest.mark.usefixtures("asa_env")
class TestResolveScope:
    """resolve_scope: campaign metadata map + currency."""

    def test_all_apps(self, httpx_mock: HTTPXMock) -> None:
        """Without --app, every campaign is in scope; currency inferred."""
        _mock_common(httpx_mock)
        client = _client()
        try:
            meta, currency = resolve_scope(client, None)
        finally:
            client.close()
        assert sorted(meta["campaign_id"]) == [1, 2]
        assert currency == "USD"
        assert meta.loc[meta["adam_id"] == 111, "app_name"].iloc[0] == "App 111"

    def test_app_filter(self, httpx_mock: HTTPXMock) -> None:
        """--app filters campaigns by adam_id."""
        _mock_common(httpx_mock)
        client = _client()
        try:
            meta, _ = resolve_scope(client, [111])
        finally:
            client.close()
        assert meta["campaign_id"].tolist() == [1]

    def test_no_match_raises(self, httpx_mock: HTTPXMock) -> None:
        """An adam_id with no campaigns raises ScopeError."""
        _mock_common(httpx_mock)
        client = _client()
        try:
            with pytest.raises(ScopeError):
                resolve_scope(client, [999])
        finally:
            client.close()


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
@pytest.mark.usefixtures("asa_env")
class TestFetchAll:
    """fetch_all: five levels + prior period, failure tolerance."""

    def _mock_reports(self, httpx_mock: HTTPXMock) -> None:
        rows = [
            report_row(
                {"campaignId": 1, "campaignName": "One"},
                [("2026-07-01", 100, 10, 1, "5.0"), ("2026-07-02", 100, 10, 1, "5.0")],
            )
        ]
        httpx_mock.add_response(
            url=f"{API}/reports/campaigns", json=report_json(rows), is_reusable=True
        )
        for cid in (1, 2):
            for tail in ("adgroups", "keywords", "searchterms", "ads"):
                httpx_mock.add_response(
                    url=f"{API}/reports/campaigns/{cid}/{tail}",
                    json=report_json(rows),
                    is_reusable=True,
                )

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

    async def test_progress_callback(self, httpx_mock: HTTPXMock) -> None:
        """on_progress fires with (key, done, total) and reaches total."""
        _mock_common(httpx_mock)
        self._mock_reports(httpx_mock)
        seen: dict[str, tuple[int, int]] = {}
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            await fetch_all(
                client, meta, START, END, today=TODAY,
                on_progress=lambda key, done, total: seen.__setitem__(key, (done, total)),
            )
        assert seen["campaigns"] == (2, 2)  # current + prior window
        assert seen["keywords"] == (2, 2)  # one window x two campaigns

    async def test_chunk_failure_warns_and_continues(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """A failing per-campaign chunk becomes a warning + note, not a crash.

        The failure response is registered BEFORE the reusable success
        mocks: pytest-httpx matches responses in registration order, so a
        reusable success registered first would shadow the failure forever.
        """
        _mock_common(httpx_mock)
        httpx_mock.add_response(
            url=f"{API}/reports/campaigns/2/keywords", status_code=400,
            json={"error": {"errors": [{"message": "boom"}]}}, is_reusable=True,
        )
        self._mock_reports(httpx_mock)
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            result = await fetch_all(client, meta, START, END, today=TODAY)
        assert any("Keywords" in w for w in result.warnings)
        assert result.levels["keywords"].notes
        assert not result.levels["keywords"].daily.empty  # campaign 1 still there

    async def test_whole_level_failure_raises(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Every chunk of a level failing aborts the run with context.

        Failure mocks registered first — see the note on the previous test.
        """
        _mock_common(httpx_mock)
        for cid in (1, 2):
            httpx_mock.add_response(
                url=f"{API}/reports/campaigns/{cid}/ads", status_code=400,
                json={"error": {"errors": [{"message": "no ads"}]}}, is_reusable=True,
            )
        self._mock_reports(httpx_mock)
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            with pytest.raises(LevelFetchError, match="Ads"):
                await fetch_all(client, meta, START, END, today=TODAY)

    async def test_search_terms_clipped_to_90_days(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Long ranges clip search terms to trailing 90 days with a note."""
        _mock_common(httpx_mock)
        self._mock_reports(httpx_mock)
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            result = await fetch_all(
                client, meta, date(2025, 8, 6), date(2026, 8, 4), today=TODAY
            )
        assert any("90" in n for n in result.levels["search_terms"].notes)
