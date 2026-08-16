"""Tests for the v1 product pages resource and models."""

import json

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.product_pages import (
    AppLocaleDetails,
    DeviceClass,
    ProductPageDetails,
    ProductPageLocaleDetails,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.product_pages import ProductPageResource

BASE_URL = "https://api.ads.apple.com/v1"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"

PAGE_ID = "45812c9b-c296-43aa-bd6e-6912b514b748"


def mock_token(httpx_mock: HTTPXMock) -> None:
    """Register a mocked OAuth token response."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
    )


def product_page_json() -> dict[str, object]:
    """Return a sample ProductPageDetails response object."""
    return {
        "id": PAGE_ID,
        "adamId": 1053807572,
        "name": "Custom Product Page 1",
        "state": "PUBLISHED",
        "deepLink": "https://example.com/promo",
        "creationTime": "2025-01-10T08:00:00.000",
        "modificationTime": "2025-01-11T09:30:00.000",
    }


def locale_details_json() -> dict[str, object]:
    """Return a sample ProductPageLocaleDetails response object."""
    return {
        "adamId": 1053807572,
        "language": "en",
        "languageCode": "en-US",
        "appName": "Example App",
        "subTitle": "Do the thing",
        "promotionalText": "Now with more things",
        "shortDescription": "An app that does things.",
        "deviceClasses": ["IPHONE", "IPAD"],
        "assetsByDevice": {
            "iphone_6_5": {
                "assets": [{"assetId": "b3d4a6c1-1111-2222-3333-444455556666"}],
                "appPreviewDeviceFallBackDevices": ["iphone6", "iphone5"],
            }
        },
        "productPageId": PAGE_ID,
    }


class TestGetProductPage:
    """Tests for GET /v1/product-pages/{productPageId}."""

    def test_get_product_page(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get() hits the item URL and parses the result."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/product-pages/{PAGE_ID}",
            json={"result": product_page_json()},
        )
        page = ProductPageResource(v1_client).get(PAGE_ID)
        request = httpx_mock.get_requests()[-1]
        assert request.method == "GET"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert page.id == PAGE_ID
        assert page.adam_id == 1053807572
        assert page.name == "Custom Product Page 1"
        assert page.state == "PUBLISHED"
        assert page.deep_link == "https://example.com/promo"
        assert page.creation_time is not None
        assert page.creation_time.year == 2025

    async def test_get_product_page_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test get_async() parses the single-item envelope."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/product-pages/{PAGE_ID}",
            json={"result": product_page_json()},
        )
        page = await ProductPageResource(v1_client).get_async(PAGE_ID)
        assert page.id == PAGE_ID

    def test_state_is_plain_string_not_enum(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test undocumented states parse fine because state is a str."""
        mock_token(httpx_mock)
        body = product_page_json()
        body["state"] = "READY_FOR_DISTRIBUTION"
        httpx_mock.add_response(
            url=f"{BASE_URL}/product-pages/{PAGE_ID}",
            json={"result": body},
        )
        page = ProductPageResource(v1_client).get(PAGE_ID)
        assert page.state == "READY_FOR_DISTRIBUTION"


class TestQueryProductPages:
    """Tests for POST /v1/product-pages/query."""

    def test_query_serializes_filters(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query() POSTs the exact unwrapped query body."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/product-pages/query",
            json={
                "result": [product_page_json()],
                "pagination": {"offset": 0, "pageSize": 10, "totalCount": 1},
            },
        )
        page = ProductPageResource(v1_client).query(
            Query()
            .where("adamId", "EQUALS", 1053807572)
            .where("state", "EQUALS", "PUBLISHED")
            .page(size=10)
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [
                {"field": "adamId", "operator": "EQUALS", "value": 1053807572},
                {"field": "state", "operator": "EQUALS", "value": "PUBLISHED"},
            ],
            "pagination": {"pageSize": 10},
        }
        assert len(page) == 1
        assert isinstance(page[0], ProductPageDetails)
        assert page[0].adam_id == 1053807572
        assert page.has_more is False

    async def test_query_async(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test query_async() parses the paged envelope."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/product-pages/query",
            json={"result": [product_page_json()]},
        )
        page = await ProductPageResource(v1_client).query_async()
        assert page[0].id == PAGE_ID

    def test_http_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx response carrying an error block raises."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/product-pages/query",
            json={
                "result": None,
                "error": {
                    "code": "INVALID_FILTER",
                    "message": "productPageId filter is required",
                    "details": [{"code": "MISSING_FILTER", "message": "bad"}],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            ProductPageResource(v1_client).query()
        assert exc_info.value.details[0]["code"] == "MISSING_FILTER"


class TestQueryLocaleDetails:
    """Tests for POST /v1/product-pages/locale-details/query."""

    def test_query_locale_details(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test the locale-details URL, body, and typed parsing."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/product-pages/locale-details/query",
            json={
                "result": [locale_details_json()],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = ProductPageResource(v1_client).query_locale_details(
            Query().where("productPageId", "EQUALS", PAGE_ID)
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [{"field": "productPageId", "operator": "EQUALS", "value": PAGE_ID}],
        }
        detail = page[0]
        assert isinstance(detail, ProductPageLocaleDetails)
        assert detail.product_page_id == PAGE_ID
        assert detail.language_code == "en-US"
        assert detail.app_name == "Example App"
        assert detail.sub_title == "Do the thing"
        assert detail.device_classes == [DeviceClass.IPHONE, DeviceClass.IPAD]
        assert detail.assets_by_device is not None
        group = detail.assets_by_device["iphone_6_5"]
        assert group.assets is not None
        assert group.assets[0].asset_id == "b3d4a6c1-1111-2222-3333-444455556666"
        assert group.app_preview_device_fall_back_devices == ["iphone6", "iphone5"]
        assert page.pagination is not None
        assert page.pagination.total_count == 1

    async def test_query_locale_details_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async locale-details query parses identically."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/product-pages/locale-details/query",
            json={"result": [locale_details_json()]},
        )
        page = await ProductPageResource(v1_client).query_locale_details_async(
            Query().where("productPageId", "EQUALS", PAGE_ID)
        )
        assert page[0].promotional_text == "Now with more things"


class TestQueryAppLocaleDetails:
    """Tests for POST /v1/apps/{adamId}/locale-details/query."""

    def test_query_app_locale_details(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the apps-rooted URL and AppLocaleDetails parsing."""
        mock_token(httpx_mock)
        body = locale_details_json()
        del body["productPageId"]
        body["isPrimaryLocale"] = True
        httpx_mock.add_response(
            url=f"{BASE_URL}/apps/1053807572/locale-details/query",
            json={
                "result": [body],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = ProductPageResource(v1_client).query_app_locale_details(
            1053807572, Query().where("languageCode", "EQUALS", "en-US")
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [{"field": "languageCode", "operator": "EQUALS", "value": "en-US"}],
        }
        detail = page[0]
        assert isinstance(detail, AppLocaleDetails)
        assert detail.is_primary_locale is True
        assert detail.adam_id == 1053807572
        assert detail.device_classes == [DeviceClass.IPHONE, DeviceClass.IPAD]

    def test_query_app_locale_details_without_query_posts_empty_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test omitting the query posts an empty JSON object."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/apps/1053807572/locale-details/query",
            json={"result": []},
        )
        ProductPageResource(v1_client).query_app_locale_details(1053807572)
        assert json.loads(httpx_mock.get_requests()[-1].content) == {}

    async def test_query_app_locale_details_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async app locale-details query."""
        mock_token(httpx_mock)
        body = locale_details_json()
        del body["productPageId"]
        body["isPrimaryLocale"] = False
        httpx_mock.add_response(
            url=f"{BASE_URL}/apps/1053807572/locale-details/query",
            json={"result": [body]},
        )
        page = await ProductPageResource(v1_client).query_app_locale_details_async(1053807572)
        assert page[0].is_primary_locale is False


class TestEnums:
    """Tests for enum round-trips."""

    def test_device_class_round_trip(self) -> None:
        """Test DeviceClass values round-trip through the model."""
        detail = ProductPageLocaleDetails.model_validate({"deviceClasses": ["IPHONE", "IPAD"]})
        assert detail.device_classes == [DeviceClass.IPHONE, DeviceClass.IPAD]
        dumped = detail.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped == {"deviceClasses": ["IPHONE", "IPAD"]}
        assert DeviceClass("IPHONE") is DeviceClass.IPHONE
