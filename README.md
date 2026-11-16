# ASA API Client

[![PyPI version](https://img.shields.io/pypi/v/asa-api-client.svg)](https://pypi.org/project/asa-api-client/)
[![Python](https://img.shields.io/pypi/pyversions/asa-api-client.svg)](https://pypi.org/project/asa-api-client/)
[![License](https://img.shields.io/github/license/SamPetherbridge/asa-api-client.svg)](https://github.com/SamPetherbridge/asa-api-client/blob/main/LICENSE)
[![CI](https://github.com/SamPetherbridge/asa-api-client/actions/workflows/ci.yml/badge.svg)](https://github.com/SamPetherbridge/asa-api-client/actions/workflows/ci.yml)

A modern, fully-typed Python client for the **Apple Ads Platform API v1** (App Store and Apple Maps ads) with async support and Pydantic models.

## Features

- **Full Type Safety** — Complete type hints with strict `mypy` + Pydantic v2 compliance (`py.typed` included)
- **Complete Platform API v1 Coverage** — Campaigns, ad groups, keywords, ads, creatives, recommendations, insights, search-term popularity, suggestions, change history, bulk operations, and Apple Maps brand ads
- **Sync & Async** — Every method has an `_async` counterpart on the same client, with multi-account scoping via `client.with_account(...)`
- **Automatic Pagination** — `iter_*` and `*_async` helpers plus fluent `Query` builder across entity, report, insight, recommendation, suggestion, and audit endpoints
- **Reports with Pandas** — `report.to_records()` and optional `report.to_dataframe()` export across all App Store and Apple Maps report levels
- **Analysis CLI** — Generate multi-sheet Excel performance & search-popularity workbooks via `asa-client analyze`

## Installation

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv add asa-api-client
```

Using pip:

```bash
pip install asa-api-client
```

Optional extras:

```bash
# DataFrame export (report.to_dataframe())
uv add "asa-api-client[pandas]"

# Excel analysis CLI (asa-client analyze / asa-client smoke)
uv add "asa-api-client[cli]"
```

## Quick Start

```python
from asa_api_client import AppleAdsClient, Query

# Reads ASA_* variables from the environment or .env
client = AppleAdsClient.from_env()

# Or pass credentials explicitly
client = AppleAdsClient(
    client_id="SEARCHADS.xxx",
    team_id="TEAM123",
    key_id="KEY123",
    ad_account_id="123456",
    private_key_path="private-key.pem",
)

with client:
    enabled = client.campaigns.query(Query().where("status", "EQUALS", "ENABLED"))
    for campaign in enabled:
        print(f"{campaign.id}: {campaign.name} ({campaign.display_status})")
```

Don't know your `ad_account_id` yet? Auto-resolve it via `client.resolve_ad_account()`, or run the bundled read-only smoke check:

```bash
asa-client smoke
```

## Environment Variables

```bash
export ASA_CLIENT_ID="SEARCHADS.your-client-id"
export ASA_TEAM_ID="your-team-id"
export ASA_KEY_ID="your-key-id"
export ASA_AD_ACCOUNT_ID="123456"
export ASA_PRIVATE_KEY_PATH="/path/to/private-key.pem"
```

Or use a `.env` file:

```bash
ASA_CLIENT_ID=SEARCHADS.your-client-id
ASA_TEAM_ID=your-team-id
ASA_KEY_ID=your-key-id
ASA_AD_ACCOUNT_ID=123456
ASA_PRIVATE_KEY_PATH=private-key.pem
```

## Resources

### Campaigns

```python
from asa_api_client import Query
from asa_api_client.v1.models.base import Money
from asa_api_client.v1.models.campaigns import (
    BillingEvent,
    CampaignCreate,
    CampaignTargeting,
    CampaignUpdate,
    DailyBudget,
    PromotedObjectType,
)
from asa_api_client.v1.models.shared import TargetingData

# Query or iterate all campaigns
page = client.campaigns.query(Query().where("status", "EQUALS", "ENABLED"))
all_campaigns = list(client.campaigns.iter_all())

# Get a specific campaign
campaign = client.campaigns.get(campaign_id)

# Create an App Store campaign
created = client.campaigns.create(
    CampaignCreate(
        ad_account_id=123456,
        name="US Search",
        billing_event=BillingEvent.TAPS,
        promoted_object_type=PromotedObjectType.APPSTORE_APP,
        promoted_object_id="987654321",
        daily_budget=DailyBudget(value=Money(amount="100.00", currency="USD")),
        targeting=CampaignTargeting(
            supply_source=TargetingData(include=["APPSTORE"]),
            supply_placement=TargetingData(include=["APPSTORE_SEARCH_RESULTS"]),
            country_or_region=TargetingData(include=["US"]),
        ),
    )
)

# Update daily budget
client.campaigns.update(
    campaign_id,
    CampaignUpdate(daily_budget=DailyBudget(value=Money(amount="150.00", currency="USD"))),
)
```

### Ad Groups

```python
from asa_api_client.v1.models.ad_groups import AdGroupCreate, PricingModel
from asa_api_client.v1.models.shared import BidStrategy, BidStrategyGoal, BidStrategyType

ad_groups = client.ad_groups.query(Query().where("campaignId", "EQUALS", str(campaign_id)))

ad_group = client.ad_groups.create(
    AdGroupCreate(
        name="Exact Core",
        campaign_id=campaign_id,
        pricing_model=PricingModel.CPT,
        bid_strategy=BidStrategy(
            bid_strategy_type=BidStrategyType.MANUAL_CPT,
            bid_strategy_goal=BidStrategyGoal.TAP,
            bid=Money(amount="1.50", currency="USD"),
        ),
    )
)
```

### Keywords & Bulk Operations

```python
from asa_api_client.v1.models.bulk import BulkKeywordUpdate
from asa_api_client.v1.models.keywords import KeywordCreate, KeywordMatchType

# Query keywords in an ad group
keywords = client.keywords.query(Query().where("adGroupId", "EQUALS", str(ad_group_id)))

# Bulk create, update, and delete keywords (automatically batched at 5,000 items)
created = client.bulk.create_keywords(
    [
        KeywordCreate(
            ad_group_id=ad_group_id,
            text="budget tracker",
            match_type=KeywordMatchType.EXACT,
            bid=Money(amount="1.75", currency="USD"),
        )
    ]
)

client.bulk.update_keywords(
    [BulkKeywordUpdate(id=keyword_id, bid=Money(amount="2.00", currency="USD"))]
)

client.bulk.delete_keywords([keyword_id])
```

### Reports

```python
from datetime import date

from asa_api_client.v1.models.reports import (
    AppsReportingRequest,
    ReportGranularity,
    ReportTimeRange,
)

report = client.reports.campaigns(
    AppsReportingRequest(
        time_range=ReportTimeRange(
            start=date(2026, 8, 1),
            end=date(2026, 8, 31),
            granularity=ReportGranularity.DAILY,
        )
    )
)

# Convert to a pandas DataFrame (requires asa-api-client[pandas])
df = report.to_dataframe()
```

## Async Usage

```python
import asyncio

from asa_api_client import AppleAdsClient


async def main() -> None:
    async with AppleAdsClient.from_env() as client:
        async for campaign in client.campaigns.iter_all_async():
            print(campaign.name)


asyncio.run(main())
```

## CLI

Generate a formatted Excel performance and search-popularity workbook with `asa-client analyze` (named `asa-client` so it never collides with the full `asa` command from [`asa-api-cli`](https://github.com/SamPetherbridge/asa-api-cli)):

```bash
pip install "asa-api-client[cli]"
asa-client analyze --period 90d --output report.xlsx
```

`asa-client analyze` auto-selects your ad account from `/v1/acls` when `ASA_AD_ACCOUNT_ID` is omitted. See the [CLI guide](https://asa-api-client.peth.au/guide/cli/) for all options.

## Legacy Campaign Management API v5

Support for Apple's deprecated Campaign Management API v5 (`AppleSearchAdsClient`, sunset January 26, 2027) was removed in `1.0.0`. Pin `asa-api-client<1.0` if you need v5, or see the [v5 → v1 migration guide](https://asa-api-client.peth.au/guide/platform-api-v1/).

## License

MIT License - Copyright (c) 2025 Peth Pty Ltd
