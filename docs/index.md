# ASA API Client

A modern, fully-typed Python client for the **Apple Ads Platform API v1** (App Store and Apple Maps ads) with async support and Pydantic models. Also includes the legacy Campaign Management API v5 client (`AppleSearchAdsClient`, sunset January 26, 2027).

## Features

- **Full Type Safety** — Complete type hints with strict `mypy` and Pydantic v2 validation
- **Async Support** — Sync and `_async` methods side by side on a single client
- **Platform API v1 Coverage** — Campaigns, ad groups, keywords, ads, creatives, recommendations, insights, search-term popularity, change history, bulk operations, and Apple Maps brand ads
- **Automatic Pagination** — `iter_all()` and `iter_all_async()` helpers plus fluent `Query` filters
- **Reports with Pandas** — `report.to_dataframe()` across all report levels
- **Analysis CLI** — Multi-sheet Excel performance & search-popularity workbooks via `asa analyze`

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
from asa_api_client import AppleAdsClient
from asa_api_client.v1 import Query

with AppleAdsClient.from_env() as client:
    enabled = client.campaigns.query(Query().where("status", "EQUALS", "ENABLED"))
    for campaign in enabled:
        print(f"{campaign.name}: {campaign.display_status}")
```

## CLI Tool

For Excel performance and search-popularity reporting from the terminal, see the [CLI guide](guide/cli.md).

## License

MIT License - Copyright (c) 2025 Peth Pty Ltd
