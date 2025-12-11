# Keywords

Keywords are accessed through a campaign and ad group context.

## List Keywords

```python
keywords = client.campaigns(campaign_id).ad_groups(ad_group_id).keywords.list()
```

## Get a Keyword

```python
keyword = client.campaigns(campaign_id).ad_groups(ad_group_id).keywords.get(keyword_id)
```

## Find Keywords

```python
from asa_api_client.models import Selector

active = client.campaigns(campaign_id).ad_groups(ad_group_id).keywords.find(
    Selector().where("status", "==", "ACTIVE")
)
```

## Create Keywords

Keywords are created in bulk:

```python
from asa_api_client.models import KeywordCreate, KeywordMatchType, Money

result = client.campaigns(campaign_id).ad_groups(ad_group_id).keywords.create_bulk([
    KeywordCreate(
        text="my keyword",
        match_type=KeywordMatchType.EXACT,
        bid_amount=Money(amount="1.50", currency="USD"),
    ),
    KeywordCreate(
        text="another keyword",
        match_type=KeywordMatchType.BROAD,
        bid_amount=Money(amount="1.00", currency="USD"),
    ),
])
```

## Update Keywords

```python
from asa_api_client.models import KeywordUpdate

client.campaigns(campaign_id).ad_groups(ad_group_id).keywords.update_bulk([
    KeywordUpdate(
        id=keyword_id,
        bid_amount=Money(amount="2.00", currency="USD"),
    )
])
```

## Match Types

- `EXACT` - Exact match only
- `BROAD` - Broad match including variations

## Keyword Status

- `ACTIVE` - Keyword is active
- `PAUSED` - Keyword is paused
- `DELETED` - Keyword is deleted
