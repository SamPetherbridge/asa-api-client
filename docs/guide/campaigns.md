# Campaigns

Platform API v1 campaigns (`client.campaigns`) represent top-level App Store (`APPSTORE_APP`) and Apple Maps (`BUSINESS_BRAND`) advertising containers.

## Query & Iterate Campaigns

```python
from asa_api_client.v1 import Query

# Single page with typed filters
enabled = client.campaigns.query(
    Query()
    .where("status", "EQUALS", "ENABLED")
    .order_by("id", "DESC")
    .page(size=100, fetch_total_count=True)
)

# Automatic pagination across all pages
for campaign in client.campaigns.iter_all():
    print(f"{campaign.id}: {campaign.name} ({campaign.display_status})")
```

## Get a Campaign

```python
campaign = client.campaigns.get(campaign_id)
```

## Create a Campaign

```python
from asa_api_client.v1.models.base import Money
from asa_api_client.v1.models.campaigns import (
    BillingEvent,
    CampaignCreate,
    CampaignTargeting,
    DailyBudget,
    PromotedObjectType,
)
from asa_api_client.v1.models.shared import TargetingData

campaign = client.campaigns.create(
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
```

## Update or Delete a Campaign

```python
from asa_api_client.v1.models.campaigns import CampaignStatus, CampaignUpdate

client.campaigns.update(
    campaign_id,
    CampaignUpdate(
        status=CampaignStatus.PAUSED,
        daily_budget=DailyBudget(value=Money(amount="150.00", currency="USD")),
    ),
)

client.campaigns.delete(campaign_id)
```

## Campaign Statuses

- `status` — Advertiser intent (`ENABLED` or `PAUSED`)
- `system_status` — System serving state (`RUNNING` or `NOT_RUNNING`)
- `display_status` — Rolled-up status (`RUNNING`, `PAUSED`, `ON_HOLD`, `LIMITED`, `PROCESSING`, `DELETED`)
