"""Tests for the v1 change history resource and models."""

import json
from datetime import UTC, datetime

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.change_history import (
    AuditEventType,
    AuditOperator,
    AuditSortOrder,
    AuditSummary,
    AuditUserType,
    ChangeDetails,
    ErrorMessage,
    ErrorMessageCode,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.change_history import ChangeHistoryResource

BASE_URL = "https://api.ads.apple.com/v1/change-history"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"

AUDIT_SUMMARY_JSON = {
    "transactionId": "txn_abc123def456",
    "eventType": "UPDATE",
    "eventTime": "2026-03-15T14:30:00.000Z",
    "entityType": "Campaign",
    "count": 2,
    "metas": [
        {
            "Campaign": "444555666",
            "detailId": "Campaign.444555666.txn_abc123def456",
            "meta": {"name": "Spring Sale"},
        }
    ],
    "userType": "CUSTOMER_API",
    "modifiedBy": "api-client-1",
}

CHANGE_DETAILS_JSON = {
    "transactionId": "txn_abc123def456",
    "detailId": "Campaign.444555666.txn_abc123def456",
    "eventType": "UPDATE",
    "entityType": "Campaign",
    "entityId": "444555666",
    "eventTime": "2026-03-15T14:30:00.000Z",
    "userType": "CUSTOMER",
    "modifiedBy": "jane",
    "entityMetaData": {"name": "Spring Sale", "adAccountId": "12345"},
    "details": [
        {
            "transactionId": "txn_abc123def456",
            "changes": [{"field": "dailyBudget", "oldValues": ["50.00"], "newValues": ["75.00"]}],
        }
    ],
}

DETAIL_ID = "Campaign.444555666.txn_abc123def456"


def mock_token(httpx_mock: HTTPXMock) -> None:
    """Mock Apple's OAuth token endpoint for the real client fixture."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
    )


class TestQuery:
    """Tests for POST /v1/change-history/query."""

    def test_query_serializes_filters_and_options(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query() POSTs the exact audit query body including options."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/query",
            json={
                "dataType": "AuditSummary",
                "result": [AUDIT_SUMMARY_JSON],
                "pagination": {"offset": 0, "pageSize": 50, "totalCount": 1},
                "error": None,
            },
        )
        page = ChangeHistoryResource(v1_client).query(
            Query()
            .where("eventTime", "BETWEEN", ["2026-02-01T00:00:00", "2026-08-01T00:00:00"])
            .where("eventType", "IN", ["UPDATE"])
            .order_by("eventTime", "DESC")
            .page(size=50, offset=0),
            options={"needTotals": "true", "metadata": "latest"},
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/query")
        assert request is not None
        assert request.method == "POST"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert json.loads(request.content) == {
            "filters": [
                {
                    "field": "eventTime",
                    "operator": "BETWEEN",
                    "value": ["2026-02-01T00:00:00", "2026-08-01T00:00:00"],
                },
                {"field": "eventType", "operator": "IN", "value": ["UPDATE"]},
            ],
            "sorting": [{"field": "eventTime", "order": "DESC"}],
            "pagination": {"pageSize": 50, "offset": 0},
            "options": {"needTotals": "true", "metadata": "latest"},
        }
        assert len(page) == 1
        summary = page[0]
        assert summary.transaction_id == "txn_abc123def456"
        assert summary.event_type is AuditEventType.UPDATE
        assert summary.event_time == datetime(2026, 3, 15, 14, 30, tzinfo=UTC)
        assert summary.entity_type == "Campaign"
        assert summary.count == 2
        assert summary.user_type is AuditUserType.CUSTOMER_API
        assert summary.modified_by == "api-client-1"
        assert page.has_more is False

    def test_query_without_options_omits_key(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query() omits the options key when no options are given."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/query",
            json={"result": [], "pagination": None, "error": None},
        )
        ChangeHistoryResource(v1_client).query(
            Query().where("eventTime", "GREATER_THAN", "2026-02-01T00:00:00")
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/query")
        assert request is not None
        assert json.loads(request.content) == {
            "filters": [
                {
                    "field": "eventTime",
                    "operator": "GREATER_THAN",
                    "value": "2026-02-01T00:00:00",
                }
            ]
        }

    async def test_query_async(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test query_async() POSTs the body and parses the page identically."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/query",
            json={"result": [AUDIT_SUMMARY_JSON], "error": None},
        )
        page = await ChangeHistoryResource(v1_client).query_async(
            Query().where("eventTime", "LESS_THAN", "2026-08-01T00:00:00"),
            options={"needTotals": "false"},
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/query")
        assert request is not None
        assert json.loads(request.content)["options"] == {"needTotals": "false"}
        assert page[0].event_type is AuditEventType.UPDATE

    def test_query_parses_metas_dynamic_entity_key(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test metas entries keep the dynamic entity-type key and detailId."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/query",
            json={"result": [AUDIT_SUMMARY_JSON], "error": None},
        )
        page = ChangeHistoryResource(v1_client).query(
            Query().where("eventTime", "GREATER_THAN", "2026-02-01T00:00:00")
        )
        meta = page[0].metas[0]
        assert meta.detail_id == DETAIL_ID
        assert meta.meta == {"name": "Spring Sale"}
        assert meta.entity_ids == {"Campaign": "444555666"}


class TestGetDetails:
    """Tests for GET /v1/change-history/{detailId}."""

    def test_get_details(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get_details() issues GET with paging params and parses changes."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/{DETAIL_ID}?limit=50&offset=10",
            json={
                "dataType": "ChangeDetail",
                "result": [CHANGE_DETAILS_JSON],
                "pagination": {"offset": 10, "pageSize": 50, "totalCount": 1},
                "error": None,
            },
        )
        page = ChangeHistoryResource(v1_client).get_details(DETAIL_ID, limit=50, offset=10)
        request = httpx_mock.get_request(url=f"{BASE_URL}/{DETAIL_ID}?limit=50&offset=10")
        assert request is not None
        assert request.method == "GET"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert len(page) == 1
        details = page[0]
        assert isinstance(details, ChangeDetails)
        assert details.detail_id == DETAIL_ID
        assert details.entity_id == "444555666"
        assert details.event_type is AuditEventType.UPDATE
        assert details.user_type is AuditUserType.CUSTOMER
        assert details.entity_meta_data == {"name": "Spring Sale", "adAccountId": "12345"}
        change = details.details[0].changes[0]
        assert change.field == "dailyBudget"
        assert change.old_values == ["50.00"]
        assert change.new_values == ["75.00"]

    def test_get_details_without_paging_params(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test get_details() sends no query string when paging is unset."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/{DETAIL_ID}",
            json={"result": [CHANGE_DETAILS_JSON], "error": None},
        )
        page = ChangeHistoryResource(v1_client).get_details(DETAIL_ID)
        request = httpx_mock.get_request(url=f"{BASE_URL}/{DETAIL_ID}")
        assert request is not None
        assert request.url.query == b""
        assert page[0].transaction_id == "txn_abc123def456"

    async def test_get_details_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test get_details_async() parses the result identically."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/{DETAIL_ID}?limit=5",
            json={"result": [CHANGE_DETAILS_JSON], "error": None},
        )
        page = await ChangeHistoryResource(v1_client).get_details_async(DETAIL_ID, limit=5)
        assert page[0].detail_id == DETAIL_ID
        assert page[0].event_time == datetime(2026, 3, 15, 14, 30, tzinfo=UTC)


class TestErrors:
    """Tests for error handling."""

    def test_http_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx response carrying an error block raises PartialFailureError."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/query",
            json={
                "result": None,
                "pagination": None,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "eventTime filter is required",
                    "details": [
                        {
                            "code": "MISSING_FIELD",
                            "message": "eventTime filter missing",
                            "info": {"field": "eventTime"},
                        }
                    ],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            ChangeHistoryResource(v1_client).query(Query().where("eventType", "IN", ["CREATE"]))
        assert exc_info.value.details[0]["code"] == "MISSING_FIELD"


class TestEnumsAndModels:
    """Tests for enum values and the change-history error object."""

    def test_event_type_round_trip(self) -> None:
        """Test AuditEventType parses from and dumps back to its wire value."""
        summary = AuditSummary.model_validate({"eventType": "DELETE"})
        assert summary.event_type is AuditEventType.DELETE
        dumped = summary.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped == {"eventType": "DELETE", "metas": []}

    def test_audit_event_type_values(self) -> None:
        """Test AuditEventType carries the exact documented values."""
        assert {event.value for event in AuditEventType} == {"CREATE", "UPDATE", "DELETE"}

    def test_audit_user_type_values(self) -> None:
        """Test AuditUserType carries the exact documented values."""
        assert {user.value for user in AuditUserType} == {
            "CUSTOMER",
            "CUSTOMER_API",
            "APPLE_SUPPORT",
        }

    def test_audit_operator_values(self) -> None:
        """Test AuditOperator carries the exact documented values."""
        assert {op.value for op in AuditOperator} == {
            "EQUALS",
            "IN",
            "LESS_THAN",
            "LESS_THAN_OR_EQUAL_TO",
            "GREATER_THAN",
            "GREATER_THAN_OR_EQUAL_TO",
            "BETWEEN",
        }

    def test_audit_sort_order_values(self) -> None:
        """Test AuditSortOrder carries the exact documented values."""
        assert {order.value for order in AuditSortOrder} == {"ASC", "DESC"}

    def test_error_message_uses_closed_code_enum(self) -> None:
        """Test ErrorMessage parses its closed code enum and detail entries."""
        error = ErrorMessage.model_validate(
            {
                "code": "NOT_AUTHED",
                "message": "not authorized",
                "details": [
                    {"code": "MISSING_FIELD", "message": "m", "info": {"field": "eventTime"}}
                ],
            }
        )
        assert error.code is ErrorMessageCode.NOT_AUTHED
        assert error.details is not None
        assert error.details[0].info == {"field": "eventTime"}
        assert {code.value for code in ErrorMessageCode} == {
            "BAD_REQUEST",
            "NOT_FOUND",
            "NOT_AUTHED",
        }
