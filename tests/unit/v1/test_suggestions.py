"""Tests for the v1 suggestions resource and models."""

import json

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.suggestions import (
    CategorySuggestion,
    KeywordSuggestion,
    PhraseSuggestion,
    SuggestionPromotedObjectType,
    SuggestionQueryType,
    TargetCpaSuggestion,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.suggestions import SuggestionResource

BASE_URL = "https://api.ads.apple.com/v1"


@pytest.fixture(autouse=True)
def _mock_token_endpoint(httpx_mock: HTTPXMock) -> None:
    """Mock Apple's OAuth token endpoint for every test in this module."""
    httpx_mock.add_response(
        url="https://appleid.apple.com/auth/oauth2/token",
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
        is_optional=True,
        is_reusable=True,
    )


class TestKeywordSuggestions:
    """Tests for POST /v1/suggestions/keywords/query."""

    def test_query_keywords_serializes_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query_keywords() posts the documented body and parses rows."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/suggestions/keywords/query",
            json={
                "result": [
                    {"text": "travel planner", "popularity": 87},
                    {"text": "trip organizer", "popularity": 42},
                ],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 2},
            },
        )
        page = SuggestionResource(v1_client).query_keywords(
            Query()
            .where("promotedObjectId", "EQUALS", ["543210012"])
            .where("promotedObjectType", "EQUALS", ["APPSTORE_APP"])
            .where("terms", "IN", ["travel", "trip"])
            .where("countriesOrRegions", "IN", ["US", "GB"])
            .order_by("popularity", "DESC")
            .page(size=20)
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert json.loads(request.content) == {
            "filters": [
                {"field": "promotedObjectId", "operator": "EQUALS", "value": ["543210012"]},
                {"field": "promotedObjectType", "operator": "EQUALS", "value": ["APPSTORE_APP"]},
                {"field": "terms", "operator": "IN", "value": ["travel", "trip"]},
                {"field": "countriesOrRegions", "operator": "IN", "value": ["US", "GB"]},
            ],
            "sorting": [{"field": "popularity", "order": "DESC"}],
            "pagination": {"pageSize": 20},
        }
        assert len(page) == 2
        assert page[0] == KeywordSuggestion(text="travel planner", popularity=87)
        assert page.has_more is False

    async def test_query_keywords_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query_keywords_async() posts to the same path."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/suggestions/keywords/query",
            json={"result": [{"text": "travel planner", "popularity": 87}]},
        )
        page = await SuggestionResource(v1_client).query_keywords_async()
        assert httpx_mock.get_requests()[-1].method == "POST"
        assert page[0].text == "travel planner"


class TestPhraseSuggestions:
    """Tests for POST /v1/suggestions/phrases/query."""

    def test_query_phrases_serializes_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query_phrases() serializes the queryType discovery filter."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/suggestions/phrases/query",
            json={
                "result": [{"phrase": "best travel planning app", "popularity": 63}],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = SuggestionResource(v1_client).query_phrases(
            Query()
            .where("promotedObjectId", "EQUALS", ["543210012"])
            .where("promotedObjectType", "EQUALS", [SuggestionPromotedObjectType.APPSTORE_APP])
            .where("queryType", "EQUALS", [SuggestionQueryType.SUGGESTION])
            .order_by("popularity", "DESC")
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [
                {"field": "promotedObjectId", "operator": "EQUALS", "value": ["543210012"]},
                {"field": "promotedObjectType", "operator": "EQUALS", "value": ["APPSTORE_APP"]},
                {"field": "queryType", "operator": "EQUALS", "value": ["SUGGESTION"]},
            ],
            "sorting": [{"field": "popularity", "order": "DESC"}],
        }
        assert page[0] == PhraseSuggestion(phrase="best travel planning app", popularity=63)

    async def test_query_phrases_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query_phrases_async() parses the bare-array result."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/suggestions/phrases/query",
            json={"result": [{"phrase": "hotel finder", "popularity": 12}]},
        )
        page = await SuggestionResource(v1_client).query_phrases_async()
        assert page[0].phrase == "hotel finder"


class TestCategorySuggestions:
    """Tests for POST /v1/suggestions/categories/query."""

    def test_query_categories_search_route(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the SEARCH route body, which omits promoted-object filters."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/suggestions/categories/query",
            json={
                "result": [{"category": "Productivity", "popularity": 91}],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = SuggestionResource(v1_client).query_categories(
            Query()
            .where("queryType", "EQUALS", [SuggestionQueryType.SEARCH])
            .where("category", "LIKE", ["prod"])
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [
                {"field": "queryType", "operator": "EQUALS", "value": ["SEARCH"]},
                {"field": "category", "operator": "LIKE", "value": ["prod"]},
            ],
        }
        assert page[0] == CategorySuggestion(category="Productivity", popularity=91)
        assert page.has_more is False

    async def test_query_categories_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query_categories_async() posts to the same path."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/suggestions/categories/query",
            json={"result": [{"category": "Restaurants", "popularity": 55}]},
        )
        page = await SuggestionResource(v1_client).query_categories_async()
        assert page[0].category == "Restaurants"


class TestTargetCpaSuggestion:
    """Tests for POST /v1/suggestions/target-cpas/query."""

    def test_query_target_cpa_parses_single_result(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query_target_cpa() parses the single-object result and Money."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/suggestions/target-cpas/query",
            json={
                "result": {
                    "suggestedTargetCPA": {"amount": "3.75", "currency": "USD"},
                    "countryOrRegion": ["US", "CA"],
                    "promotedObjectId": "543210012",
                    "appCategory": "Travel",
                },
                "pagination": None,
            },
        )
        suggestion = SuggestionResource(v1_client).query_target_cpa(
            Query()
            .where("promotedObjectId", "EQUALS", ["543210012"])
            .where("promotedObjectType", "EQUALS", ["APPSTORE_APP"])
            .where("countryOrRegion", "IN", ["US", "CA"])
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert json.loads(request.content) == {
            "filters": [
                {"field": "promotedObjectId", "operator": "EQUALS", "value": ["543210012"]},
                {"field": "promotedObjectType", "operator": "EQUALS", "value": ["APPSTORE_APP"]},
                {"field": "countryOrRegion", "operator": "IN", "value": ["US", "CA"]},
            ],
        }
        assert isinstance(suggestion, TargetCpaSuggestion)
        assert suggestion.suggested_target_cpa is not None
        assert suggestion.suggested_target_cpa.amount == "3.75"
        assert suggestion.suggested_target_cpa.currency == "USD"
        assert suggestion.country_or_region == ["US", "CA"]
        assert suggestion.promoted_object_id == "543210012"
        assert suggestion.app_category == "Travel"

    async def test_query_target_cpa_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query_target_cpa_async() parses the single-object result."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/suggestions/target-cpas/query",
            json={
                "result": {
                    "suggestedTargetCPA": {"amount": "1.50", "currency": "EUR"},
                    "countryOrRegion": ["DE"],
                }
            },
        )
        suggestion = await SuggestionResource(v1_client).query_target_cpa_async()
        assert suggestion.suggested_target_cpa is not None
        assert suggestion.suggested_target_cpa.currency == "EUR"

    def test_http_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx response carrying an error block raises PartialFailureError."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/suggestions/target-cpas/query",
            json={
                "result": None,
                "pagination": None,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "required filter missing",
                    "details": [
                        {
                            "code": "MISSING_REQUIRED_FILTER",
                            "message": "promotedObjectId filter is required",
                            "info": {"field": "promotedObjectId", "location": "filters"},
                        }
                    ],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            SuggestionResource(v1_client).query_target_cpa()
        assert exc_info.value.details[0]["code"] == "MISSING_REQUIRED_FILTER"


class TestModels:
    """Tests for suggestions model and enum behavior."""

    def test_promoted_object_type_enum_round_trip(self) -> None:
        """Test SuggestionPromotedObjectType parses and serializes verbatim."""
        assert SuggestionPromotedObjectType("APPSTORE_APP").value == "APPSTORE_APP"
        assert SuggestionPromotedObjectType("BUSINESS_BRAND").value == "BUSINESS_BRAND"
        assert json.loads(json.dumps(SuggestionPromotedObjectType.BUSINESS_BRAND)) == (
            "BUSINESS_BRAND"
        )

    def test_query_type_enum_round_trip(self) -> None:
        """Test SuggestionQueryType parses and serializes verbatim."""
        assert SuggestionQueryType("SUGGESTION") is SuggestionQueryType.SUGGESTION
        assert SuggestionQueryType("SEARCH") is SuggestionQueryType.SEARCH
        assert json.loads(json.dumps(SuggestionQueryType.SEARCH)) == "SEARCH"

    def test_target_cpa_suggestion_uses_camel_case_aliases(self) -> None:
        """Test TargetCpaSuggestion serializes with documented camelCase aliases."""
        suggestion = TargetCpaSuggestion.model_validate(
            {
                "suggestedTargetCPA": {"amount": "5.00", "currency": "USD"},
                "countryOrRegion": ["US"],
                "promotedObjectId": "1",
                "appCategory": "Games",
            }
        )
        assert suggestion.model_dump(by_alias=True, exclude_none=True) == {
            "suggestedTargetCPA": {"amount": "5.00", "currency": "USD"},
            "countryOrRegion": ["US"],
            "promotedObjectId": "1",
            "appCategory": "Games",
        }

    def test_keyword_suggestion_uses_field_names_and_aliases(self) -> None:
        """Test KeywordSuggestion populates by name and dumps unchanged."""
        suggestion = KeywordSuggestion(text="travel", popularity=100)
        assert suggestion.model_dump(by_alias=True, exclude_none=True) == {
            "text": "travel",
            "popularity": 100,
        }
