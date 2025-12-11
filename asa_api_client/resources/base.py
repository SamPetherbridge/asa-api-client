"""Base resource class for API interactions.

This module provides the base infrastructure for all resource classes,
including HTTP request handling, error mapping, and pagination.
"""

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import httpx
from pydantic import BaseModel

from asa_api_client.exceptions import (
    AppleSearchAdsError,
    AuthenticationError,
    AuthorizationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from asa_api_client.logging import get_logger
from asa_api_client.models.base import PageDetail, PaginatedResponse, Selector

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)
CreateT = TypeVar("CreateT", bound=BaseModel)
UpdateT = TypeVar("UpdateT", bound=BaseModel)


class BaseResource(Generic[T, CreateT, UpdateT]):
    """Base class for API resources.

    Provides common functionality for making API requests, handling
    errors, and paginating results.

    Attributes:
        client: The parent AppleSearchAdsClient.
        base_path: The base URL path for this resource.
        model_class: The Pydantic model class for this resource.
    """

    base_path: str = ""
    model_class: type[T]

    def __init__(self, client: "AppleSearchAdsClient") -> None:
        """Initialize the resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
        """
        self._client = client

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

        if extra:
            return f"{base}/{resource_path}/{extra}"
        return f"{base}/{resource_path}"

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests.

        Returns:
            Dictionary of headers including authorization.
        """
        token = self._client._authenticator.get_access_token(self._http_client)
        return {
            "Authorization": token.authorization_header,
            "X-AP-Context": f"orgId={self._client.org_id}",
            "Content-Type": "application/json",
        }

    async def _get_headers_async(self) -> dict[str, str]:
        """Get headers for async API requests.

        Returns:
            Dictionary of headers including authorization.
        """
        token = await self._client._authenticator.get_access_token_async(self._async_http_client)
        return {
            "Authorization": token.authorization_header,
            "X-AP-Context": f"orgId={self._client.org_id}",
            "Content-Type": "application/json",
        }

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
            error_body = response.json()
        except Exception:
            error_body = {"message": response.text}

        # Include request info in error body for debugging
        error_body["_request"] = request_info

        # Extract error message
        error_message = error_body.get("error", {}).get(
            "message",
            error_body.get("message", f"HTTP {status} error"),
        )

        logger.warning("API error: %s (status=%d) - %s", error_message, status, request_info)

        if status == 401:
            # Invalidate token and raise auth error
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
            # Extract field-level errors if available
            field_errors: dict[str, list[str]] = {}
            if "errors" in error_body:
                for err in error_body["errors"]:
                    field = err.get("field", "general")
                    msg = err.get("message", "Unknown error")
                    if field not in field_errors:
                        field_errors[field] = []
                    field_errors[field].append(msg)

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

    def _request(
        self,
        method: str,
        path: str = "",
        *,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a synchronous API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: URL path to append to base_path.
            json: JSON body to send.
            params: Query parameters.

        Returns:
            The parsed JSON response.

        Raises:
            AppleSearchAdsError: If the request fails.
        """
        url = self._build_url(path)
        headers = self._get_headers()

        logger.debug("%s %s", method, url)

        try:
            response = self._http_client.request(
                method,
                url,
                json=json,
                params=params,
                headers=headers,
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Request failed: {e}") from e

        if response.status_code >= 400:
            self._handle_error(response)

        if response.status_code == 204:
            return {}

        result: dict[str, Any] = response.json()
        return result

    async def _request_async(
        self,
        method: str,
        path: str = "",
        *,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an asynchronous API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: URL path to append to base_path.
            json: JSON body to send.
            params: Query parameters.

        Returns:
            The parsed JSON response.

        Raises:
            AppleSearchAdsError: If the request fails.
        """
        url = self._build_url(path)
        headers = await self._get_headers_async()

        logger.debug("%s %s (async)", method, url)

        try:
            response = await self._async_http_client.request(
                method,
                url,
                json=json,
                params=params,
                headers=headers,
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Request failed: {e}") from e

        if response.status_code >= 400:
            self._handle_error(response)

        if response.status_code == 204:
            return {}

        result: dict[str, Any] = response.json()
        return result

    def _parse_response(self, data: dict[str, Any]) -> T:
        """Parse a single item response.

        Args:
            data: The API response data.

        Returns:
            The parsed model instance.
        """
        # Apple wraps responses in a "data" key
        item_data = data.get("data", data)
        return self.model_class.model_validate(item_data)

    def _parse_list_response(self, data: dict[str, Any]) -> PaginatedResponse[T]:
        """Parse a list response.

        Args:
            data: The API response data.

        Returns:
            A paginated response containing the items.
        """
        items_data = data.get("data", [])
        pagination_data = data.get("pagination")

        items = [self.model_class.model_validate(item) for item in items_data]

        pagination = None
        if pagination_data:
            pagination = PageDetail.model_validate(pagination_data)

        return PaginatedResponse[T](data=items, pagination=pagination)


class ReadableResource(BaseResource[T, CreateT, UpdateT]):
    """A resource that supports read operations."""

    def get(self, resource_id: int) -> T:
        """Get a single resource by ID.

        Args:
            resource_id: The resource ID.

        Returns:
            The resource instance.

        Raises:
            NotFoundError: If the resource doesn't exist.
        """
        data = self._request("GET", str(resource_id))
        return self._parse_response(data)

    async def get_async(self, resource_id: int) -> T:
        """Get a single resource by ID asynchronously.

        Args:
            resource_id: The resource ID.

        Returns:
            The resource instance.

        Raises:
            NotFoundError: If the resource doesn't exist.
        """
        data = await self._request_async("GET", str(resource_id))
        return self._parse_response(data)

    def list(
        self,
        *,
        limit: int = 1000,
        offset: int = 0,
    ) -> PaginatedResponse[T]:
        """List resources with pagination.

        Args:
            limit: Maximum number of results to return.
            offset: Starting position for results.

        Returns:
            A paginated response containing the resources.
        """
        params = {"limit": limit, "offset": offset}
        data = self._request("GET", params=params)
        return self._parse_list_response(data)

    async def list_async(
        self,
        *,
        limit: int = 1000,
        offset: int = 0,
    ) -> PaginatedResponse[T]:
        """List resources with pagination asynchronously.

        Args:
            limit: Maximum number of results to return.
            offset: Starting position for results.

        Returns:
            A paginated response containing the resources.
        """
        params = {"limit": limit, "offset": offset}
        data = await self._request_async("GET", params=params)
        return self._parse_list_response(data)

    def find(self, selector: Selector) -> PaginatedResponse[T]:
        """Find resources matching a selector.

        Args:
            selector: The query selector with conditions.

        Returns:
            A paginated response containing matching resources.

        Example:
            Find enabled campaigns::

                results = client.campaigns.find(
                    Selector()
                    .where("status", "==", "ENABLED")
                    .limit(50)
                )
        """
        data = self._request(
            "POST",
            "find",
            json=selector.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return self._parse_list_response(data)

    async def find_async(self, selector: Selector) -> PaginatedResponse[T]:
        """Find resources matching a selector asynchronously.

        Args:
            selector: The query selector with conditions.

        Returns:
            A paginated response containing matching resources.
        """
        data = await self._request_async(
            "POST",
            "find",
            json=selector.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return self._parse_list_response(data)

    def iter_all(self, *, page_size: int = 1000) -> Iterator[T]:
        """Iterate over all resources with automatic pagination.

        This method handles pagination automatically, yielding each
        resource one at a time.

        Args:
            page_size: Number of items to fetch per page.

        Yields:
            Each resource in the collection.

        Example:
            Iterate over all campaigns::

                for campaign in client.campaigns.iter_all():
                    print(campaign.name)
        """
        offset = 0
        while True:
            page = self.list(limit=page_size, offset=offset)
            yield from page

            if not page.has_more:
                break

            offset += page_size

    async def iter_all_async(self, *, page_size: int = 1000) -> AsyncIterator[T]:
        """Iterate over all resources with automatic pagination asynchronously.

        Args:
            page_size: Number of items to fetch per page.

        Yields:
            Each resource in the collection.
        """
        offset = 0
        while True:
            page = await self.list_async(limit=page_size, offset=offset)
            for item in page:
                yield item

            if not page.has_more:
                break

            offset += page_size


class WritableResource(ReadableResource[T, CreateT, UpdateT]):
    """A resource that supports create, update, and delete operations."""

    def create(self, data: CreateT) -> T:
        """Create a new resource.

        Args:
            data: The creation data.

        Returns:
            The created resource.

        Raises:
            ValidationError: If the data is invalid.
        """
        response = self._request(
            "POST",
            json=data.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return self._parse_response(response)

    async def create_async(self, data: CreateT) -> T:
        """Create a new resource asynchronously.

        Args:
            data: The creation data.

        Returns:
            The created resource.

        Raises:
            ValidationError: If the data is invalid.
        """
        response = await self._request_async(
            "POST",
            json=data.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return self._parse_response(response)

    def update(self, resource_id: int, data: UpdateT) -> T:
        """Update an existing resource.

        Args:
            resource_id: The resource ID to update.
            data: The update data.

        Returns:
            The updated resource.

        Raises:
            NotFoundError: If the resource doesn't exist.
            ValidationError: If the data is invalid.
        """
        response = self._request(
            "PUT",
            str(resource_id),
            json=data.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return self._parse_response(response)

    async def update_async(self, resource_id: int, data: UpdateT) -> T:
        """Update an existing resource asynchronously.

        Args:
            resource_id: The resource ID to update.
            data: The update data.

        Returns:
            The updated resource.

        Raises:
            NotFoundError: If the resource doesn't exist.
            ValidationError: If the data is invalid.
        """
        response = await self._request_async(
            "PUT",
            str(resource_id),
            json=data.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return self._parse_response(response)

    def delete(self, resource_id: int) -> None:
        """Delete a resource.

        Args:
            resource_id: The resource ID to delete.

        Raises:
            NotFoundError: If the resource doesn't exist.
        """
        self._request("DELETE", str(resource_id))

    async def delete_async(self, resource_id: int) -> None:
        """Delete a resource asynchronously.

        Args:
            resource_id: The resource ID to delete.

        Raises:
            NotFoundError: If the resource doesn't exist.
        """
        await self._request_async("DELETE", str(resource_id))
