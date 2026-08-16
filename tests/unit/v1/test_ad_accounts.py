"""Tests for the v1 ad_accounts resource group.

Covers caller identity (``GET /me``), access control (``GET /acls``),
organizations (``GET /orgs/{id}``), ad accounts (``POST /ad-accounts``,
``GET/PUT /ad-accounts/{id}``), and advertiser resources
(``GET /advertiser-resources``).
"""

import json

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import ConfigurationError, PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.ad_accounts import (
    AdAccountCreate,
    AdAccountCurrency,
    AdAccountSystemStatus,
    AdAccountSystemStatusReason,
    AdAccountUpdate,
    AdvertiserResourceType,
    DelegationCreate,
    DelegationUpdate,
    OrgSystemStatus,
    PaymentModel,
    ProductFeatures,
)
from asa_api_client.v1.resources.ad_accounts import (
    AclResource,
    AdAccountResource,
    AdvertiserResourceResource,
    OrgResource,
)

BASE_URL = "https://api.ads.apple.com/v1"


@pytest.fixture(autouse=True)
def _mock_token_endpoint(httpx_mock: HTTPXMock) -> None:
    """Mock Apple's OAuth token endpoint for every test."""
    httpx_mock.add_response(
        url="https://appleid.apple.com/auth/oauth2/token",
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
        is_optional=True,
        is_reusable=True,
    )


AD_ACCOUNT_JSON = {
    "id": 565377349,
    "name": "Primary Account",
    "orgId": 40669820,
    "timezone": "America/New_York",
    "currency": "USD",
    "paymentModel": "LOC",
    "systemStatus": "ACTIVE",
    "systemStatusReasons": None,
    "delegations": [
        {
            "resourceId": "10001",
            "resourceType": "CONTENT_PROVIDER",
            "resourceName": "Acme Apps",
        }
    ],
    "productFeatures": ["APPSTORE_APP_MANUAL"],
    "creationTime": "2025-01-10T08:00:00.000",
    "modificationTime": "2025-01-10T08:00:00.000",
}


class TestMe:
    """Tests for GET /v1/me."""

    def test_me_returns_identity(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test me() GETs /me and parses the caller identity."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/me",
            json={"result": {"userId": 999, "orgId": 40669820}},
        )
        me = AdAccountResource(v1_client).me()
        request = httpx_mock.get_requests()[-1]
        assert request.method == "GET"
        assert me.user_id == 999
        assert me.org_id == 40669820

    def test_me_without_account_context(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test me() works with no ad_account_id and omits X-AP-Context."""
        v1_client.ad_account_id = None
        httpx_mock.add_response(url=f"{BASE_URL}/me", json={"result": {"userId": 1, "orgId": 2}})
        me = AdAccountResource(v1_client).me()
        assert "X-AP-Context" not in httpx_mock.get_requests()[-1].headers
        assert me.org_id == 2

    async def test_me_async(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test me_async() parses the caller identity."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/me",
            json={"result": {"userId": 7, "orgId": 8}},
        )
        me = await AdAccountResource(v1_client).me_async()
        assert me.user_id == 7


class TestAcls:
    """Tests for GET /v1/acls."""

    def test_list_acls(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test list() GETs /acls and parses the nested acls array."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/acls",
            json={
                "result": {
                    "acls": [
                        {
                            "adAccount": {"id": 565377349, "name": "Primary", "orgId": 40669820},
                            "roles": ["Admin", "API Account Manager"],
                        }
                    ]
                }
            },
        )
        acls = AclResource(v1_client).list()
        request = httpx_mock.get_requests()[-1]
        assert request.method == "GET"
        assert len(acls) == 1
        assert acls[0].ad_account is not None
        assert acls[0].ad_account.id == 565377349
        assert acls[0].ad_account.org_id == 40669820
        assert acls[0].roles == ["Admin", "API Account Manager"]

    def test_list_acls_without_account_context(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test list() works with no ad_account_id and omits X-AP-Context."""
        v1_client.ad_account_id = None
        httpx_mock.add_response(url=f"{BASE_URL}/acls", json={"result": {"acls": []}})
        assert AclResource(v1_client).list() == []
        assert "X-AP-Context" not in httpx_mock.get_requests()[-1].headers

    async def test_list_acls_async(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test list_async() parses ACL entries."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/acls",
            json={"result": {"acls": [{"adAccount": {"id": 1}, "roles": ["Admin"]}]}},
        )
        acls = await AclResource(v1_client).list_async()
        assert acls[0].roles == ["Admin"]


class TestOrgs:
    """Tests for GET /v1/orgs/{id}."""

    def test_get_org(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get() GETs /orgs/{id} and round-trips the org enums."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/orgs/40669820",
            json={
                "result": {
                    "id": 40669820,
                    "name": "Acme Org",
                    "currency": "USD",
                    "timezone": "America/New_York",
                    "paymentModel": "LOC",
                    "systemStatus": "ACTIVE",
                }
            },
        )
        org = OrgResource(v1_client).get(40669820)
        assert httpx_mock.get_requests()[-1].method == "GET"
        assert org.id == 40669820
        assert org.currency is AdAccountCurrency.USD
        assert org.payment_model is PaymentModel.LOC
        assert org.system_status is OrgSystemStatus.ACTIVE

    def test_get_org_without_account_context(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test get() works with no ad_account_id configured."""
        v1_client.ad_account_id = None
        httpx_mock.add_response(url=f"{BASE_URL}/orgs/1", json={"result": {"id": 1}})
        assert OrgResource(v1_client).get(1).id == 1
        assert "X-AP-Context" not in httpx_mock.get_requests()[-1].headers


class TestCreateAdAccount:
    """Tests for POST /v1/ad-accounts."""

    def test_create_serializes_bare_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test create() POSTs the aliased AdAccountCreate body unwrapped."""
        httpx_mock.add_response(url=f"{BASE_URL}/ad-accounts", json={"result": AD_ACCOUNT_JSON})
        created = AdAccountResource(v1_client).create(
            AdAccountCreate(
                name="Primary Account",
                product_features=[ProductFeatures.APPSTORE_APP_MANUAL],
                delegations=[
                    DelegationCreate(
                        resource_id="10001",
                        resource_type=AdvertiserResourceType.CONTENT_PROVIDER,
                    )
                ],
            )
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "name": "Primary Account",
            "productFeatures": ["APPSTORE_APP_MANUAL"],
            "delegations": [{"resourceId": "10001", "resourceType": "CONTENT_PROVIDER"}],
        }
        assert created.id == 565377349
        assert created.system_status is AdAccountSystemStatus.ACTIVE

    def test_create_without_account_context(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test create() works with no ad_account_id and omits X-AP-Context."""
        v1_client.ad_account_id = None
        httpx_mock.add_response(url=f"{BASE_URL}/ad-accounts", json={"result": AD_ACCOUNT_JSON})
        created = AdAccountResource(v1_client).create(
            AdAccountCreate(name="A", product_features=[ProductFeatures.BUSINESS_BRAND_MANUAL])
        )
        assert "X-AP-Context" not in httpx_mock.get_requests()[-1].headers
        assert created.name == "Primary Account"

    async def test_create_async(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test create_async() POSTs and parses the created account."""
        httpx_mock.add_response(url=f"{BASE_URL}/ad-accounts", json={"result": AD_ACCOUNT_JSON})
        created = await AdAccountResource(v1_client).create_async(
            AdAccountCreate(name="A", product_features=[ProductFeatures.APPSTORE_APP_MANUAL])
        )
        assert created.org_id == 40669820


class TestGetAdAccount:
    """Tests for GET /v1/ad-accounts/{id}."""

    def test_get_ad_account(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get() GETs /ad-accounts/{id} with X-AP-Context and parses enums."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/ad-accounts/565377349", json={"result": AD_ACCOUNT_JSON}
        )
        account = AdAccountResource(v1_client).get(565377349)
        request = httpx_mock.get_requests()[-1]
        assert request.method == "GET"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert account.currency is AdAccountCurrency.USD
        assert account.payment_model is PaymentModel.LOC
        assert account.product_features == [ProductFeatures.APPSTORE_APP_MANUAL]
        assert account.delegations is not None
        assert account.delegations[0].resource_type is AdvertiserResourceType.CONTENT_PROVIDER
        assert account.delegations[0].resource_id == "10001"

    def test_get_parses_inactive_status_reasons(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test get() round-trips systemStatusReasons enum values."""
        body = dict(AD_ACCOUNT_JSON)
        body["systemStatus"] = "INACTIVE"
        body["systemStatusReasons"] = ["ORG_NO_PAYMENT_METHOD_ON_FILE", "INVALID_PAYMENT_PROFILE"]
        httpx_mock.add_response(url=f"{BASE_URL}/ad-accounts/565377349", json={"result": body})
        account = AdAccountResource(v1_client).get(565377349)
        assert account.system_status is AdAccountSystemStatus.INACTIVE
        assert account.system_status_reasons == [
            AdAccountSystemStatusReason.ORG_NO_PAYMENT_METHOD_ON_FILE,
            AdAccountSystemStatusReason.INVALID_PAYMENT_PROFILE,
        ]

    def test_get_requires_account_context(self, v1_client: AppleAdsClient) -> None:
        """Test get() raises ConfigurationError without an ad_account_id."""
        v1_client.ad_account_id = None
        with pytest.raises(ConfigurationError, match="ad_account_id"):
            AdAccountResource(v1_client).get(565377349)


class TestUpdateAdAccount:
    """Tests for PUT /v1/ad-accounts/{id}."""

    def test_update_puts_partial_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test update() PUTs only the fields set on AdAccountUpdate."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/ad-accounts/565377349", json={"result": AD_ACCOUNT_JSON}
        )
        updated = AdAccountResource(v1_client).update(565377349, AdAccountUpdate(name="Renamed"))
        request = httpx_mock.get_requests()[-1]
        assert request.method == "PUT"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert json.loads(request.content) == {"name": "Renamed"}
        assert updated.id == 565377349

    def test_update_delegations_full_replacement(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test update() serializes an empty delegations array (remove all)."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/ad-accounts/565377349", json={"result": AD_ACCOUNT_JSON}
        )
        AdAccountResource(v1_client).update(565377349, AdAccountUpdate(delegations=[]))
        assert json.loads(httpx_mock.get_requests()[-1].content) == {"delegations": []}

    def test_update_delegation_entries_serialize_aliases(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test update() serializes DelegationUpdate entries with camelCase aliases."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/ad-accounts/565377349", json={"result": AD_ACCOUNT_JSON}
        )
        AdAccountResource(v1_client).update(
            565377349,
            AdAccountUpdate(
                delegations=[
                    DelegationUpdate(
                        resource_id="B123",
                        resource_type=AdvertiserResourceType.BUSINESS_BRAND,
                    )
                ]
            ),
        )
        assert json.loads(httpx_mock.get_requests()[-1].content) == {
            "delegations": [{"resourceId": "B123", "resourceType": "BUSINESS_BRAND"}]
        }

    def test_update_requires_account_context(self, v1_client: AppleAdsClient) -> None:
        """Test update() raises ConfigurationError without an ad_account_id."""
        v1_client.ad_account_id = None
        with pytest.raises(ConfigurationError, match="ad_account_id"):
            AdAccountResource(v1_client).update(565377349, AdAccountUpdate(name="X"))


class TestAdvertiserResources:
    """Tests for GET /v1/advertiser-resources."""

    def test_list_advertiser_resources(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test list() sends resourceType and parses the bare result array."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/advertiser-resources?resourceType=CONTENT_PROVIDER",
            json={
                "result": [
                    {
                        "resourceId": "10001",
                        "resourceType": "CONTENT_PROVIDER",
                        "resourceName": "Acme Apps",
                    }
                ]
            },
        )
        resources = AdvertiserResourceResource(v1_client).list(
            AdvertiserResourceType.CONTENT_PROVIDER
        )
        assert httpx_mock.get_requests()[-1].method == "GET"
        assert len(resources) == 1
        assert resources[0].resource_id == "10001"
        assert resources[0].resource_type is AdvertiserResourceType.CONTENT_PROVIDER
        assert resources[0].resource_name == "Acme Apps"

    def test_list_advertiser_resources_without_account_context(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test list() works with no ad_account_id configured."""
        v1_client.ad_account_id = None
        httpx_mock.add_response(
            url=f"{BASE_URL}/advertiser-resources?resourceType=BUSINESS_BRAND",
            json={"result": []},
        )
        assert AdvertiserResourceResource(v1_client).list("BUSINESS_BRAND") == []
        assert "X-AP-Context" not in httpx_mock.get_requests()[-1].headers

    async def test_list_advertiser_resources_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test list_async() sends resourceType and parses Delegation items."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/advertiser-resources?resourceType=BUSINESS_BRAND",
            json={"result": [{"resourceId": "B1", "resourceType": "BUSINESS_BRAND"}]},
        )
        resources = await AdvertiserResourceResource(v1_client).list_async(
            AdvertiserResourceType.BUSINESS_BRAND
        )
        assert resources[0].resource_type is AdvertiserResourceType.BUSINESS_BRAND


class TestPartialFailure:
    """Tests for 200-with-error-block handling."""

    def test_http_200_with_error_block_raises(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx response carrying an error block raises PartialFailureError."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/ad-accounts/565377349",
            json={
                "result": None,
                "error": {
                    "code": "INVALID_DELEGATION",
                    "message": "delegation resource type mismatch",
                    "details": [{"code": "INVALID_DELEGATION", "message": "bad delegation"}],
                },
            },
        )
        with pytest.raises(PartialFailureError, match="delegation resource type mismatch"):
            AdAccountResource(v1_client).get(565377349)
