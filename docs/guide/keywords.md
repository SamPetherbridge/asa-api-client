# Keywords

Platform API v1 provides single-item CRUD on `client.keywords` and `client.negative_keywords`, plus high-throughput batch endpoints on `client.bulk`.

## Query & Get Keywords

```python
from asa_api_client.v1 import Query

page = client.keywords.query(
    Query().where("adGroupId", "EQUALS", str(ad_group_id)).where("status", "EQUALS", "ENABLED")
)

keyword = client.keywords.get(keyword_id)
```

## Single-Item Create, Update, and Delete

```python
from asa_api_client.v1.models.base import Money
from asa_api_client.v1.models.keywords import (
    KeywordCreate,
    KeywordMatchType,
    KeywordStatus,
    KeywordUpdate,
)

created = client.keywords.create(
    KeywordCreate(
        ad_group_id=ad_group_id,
        text="budget app",
        match_type=KeywordMatchType.EXACT,
        bid=Money(amount="1.50", currency="USD"),
        status=KeywordStatus.ENABLED,
    )
)

client.keywords.update(
    keyword_id,
    KeywordUpdate(bid=Money(amount="1.80", currency="USD")),
)

client.keywords.delete(keyword_id)
```

## Bulk Create, Update, and Delete

Use `client.bulk` to create, update, or delete keywords and negative keywords in batches. Lists larger than Apple's 5,000-item per-request limit are automatically split into sequential 5,000-item chunks with continuous `correlationId` numbering:

```python
from asa_api_client.v1.models.bulk import BulkKeywordCreate, BulkKeywordUpdate

created_items = client.bulk.create_keywords(
    [
        BulkKeywordCreate(
            ad_group_id=ad_group_id,
            text="expense tracker",
            match_type=KeywordMatchType.EXACT,
            bid=Money(amount="1.60", currency="USD"),
        ),
        BulkKeywordCreate(
            ad_group_id=ad_group_id,
            text="personal finance",
            match_type=KeywordMatchType.BROAD,
            bid=Money(amount="1.20", currency="USD"),
        ),
    ]
)

client.bulk.update_keywords(
    [
        BulkKeywordUpdate(
            id=keyword_id,
            bid=Money(amount="2.00", currency="USD"),
            status=KeywordStatus.PAUSED,
        )
    ]
)

# Pass bare IDs, BulkKeywordDelete models, or BulkRequestItem wrappers
client.bulk.delete_keywords([keyword_id])
```

Negative keywords support the same bulk operations via `create_negative_keywords`, `update_negative_keywords`, and `delete_negative_keywords`.

## Match Types & Statuses

- **App Store match types**: `EXACT`, `BROAD`
- **Apple Maps match types**: `PHRASE`, `CATEGORY` (targeting keywords only)
- **Statuses**: `ENABLED`, `PAUSED` (`DELETED` appears on `display_status` after soft-deletion)
