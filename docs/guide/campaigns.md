# Campaigns

## List Campaigns

```python
campaigns = client.campaigns.list()
```

## Get a Campaign

```python
campaign = client.campaigns.get(campaign_id)
```

## Find Campaigns

Use selectors for filtering:

```python
from asa_api_client.models import Selector

# By status
enabled = client.campaigns.find(
    Selector().where("status", "==", "ENABLED")
)

# By country
us_campaigns = client.campaigns.find(
    Selector().where("countriesOrRegions", "CONTAINS_ANY", ["US"])
)
```

## Create a Campaign

```python
from asa_api_client.models import (
    CampaignCreate,
    Money,
    CampaignSupplySource,
)

campaign = client.campaigns.create(
    CampaignCreate(
        name="My Campaign",
        adam_id=123456789,  # Your app's Adam ID
        countries_or_regions=["US"],
        daily_budget_amount=Money(amount="100", currency="USD"),
        supply_sources=[CampaignSupplySource.APPSTORE_SEARCH_RESULTS],
    )
)
```

## Update a Campaign

```python
from asa_api_client.models import CampaignUpdate

client.campaigns.update(
    campaign_id,
    CampaignUpdate(
        daily_budget_amount=Money(amount="150", currency="USD")
    )
)
```

## Campaign States

- `ENABLED` - Campaign is active and running
- `PAUSED` - Campaign is paused by user
- `DELETED` - Campaign is deleted

## Iterate All Campaigns

For large numbers of campaigns:

```python
for campaign in client.campaigns.iter_all():
    print(campaign.name)
```
