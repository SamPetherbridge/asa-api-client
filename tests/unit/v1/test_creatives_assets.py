"""Tests for the v1 creatives and assets resources."""

import io
import json

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.creatives import (
    Asset,
    AssetEligibilityStatus,
    AssetReference,
    AssetType,
    CreativeCreate,
    CreativeSpec,
    CreativeSystemStatus,
    CreativeType,
    CreativeUpdate,
    DestinationCreate,
    DestinationParameter,
    DestinationType,
    ImageType,
    LocalizedPromoText,
    Orientation,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.creatives import AssetResource, CreativeResource

BASE_URL = "https://api.ads.apple.com/v1"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"


def mock_token(httpx_mock: HTTPXMock) -> None:
    """Register a mocked OAuth token response."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
    )


class TestCreativeResource:
    """Tests for CreativeResource endpoints."""

    def test_create_creative_serializes_exact_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test POST /v1/creatives sends the unwrapped documented body."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/creatives",
            json={
                "result": {
                    "id": 1234567,
                    "adAccountId": 12345,
                    "name": "AwayFinder - Summer Campaign Creative",
                    "creativeType": "CUSTOM_PRODUCT_PAGE",
                    "creativeSpec": {},
                    "destination": {
                        "destinationType": "APP_STORE_PRODUCT_PAGE",
                        "parameters": {
                            "adamId": "987654321",
                            "productPageId": "76659d7a-d146-43d3-b6b8-b7a12f74bf6b",
                        },
                    },
                    "systemStatus": "PENDING",
                }
            },
        )
        creative = CreativeResource(v1_client).create(
            CreativeCreate(
                name="AwayFinder - Summer Campaign Creative",
                creative_type=CreativeType.CUSTOM_PRODUCT_PAGE,
                creative_spec=CreativeSpec(),
                destination=DestinationCreate(
                    destination_type=DestinationType.APP_STORE_PRODUCT_PAGE,
                    parameters=DestinationParameter(
                        adam_id="987654321",
                        product_page_id="76659d7a-d146-43d3-b6b8-b7a12f74bf6b",
                    ),
                ),
            )
        )
        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {
            "name": "AwayFinder - Summer Campaign Creative",
            "creativeType": "CUSTOM_PRODUCT_PAGE",
            "creativeSpec": {},
            "destination": {
                "destinationType": "APP_STORE_PRODUCT_PAGE",
                "parameters": {
                    "adamId": "987654321",
                    "productPageId": "76659d7a-d146-43d3-b6b8-b7a12f74bf6b",
                },
            },
        }
        assert creative.id == 1234567
        assert creative.system_status is CreativeSystemStatus.PENDING

    def test_create_local_ads_creative_serializes_spec(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the Apple Maps creativeSpec serializes with camelCase aliases."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/creatives",
            json={"result": {"id": 99, "creativeType": "LOCAL_ADS_SEARCH_CREATIVE"}},
        )
        CreativeResource(v1_client).create(
            CreativeCreate(
                name="AwayFinder - Store Promotion Creative",
                creative_type="LOCAL_ADS_SEARCH_CREATIVE",
                creative_spec=CreativeSpec(
                    brand_id="111222",
                    creative_subtype="BUSINESS_ASSET",
                    creative_assets=[
                        AssetReference(asset_id="770e8400-e29b-41d4-a716-446655440002")
                    ],
                    localized_text={
                        "en-US": LocalizedPromoText(promo_text="Visit us today for special offers!")
                    },
                    default_locale="en-US",
                ),
                destination=DestinationCreate(destination_type=DestinationType.LOCAL_ADS_PLACECARD),
            )
        )
        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {
            "name": "AwayFinder - Store Promotion Creative",
            "creativeType": "LOCAL_ADS_SEARCH_CREATIVE",
            "creativeSpec": {
                "brandId": "111222",
                "creativeSubtype": "BUSINESS_ASSET",
                "creativeAssets": [{"assetId": "770e8400-e29b-41d4-a716-446655440002"}],
                "localizedText": {"en-US": {"promoText": "Visit us today for special offers!"}},
                "defaultLocale": "en-US",
            },
            "destination": {"destinationType": "LOCAL_ADS_PLACECARD"},
        }

    def test_get_creative_parses_full_object(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test GET /v1/creatives/{id} parses status, spec, and eligibility."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/creatives/1234567",
            json={
                "result": {
                    "id": 1234567,
                    "adAccountId": 12345,
                    "name": "Test Creative",
                    "creativeType": "DEFAULT_PRODUCT_PAGE",
                    "creativeSpec": {},
                    "destination": {
                        "destinationType": "APP_STORE_PRODUCT_PAGE",
                        "parameters": {"adamId": "987654321"},
                        "url": "https://apps.apple.com/app/id987654321",
                    },
                    "systemStatus": "VALID",
                    "systemStatusReasons": ["NEEDS_REVIEW"],
                    "creationTime": "2026-01-01T00:00:00.000Z",
                    "modificationTime": "2026-01-02T00:00:00.000Z",
                    "eligibility": {
                        "status": "ELIGIBLE",
                        "allowedGroups": [
                            {
                                "supplyPlacement": ["APPSTORE_SEARCH_TAB"],
                                "countryOrRegion": ["US", "GB"],
                            }
                        ],
                        "blockedGroups": [],
                    },
                    "deleted": False,
                }
            },
        )
        creative = CreativeResource(v1_client).get(1234567)
        request = httpx_mock.get_requests()[-1]
        assert request.method == "GET"
        assert creative.creative_type is CreativeType.DEFAULT_PRODUCT_PAGE
        assert creative.system_status is CreativeSystemStatus.VALID
        assert creative.destination is not None
        assert creative.destination.url == "https://apps.apple.com/app/id987654321"
        assert creative.eligibility is not None
        assert creative.eligibility.status == "ELIGIBLE"
        assert creative.eligibility.allowed_groups is not None
        assert creative.eligibility.allowed_groups[0].country_or_region == ["US", "GB"]
        assert creative.deleted is False

    def test_query_creatives_serializes_filters(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test POST /v1/creatives/query sends filters and parses a page."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/creatives/query",
            json={
                "result": [
                    {"id": 1, "name": "A", "creativeType": "CUSTOM_PRODUCT_PAGE"},
                    {"id": 2, "name": "B", "creativeType": "DEFAULT_PRODUCT_PAGE"},
                ],
                "pagination": {"offset": 0, "pageSize": 10, "totalCount": 2},
            },
        )
        page = CreativeResource(v1_client).query(
            Query().where("creativeType", "EQUALS", "CUSTOM_PRODUCT_PAGE").page(size=10)
        )
        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {
            "filters": [
                {"field": "creativeType", "operator": "EQUALS", "value": "CUSTOM_PRODUCT_PAGE"}
            ],
            "pagination": {"pageSize": 10},
        }
        assert len(page) == 2
        assert not page.has_more
        assert page[0].creative_type is CreativeType.CUSTOM_PRODUCT_PAGE

    def test_update_creative_sends_only_set_fields(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test PUT /v1/creatives/{id} sends an unwrapped partial body."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="PUT",
            url=f"{BASE_URL}/creatives/1234567",
            json={"result": {"id": 1234567, "name": "Renamed", "systemStatus": "PENDING"}},
        )
        creative = CreativeResource(v1_client).update(1234567, CreativeUpdate(name="Renamed"))
        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {"name": "Renamed"}
        assert creative.name == "Renamed"

    def test_delete_creative(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test DELETE /v1/creatives/{id} issues the right request."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="DELETE",
            url=f"{BASE_URL}/creatives/1234567",
            json={"result": None},
        )
        CreativeResource(v1_client).delete(1234567)
        request = httpx_mock.get_requests()[-1]
        assert request.method == "DELETE"
        assert str(request.url) == f"{BASE_URL}/creatives/1234567"

    def test_http_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx creative response carrying an error block raises."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/creatives/7",
            json={
                "result": None,
                "error": {
                    "code": "CREATIVE_ERROR",
                    "message": "creative processing failed",
                    "details": [{"code": "MISSING_ASSET", "message": "asset gone"}],
                },
            },
        )
        with pytest.raises(PartialFailureError, match="creative processing failed"):
            CreativeResource(v1_client).get(7)

    async def test_get_creative_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async get variant hits the same endpoint."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/creatives/55",
            json={"result": {"id": 55, "creativeType": "CUSTOM_PRODUCT_PAGE"}},
        )
        creative = await CreativeResource(v1_client).get_async(55)
        assert creative.id == 55


class TestAssetResource:
    """Tests for AssetResource endpoints."""

    def test_upload_retries_transient_5xx(
        self,
        httpx_mock: HTTPXMock,
        v1_client: AppleAdsClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test uploads retry on 503 and re-send the file bytes."""
        monkeypatch.setattr("asa_api_client.v1.resources.base.time.sleep", lambda _: None)
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/assets/upload",
            status_code=503,
            json={"error": {"message": "temporarily unavailable"}},
        )
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/assets/upload",
            json={"result": {"id": "770e8400-e29b-41d4-a716-446655440002", "assetType": "IMAGE"}},
        )
        asset = AssetResource(v1_client).upload(io.BytesIO(b"png-bytes"), promoted_object_id="42")
        assert asset.id == "770e8400-e29b-41d4-a716-446655440002"
        retried = httpx_mock.get_requests(url=f"{BASE_URL}/assets/upload")[1]
        assert b"png-bytes" in retried.content

    def test_upload_asset_sends_multipart(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test POST /v1/assets/upload sends multipart/form-data parts."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/assets/upload",
            json={
                "result": {
                    "id": "770e8400-e29b-41d4-a716-446655440002",
                    "assetType": "IMAGE",
                    "providerAssetId": "prov-123",
                    "promotedObjectId": "111222",
                    "promotedObjectType": "BUSINESS_BRAND",
                }
            },
        )
        asset = AssetResource(v1_client).upload(
            b"\x89PNG-fake-bytes",
            promoted_object_id="111222",
            file_name="logo.png",
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert str(request.url) == f"{BASE_URL}/assets/upload"
        assert request.headers["Content-Type"].startswith("multipart/form-data")
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        content = request.content
        assert b'name="file"' in content
        assert b"logo.png" in content
        assert b'name="promotedObjectId"' in content
        assert b"111222" in content
        assert b'name="promotedObjectType"' in content
        assert b"BUSINESS_BRAND" in content
        assert asset.id == "770e8400-e29b-41d4-a716-446655440002"
        assert asset.asset_type is AssetType.IMAGE

    async def test_upload_asset_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async upload variant sends the same multipart request."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/assets/upload",
            json={"result": {"id": "abc-123", "assetType": "IMAGE"}},
        )
        asset = await AssetResource(v1_client).upload_async(
            b"fake-image",
            promoted_object_id="111222",
        )
        request = httpx_mock.get_requests()[-1]
        assert request.headers["Content-Type"].startswith("multipart/form-data")
        assert asset.id == "abc-123"

    def test_get_asset_parses_details_and_eligibility(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test GET /v1/assets/{id} parses image details and enums round-trip."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/assets/770e8400-e29b-41d4-a716-446655440002",
            json={
                "result": {
                    "id": "770e8400-e29b-41d4-a716-446655440002",
                    "name": "logo.png",
                    "assetType": "IMAGE",
                    "providerAssetId": "prov-123",
                    "promotedObjectId": "111222",
                    "promotedObjectType": "BUSINESS_BRAND",
                    "assetDetails": {
                        "adAccountId": "12345",
                        "width": 1200,
                        "height": 1200,
                        "format": "PNG",
                        "sizeBytes": 204800,
                        "orientation": "SQUARE",
                        "checkSum": "abc123",
                    },
                    "parentAssetId": None,
                    "variantIds": ["variant-1"],
                    "creationTime": "2026-01-01T00:00:00.000Z",
                    "modificationTime": "2026-01-01T00:00:00.000Z",
                    "deleted": False,
                    "eligibility": {
                        "status": "LIMITED",
                        "blockedGroups": [
                            {"supplyPlacement": ["TODAY_TAB"], "countryOrRegion": ["CN"]}
                        ],
                        "allowedGroups": [
                            {"supplyPlacement": ["SEARCH_TAB"], "countryOrRegion": ["US"]}
                        ],
                    },
                }
            },
        )
        asset = AssetResource(v1_client).get("770e8400-e29b-41d4-a716-446655440002")
        assert asset.asset_details is not None
        assert asset.asset_details.format is ImageType.PNG
        assert asset.asset_details.orientation is Orientation.SQUARE
        assert asset.asset_details.size_bytes == 204800
        assert asset.eligibility is not None
        assert asset.eligibility.status is AssetEligibilityStatus.LIMITED
        assert asset.eligibility.blocked_groups is not None
        assert asset.eligibility.blocked_groups[0].supply_placement == ["TODAY_TAB"]
        assert asset.variant_ids == ["variant-1"]

    def test_query_assets_serializes_filters(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test POST /v1/assets/query sends filters and parses a page."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/assets/query",
            json={
                "result": [{"id": "a-1", "assetType": "IMAGE"}],
                "pagination": {"offset": 0, "pageSize": 500, "totalCount": 1},
            },
        )
        page = AssetResource(v1_client).query(
            Query()
            .where("promotedObjectId", "EQUALS", "111222")
            .page(size=500, fetch_total_count=True)
        )
        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {
            "filters": [{"field": "promotedObjectId", "operator": "EQUALS", "value": "111222"}],
            "pagination": {"pageSize": 500, "fetchTotalCount": True},
        }
        assert len(page) == 1
        assert page[0].asset_type is AssetType.IMAGE

    def test_delete_asset(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test DELETE /v1/assets/{id} issues the right request."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="DELETE",
            url=f"{BASE_URL}/assets/770e8400-e29b-41d4-a716-446655440002",
            json={"result": None},
        )
        AssetResource(v1_client).delete("770e8400-e29b-41d4-a716-446655440002")
        request = httpx_mock.get_requests()[-1]
        assert request.method == "DELETE"

    def test_upload_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx upload response carrying an error block raises."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/assets/upload",
            json={
                "error": {
                    "code": "INVALID_IMAGE",
                    "message": "unsupported image format",
                    "details": [],
                }
            },
        )
        with pytest.raises(PartialFailureError, match="unsupported image format"):
            AssetResource(v1_client).upload(b"bad", promoted_object_id="111222")


class TestEnums:
    """Enum round-trip tests."""

    def test_creative_type_round_trip(self) -> None:
        """Test CreativeType parses from and serializes to its wire value."""
        assert CreativeType("LOCAL_ADS_SEARCH_CREATIVE") is CreativeType.LOCAL_ADS_SEARCH_CREATIVE
        assert str(CreativeType.LOCAL_ADS_SEARCH_CREATIVE) == "LOCAL_ADS_SEARCH_CREATIVE"

    def test_asset_eligibility_status_round_trip(self) -> None:
        """Test AssetEligibilityStatus has all five documented values."""
        values = {status.value for status in AssetEligibilityStatus}
        assert values == {"ELIGIBLE", "INELIGIBLE", "LIMITED", "PENDING", "UNDEFINED"}
        assert AssetEligibilityStatus("UNDEFINED") is AssetEligibilityStatus.UNDEFINED

    def test_asset_parses_unknown_asset_via_alias(self) -> None:
        """Test Asset populates snake_case fields from camelCase aliases."""
        asset = Asset.model_validate(
            {"id": "a-1", "providerAssetId": "p-1", "promotedObjectType": "APPSTORE_APP"}
        )
        assert asset.provider_asset_id == "p-1"
        assert asset.promoted_object_type == "APPSTORE_APP"
