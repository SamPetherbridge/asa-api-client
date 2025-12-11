"""Custom exceptions for the Apple Search Ads API client.

This module defines a hierarchy of exceptions that can be raised when
interacting with the Apple Search Ads API. All exceptions inherit from
`AppleSearchAdsError` for easy catching of any API-related error.

Example:
    Handling specific exceptions::

        from asa_api_client import AppleSearchAdsClient
        from asa_api_client.exceptions import NotFoundError, RateLimitError

        client = AppleSearchAdsClient(...)

        try:
            campaign = client.campaigns.get(campaign_id=12345)
        except NotFoundError:
            print("Campaign not found")
        except RateLimitError as e:
            print(f"Rate limited, retry after {e.retry_after} seconds")
"""

from typing import Any


class AppleSearchAdsError(Exception):
    """Base exception for all Apple Search Ads API errors.

    All exceptions raised by this library inherit from this class,
    making it easy to catch any API-related error.

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code from the API response, if applicable.
        response_body: Raw response body from the API, if available.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code from the API response.
            response_body: Raw response body from the API.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        """Return a string representation of the error."""
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(AppleSearchAdsError):
    """Raised when authentication fails.

    This can occur due to:
    - Invalid or expired credentials
    - Invalid JWT token
    - Missing or invalid private key
    - Incorrect client_id, team_id, or key_id

    Example:
        Handling authentication errors::

            try:
                client = AppleSearchAdsClient(
                    client_id="invalid",
                    ...
                )
                client.campaigns.list()
            except AuthenticationError as e:
                print(f"Auth failed: {e}")
    """


class AuthorizationError(AppleSearchAdsError):
    """Raised when the user lacks permission for an action.

    This occurs when the authenticated user doesn't have the required
    role or permissions to perform the requested operation.

    Common causes:
    - Insufficient API role (e.g., read-only trying to write)
    - Organization access restrictions
    - Campaign-level permission limitations
    """


class NotFoundError(AppleSearchAdsError):
    """Raised when a requested resource is not found.

    This typically occurs when:
    - A campaign, ad group, keyword, or other resource doesn't exist
    - The resource was deleted
    - The resource ID is incorrect

    Example:
        Handling not found errors::

            try:
                campaign = client.campaigns.get(campaign_id=99999)
            except NotFoundError:
                print("Campaign does not exist")
    """


class ValidationError(AppleSearchAdsError):
    """Raised when request validation fails.

    This occurs when:
    - Required fields are missing
    - Field values are invalid or out of range
    - Business logic validation fails (e.g., invalid budget)

    Attributes:
        field_errors: Dictionary mapping field names to error messages.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
        field_errors: dict[str, list[str]] | None = None,
    ) -> None:
        """Initialize the validation error.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code from the API response.
            response_body: Raw response body from the API.
            field_errors: Dictionary mapping field names to their errors.
        """
        super().__init__(message, status_code=status_code, response_body=response_body)
        self.field_errors = field_errors or {}


class RateLimitError(AppleSearchAdsError):
    """Raised when API rate limits are exceeded.

    The Apple Search Ads API has rate limits that, when exceeded,
    will return a 429 status code. This exception provides information
    about when to retry.

    Attributes:
        retry_after: Number of seconds to wait before retrying.

    Example:
        Handling rate limits::

            import time
            from asa_api_client.exceptions import RateLimitError

            try:
                campaigns = client.campaigns.list()
            except RateLimitError as e:
                print(f"Rate limited, waiting {e.retry_after}s")
                time.sleep(e.retry_after)
                campaigns = client.campaigns.list()
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
        retry_after: int | None = None,
    ) -> None:
        """Initialize the rate limit error.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code from the API response.
            response_body: Raw response body from the API.
            retry_after: Seconds to wait before retrying.
        """
        super().__init__(message, status_code=status_code, response_body=response_body)
        self.retry_after = retry_after


class ServerError(AppleSearchAdsError):
    """Raised when the API returns a server error (5xx).

    This indicates a problem on Apple's side. These errors are
    typically transient and can be retried.
    """


class NetworkError(AppleSearchAdsError):
    """Raised when a network-level error occurs.

    This includes:
    - Connection timeouts
    - DNS resolution failures
    - Connection refused errors
    - SSL/TLS errors
    """


class ConfigurationError(AppleSearchAdsError):
    """Raised when the client is misconfigured.

    This occurs before any API call is made, when the client
    detects invalid configuration such as:
    - Missing required credentials
    - Invalid private key format
    - Invalid org_id
    """
