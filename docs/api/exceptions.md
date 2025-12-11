# Exceptions Reference

## Exception Hierarchy

```
AppleSearchAdsError
├── AuthenticationError
├── ConfigurationError
├── NotFoundError
├── RateLimitError
└── ValidationError
```

## AppleSearchAdsError

Base exception for all API errors.

```python
from asa_api_client import AppleSearchAdsError

try:
    client.campaigns.list()
except AppleSearchAdsError as e:
    print(f"API error: {e}")
```

## AuthenticationError

Raised when authentication fails.

```python
from asa_api_client import AuthenticationError

try:
    client.campaigns.list()
except AuthenticationError:
    print("Invalid credentials or expired token")
```

## ConfigurationError

Raised when client configuration is invalid.

```python
from asa_api_client import ConfigurationError

try:
    client = AppleSearchAdsClient(...)
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## NotFoundError

Raised when a resource is not found.

```python
from asa_api_client import NotFoundError

try:
    campaign = client.campaigns.get(123)
except NotFoundError:
    print("Campaign not found")
```

## RateLimitError

Raised when API rate limit is exceeded.

```python
from asa_api_client import RateLimitError

try:
    client.campaigns.list()
except RateLimitError as e:
    print(f"Rate limited, retry after: {e.retry_after}")
```

## ValidationError

Raised when request validation fails.

```python
from asa_api_client import ValidationError

try:
    client.campaigns.create(invalid_data)
except ValidationError as e:
    print(f"Validation error: {e}")
```
