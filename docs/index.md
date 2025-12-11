# ASA API Client

A modern, fully-typed Python client for the Apple Search Ads API with async support and Pydantic models.

## Features

- **Full Type Safety** - Complete type hints with strict mypy compliance
- **Async Support** - Both sync and async methods in a unified client
- **Pydantic Models** - Validated request/response models
- **Resource-based API** - Intuitive `client.campaigns.list()` pattern
- **Automatic Pagination** - `iter_all()` and `iter_all_async()` helpers
- **Reports with Pandas** - Optional DataFrame export

## Installation

```bash
uv add asa-api-client
```

Or with pip:

```bash
pip install asa-api-client
```

## Quick Example

```python
from asa_api_client import AppleSearchAdsClient

client = AppleSearchAdsClient.from_env()

with client:
    campaigns = client.campaigns.list()
    for campaign in campaigns:
        print(f"{campaign.name}: {campaign.status}")
```

## CLI Tool

For a command-line interface, see [asa-api-cli](https://github.com/SamPetherbridge/asa-api-cli).

## License

MIT License - Copyright (c) 2025 Peth Pty Ltd
