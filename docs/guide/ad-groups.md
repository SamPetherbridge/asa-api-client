# Ad Groups

Ad groups are accessed through a campaign context.

## List Ad Groups

```python
ad_groups = client.campaigns(campaign_id).ad_groups.list()
```

## Get an Ad Group

```python
ad_group = client.campaigns(campaign_id).ad_groups.get(ad_group_id)
```

## Find Ad Groups

```python
from asa_api_client.models import Selector

active = client.campaigns(campaign_id).ad_groups.find(
    Selector().where("status", "==", "ENABLED")
)
```

## Create an Ad Group

```python
from asa_api_client.models import AdGroupCreate, Money

ad_group = client.campaigns(campaign_id).ad_groups.create(
    AdGroupCreate(
        name="My Ad Group",
        default_bid_amount=Money(amount="1.00", currency="USD"),
    )
)
```

## Update an Ad Group

```python
from asa_api_client.models import AdGroupUpdate

client.campaigns(campaign_id).ad_groups.update(
    ad_group_id,
    AdGroupUpdate(
        default_bid_amount=Money(amount="1.50", currency="USD")
    )
)
```

## Ad Group Settings

- `default_bid_amount` - Default bid for keywords without explicit bids
- `cpa_goal` - Target cost per acquisition
- `status` - ENABLED, PAUSED, or DELETED
