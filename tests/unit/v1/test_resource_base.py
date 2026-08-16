"""Tests for the v1 transport base and resource mixins."""

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NotFoundError,
    PartialFailureError,
    RateLimitError,
    ValidationError,
)
from asa_api_client.v1.models.base import V1Model
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.base import (
    CreatableMixin,
    DeletableMixin,
    GettableMixin,
    QueryableMixin,
    UpdatableMixin,
    V1Resource,
)

BASE_URL = "https://api.ads.apple.com/v1"


class DummyModel(V1Model):
    """Minimal model for transport tests."""

    id: int
    name: str = ""


class DummyResource(
    GettableMixin,
    QueryableMixin,
    CreatableMixin,
    UpdatableMixin,
    DeletableMixin,
    V1Resource[DummyModel, DummyModel, DummyModel],
):
    """Resource with every mixin, for exercising the base."""

    base_path = "dummies"
    model_class = DummyModel


class WrappedResource(DummyResource):
    """Resource whose write bodies are wrapped in a named key."""

    payload_wrapper = "dummy"


class ContextFreeResource(DummyResource):
    """Resource that does not require the ad-account context header."""

    requires_account_context = False


class StubAuthenticator:
    """Authenticator stub recording invalidations."""

    def __init__(self) -> None:
        """Initialize with no invalidations recorded."""
        self.invalidated = False

    def get_access_token(self, _http_client: Any) -> Any:
        """Return a stub token."""
        return SimpleNamespace(authorization_header="Bearer test-token")

    async def get_access_token_async(self, _http_client: Any) -> Any:
        """Return a stub token asynchronously."""
        return SimpleNamespace(authorization_header="Bearer test-token")

    def invalidate_token(self) -> None:
        """Record that the token was invalidated."""
        self.invalidated = True


def make_client(ad_account_id: str | None = "12345") -> Any:
    """Build a fake client satisfying the V1Resource protocol."""
    return SimpleNamespace(
        _base_url=BASE_URL,
        ad_account_id=ad_account_id,
        _authenticator=StubAuthenticator(),
        _get_http_client=lambda: httpx.Client(),
        _get_async_http_client=lambda: httpx.AsyncClient(),
    )


class TestHeaders:
    """Tests for request header construction."""

    def test_sends_auth_and_account_context(self, httpx_mock: HTTPXMock) -> None:
        """Test Authorization, X-AP-Context, and Content-Type headers."""
        httpx_mock.add_response(url=f"{BASE_URL}/dummies/1", json={"result": {"id": 1}})
        DummyResource(make_client()).get(1)
        request = httpx_mock.get_requests()[0]
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert request.headers["Content-Type"] == "application/json"

    def test_missing_account_id_raises_configuration_error(self) -> None:
        """Test account-scoped resources demand an ad_account_id."""
        with pytest.raises(ConfigurationError, match="ad_account_id"):
            DummyResource(make_client(ad_account_id=None)).get(1)

    def test_context_free_resource_omits_header(self, httpx_mock: HTTPXMock) -> None:
        """Test context-free resources work without an ad_account_id."""
        httpx_mock.add_response(url=f"{BASE_URL}/dummies/1", json={"result": {"id": 1}})
        ContextFreeResource(make_client(ad_account_id=None)).get(1)
        assert "X-AP-Context" not in httpx_mock.get_requests()[0].headers

    def test_context_free_resource_sends_header_when_set(self, httpx_mock: HTTPXMock) -> None:
        """Test context-free resources still send the header when available."""
        httpx_mock.add_response(url=f"{BASE_URL}/dummies/1", json={"result": {"id": 1}})
        ContextFreeResource(make_client()).get(1)
        assert httpx_mock.get_requests()[0].headers["X-AP-Context"] == "adAccountId=12345"


class TestEnvelope:
    """Tests for {result, pagination, error} envelope handling."""

    def test_parses_single_item_result(self, httpx_mock: HTTPXMock) -> None:
        """Test result objects parse into the resource model."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/7", json={"result": {"id": 7, "name": "A"}}
        )
        item = DummyResource(make_client()).get(7)
        assert item == DummyModel(id=7, name="A")

    def test_http_200_with_error_block_raises_partial_failure(self, httpx_mock: HTTPXMock) -> None:
        """Test the issue-#30 class: 2xx responses carrying errors raise."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/7",
            json={
                "result": None,
                "error": {
                    "code": "PARTIAL",
                    "message": "some items failed",
                    "details": [{"code": "NOT_SAME_CURRENCY_AS_ORG_CURRENCY", "message": "bad"}],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            DummyResource(make_client()).get(7)
        assert exc_info.value.details[0]["code"] == "NOT_SAME_CURRENCY_AS_ORG_CURRENCY"

    def test_null_error_block_is_ignored(self, httpx_mock: HTTPXMock) -> None:
        """Test explicit "error": null does not raise."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/7",
            json={"result": {"id": 7}, "pagination": None, "error": None},
        )
        assert DummyResource(make_client()).get(7).id == 7

    async def test_async_error_block_raises(self, httpx_mock: HTTPXMock) -> None:
        """Test the async path also raises on 2xx error blocks."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/7",
            json={"result": None, "error": {"message": "nope"}},
        )
        with pytest.raises(PartialFailureError):
            await DummyResource(make_client()).get_async(7)


class TestErrorMapping:
    """Tests for HTTP status → exception mapping."""

    def test_404_raises_not_found(self, httpx_mock: HTTPXMock) -> None:
        """Test 404 maps to NotFoundError with the API message."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/9",
            status_code=404,
            json={"error": {"code": "not_found", "message": "no such dummy"}},
        )
        with pytest.raises(NotFoundError, match="no such dummy"):
            DummyResource(make_client()).get(9)

    def test_400_raises_validation_error_with_field_errors(self, httpx_mock: HTTPXMock) -> None:
        """Test 400 details become ValidationError field errors."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies",
            status_code=400,
            json={
                "error": {
                    "code": "bad_request",
                    "message": "invalid",
                    "details": [
                        {
                            "code": "UNRECOGNIZED_PROPERTY",
                            "message": "unknown field",
                            "info": {"field": "budget"},
                        }
                    ],
                }
            },
        )
        with pytest.raises(ValidationError) as exc_info:
            DummyResource(make_client()).create(DummyModel(id=1))
        assert exc_info.value.field_errors == {"budget": ["unknown field"]}

    def test_401_invalidates_token(self, httpx_mock: HTTPXMock) -> None:
        """Test 401 raises AuthenticationError and invalidates the token."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/1",
            status_code=401,
            json={"error": {"message": "expired"}},
        )
        client = make_client()
        with pytest.raises(AuthenticationError):
            DummyResource(client).get(1)
        assert client._authenticator.invalidated is True

    def test_429_exhausts_retries_then_raises(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test rate limiting raises after retries are exhausted."""
        monkeypatch.setattr("asa_api_client.v1.resources.base.time.sleep", lambda _: None)
        for _ in range(2):
            httpx_mock.add_response(
                url=f"{BASE_URL}/dummies/1",
                status_code=429,
                json={"error": {"message": "slow down"}},
            )
        with pytest.raises(RateLimitError):
            DummyResource(make_client())._request("GET", "1", max_retries=1)


class TestRetry:
    """Tests for retry behavior."""

    def test_retries_429_then_succeeds(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test a 429 is retried and the retry succeeds."""
        monkeypatch.setattr("asa_api_client.v1.resources.base.time.sleep", lambda _: None)
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/1", status_code=429, json={"error": {"message": "wait"}}
        )
        httpx_mock.add_response(url=f"{BASE_URL}/dummies/1", json={"result": {"id": 1}})
        assert DummyResource(make_client()).get(1).id == 1

    def test_query_post_is_retried(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test POST query endpoints participate in retry (idempotent read)."""
        monkeypatch.setattr("asa_api_client.v1.resources.base.time.sleep", lambda _: None)
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/query", status_code=503, json={"error": {"message": "down"}}
        )
        httpx_mock.add_response(url=f"{BASE_URL}/dummies/query", json={"result": [{"id": 1}]})
        page = DummyResource(make_client()).query()
        assert len(page) == 1


class TestQueryAndPagination:
    """Tests for query() and iter_all()."""

    def test_query_posts_payload(self, httpx_mock: HTTPXMock) -> None:
        """Test query() POSTs the serialized query body to /query."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/query",
            json={
                "result": [{"id": 1, "name": "A"}],
                "pagination": {"offset": 0, "pageSize": 10, "totalCount": 1},
            },
        )
        page = DummyResource(make_client()).query(
            Query().where("status", "EQUALS", "ENABLED").page(size=10)
        )
        body = json.loads(httpx_mock.get_requests()[0].content)
        assert body == {
            "filters": [{"field": "status", "operator": "EQUALS", "value": "ENABLED"}],
            "pagination": {"pageSize": 10},
        }
        assert page[0].name == "A"
        assert page.has_more is False

    def test_query_without_arguments_posts_empty_body(self, httpx_mock: HTTPXMock) -> None:
        """Test query() with no Query posts an empty JSON object."""
        httpx_mock.add_response(url=f"{BASE_URL}/dummies/query", json={"result": []})
        DummyResource(make_client()).query()
        assert json.loads(httpx_mock.get_requests()[0].content) == {}

    def test_iter_all_walks_pages(self, httpx_mock: HTTPXMock) -> None:
        """Test iter_all pages through results using totalCount."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/query",
            json={
                "result": [{"id": 1}, {"id": 2}],
                "pagination": {"offset": 0, "pageSize": 2, "totalCount": 3},
            },
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/query",
            json={
                "result": [{"id": 3}],
                "pagination": {"offset": 2, "pageSize": 2, "totalCount": 3},
            },
        )
        items = list(DummyResource(make_client()).iter_all(page_size=2))
        assert [item.id for item in items] == [1, 2, 3]
        first, second = httpx_mock.get_requests()
        assert json.loads(first.content)["pagination"] == {
            "pageSize": 2,
            "offset": 0,
            "fetchTotalCount": True,
        }
        assert json.loads(second.content)["pagination"]["offset"] == 2

    def test_iter_all_preserves_filters(self, httpx_mock: HTTPXMock) -> None:
        """Test iter_all keeps the caller's filters on every page."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/query",
            json={
                "result": [{"id": 1}],
                "pagination": {"offset": 0, "pageSize": 2, "totalCount": 1},
            },
        )
        query = Query().where("status", "EQUALS", "ENABLED")
        list(DummyResource(make_client()).iter_all(query, page_size=2))
        body = json.loads(httpx_mock.get_requests()[0].content)
        assert body["filters"] == [{"field": "status", "operator": "EQUALS", "value": "ENABLED"}]

    async def test_iter_all_async_walks_pages(self, httpx_mock: HTTPXMock) -> None:
        """Test the async iterator pages identically."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/query",
            json={
                "result": [{"id": 1}],
                "pagination": {"offset": 0, "pageSize": 1, "totalCount": 2},
            },
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/query",
            json={
                "result": [{"id": 2}],
                "pagination": {"offset": 1, "pageSize": 1, "totalCount": 2},
            },
        )
        ids = [item.id async for item in DummyResource(make_client()).iter_all_async(page_size=1)]
        assert ids == [1, 2]


class TestWrites:
    """Tests for create/update/delete."""

    def test_create_posts_serialized_body(self, httpx_mock: HTTPXMock) -> None:
        """Test create() POSTs the aliased, none-stripped body."""
        httpx_mock.add_response(url=f"{BASE_URL}/dummies", json={"result": {"id": 1, "name": "A"}})
        created = DummyResource(make_client()).create(DummyModel(id=1, name="A"))
        assert json.loads(httpx_mock.get_requests()[0].content) == {"id": 1, "name": "A"}
        assert created.id == 1

    def test_payload_wrapper_wraps_write_bodies(self, httpx_mock: HTTPXMock) -> None:
        """Test payload_wrapper nests create/update bodies under its key."""
        httpx_mock.add_response(url=f"{BASE_URL}/dummies", json={"result": {"id": 1, "name": "A"}})
        WrappedResource(make_client()).create(DummyModel(id=1, name="A"))
        assert json.loads(httpx_mock.get_requests()[0].content) == {"dummy": {"id": 1, "name": "A"}}

    def test_update_puts_to_resource_id(self, httpx_mock: HTTPXMock) -> None:
        """Test update() PUTs to the item path."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/dummies/5", json={"result": {"id": 5, "name": "B"}}
        )
        updated = DummyResource(make_client()).update(5, DummyModel(id=5, name="B"))
        request = httpx_mock.get_requests()[0]
        assert request.method == "PUT"
        assert updated.name == "B"

    def test_delete_returns_none_on_204(self, httpx_mock: HTTPXMock) -> None:
        """Test delete() handles an empty 204 response."""
        httpx_mock.add_response(url=f"{BASE_URL}/dummies/5", status_code=204)
        assert DummyResource(make_client()).delete(5) is None
