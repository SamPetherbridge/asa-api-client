"""Base transport and mixins for Apple Ads Platform API v1 resources.

This module provides the v1 counterpart of the v5 resource base: HTTP
request handling with retries, the ``{result, pagination, error}``
envelope, error mapping, and the CRUD/query mixins concrete resources
compose from.

Unlike v5, an ``error`` block in the response body always raises — even
on HTTP 2xx — so partial failures can never masquerade as success.
"""

import asyncio
import os
import sys
import time
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar

import httpx
from pydantic import BaseModel

from asa_api_client.exceptions import (
    AppleSearchAdsError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    NetworkError,
    NotFoundError,
    PartialFailureError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from asa_api_client.logging import get_logger
from asa_api_client.v1.models.base import V1Error, V1Page, V1Pagination
from asa_api_client.v1.query import Query

if TYPE_CHECKING:
    from asa_api_client.v1.client import AppleAdsClient

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)
CreateT = TypeVar("CreateT", bound=BaseModel)
UpdateT = TypeVar("UpdateT", bound=BaseModel)

# Retry configuration (mirrors the v5 client's behavior).
DEFAULT_MAX_RETRIES = 5
DEFAULT_INITIAL_DELAY = 5.0  # seconds - Apple rate limits often need longer waits
DEFAULT_MAX_DELAY = 120.0  # seconds
DEFAULT_BACKOFF_FACTOR = 2.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Request counter for ASA_DEBUG output
_request_count = 0


class _SupportsResource(Protocol):
    """The slice of AppleAdsClient that V1Resource depends on."""

    _base_url: str
    ad_account_id: str | None

    @property
    def _authenticator(self) -> Any: ...

    def _get_http_client(self) -> httpx.Client: ...

    def _get_async_http_client(self) -> httpx.AsyncClient: ...


class V1Resource(Generic[T, CreateT, UpdateT]):
    """Base class for v1 API resources.

    Attributes:
        base_path: The resource's URL path segment (e.g. ``"campaigns"``).
        model_class: The Pydantic model for items of this resource.
        payload_wrapper: When set, create/update bodies are nested under
            this key (e.g. ``"campaign"`` → ``{"campaign": {...}}``).
        requires_account_context: Whether requests need the
            ``X-AP-Context: adAccountId=...`` header. Account-scoped
            resources (the default) raise ``ConfigurationError`` when the
            client has no ``ad_account_id``.
    """

    base_path: str = ""
    model_class: type[T]
    payload_wrapper: str | None = None
    requires_account_context: bool = True

    def __init__(self, client: "AppleAdsClient") -> None:
        """Initialize the resource.

        Args:
            client: The parent AppleAdsClient instance.
        """
        self._client: _SupportsResource = client

    @property
    def _http_client(self) -> httpx.Client:
        """Get the sync HTTP client."""
        return self._client._get_http_client()

    @property
    def _async_http_client(self) -> httpx.AsyncClient:
        """Get the async HTTP client."""
        return self._client._get_async_http_client()

    def _build_url(self, path: str = "") -> str:
        """Build the full API URL.

        Args:
            path: Additional path to append to base_path.

        Returns:
            The full API URL.
        """
        base = self._client._base_url.rstrip("/")
        resource_path = self.base_path.strip("/")
        extra = path.strip("/") if path else ""

        parts = [part for part in (base, resource_path, extra) if part]
        return "/".join(parts)

    def _context_header(self) -> dict[str, str]:
        """Build the X-AP-Context header, validating configuration.

        Returns:
            A dict with the context header, or empty when the resource
            is context-free and no account is configured.

        Raises:
            ConfigurationError: If the resource requires account context
                but the client has no ad_account_id.
        """
        ad_account_id = self._client.ad_account_id
        if ad_account_id is not None:
            return {"X-AP-Context": f"adAccountId={ad_account_id}"}
        if self.requires_account_context:
            raise ConfigurationError(
                "ad_account_id is required for this endpoint. Set it on the "
                "client (or ASA_AD_ACCOUNT_ID in the environment); use "
                "client.ad_accounts to discover available accounts."
            )
        return {}

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests.

        Returns:
            Dictionary of headers including authorization.
        """
        token = self._client._authenticator.get_access_token(self._http_client)
        return {
            "Authorization": token.authorization_header,
            "Content-Type": "application/json",
            **self._context_header(),
        }

    async def _get_headers_async(self) -> dict[str, str]:
        """Get headers for async API requests.

        Returns:
            Dictionary of headers including authorization.
        """
        token = await self._client._authenticator.get_access_token_async(self._async_http_client)
        return {
            "Authorization": token.authorization_header,
            "Content-Type": "application/json",
            **self._context_header(),
        }

    def _extract_error(self, body: dict[str, Any]) -> V1Error | None:
        """Extract the error block from a response body, if present.

        Args:
            body: The parsed response JSON.

        Returns:
            The parsed error, or None when the body carries no error.
        """
        error_data = body.get("error")
        if not error_data:
            return None
        return V1Error.model_validate(error_data)

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle an error response from the API.

        Args:
            response: The HTTP response.

        Raises:
            AppleSearchAdsError: An appropriate exception based on status code.
        """
        status = response.status_code
        request_info = f"{response.request.method} {response.request.url}"

        try:
            error_body: dict[str, Any] = response.json()
        except Exception:
            error_body = {"message": response.text}

        error_body["_request"] = request_info

        error = self._extract_error(error_body)
        error_message = (
            (error.message if error else None)
            or error_body.get("message")
            or f"HTTP {status} error"
        )

        logger.warning("API error: %s (status=%d) - %s", error_message, status, request_info)

        if status == 401:
            self._client._authenticator.invalidate_token()
            raise AuthenticationError(
                error_message,
                status_code=status,
                response_body=error_body,
            )

        if status == 403:
            raise AuthorizationError(
                error_message,
                status_code=status,
                response_body=error_body,
            )

        if status == 404:
            raise NotFoundError(
                error_message,
                status_code=status,
                response_body=error_body,
            )

        if status == 400 or status == 422:
            field_errors: dict[str, list[str]] = {}
            if error and error.details:
                for detail in error.details:
                    info = detail.info or {}
                    field = str(info.get("field", "general"))
                    message = detail.message or detail.code or "Unknown error"
                    field_errors.setdefault(field, []).append(message)

            raise ValidationError(
                error_message,
                status_code=status,
                response_body=error_body,
                field_errors=field_errors,
            )

        if status == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                error_message,
                status_code=status,
                response_body=error_body,
                retry_after=int(retry_after) if retry_after else None,
            )

        if status >= 500:
            raise ServerError(
                error_message,
                status_code=status,
                response_body=error_body,
            )

        raise AppleSearchAdsError(
            error_message,
            status_code=status,
            response_body=error_body,
        )

    def _check_body_error(self, body: dict[str, Any], status_code: int) -> None:
        """Raise when a successful HTTP response carries an error block.

        Args:
            body: The parsed response JSON.
            status_code: The HTTP status code of the response.

        Raises:
            PartialFailureError: When the body has a non-null error.
        """
        error = self._extract_error(body)
        if error is None:
            return
        details = [detail.model_dump() for detail in error.details or []]
        raise PartialFailureError(
            error.message or error.code or "API reported errors in the response",
            status_code=status_code,
            response_body=body,
            details=details,
        )

    def _calculate_retry_delay(
        self,
        attempt: int,
        response: httpx.Response | None = None,
    ) -> float:
        """Calculate delay before next retry attempt.

        Uses exponential backoff, respecting Retry-After header if present.

        Args:
            attempt: Current attempt number (0-indexed).
            response: The HTTP response (to check Retry-After header).

        Returns:
            Delay in seconds before next retry.
        """
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(float(retry_after), DEFAULT_MAX_DELAY)
                except ValueError:
                    pass

        delay = DEFAULT_INITIAL_DELAY * (DEFAULT_BACKOFF_FACTOR**attempt)
        return min(delay, DEFAULT_MAX_DELAY)

    def _request(
        self,
        method: str,
        path: str = "",
        *,
        json: dict[str, Any] | list[dict[str, Any]] | list[int] | None = None,
        params: dict[str, Any] | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> dict[str, Any]:
        """Make a synchronous API request with automatic retry.

        Automatically retries on rate limiting (429) and server errors
        (5xx) with exponential backoff. This includes POST query
        endpoints, which are idempotent reads.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: URL path to append to base_path.
            json: JSON body to send.
            params: Query parameters.
            max_retries: Maximum number of retry attempts.

        Returns:
            The parsed JSON response.

        Raises:
            AppleSearchAdsError: If the request fails after all retries.
        """
        global _request_count
        _request_count += 1

        url = self._build_url(path)
        headers = self._get_headers()

        if os.environ.get("ASA_DEBUG"):
            short_url = url.replace("https://api.ads.apple.com/v1/", "")
            print(f"[{_request_count}] {method} {short_url}", file=sys.stderr)

        logger.debug("%s %s", method, url)

        for attempt in range(max_retries + 1):
            try:
                response = self._http_client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=headers,
                )
            except httpx.RequestError as e:
                if attempt < max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        "Request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        max_retries + 1,
                        delay,
                        str(e),
                    )
                    time.sleep(delay)
                    continue
                raise NetworkError(f"Request failed: {e}") from e

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                delay = self._calculate_retry_delay(attempt, response)
                logger.warning(
                    "Received %d (attempt %d/%d), retrying in %.1fs",
                    response.status_code,
                    attempt + 1,
                    max_retries + 1,
                    delay,
                )
                msg = f"⏳ Rate limited ({response.status_code}), "
                msg += f"attempt {attempt + 1}/{max_retries + 1}, retrying in {delay:.0f}s..."
                print(msg, file=sys.stderr)
                time.sleep(delay)
                continue

            if response.status_code >= 400:
                self._handle_error(response)

            if response.status_code == 204:
                return {}

            result: dict[str, Any] = response.json()
            self._check_body_error(result, response.status_code)
            return result

        raise NetworkError("Request failed after all retries")

    async def _request_async(
        self,
        method: str,
        path: str = "",
        *,
        json: dict[str, Any] | list[dict[str, Any]] | list[int] | None = None,
        params: dict[str, Any] | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> dict[str, Any]:
        """Make an asynchronous API request with automatic retry.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: URL path to append to base_path.
            json: JSON body to send.
            params: Query parameters.
            max_retries: Maximum number of retry attempts.

        Returns:
            The parsed JSON response.

        Raises:
            AppleSearchAdsError: If the request fails after all retries.
        """
        url = self._build_url(path)
        headers = await self._get_headers_async()

        logger.debug("%s %s (async)", method, url)

        for attempt in range(max_retries + 1):
            try:
                response = await self._async_http_client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=headers,
                )
            except httpx.RequestError as e:
                if attempt < max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        "Request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        max_retries + 1,
                        delay,
                        str(e),
                    )
                    await asyncio.sleep(delay)
                    continue
                raise NetworkError(f"Request failed: {e}") from e

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                delay = self._calculate_retry_delay(attempt, response)
                logger.warning(
                    "Received %d (attempt %d/%d), retrying in %.1fs",
                    response.status_code,
                    attempt + 1,
                    max_retries + 1,
                    delay,
                )
                await asyncio.sleep(delay)
                continue

            if response.status_code >= 400:
                self._handle_error(response)

            if response.status_code == 204:
                return {}

            result: dict[str, Any] = response.json()
            self._check_body_error(result, response.status_code)
            return result

        raise NetworkError("Request failed after all retries")

    def _parse_item(self, data: dict[str, Any]) -> T:
        """Parse a single-item response.

        Args:
            data: The API response body.

        Returns:
            The parsed model instance.
        """
        item_data = data.get("result", data)
        return self.model_class.model_validate(item_data)

    def _parse_page(self, data: dict[str, Any]) -> V1Page[T]:
        """Parse a list response into a typed page.

        Args:
            data: The API response body.

        Returns:
            A V1Page of parsed items with pagination metadata.
        """
        items_data = data.get("result") or []
        pagination_data = data.get("pagination")

        items = [self.model_class.model_validate(item) for item in items_data]
        pagination = V1Pagination.model_validate(pagination_data) if pagination_data else None

        return V1Page[T](result=items, pagination=pagination)

    def _wrap(self, body: dict[str, Any]) -> dict[str, Any]:
        """Apply the payload wrapper to a write body, if configured.

        Args:
            body: The serialized request body.

        Returns:
            The wrapped body, or the body unchanged.
        """
        if self.payload_wrapper is None:
            return body
        return {self.payload_wrapper: body}

    def _dump(self, data: BaseModel) -> dict[str, Any]:
        """Serialize a write model to its API JSON shape.

        Args:
            data: The model to serialize.

        Returns:
            The aliased, none-stripped JSON dict.
        """
        dumped: dict[str, Any] = data.model_dump(by_alias=True, exclude_none=True, mode="json")
        return dumped


class GettableMixin(V1Resource[T, CreateT, UpdateT]):
    """Adds get-by-id operations."""

    def get(self, resource_id: int | str) -> T:
        """Get a single resource by ID.

        Args:
            resource_id: The resource ID.

        Returns:
            The resource instance.

        Raises:
            NotFoundError: If the resource doesn't exist.
        """
        data = self._request("GET", str(resource_id))
        return self._parse_item(data)

    async def get_async(self, resource_id: int | str) -> T:
        """Get a single resource by ID asynchronously.

        Args:
            resource_id: The resource ID.

        Returns:
            The resource instance.

        Raises:
            NotFoundError: If the resource doesn't exist.
        """
        data = await self._request_async("GET", str(resource_id))
        return self._parse_item(data)


class QueryableMixin(V1Resource[T, CreateT, UpdateT]):
    """Adds POST /query operations and pagination iteration."""

    def query(self, query: Query | None = None) -> V1Page[T]:
        """Find resources matching a query.

        Args:
            query: The query with filters/sorting/pagination. An empty
                or omitted query returns all non-deleted resources.

        Returns:
            A page of matching resources.

        Example:
            Find enabled campaigns::

                page = client.campaigns.query(
                    Query().where("status", "EQUALS", "ENABLED")
                )
        """
        payload = query.to_payload() if query is not None else {}
        data = self._request("POST", "query", json=payload)
        return self._parse_page(data)

    async def query_async(self, query: Query | None = None) -> V1Page[T]:
        """Find resources matching a query asynchronously.

        Args:
            query: The query with filters/sorting/pagination.

        Returns:
            A page of matching resources.
        """
        payload = query.to_payload() if query is not None else {}
        data = await self._request_async("POST", "query", json=payload)
        return self._parse_page(data)

    def _paged_payload(self, query: Query | None, page_size: int, offset: int) -> dict[str, Any]:
        """Build a query payload with iteration-controlled pagination.

        Args:
            query: The caller's query (filters/sorting preserved).
            page_size: Items per page.
            offset: Zero-based position for this page.

        Returns:
            The payload with pagination overridden for iteration.
        """
        payload = query.to_payload() if query is not None else {}
        payload["pagination"] = {
            "pageSize": page_size,
            "offset": offset,
            "fetchTotalCount": True,
        }
        return payload

    def iter_all(self, query: Query | None = None, *, page_size: int = 500) -> Iterator[T]:
        """Iterate over all matching resources with automatic pagination.

        Any pagination set on ``query`` is overridden; filters and
        sorting are preserved.

        Args:
            query: Optional query with filters/sorting.
            page_size: Number of items to fetch per page.

        Yields:
            Each matching resource.

        Example:
            Iterate over all campaigns::

                for campaign in client.campaigns.iter_all():
                    print(campaign.name)
        """
        offset = 0
        while True:
            data = self._request(
                "POST", "query", json=self._paged_payload(query, page_size, offset)
            )
            page = self._parse_page(data)
            yield from page

            if not page.has_more:
                break

            offset += len(page)

    async def iter_all_async(
        self, query: Query | None = None, *, page_size: int = 500
    ) -> AsyncIterator[T]:
        """Iterate over all matching resources asynchronously.

        Args:
            query: Optional query with filters/sorting.
            page_size: Number of items to fetch per page.

        Yields:
            Each matching resource.
        """
        offset = 0
        while True:
            data = await self._request_async(
                "POST", "query", json=self._paged_payload(query, page_size, offset)
            )
            page = self._parse_page(data)
            for item in page:
                yield item

            if not page.has_more:
                break

            offset += len(page)


class CreatableMixin(V1Resource[T, CreateT, UpdateT]):
    """Adds create operations."""

    def create(self, data: CreateT) -> T:
        """Create a new resource.

        Args:
            data: The creation data.

        Returns:
            The created resource.

        Raises:
            ValidationError: If the data is invalid.
        """
        response = self._request("POST", json=self._wrap(self._dump(data)))
        return self._parse_item(response)

    async def create_async(self, data: CreateT) -> T:
        """Create a new resource asynchronously.

        Args:
            data: The creation data.

        Returns:
            The created resource.

        Raises:
            ValidationError: If the data is invalid.
        """
        response = await self._request_async("POST", json=self._wrap(self._dump(data)))
        return self._parse_item(response)


class UpdatableMixin(V1Resource[T, CreateT, UpdateT]):
    """Adds update operations.

    Note:
        v1 PUT endpoints support partial updates for scalar fields, but
        array fields are replaced entirely — send the complete desired
        array state.
    """

    def update(self, resource_id: int | str, data: UpdateT) -> T:
        """Update an existing resource.

        Args:
            resource_id: The resource ID to update.
            data: The update data (only fields to change).

        Returns:
            The updated resource.

        Raises:
            NotFoundError: If the resource doesn't exist.
            ValidationError: If the data is invalid.
        """
        response = self._request("PUT", str(resource_id), json=self._wrap(self._dump(data)))
        return self._parse_item(response)

    async def update_async(self, resource_id: int | str, data: UpdateT) -> T:
        """Update an existing resource asynchronously.

        Args:
            resource_id: The resource ID to update.
            data: The update data (only fields to change).

        Returns:
            The updated resource.

        Raises:
            NotFoundError: If the resource doesn't exist.
            ValidationError: If the data is invalid.
        """
        response = await self._request_async(
            "PUT", str(resource_id), json=self._wrap(self._dump(data))
        )
        return self._parse_item(response)


class DeletableMixin(V1Resource[T, CreateT, UpdateT]):
    """Adds delete operations."""

    def delete(self, resource_id: int | str) -> None:
        """Delete a resource.

        Args:
            resource_id: The resource ID to delete.

        Raises:
            NotFoundError: If the resource doesn't exist.
        """
        self._request("DELETE", str(resource_id))

    async def delete_async(self, resource_id: int | str) -> None:
        """Delete a resource asynchronously.

        Args:
            resource_id: The resource ID to delete.

        Raises:
            NotFoundError: If the resource doesn't exist.
        """
        await self._request_async("DELETE", str(resource_id))
