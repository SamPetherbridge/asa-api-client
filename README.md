# ASA API Client

[![PyPI version](https://img.shields.io/pypi/v/asa-api-client.svg)](https://pypi.org/project/asa-api-client/)
[![Python](https://img.shields.io/pypi/pyversions/asa-api-client.svg)](https://pypi.org/project/asa-api-client/)
[![License](https://img.shields.io/github/license/SamPetherbridge/asa-api-client.svg)](https://github.com/SamPetherbridge/asa-api-client/blob/main/LICENSE)
[![CI](https://github.com/SamPetherbridge/asa-api-client/actions/workflows/ci.yml/badge.svg)](https://github.com/SamPetherbridge/asa-api-client/actions/workflows/ci.yml)

A modern, fully-typed Python client for the Apple Search Ads API with async support and Pydantic models.

## Features

- **Full Type Safety** - Complete type hints with strict mypy compliance
- **Async Support** - Both sync and async methods in a unified client
- **Pydantic Models** - Validated request/response models
- **Resource-based API** - Intuitive `client.campaigns.list()` pattern
- **Automatic Pagination** - `iter_all()` and `iter_all_async()` helpers
- **Reports with Pandas** - Optional DataFrame export

## Installation

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv add asa-api-client
```

Using pip:

```bash
pip install asa-api-client
```

With pandas support:

```bash
uv add "asa-api-client[pandas]"
# or
pip install "asa-api-client[pandas]"
```

## Quick Start

```python
from asa_api_client import AppleSearchAdsClient

# From environment variables
client = AppleSearchAdsClient.from_env()

# Or explicit configuration
client = AppleSearchAdsClient(
    client_id="SEARCHADS.xxx",
    team_id="SEARCHADS.xxx",
    key_id="xxx",
    org_id=123456,
    private_key_path="private-key.pem",
)

# List campaigns
with client:
    campaigns = client.campaigns.list()
    for campaign in campaigns:
        print(f"{campaign.name}: {campaign.status}")
```

## Environment Variables

```bash
export ASA_CLIENT_ID="SEARCHADS.your-client-id"
export ASA_TEAM_ID="SEARCHADS.your-team-id"
export ASA_KEY_ID="your-key-id"
export ASA_ORG_ID="123456"
export ASA_PRIVATE_KEY_PATH="/path/to/private-key.pem"
```

Or use a `.env` file:

```bash
ASA_CLIENT_ID=SEARCHADS.your-client-id
ASA_TEAM_ID=SEARCHADS.your-team-id
ASA_KEY_ID=your-key-id
ASA_ORG_ID=123456
ASA_PRIVATE_KEY_PATH=private-key.pem
```

## Resources

### Campaigns

```python
# List all campaigns
campaigns = client.campaigns.list()

# Get a specific campaign
campaign = client.campaigns.get(campaign_id)

# Find with filters
from asa_api_client.models import Selector
enabled = client.campaigns.find(
    Selector().where("status", "==", "ENABLED")
)

# Create a campaign
from asa_api_client.models import CampaignCreate, Money, CampaignSupplySource
campaign = client.campaigns.create(
    CampaignCreate(
        name="My Campaign",
        adam_id=123456789,
        countries_or_regions=["US"],
        daily_budget_amount=Money(amount="100", currency="USD"),
        supply_sources=[CampaignSupplySource.APPSTORE_SEARCH_RESULTS],
    )
)
```

### Ad Groups

```python
# Access ad groups through campaign
ad_groups = client.campaigns(campaign_id).ad_groups.list()

# Create an ad group
from asa_api_client.models import AdGroupCreate
ad_group = client.campaigns(campaign_id).ad_groups.create(
    AdGroupCreate(
        name="My Ad Group",
        default_bid_amount=Money(amount="1.00", currency="USD"),
    )
)
```

### Keywords

```python
# List keywords in an ad group
keywords = client.campaigns(campaign_id).ad_groups(ad_group_id).keywords.list()

# Create keywords (bulk only)
from asa_api_client.models import KeywordCreate, KeywordMatchType
result = client.campaigns(campaign_id).ad_groups(ad_group_id).keywords.create_bulk([
    KeywordCreate(
        text="my keyword",
        match_type=KeywordMatchType.EXACT,
        bid_amount=Money(amount="1.50", currency="USD"),
    )
])
```

### Reports

```python
from datetime import date

# Campaign report
report = client.reports.campaigns(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
)

# Convert to DataFrame (requires pandas)
df = report.to_dataframe()
```

## Async Usage

```python
import asyncio

async def main():
    client = AppleSearchAdsClient.from_env()

    async with client:
        campaigns = await client.campaigns.list_async()

        # Async iteration
        async for campaign in client.campaigns.iter_all_async():
            print(campaign.name)

asyncio.run(main())
```

## CLI

For a command-line interface, install [asa-api-cli](https://github.com/SamPetherbridge/asa-api-cli):

```bash
uv tool install asa-api-cli
# or
pip install asa-api-cli
```

## License

MIT License - Copyright (c) 2025 Peth Pty Ltd
