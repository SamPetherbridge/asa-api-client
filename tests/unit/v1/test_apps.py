"""Tests for the v1 apps resource and models."""

import json

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import NotFoundError, PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.apps import (
    AppDetails,
    AppInfo,
    AppSupportedLanguages,
    CreativeRejectionReason,
    DeviceClass,
    EligibilityResponse,
    EligibilityState,
    RejectionReasonLevel,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.apps import AppResource

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


class TestSearchApps:
    """Tests for GET /v1/search/apps."""

    def test_search_builds_query_params(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test search() sends GET with the documented query parameters."""
        httpx_mock.add_response(
            url=(
                f"{BASE_URL}/search/apps"
                "?query=AwayFinder&returnOwnedApps=false"
                "&storeFronts=US&storeFronts=GB&offset=0&limit=20"
            ),
            json={
                "result": [
                    {
                        "adamId": 543210012,
                        "appName": "AwayFinder",
                        "developerName": "Example Dev",
                        "countryOrRegionCodes": ["US", "GB"],
                    }
                ],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = AppResource(v1_client).search(
            "AwayFinder",
            return_owned_apps=False,
            store_fronts=["US", "GB"],
            offset=0,
            limit=20,
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "GET"
        assert request.url.params.get_list("storeFronts") == ["US", "GB"]
        assert request.url.params["returnOwnedApps"] == "false"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert len(page) == 1
        assert page[0] == AppInfo(
            adam_id=543210012,
            app_name="AwayFinder",
            developer_name="Example Dev",
            country_or_region_codes=["US", "GB"],
        )
        assert page.has_more is False

    def test_search_joins_cpids_list(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test search() joins a cpids list into a comma-separated param."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/search/apps?cpids=100,200",
            json={"result": []},
        )
        AppResource(v1_client).search(cpids=["100", "200"])
        assert httpx_mock.get_requests()[-1].url.params["cpids"] == "100,200"

    def test_search_owned_apps_only(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test search() with only returnOwnedApps sends no other params."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/search/apps?returnOwnedApps=true",
            json={"result": []},
        )
        AppResource(v1_client).search(return_owned_apps=True)
        params = httpx_mock.get_requests()[-1].url.params
        assert dict(params) == {"returnOwnedApps": "true"}

    async def test_search_async(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test search_async() hits the same endpoint asynchronously."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/search/apps?query=AwayFinder",
            json={
                "result": [
                    {
                        "adamId": 1,
                        "appName": "AwayFinder",
                        "developerName": "Dev",
                        "countryOrRegionCodes": ["US"],
                    }
                ]
            },
        )
        page = await AppResource(v1_client).search_async("AwayFinder")
        assert page[0].adam_id == 1


class TestAppDetails:
    """Tests for GET /v1/apps/{adamId}."""

    def test_get_app_details(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get() fetches and parses one app's App Store details."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/apps/543210012",
            json={
                "result": {
                    "id": "543210012",
                    "appName": "AwayFinder",
                    "artistName": "Example Dev",
                    "primaryLanguage": "en-US",
                    "primaryGenre": ">Mobile Software Applications>Travel",
                    "deviceClasses": ["IPHONE", "IPAD"],
                    "iconPictureUrl": "https://example.com/icon.png",
                    "isPreorder": False,
                    "availableStorefronts": ["US", "GB"],
                }
            },
        )
        details = AppResource(v1_client).get(543210012)
        request = httpx_mock.get_requests()[-1]
        assert request.method == "GET"
        assert details.id == "543210012"
        assert details.device_classes == [DeviceClass.IPHONE, DeviceClass.IPAD]
        assert details.is_preorder is False

    def test_get_app_details_404_raises_not_found(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 404 AppDetailsResponse body raises NotFoundError."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/apps/999",
            status_code=404,
            json={"error": {"code": "ENTITY_NOT_FOUND", "message": "app not found"}},
        )
        with pytest.raises(NotFoundError, match="app not found"):
            AppResource(v1_client).get(999)

    async def test_get_app_details_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test get_async() parses the single-item envelope."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/apps/543210012",
            json={"result": {"id": "543210012", "appName": "AwayFinder"}},
        )
        details = await AppResource(v1_client).get_async(543210012)
        assert details.app_name == "AwayFinder"


class TestSupportedLanguages:
    """Tests for POST /v1/metadata/apps/supported-languages/query."""

    def test_query_supported_languages_serializes_filters(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the query body serializes filters, sorting, and pagination."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/metadata/apps/supported-languages/query",
            json={
                "result": [
                    {
                        "name": "United States",
                        "countryCode": "US",
                        "adsSupportedLanguages": [
                            {"language": "en", "languageCode": "en-US"},
                            {"language": "es", "languageCode": "es-MX"},
                        ],
                        "adsDefaultLanguages": [{"language": "en", "languageCode": "en-US"}],
                    }
                ],
                "pagination": {"offset": 0, "pageSize": 10, "totalCount": 1},
            },
        )
        page = AppResource(v1_client).query_supported_languages(
            Query().where("countryCode", "EQUALS", "US").order_by("name").page(size=10)
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [{"field": "countryCode", "operator": "EQUALS", "value": "US"}],
            "sorting": [{"field": "name", "order": "ASC"}],
            "pagination": {"pageSize": 10},
        }
        market = page[0]
        assert isinstance(market, AppSupportedLanguages)
        assert market.country_code == "US"
        assert market.ads_supported_languages is not None
        assert market.ads_supported_languages[1].language_code == "es-MX"

    def test_query_supported_languages_empty_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test an omitted query posts an empty JSON object."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/metadata/apps/supported-languages/query",
            json={"result": []},
        )
        AppResource(v1_client).query_supported_languages()
        assert json.loads(httpx_mock.get_requests()[-1].content) == {}

    async def test_query_supported_languages_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async variant posts to the same path."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/metadata/apps/supported-languages/query",
            json={"result": [{"name": "Canada", "countryCode": "CA"}]},
        )
        page = await AppResource(v1_client).query_supported_languages_async()
        assert page[0].name == "Canada"


class TestEligibilities:
    """Tests for POST /v1/eligibilities/apps/query."""

    def test_query_eligibilities_serializes_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the eligibility query body and typed row parsing."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/eligibilities/apps/query",
            json={
                "result": [
                    {
                        "adamId": 543210012,
                        "supplyPlacement": "APPSTORE_SEARCH_RESULTS",
                        "supplySource": "APPSTORE",
                        "minAge": 17,
                        "state": "INELIGIBLE",
                        "countryOrRegion": "US",
                        "deviceClass": "IPHONE",
                        "reasons": ["APP_NOT_ELIGIBLE_IN_STOREFRONT"],
                        "creationTime": "2026-02-05T08:30:00.000",
                        "modificationTime": "2026-02-05T08:30:00.000",
                    }
                ],
                "pagination": {"offset": 0, "pageSize": 50, "totalCount": 1},
            },
        )
        page = AppResource(v1_client).query_eligibilities(
            Query()
            .where("adamId", "IN", [543210012])
            .where("countryOrRegion", "EQUALS", "US")
            .page(size=50)
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [
                {"field": "adamId", "operator": "IN", "value": [543210012]},
                {"field": "countryOrRegion", "operator": "EQUALS", "value": "US"},
            ],
            "pagination": {"pageSize": 50},
        }
        row = page[0]
        assert isinstance(row, EligibilityResponse)
        assert row.state is EligibilityState.INELIGIBLE
        assert row.reasons == ["APP_NOT_ELIGIBLE_IN_STOREFRONT"]
        assert row.creation_time is not None
        assert row.creation_time.year == 2026

    def test_http_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx eligibility response carrying an error block raises."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/eligibilities/apps/query",
            json={
                "result": None,
                "error": {
                    "code": "PARTIAL",
                    "message": "some checks failed",
                    "details": [{"code": "INVALID_INPUT", "message": "bad adamId"}],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            AppResource(v1_client).query_eligibilities()
        assert exc_info.value.details[0]["code"] == "INVALID_INPUT"

    async def test_query_eligibilities_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async eligibility query parses rows."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/eligibilities/apps/query",
            json={"result": [{"adamId": 1, "state": "ELIGIBLE"}]},
        )
        page = await AppResource(v1_client).query_eligibilities_async()
        assert page[0].state is EligibilityState.ELIGIBLE


class TestRejectionReasons:
    """Tests for the creative rejection reason endpoints."""

    def test_query_rejection_reasons_serializes_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the rejection reason query body and row parsing."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/rejection-reasons/apps/query",
            json={
                "result": [
                    {
                        "id": 9001,
                        "adamId": 543210012,
                        "creativeId": 77,
                        "productPageId": "pp-1",
                        "assetId": "0a1b2c3d-0000-1111-2222-333344445555",
                        "supplySource": "APPSTORE",
                        "supplyPlacement": "APPSTORE_TODAY_TAB",
                        "countryOrRegion": "US",
                        "languageCode": "en-US",
                        "reasonType": "REJECTION_REASON",
                        "reasonCode": "SCREENSHOT_NOT_REPRESENTATIVE",
                        "comment": "screenshot mismatch",
                        "reasonLevel": "CUSTOM_PRODUCT_PAGE",
                        "creationTime": "2026-02-05T08:30:00.000",
                        "modificationTime": "2026-02-05T08:30:00.000",
                    }
                ],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = AppResource(v1_client).query_rejection_reasons(
            Query().where("adamId", "EQUALS", 543210012).order_by("creationTime", "DESC")
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [{"field": "adamId", "operator": "EQUALS", "value": 543210012}],
            "sorting": [{"field": "creationTime", "order": "DESC"}],
        }
        reason = page[0]
        assert isinstance(reason, CreativeRejectionReason)
        assert reason.id == 9001
        assert reason.creative_id == 77
        assert reason.reason_level is RejectionReasonLevel.CUSTOM_PRODUCT_PAGE

    def test_get_rejection_reason(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get_rejection_reason() fetches one record by ID."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/rejection-reasons/apps/9001",
            json={
                "result": {
                    "id": 9001,
                    "reasonCode": "APP_NOT_ELIGIBLE",
                    "reasonLevel": "DEFAULT_PRODUCT_PAGE",
                }
            },
        )
        reason = AppResource(v1_client).get_rejection_reason(9001)
        assert httpx_mock.get_requests()[-1].method == "GET"
        assert reason.reason_code == "APP_NOT_ELIGIBLE"
        assert reason.reason_level is RejectionReasonLevel.DEFAULT_PRODUCT_PAGE

    async def test_get_rejection_reason_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async single-record fetch."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/rejection-reasons/apps/9001",
            json={"result": {"id": 9001}},
        )
        reason = await AppResource(v1_client).get_rejection_reason_async(9001)
        assert reason.id == 9001


class TestModels:
    """Tests for apps model serialization behavior."""

    def test_eligibility_state_enum_round_trip(self) -> None:
        """Test EligibilityState survives a parse/serialize round trip."""
        row = EligibilityResponse.model_validate({"adamId": 1, "state": "INELIGIBLE"})
        assert row.state is EligibilityState.INELIGIBLE
        dumped = row.model_dump(by_alias=True, exclude_none=True)
        assert dumped["state"] == "INELIGIBLE"
        assert dumped["adamId"] == 1

    def test_device_class_enum_round_trip(self) -> None:
        """Test DeviceClass parses from and serializes to documented values."""
        details = AppDetails.model_validate({"id": "1", "deviceClasses": ["IPAD"]})
        assert details.device_classes == [DeviceClass.IPAD]
        dumped = details.model_dump(by_alias=True, exclude_none=True)
        assert dumped["deviceClasses"] == [DeviceClass.IPAD]
        assert DeviceClass("IPAD").value == "IPAD"

    def test_app_info_uses_camel_case_aliases(self) -> None:
        """Test AppInfo serializes with the documented camelCase aliases."""
        info = AppInfo(
            adam_id=1,
            app_name="A",
            developer_name="D",
            country_or_region_codes=["US"],
        )
        assert info.model_dump(by_alias=True) == {
            "adamId": 1,
            "appName": "A",
            "developerName": "D",
            "countryOrRegionCodes": ["US"],
        }
