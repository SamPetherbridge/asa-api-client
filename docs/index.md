# ASA API Client

A modern, fully-typed Python client for the **Apple Ads Platform API v1** (App Store and Apple Maps ads) with async support and Pydantic models.

## Features

- **Full Type Safety** — Complete type hints with strict `mypy` and Pydantic v2 validation (`py.typed` included)
- **Async Support** — Sync and `_async` methods side by side on a single client
- **Complete Platform API v1 Coverage** — Campaigns, ad groups, keywords, ads, creatives, recommendations, insights, search-term popularity, change history, bulk operations, and Apple Maps brand ads
- **Automatic Pagination** — `iter_*` and `*_async` helpers plus fluent `Query` filters across entity, report, insight, recommendation, suggestion, and audit endpoints
- **Reports with Pandas** — `report.to_dataframe()` and `report.to_records()` across all report levels
- **Analysis CLI** — Multi-sheet Excel performance & search-popularity workbooks via `asa-client analyze`

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
from asa_api_client import AppleAdsClient, Query

with AppleAdsClient.from_env() as client:
    enabled = client.campaigns.query(Query().where("status", "EQUALS", "ENABLED"))
    for campaign in enabled:
        print(f"{campaign.name}: {campaign.display_status}")
```

## CLI Tool

For Excel performance and search-popularity reporting from the terminal, see the [CLI guide](guide/cli.md).

> [!NOTE]
> Looking for the legacy Campaign Management API v5 (`AppleSearchAdsClient`, sunset January 26, 2027)? Pin `asa-api-client<1.0`.

## License

MIT License - Copyright (c) 2025 Peth Pty Ltd
