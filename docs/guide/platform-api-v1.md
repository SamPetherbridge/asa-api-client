# Platform API v1 & Migration

`asa-api-client` `1.0+` targets the **Apple Ads Platform API v1** (`https://api.ads.apple.com/v1`) exclusively.

> [!NOTE]
> Apple sunsets the legacy Campaign Management API v5 on **January 26, 2027**. Legacy `AppleSearchAdsClient` (v5) was removed in `asa-api-client` `1.0.0` — pin `asa-api-client<1.0` if you still need v5 before the sunset.

## Setup & Account Discovery

```bash
ASA_CLIENT_ID=SEARCHADS.xxxxxxxx-...
ASA_TEAM_ID=YOUR_TEAM_ID
ASA_KEY_ID=YOUR_KEY_ID
ASA_PRIVATE_KEY_PATH=/path/to/private-key.pem
ASA_AD_ACCOUNT_ID=123456
```

`ad_account_id` may be omitted at construction to auto-resolve via `/v1/acls`, or you can fan out across multiple accounts using `client.with_account(...)` (sharing the OAuth token cache and HTTP connection pools without mutating the parent client):

```python
from asa_api_client import AppleAdsClient

with AppleAdsClient.from_env() as client:
    # Auto-select sole account (or match prefer_org_id / ASA_ORG_ID)
    client.resolve_ad_account()

    # Or query multiple accounts independently
    for acl in client.acls.list():
        if acl.ad_account and acl.ad_account.id is not None:
            scoped = client.with_account(acl.ad_account.id)
            print(acl.ad_account.name, len(scoped.campaigns.query()))
```

Or run the bundled read-only smoke check:

```bash
asa smoke
```

## Querying & Pagination

Resources expose `POST <resource>/query` endpoints backed by the fluent `Query` builder:

```python
from asa_api_client import Query

page = client.campaigns.query(
    Query()
    .where("status", "EQUALS", "ENABLED")
    .where("name", "CONTAINS_ANY", ["Brand", "Generic"], ignore_case=True)
    .order_by("id", "DESC")
    .page(size=100, fetch_total_count=True)
)
for campaign in page:
    print(campaign.name)

# Automatic pagination across all pages
for campaign in client.campaigns.iter_all():
    print(campaign.name)
```

## Resource Coverage

- **Core App Store ads**: `campaigns`, `ad_groups`, `keywords`, `negative_keywords`, `ads`, `creatives`, `assets`, `product_pages`, `budget_orders`, `apps`, `geo`, `reports`
- **Account & organization discovery**: `me()` / `me_async()`, `acls`, `ad_accounts`, `orgs`, `advertiser_resources`
- **`recommendations`**: Target-CPA and daily-budget recommendations with `apply` / `dismiss` and `iter_target_cpas` / `iter_daily_budgets`
- **`suggestions`**: Keyword, phrase, category, and target-CPA suggestions (`iter_keywords`, `iter_phrases`, `iter_categories`)
- **`insights`**: Impression share (`iter_impression_share`) and search-term popularity (`iter_search_term_popularity`)
- **`change_history`**: Account audit trail (`query` / `iter_all` / `get_details`)
- **`bulk`**: Bulk keyword and negative-keyword `create_*`, `update_*`, and `delete_*` (lists over 5,000 items are automatically split into 5,000-item batches)
- **Apple Maps ads**: `brands`, `locations`, `location_groups`, `business_categories`, `brand_rejection_reasons`, `brand_reports`

Every sync method has an `_async` twin.

## Error Handling, Bulk Operations & Retries

Responses carrying a top-level `error` block on HTTP 2xx raise `PartialFailureError` (exposing `exc.details`). In bulk operations with `allow_partial_success=True` (the default), Apple returns per-item `success` and `error` entries on each `BulkItemResult`:

```python
from asa_api_client import PartialFailureError

try:
    results = client.bulk.delete_keywords([101, 102], allow_partial_success=True)
    for item in results:
        if not item.success and item.error:
            print(item.correlation_id, item.error.code, item.error.message)
except PartialFailureError as exc:
    for detail in exc.details:
        print(detail.get("code"), detail.get("message"))
```

Automatic retries with exponential backoff and bounded jitter cover rate limiting (`429`) and connection errors across all methods, and server errors (`5xx`) on idempotent requests (`GET`, `PUT`, `DELETE`, and read-only `POST .../query` endpoints). Non-idempotent `POST` writes never retry after `5xx` or read timeouts so entities are not duplicated. Configure retry parameters on `AppleAdsClient(..., max_retries=5, retry_initial_delay=5.0, retry_max_delay=120.0, retry_jitter=True)`.

## Migration Crib (`0.x` / v5 → `1.0` / v1)

| Legacy v5 (`0.x`) | Platform API v1 (`1.0+`) |
|---|---|
| `AppleSearchAdsClient` | `AppleAdsClient` |
| `ASA_ORG_ID` (`orgId`) | `ASA_AD_ACCOUNT_ID` (`adAccountId`) or `client.resolve_ad_account()` |
| `client.campaigns.list()` | `client.campaigns.query()` / `iter_all()` |
| `Selector().where("status", "==", "ENABLED")` | `Query().where("status", "EQUALS", "ENABLED")` |
| `ACTIVE` keyword status | `ENABLED` |
| `adamId` | `promotedObjectId` + `promotedObjectType` |
| `defaultBidAmount` | `bidStrategy.bid` |
| `limit` / `offset` | `pageSize` / `offset` (+ `fetchTotalCount`) |
| Nested `client.campaigns(id).ad_groups` | Flat `client.ad_groups` + `campaignId` filter |
| Lifetime budget, `cpaCap` | Removed by Apple — use `dailyBudget` / `bidStrategy` |
