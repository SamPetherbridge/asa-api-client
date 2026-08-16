"""Tests for the v1 geo targeting search resource."""

import json

import httpx
import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import ConfigurationError, PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.geo import (
    GeoBlockedReason,
    GeoEntityType,
    GeoRequest,
    GeoSearchPagination,
    GeoSearchPostRequest,
    SearchEntity,
    SearchSupplySourceType,
)
from asa_api_client.v1.resources.geo import GeoResource

BASE_URL = "https://api.ads.apple.com/v1"
GEO_URL = f"{BASE_URL}/search/geo"


@pytest.fixture(autouse=True)
def _mock_token_endpoint(httpx_mock: HTTPXMock) -> None:
    """Mock the Apple OAuth token endpoint for every test."""
    httpx_mock.add_response(
        url="https://appleid.apple.com/auth/oauth2/token",
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
        is_optional=True,
        is_reusable=True,
    )


SAN_FRANCISCO = {
    "id": "11390462",
    "legacyId": "US|CA|San Francisco",
    "entity": "Locality",
    "displayName": "San Francisco, California, United States",
    "countryOrRegion": "US",
    "adminArea": "CA",
    "locality": "San Francisco",
}

SPARSE_POSTAL_CODE = {
    "id": "12345678",
    "legacyId": "US|TX|78238",
    "entity": "PostalCode",
    "displayName": "78238, Texas, United States",
    "countryOrRegion": "US",
    "adminArea": "TX",
    "postalCode": "78238",
    "eligibility": {
        "blockedGroups": [{"supplySource": ["MAPS"], "reasons": ["POSTAL_CODE_SPARSE"]}]
    },
}


class TestSearch:
    """Tests for GET /v1/search/geo."""

    def test_search_sends_all_query_params(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test search() GETs /search/geo with every documented parameter."""
        httpx_mock.add_response(
            url=httpx.URL(
                GEO_URL,
                params={
                    "supplySource": "MAPS",
                    "query": "san",
                    "entity": "Locality",
                    "countrycode": "US",
                    "eligible": "true",
                    "offset": "0",
                    "pageSize": "10",
                },
            ),
            json={
                "result": [SAN_FRANCISCO],
                "pagination": {"totalCount": 1, "offset": 0, "pageSize": 10},
            },
        )
        page = GeoResource(v1_client).search(
            supply_source=SearchSupplySourceType.MAPS,
            query="san",
            entity=GeoEntityType.LOCALITY,
            country_code="US",
            eligible=True,
            offset=0,
            page_size=10,
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "GET"
        assert len(page) == 1
        assert page[0].locality == "San Francisco"

    def test_search_with_only_supply_source(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test search() omits every unset optional query parameter."""
        httpx_mock.add_response(
            url=httpx.URL(GEO_URL, params={"supplySource": "APPSTORE"}),
            json={"result": [], "pagination": {"totalCount": 0, "offset": 0, "pageSize": 20}},
        )
        page = GeoResource(v1_client).search(supply_source="APPSTORE")
        request = httpx_mock.get_requests()[-1]
        assert dict(request.url.params) == {"supplySource": "APPSTORE"}
        assert len(page) == 0

    def test_search_sends_account_context_header(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test search() sends the required X-AP-Context header."""
        httpx_mock.add_response(
            url=httpx.URL(GEO_URL, params={"supplySource": "APPSTORE"}),
            json={"result": []},
        )
        GeoResource(v1_client).search(supply_source="APPSTORE")
        request = httpx_mock.get_requests()[-1]
        assert request.headers["X-AP-Context"] == "adAccountId=12345"

    def test_search_requires_account_context(self, ec_private_key_pem: str) -> None:
        """Test search() raises ConfigurationError without an ad_account_id."""
        client = AppleAdsClient(
            client_id="SEARCHADS.test",
            team_id="TEAM123",
            key_id="KEY123",
            private_key=ec_private_key_pem,
        )
        with pytest.raises(ConfigurationError, match="ad_account_id"):
            GeoResource(client).search(supply_source="APPSTORE")

    def test_search_parses_entities_and_eligibility(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test search() parses SearchEntity rows including eligibility."""
        httpx_mock.add_response(
            url=httpx.URL(GEO_URL, params={"supplySource": "MAPS"}),
            json={
                "result": [SAN_FRANCISCO, SPARSE_POSTAL_CODE],
                "pagination": {"totalCount": 2, "offset": 0, "pageSize": 20},
            },
        )
        page = GeoResource(v1_client).search(supply_source="MAPS")
        city, postal = page[0], page[1]
        assert isinstance(city, SearchEntity)
        assert city.id == "11390462"
        assert city.legacy_id == "US|CA|San Francisco"
        assert city.display_name == "San Francisco, California, United States"
        assert city.eligibility is None
        assert postal.postal_code == "78238"
        assert postal.eligibility is not None
        blocked = postal.eligibility.blocked_groups
        assert blocked is not None
        assert blocked[0].supply_source == [SearchSupplySourceType.MAPS]
        assert blocked[0].reasons == [GeoBlockedReason.POSTAL_CODE_SPARSE]

    def test_search_pagination_has_more(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test search() pagination exposes totalCount-driven has_more."""
        httpx_mock.add_response(
            url=httpx.URL(GEO_URL, params={"supplySource": "APPSTORE"}),
            json={
                "result": [SAN_FRANCISCO],
                "pagination": {"totalCount": 5, "offset": 0, "pageSize": 1},
            },
        )
        page = GeoResource(v1_client).search(supply_source="APPSTORE")
        assert page.has_more is True

    async def test_search_async(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test search_async() GETs /search/geo and parses results."""
        httpx_mock.add_response(
            url=httpx.URL(GEO_URL, params={"supplySource": "APPSTORE", "query": "united"}),
            json={"result": [SAN_FRANCISCO]},
        )
        page = await GeoResource(v1_client).search_async(supply_source="APPSTORE", query="united")
        assert httpx_mock.get_requests()[-1].method == "GET"
        assert page[0].entity is GeoEntityType.LOCALITY

    def test_search_200_with_error_block_raises(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 200 response carrying an error block raises PartialFailureError."""
        httpx_mock.add_response(
            url=httpx.URL(GEO_URL, params={"supplySource": "APPSTORE", "query": "a"}),
            json={
                "result": None,
                "error": {
                    "code": "MIN_QUERY_LENGTH",
                    "message": "query must be at least 2 characters",
                    "details": [{"code": "MIN_QUERY_LENGTH", "message": "too short"}],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            GeoResource(v1_client).search(supply_source="APPSTORE", query="a")
        assert exc_info.value.details[0]["code"] == "MIN_QUERY_LENGTH"


class TestLookup:
    """Tests for POST /v1/search/geo."""

    def test_lookup_posts_exact_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test lookup() POSTs the documented GeoSearchPostRequest body."""
        httpx_mock.add_response(
            url=GEO_URL,
            json={
                "result": [SAN_FRANCISCO],
                "pagination": {"totalCount": 1, "offset": 0, "pageSize": 20},
            },
        )
        request_model = GeoSearchPostRequest(
            geo_request=[
                GeoRequest(id="123456789", entity=GeoEntityType.ADMIN_AREA),
                GeoRequest(legacy_id="US|CA|San Francisco", entity=GeoEntityType.LOCALITY),
            ],
            supply_source=SearchSupplySourceType.APPSTORE,
            pagination=GeoSearchPagination(offset=0, page_size=20),
        )
        page = GeoResource(v1_client).lookup(request_model)
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "geoRequest": [
                {"id": "123456789", "entity": "AdminArea"},
                {"legacyId": "US|CA|San Francisco", "entity": "Locality"},
            ],
            "supplySource": "APPSTORE",
            "pagination": {"offset": 0, "pageSize": 20},
        }
        assert page[0].id == "11390462"

    def test_lookup_omits_unset_pagination(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test lookup() drops pagination from the body when not provided."""
        httpx_mock.add_response(url=GEO_URL, json={"result": []})
        request_model = GeoSearchPostRequest(
            geo_request=[GeoRequest(id="1", entity=GeoEntityType.COUNTRY)],
            supply_source="MAPS",
        )
        GeoResource(v1_client).lookup(request_model)
        assert json.loads(httpx_mock.get_requests()[-1].content) == {
            "geoRequest": [{"id": "1", "entity": "Country"}],
            "supplySource": "MAPS",
        }

    async def test_lookup_async(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test lookup_async() POSTs the body and parses the page."""
        httpx_mock.add_response(url=GEO_URL, json={"result": [SPARSE_POSTAL_CODE]})
        request_model = GeoSearchPostRequest(
            geo_request=[GeoRequest(legacy_id="US|TX|78238", entity=GeoEntityType.POSTAL_CODE)],
            supply_source=SearchSupplySourceType.MAPS,
        )
        page = await GeoResource(v1_client).lookup_async(request_model)
        assert httpx_mock.get_requests()[-1].method == "POST"
        assert page[0].entity is GeoEntityType.POSTAL_CODE

    def test_lookup_200_with_error_block_raises(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test lookup() raises PartialFailureError on 2xx error blocks."""
        httpx_mock.add_response(
            url=GEO_URL,
            json={"result": None, "error": {"message": "bad geo request"}},
        )
        request_model = GeoSearchPostRequest(
            geo_request=[GeoRequest(id="1", entity=GeoEntityType.COUNTRY)],
            supply_source="APPSTORE",
        )
        with pytest.raises(PartialFailureError, match="bad geo request"):
            GeoResource(v1_client).lookup(request_model)


class TestEnums:
    """Tests for geo enum round trips."""

    def test_geo_entity_type_round_trip(self) -> None:
        """Test GeoEntityType parses from and serializes to CamelCase values."""
        entity = SearchEntity.model_validate({"entity": "AdminArea"})
        assert entity.entity is GeoEntityType.ADMIN_AREA
        assert entity.model_dump(by_alias=True, exclude_none=True) == {"entity": "AdminArea"}
        assert GeoEntityType("PostalCode") is GeoEntityType.POSTAL_CODE

    def test_supply_source_round_trip(self) -> None:
        """Test SearchSupplySourceType round-trips through a request model."""
        request_model = GeoSearchPostRequest(
            geo_request=[GeoRequest(id="1", entity="Country")],
            supply_source="MAPS",
        )
        assert request_model.supply_source is SearchSupplySourceType.MAPS
        dumped = request_model.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped["supplySource"] == "MAPS"

    def test_blocked_reason_values(self) -> None:
        """Test GeoBlockedReason covers the complete documented value list."""
        assert {reason.value for reason in GeoBlockedReason} == {
            "NO_MUID",
            "NOT_SUPPORTED",
            "SOURCE_REMOVED",
            "COUNTRY_NOT_SUPPORTED",
            "COUNTRY_NOT_SEARCHABLE",
            "MAPS_SOURCE_NOT_MATCHED",
            "LOCALITY_LOW_SEARCH_VOLUME",
            "POSTAL_CODE_SPARSE",
        }
