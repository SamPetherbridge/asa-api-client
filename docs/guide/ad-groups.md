# Ad Groups

In Platform API v1, ad groups live directly on `client.ad_groups` and link to their parent campaign via `campaign_id`.

## Query Ad Groups

```python
from asa_api_client.v1 import Query

ad_groups = client.ad_groups.query(
    Query().where("campaignId", "EQUALS", str(campaign_id)).where("status", "EQUALS", "ENABLED")
)

for ad_group in ad_groups:
    print(ad_group.id, ad_group.name)
```

## Get an Ad Group

```python
ad_group = client.ad_groups.get(ad_group_id)
```

## Create an Ad Group

```python
from asa_api_client.v1.models.ad_groups import AdGroupCreate, AdGroupStatus, PricingModel
from asa_api_client.v1.models.base import Money
from asa_api_client.v1.models.shared import BidStrategy, BidStrategyGoal, BidStrategyType

ad_group = client.ad_groups.create(
    AdGroupCreate(
        name="Exact Core",
        campaign_id=campaign_id,
        pricing_model=PricingModel.CPT,
        status=AdGroupStatus.ENABLED,
        automated_keywords_opt_in=False,
        bid_strategy=BidStrategy(
            bid_strategy_type=BidStrategyType.MANUAL_CPT,
            bid_strategy_goal=BidStrategyGoal.TAP,
            bid=Money(amount="1.50", currency="USD"),
        ),
    )
)
```

## Update or Delete an Ad Group

```python
from asa_api_client.v1.models.ad_groups import AdGroupUpdate

client.ad_groups.update(
    ad_group_id,
    AdGroupUpdate(
        bid_strategy=BidStrategy(
            bid_strategy_type=BidStrategyType.MANUAL_CPT,
            bid_strategy_goal=BidStrategyGoal.TAP,
            bid=Money(amount="2.00", currency="USD"),
        )
    ),
)

client.ad_groups.delete(ad_group_id)
```
