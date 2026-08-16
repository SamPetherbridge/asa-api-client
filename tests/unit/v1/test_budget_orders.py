"""Tests for the v1 budget orders (shared budgets) resource and models."""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError as PydanticValidationError
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.base import Money
from asa_api_client.v1.models.budget_orders import (
    BudgetSystemStatus,
    BudgetSystemStatusReason,
    InvoiceDetail,
    InvoiceDetailUpdate,
    PaymentModel,
    SharedBudget,
    SharedBudgetAssignment,
    SharedBudgetAssignmentCreate,
    SharedBudgetAssignmentUpdate,
    SharedBudgetCreate,
    SharedBudgetUpdate,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.budget_orders import BudgetOrderResource

BASE_URL = "https://api.ads.apple.com/v1/shared-budgets"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"

SHARED_BUDGET_JSON = {
    "id": 90001,
    "name": "Q4 Budget",
    "startTime": "2026-09-01T00:00:00.000",
    "endTime": "2026-12-31T23:59:59.999",
    "value": {"amount": "20000.00", "currency": "USD"},
    "adAccountIds": [12345],
    "orgId": 40669820,
    "systemStatus": "INACTIVE",
    "systemStatusReasons": ["SCHEDULE_PENDING"],
    "invoiceDetail": {
        "name": "Acme Billing",
        "clientName": "Acme",
        "primaryBuyerName": "Jane Doe",
        "primaryBuyerEmail": "jane@example.com",
        "orderNumber": "PO-42",
        "billingEmail": "billing@example.com",
    },
    "creationTime": "2026-08-01T10:00:00.000",
    "modificationTime": "2026-08-02T10:00:00.000",
    "deleted": False,
}


def mock_token(httpx_mock: HTTPXMock) -> None:
    """Mock Apple's OAuth token endpoint for the real client fixture."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
    )


class TestGet:
    """Tests for GET /v1/shared-budgets/{id}."""

    def test_get_budget_order(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get() issues GET to the item path and parses the result."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/90001", json={"result": SHARED_BUDGET_JSON, "error": None}
        )
        budget = BudgetOrderResource(v1_client).get(90001)
        request = httpx_mock.get_request(url=f"{BASE_URL}/90001")
        assert request is not None
        assert request.method == "GET"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert budget.id == 90001
        assert budget.name == "Q4 Budget"
        assert budget.value == Money(amount="20000.00", currency="USD")
        assert budget.ad_account_ids == [12345]
        assert budget.system_status is BudgetSystemStatus.INACTIVE
        assert budget.system_status_reasons == [BudgetSystemStatusReason.SCHEDULE_PENDING]
        assert budget.invoice_detail is not None
        assert budget.invoice_detail.primary_buyer_email == "jane@example.com"
        assert budget.start_time == datetime(2026, 9, 1)
        assert budget.deleted is False

    async def test_get_budget_order_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test get_async() parses the result identically."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/90001", json={"result": SHARED_BUDGET_JSON})
        budget = await BudgetOrderResource(v1_client).get_async(90001)
        assert budget.id == 90001
        assert budget.system_status is BudgetSystemStatus.INACTIVE


class TestQuery:
    """Tests for POST /v1/shared-budgets/query."""

    def test_query_serializes_filters(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query() POSTs the exact filter body and parses the page."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/query",
            json={
                "result": [SHARED_BUDGET_JSON],
                "pagination": {"offset": 0, "pageSize": 10, "totalCount": 1},
            },
        )
        page = BudgetOrderResource(v1_client).query(
            Query().where("deleted", "EQUALS", True).page(size=10)
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/query")
        assert request is not None
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [{"field": "deleted", "operator": "EQUALS", "value": True}],
            "pagination": {"pageSize": 10},
        }
        assert len(page) == 1
        assert page[0].id == 90001
        assert page.has_more is False


class TestCreate:
    """Tests for POST /v1/shared-budgets."""

    def test_create_posts_exact_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test create() POSTs the unwrapped, aliased body with .SSS timestamps."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=BASE_URL, json={"result": SHARED_BUDGET_JSON})
        created = BudgetOrderResource(v1_client).create(
            SharedBudgetCreate(
                name="Q4 Budget",
                start_time=datetime(2026, 9, 1),
                end_time=datetime(2026, 12, 31, 23, 59, 59, 999000),
                value=Money(amount="20000.00", currency="USD"),
                ad_account_ids=[12345],
                invoice_detail=InvoiceDetail(
                    name="Acme Billing",
                    client_name="Acme",
                    primary_buyer_name="Jane Doe",
                    primary_buyer_email="jane@example.com",
                    order_number="PO-42",
                    billing_email="billing@example.com",
                ),
            )
        )
        request = httpx_mock.get_request(url=BASE_URL)
        assert request is not None
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "name": "Q4 Budget",
            "startTime": "2026-09-01T00:00:00.000",
            "endTime": "2026-12-31T23:59:59.999",
            "value": {"amount": "20000.00", "currency": "USD"},
            "adAccountIds": [12345],
            "invoiceDetail": {
                "name": "Acme Billing",
                "clientName": "Acme",
                "primaryBuyerName": "Jane Doe",
                "primaryBuyerEmail": "jane@example.com",
                "orderNumber": "PO-42",
                "billingEmail": "billing@example.com",
            },
        }
        assert created.id == 90001

    def test_create_omits_unset_end_time(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test an open-ended create omits endTime from the body entirely."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=BASE_URL, json={"result": SHARED_BUDGET_JSON})
        BudgetOrderResource(v1_client).create(
            SharedBudgetCreate(
                name="Open Ended",
                start_time=datetime(2026, 9, 1),
                value=Money(amount="500.00", currency="USD"),
                ad_account_ids=[12345],
                invoice_detail=InvoiceDetail(
                    name="Acme Billing",
                    primary_buyer_name="Jane Doe",
                    primary_buyer_email="jane@example.com",
                    billing_email="billing@example.com",
                ),
            )
        )
        request = httpx_mock.get_request(url=BASE_URL)
        assert request is not None
        assert "endTime" not in json.loads(request.content)

    def test_create_requires_exactly_one_ad_account_id(self) -> None:
        """Test the single-ID constraint on adAccountIds is enforced client-side."""
        with pytest.raises(PydanticValidationError):
            SharedBudgetCreate(
                name="Too Many",
                start_time=datetime(2026, 9, 1),
                value=Money(amount="500.00", currency="USD"),
                ad_account_ids=[1, 2],
                invoice_detail=InvoiceDetail(name="X"),
            )


class TestUpdate:
    """Tests for PUT /v1/shared-budgets/{id}."""

    def test_update_puts_partial_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test update() PUTs only the fields that were explicitly set."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/90001", json={"result": SHARED_BUDGET_JSON})
        updated = BudgetOrderResource(v1_client).update(
            90001,
            SharedBudgetUpdate(
                name="Renamed",
                value=Money(amount="30000.00", currency="USD"),
                invoice_detail=InvoiceDetailUpdate(order_number="PO-43"),
            ),
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/90001")
        assert request is not None
        assert request.method == "PUT"
        assert json.loads(request.content) == {
            "name": "Renamed",
            "value": {"amount": "30000.00", "currency": "USD"},
            "invoiceDetail": {"orderNumber": "PO-43"},
        }
        assert updated.id == 90001

    def test_update_end_time_null_removes_expiration(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test explicitly setting end_time=None sends endTime: null."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/90001", json={"result": SHARED_BUDGET_JSON})
        BudgetOrderResource(v1_client).update(90001, SharedBudgetUpdate(end_time=None))
        request = httpx_mock.get_request(url=f"{BASE_URL}/90001")
        assert request is not None
        assert json.loads(request.content) == {"endTime": None}


class TestDelete:
    """Tests for DELETE /v1/shared-budgets/{id}."""

    def test_delete_budget_order(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test delete() issues DELETE to the item path and returns None."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/90001", json={})
        assert BudgetOrderResource(v1_client).delete(90001) is None
        request = httpx_mock.get_request(url=f"{BASE_URL}/90001")
        assert request is not None
        assert request.method == "DELETE"


class TestErrors:
    """Tests for error handling."""

    def test_http_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx response carrying an error block raises PartialFailureError."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/90001",
            json={
                "result": None,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "budget order rejected",
                    "details": [{"code": "BUDGET_ORDER_OVERLAPPING", "message": "overlap"}],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            BudgetOrderResource(v1_client).get(90001)
        assert exc_info.value.details[0]["code"] == "BUDGET_ORDER_OVERLAPPING"


class TestEnumsAndModels:
    """Tests for enum values and embedded assignment models."""

    def test_system_status_enum_round_trip(self) -> None:
        """Test status enums parse from and dump back to their wire values."""
        budget = SharedBudget.model_validate(
            {"systemStatus": "ACTIVE", "systemStatusReasons": ["EXHAUSTED", "PROCESSING"]}
        )
        assert budget.system_status is BudgetSystemStatus.ACTIVE
        assert budget.system_status_reasons == [
            BudgetSystemStatusReason.EXHAUSTED,
            BudgetSystemStatusReason.PROCESSING,
        ]
        dumped = budget.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped == {
            "systemStatus": "ACTIVE",
            "systemStatusReasons": ["EXHAUSTED", "PROCESSING"],
        }

    def test_payment_model_enum_values(self) -> None:
        """Test the PaymentModel enum carries the exact documented values."""
        assert PaymentModel.PAYG.value == "PAYG"
        assert PaymentModel.LOC.value == "LOC"
        assert PaymentModel("LOC") is PaymentModel.LOC

    def test_budget_system_status_reason_values(self) -> None:
        """Test every documented systemStatusReasons value is representable."""
        values = {reason.value for reason in BudgetSystemStatusReason}
        assert values == {
            "CANCELED",
            "CAMPAIGN_BUDGET_UNASSIGNED",
            "DELETED_BY_USER",
            "EXHAUSTED",
            "PROCESSING",
            "SCHEDULE_EXPIRED",
            "SCHEDULE_PENDING",
        }

    def test_shared_budget_assignment_models_serialize_budget_id(self) -> None:
        """Test assignment models use the budgetId alias for embedding in campaigns."""
        assert SharedBudgetAssignment.model_validate({"budgetId": 90001}).budget_id == 90001
        create_dump = SharedBudgetAssignmentCreate(budget_id=90001).model_dump(
            by_alias=True, exclude_none=True
        )
        assert create_dump == {"budgetId": 90001}
        update_dump = SharedBudgetAssignmentUpdate(budget_id=90002).model_dump(
            by_alias=True, exclude_none=True
        )
        assert update_dump == {"budgetId": 90002}
