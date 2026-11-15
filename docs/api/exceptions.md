# Exceptions Reference

## Exception Hierarchy

```text
AppleAdsError (alias: AppleSearchAdsError)
├── AuthenticationError
├── AuthorizationError
├── ConfigurationError
├── NetworkError
├── NotFoundError
├── PartialFailureError
├── RateLimitError
├── ServerError
└── ValidationError
```

All exceptions are exported directly from `asa_api_client`.

## AppleAdsError

Base exception for all API and client errors (`AppleSearchAdsError` is preserved as an alias for compatibility with 0.x releases).

```python
from asa_api_client import AppleAdsError

try:
    client.campaigns.query()
except AppleAdsError as exc:
    print(f"API error ({exc.status_code}): {exc}")
```

## AuthenticationError & AuthorizationError

`AuthenticationError` is raised on 401 / OAuth failures; `AuthorizationError` is raised on 403 permission failures.

```python
from asa_api_client import AuthenticationError, AuthorizationError

try:
    client.campaigns.query()
except AuthenticationError:
    print("Invalid credentials or expired key")
except AuthorizationError:
    print("Insufficient permissions for this ad account")
```

## ConfigurationError

Raised before any network request when required credentials or account settings are missing or malformed.

```python
from asa_api_client import AppleAdsClient, ConfigurationError

try:
    client = AppleAdsClient.from_env()
except ConfigurationError as exc:
    print(f"Configuration error: {exc}")
```

## NotFoundError

Raised when a requested entity ID does not exist (HTTP 404).

```python
from asa_api_client import NotFoundError

try:
    campaign = client.campaigns.get(123)
except NotFoundError:
    print("Campaign not found")
```

## PartialFailureError

Raised when the API returns HTTP 2xx with a non-empty `error` block (exposes `exc.details`).

```python
from asa_api_client import PartialFailureError

try:
    client.bulk.create_keywords(items, allow_partial_success=False)
except PartialFailureError as exc:
    for detail in exc.details:
        print(detail)
```

## RateLimitError, ServerError & NetworkError

`RateLimitError` (HTTP 429, exposes `exc.retry_after`), `ServerError` (HTTP 5xx), and `NetworkError` (timeouts / transport errors) are raised when retries are exhausted or on non-idempotent write endpoints.

## ValidationError

Raised on HTTP 400/422 validation errors (exposes `exc.field_errors`).
