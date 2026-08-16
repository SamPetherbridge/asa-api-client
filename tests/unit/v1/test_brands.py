"""Tests for the v1 brands group: brands, categories, locations, groups."""

import json

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.brands import (
    EligibilityStatus,
    LocationGroupCreate,
    LocationGroupSystemStatus,
    LocationGroupType,
    LocationGroupUpdate,
    LocationStatus,
    Rule,
    RuleField,
    RuleOperator,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.brands import (
    BrandRejectionReasonResource,
    BrandResource,
    BusinessCategoryResource,
    LocationGroupResource,
    LocationResource,
)

BASE_URL = "https://api.ads.apple.com/v1"


@pytest.fixture(autouse=True)
def _mock_token_endpoint(httpx_mock: HTTPXMock) -> None:
    """Mock the Apple OAuth token endpoint for every test."""
    httpx_mock.add_response(
        url="https://appleid.apple.com/auth/oauth2/token",
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
        is_optional=True,
        is_reusable=True,
    )


class TestBrandResource:
    """Tests for the read-only business-brands endpoints."""

    def test_get_brand(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test GET /business-brands/{id} parses a Brand."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/business-brands/brand-123",
            json={
                "result": {
                    "id": "brand-123",
                    "name": "Acme Coffee",
                    "countryOrRegion": "US",
                    "categories": ["dining.cafe", "shopping.retail"],
                    "eligibility": {"status": "ELIGIBLE"},
                    "creationTime": "2025-01-10T08:00:00.000",
                    "modificationTime": "2026-02-01T09:00:00Z",
                }
            },
        )
        brand = BrandResource(v1_client).get("brand-123")
        request = httpx_mock.get_request(url=f"{BASE_URL}/business-brands/brand-123")
        assert request is not None
        assert request.method == "GET"
        assert brand.id == "brand-123"
        assert brand.name == "Acme Coffee"
        assert brand.categories == ["dining.cafe", "shopping.retail"]
        assert brand.eligibility is not None
        assert brand.eligibility.status is EligibilityStatus.ELIGIBLE

    def test_query_brands_serializes_filters(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test POST /business-brands/query sends the exact filter body."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/business-brands/query",
            json={
                "result": [{"id": "brand-123", "name": "Acme Coffee"}],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = BrandResource(v1_client).query(
            Query().where("id", "IN", ["brand-123"]).page(size=20)
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/business-brands/query")
        assert request is not None
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [{"field": "id", "operator": "IN", "value": ["brand-123"]}],
            "pagination": {"pageSize": 20},
        }
        assert len(page) == 1
        assert page[0].id == "brand-123"
        assert page.has_more is False

    def test_get_brand_200_with_error_block_raises(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test an HTTP 200 carrying an error block raises PartialFailureError."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/business-brands/brand-123",
            json={
                "error": {
                    "code": "PARTIAL",
                    "message": "brand lookup failed",
                    "details": [{"code": "INVALID_BRAND", "message": "bad brand"}],
                }
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            BrandResource(v1_client).get("brand-123")
        assert exc_info.value.details[0]["code"] == "INVALID_BRAND"

    async def test_query_brands_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async query path parses brands identically."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/business-brands/query",
            json={"result": [{"id": "brand-123"}]},
        )
        page = await BrandResource(v1_client).query_async()
        assert page[0].id == "brand-123"


class TestBusinessCategoryResource:
    """Tests for the business-categories endpoints."""

    def test_get_business_category(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test GET /business-categories/{id} parses a BusinessCategory."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/business-categories/muid-42",
            json={
                "result": {
                    "id": "muid-42",
                    "name": "Restaurant",
                    "qualifiedId": "dining.restaurant",
                    "description": "Places serving food",
                    "eligibility": {"status": "ELIGIBLE"},
                }
            },
        )
        category = BusinessCategoryResource(v1_client).get("muid-42")
        assert category.id == "muid-42"
        assert category.qualified_id == "dining.restaurant"
        assert category.eligibility is not None
        assert category.eligibility.status is EligibilityStatus.ELIGIBLE

    def test_query_business_categories(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test POST /business-categories/query with an empty body."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/business-categories/query",
            json={
                "result": [{"id": "muid-42", "qualifiedId": "dining.restaurant"}],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = BusinessCategoryResource(v1_client).query()
        request = httpx_mock.get_request(url=f"{BASE_URL}/business-categories/query")
        assert request is not None
        assert json.loads(request.content) == {}
        assert page[0].qualified_id == "dining.restaurant"


class TestBrandRejectionReasonResource:
    """Tests for the rejection-reasons/business-brands query endpoint."""

    def test_query_rejection_reasons(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test POST /rejection-reasons/business-brands/query URL and parsing."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/rejection-reasons/business-brands/query",
            json={
                "result": [
                    {
                        "id": 987654,
                        "promotedObjectId": "brand-123",
                        "promotedObjectType": "BUSINESS_BRAND",
                        "entityId": "brand-123",
                        "entityType": "BUSINESS_BRAND",
                        "componentType": "ENTITY_ASSET",
                        "component": "asset-uuid-1",
                        "code": "PERSONAL_INFORMATION",
                        "title": "Personal information",
                        "body": "The asset contains personal information.",
                    }
                ],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = BrandRejectionReasonResource(v1_client).query(
            Query().where("promotedObjectId", "EQUALS", "brand-123")
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/rejection-reasons/business-brands/query")
        assert request is not None
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [{"field": "promotedObjectId", "operator": "EQUALS", "value": "brand-123"}]
        }
        reason = page[0]
        assert reason.id == 987654
        assert reason.code == "PERSONAL_INFORMATION"
        assert reason.component_type == "ENTITY_ASSET"


class TestLocationResource:
    """Tests for the read-only locations endpoints."""

    def test_get_location(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test GET /locations/{id} parses nested address and display point."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/locations/loc-1",
            json={
                "result": {
                    "id": "loc-1",
                    "brandId": "brand-123",
                    "status": "OPEN",
                    "name": "Acme Coffee Cupertino",
                    "categories": ["dining.cafe"],
                    "address": {
                        "countryOrRegion": "US",
                        "adminArea": "California",
                        "adminAreaCode": "CA",
                        "locality": "Cupertino",
                        "postalCode": "95014",
                        "thoroughfare": "Apple Park Way",
                        "subThoroughfare": "1",
                        "fullThoroughfare": "1 Apple Park Way",
                        "fullAddress": "1 Apple Park Way, Cupertino, CA 95014",
                    },
                    "displayPoint": {"latitude": "37.3318", "longitude": "-122.0312"},
                    "countryOrRegion": "US",
                    "eligibility": {
                        "status": "LIMITED",
                        "blockedGroups": [
                            {
                                "supplyPlacement": ["MAPS_SEARCH_HOME"],
                                "countryOrRegion": ["GB"],
                            }
                        ],
                    },
                }
            },
        )
        location = LocationResource(v1_client).get("loc-1")
        assert location.status is LocationStatus.OPEN
        assert location.address is not None
        assert location.address.admin_area == "California"
        assert location.address.postal_code == "95014"
        assert location.display_point is not None
        assert location.display_point.latitude == "37.3318"
        assert location.eligibility is not None
        assert location.eligibility.status is EligibilityStatus.LIMITED
        blocked = location.eligibility.blocked_groups
        assert blocked is not None
        assert blocked[0].supply_placement == ["MAPS_SEARCH_HOME"]

    def test_query_locations_serializes_filters(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test POST /locations/query sends brandId and status filters."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/locations/query",
            json={
                "result": [{"id": "loc-1", "brandId": "brand-123", "status": "OPEN"}],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = LocationResource(v1_client).query(
            Query()
            .where("brandId", "EQUALS", "brand-123")
            .where("status", "EQUALS", str(LocationStatus.OPEN))
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/locations/query")
        assert request is not None
        assert json.loads(request.content) == {
            "filters": [
                {"field": "brandId", "operator": "EQUALS", "value": "brand-123"},
                {"field": "status", "operator": "EQUALS", "value": "OPEN"},
            ]
        }
        assert page[0].status is LocationStatus.OPEN

    def test_location_status_enum_round_trip(self) -> None:
        """Test LocationStatus values round-trip through their strings."""
        assert LocationStatus("TEMPORARILY_CLOSED") is LocationStatus.TEMPORARILY_CLOSED
        assert LocationStatus.OPENING_SOON.value == "OPENING_SOON"


class TestLocationGroupResource:
    """Tests for the writable location-groups endpoints."""

    def test_create_static_location_group(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test POST /location-groups sends a bare aliased body."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/location-groups",
            json={
                "result": {
                    "id": "lg-1",
                    "name": "Bay Area Stores",
                    "brandId": "brand-123",
                    "adAccountId": "12345",
                    "groupType": "STATIC",
                    "systemStatus": "VALID",
                    "locationIds": ["loc-1", "loc-2"],
                    "isAllLocationsGroup": False,
                    "groupTotal": 2,
                    "eligibility": {"status": "ELIGIBLE"},
                }
            },
        )
        group = LocationGroupResource(v1_client).create(
            LocationGroupCreate(
                name="Bay Area Stores",
                brand_id="brand-123",
                ad_account_id="12345",
                group_type=LocationGroupType.STATIC,
                location_ids=["loc-1", "loc-2"],
            )
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/location-groups")
        assert request is not None
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "name": "Bay Area Stores",
            "brandId": "brand-123",
            "adAccountId": "12345",
            "groupType": "STATIC",
            "locationIds": ["loc-1", "loc-2"],
        }
        assert group.id == "lg-1"
        assert group.group_type is LocationGroupType.STATIC
        assert group.system_status is LocationGroupSystemStatus.VALID
        assert group.group_total == 2

    def test_create_dynamic_location_group_serializes_rules(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test rules serialize with enum values and polymorphic values."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/location-groups",
            json={
                "result": {
                    "id": "lg-2",
                    "name": "West Coast",
                    "groupType": "DYNAMIC",
                    "systemStatus": "PENDING",
                    "groupTotal": 0,
                    "rules": [{"field": "adminArea", "operator": "IN", "value": ["California"]}],
                    "query": "administrativeArea==California",
                }
            },
        )
        group = LocationGroupResource(v1_client).create(
            LocationGroupCreate(
                name="West Coast",
                brand_id="brand-123",
                ad_account_id="12345",
                group_type=LocationGroupType.DYNAMIC,
                rules=[
                    Rule(
                        field=RuleField.ADMIN_AREA,
                        operator=RuleOperator.IN,
                        value=["California"],
                    ),
                    Rule(
                        field=RuleField.LOCALITY,
                        operator=RuleOperator.EQUALS,
                        value="US|New York|Brooklyn",
                    ),
                ],
            )
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/location-groups")
        assert request is not None
        assert json.loads(request.content) == {
            "name": "West Coast",
            "brandId": "brand-123",
            "adAccountId": "12345",
            "groupType": "DYNAMIC",
            "rules": [
                {"field": "adminArea", "operator": "IN", "value": ["California"]},
                {
                    "field": "locality",
                    "operator": "EQUALS",
                    "value": "US|New York|Brooklyn",
                },
            ],
        }
        assert group.system_status is LocationGroupSystemStatus.PENDING
        assert group.rules is not None
        assert group.rules[0].field is RuleField.ADMIN_AREA
        assert group.query == "administrativeArea==California"

    def test_get_location_group(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test GET /location-groups/{id} parses a LocationGroup."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/location-groups/lg-1",
            json={
                "result": {
                    "id": "lg-1",
                    "name": "Bay Area Stores",
                    "groupType": "STATIC",
                    "systemStatus": "DELETED",
                    "groupTotal": 2,
                }
            },
        )
        group = LocationGroupResource(v1_client).get("lg-1")
        assert group.system_status is LocationGroupSystemStatus.DELETED

    def test_query_location_groups(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test POST /location-groups/query serializes groupType filters."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/location-groups/query",
            json={
                "result": [{"id": "lg-1", "name": "Bay Area Stores", "groupType": "STATIC"}],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = LocationGroupResource(v1_client).query(
            Query()
            .where("brandId", "EQUALS", "brand-123")
            .where("groupType", "EQUALS", str(LocationGroupType.STATIC))
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/location-groups/query")
        assert request is not None
        assert json.loads(request.content) == {
            "filters": [
                {"field": "brandId", "operator": "EQUALS", "value": "brand-123"},
                {"field": "groupType", "operator": "EQUALS", "value": "STATIC"},
            ]
        }
        assert page[0].group_type is LocationGroupType.STATIC

    def test_update_location_group(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test PUT /location-groups/{id} sends only the provided fields."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/location-groups/lg-1",
            json={
                "result": {
                    "id": "lg-1",
                    "name": "Renamed Stores",
                    "groupType": "STATIC",
                    "locationIds": ["loc-1", "loc-2", "loc-3"],
                    "groupTotal": 3,
                }
            },
        )
        group = LocationGroupResource(v1_client).update(
            "lg-1",
            LocationGroupUpdate(
                name="Renamed Stores",
                location_ids=["loc-1", "loc-2", "loc-3"],
            ),
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/location-groups/lg-1")
        assert request is not None
        assert request.method == "PUT"
        assert json.loads(request.content) == {
            "name": "Renamed Stores",
            "locationIds": ["loc-1", "loc-2", "loc-3"],
        }
        assert group.name == "Renamed Stores"
        assert group.location_ids == ["loc-1", "loc-2", "loc-3"]

    def test_delete_location_group(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test DELETE /location-groups/{id} tolerates the 200 envelope body."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/location-groups/lg-1",
            json={
                "result": {
                    "id": "lg-1",
                    "name": "Bay Area Stores",
                    "groupType": "STATIC",
                    "systemStatus": "DELETED",
                    "groupTotal": 2,
                }
            },
        )
        assert LocationGroupResource(v1_client).delete("lg-1") is None
        request = httpx_mock.get_request(url=f"{BASE_URL}/location-groups/lg-1")
        assert request is not None
        assert request.method == "DELETE"

    def test_location_group_type_enum_round_trip(self) -> None:
        """Test LocationGroupType values round-trip through their strings."""
        assert LocationGroupType("DYNAMIC") is LocationGroupType.DYNAMIC
        assert LocationGroupType.STATIC.value == "STATIC"
