# Platform API v1

Apple launched the **Apple Ads Platform API v1** (`https://api.ads.apple.com/v1`) in Summer 2026, replacing the Campaign Management API v5. **v5 sunsets on January 26, 2027** — after that date, v5 endpoints stop working entirely.

This library ships both clients side by side, with `AppleAdsClient` (v1) as the primary client:

| | v1 (current) | v5 (legacy, sunset 2027-01-26) |
|---|---|---|
| Client class | `AppleAdsClient` | `AppleSearchAdsClient` |
| Base URL | `api.ads.apple.com/v1` | `api.searchads.apple.com/api/v5` |
| Request scope | `adAccountId` (`X-AP-Context`) | `orgId` (`X-AP-Context`) |
| Credentials | ES256 OAuth (shared) | Same key pair |

Import `AppleAdsClient` from the package root:

```python
from asa_api_client import AppleAdsClient
```

## Setup

Your existing ES256 OAuth credentials work unchanged — add `ASA_AD_ACCOUNT_ID`:

```bash
ASA_CLIENT_ID=SEARCHADS.xxxxxxxx-...
ASA_TEAM_ID=YOUR_TEAM_ID
ASA_KEY_ID=YOUR_KEY_ID
ASA_PRIVATE_KEY_PATH=/path/to/private-key.pem
ASA_AD_ACCOUNT_ID=123456
```

```python
client = AppleAdsClient.from_env()
```

### Discovering & Scoping Ad Accounts

`ad_account_id` may be omitted at construction to auto-resolve via `/v1/acls`, or you can fan out across multiple accounts using `client.with_account(...)` (which shares the OAuth token cache and HTTP connection pools without mutating the parent client):

```python
with AppleAdsClient.from_env() as client:
    # Auto-select sole account (or match prefer_org_id / ASA_ORG_ID)
    client.resolve_ad_account()

    # Or query multiple accounts concurrently / independently
    for acl in client.acls.list():
        if acl.ad_account and acl.ad_account.id is not None:
            scoped = client.with_account(acl.ad_account.id)
            print(acl.ad_account.name, len(scoped.campaigns.query()))
```

Or run the bundled read-only smoke check:

```bash
asa v1-smoke
```

## Querying

v1 replaces v5's `Selector` / `find` with `POST <resource>/query` and a structured filter grammar. Use the `Query` builder:

```python
from asa_api_client.v1 import Query

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

Filters combine with logical AND. `totalCount` is returned when `fetch_total_count=True`; `iter_all()` paginates automatically until a short page is returned.

## Resources

Account-scoped parity resources: `campaigns`, `ad_groups`, `keywords`, `negative_keywords`, `ads`, `creatives`, `assets`, `product_pages`, `budget_orders`, `apps`, `geo`, `reports`.

v1-exclusive capabilities:

- **`recommendations`** — Target-CPA and daily-budget recommendations with `apply` / `dismiss` and `iter_target_cpas` / `iter_daily_budgets`
- **`suggestions`** — Keyword, phrase, category, and target-CPA suggestions
- **`insights`** — Impression share (`iter_impression_share`) and **search term popularity** (`iter_search_term_popularity`)
- **`change_history`** — Account audit trail (`query` / `iter_all` / `get_details`)
- **`bulk`** — Bulk keyword and negative-keyword `create_*`, `update_*`, and `delete_*` (lists over 5,000 items are automatically split into 5,000-item batches)
- **Apple Maps ads** — `brands`, `locations`, `location_groups`, `business_categories`, `brand_rejection_reasons`, `brand_reports`

Every sync method has an `_async` twin.

## Error Handling & Bulk Operations

Responses carrying a top-level `error` block on HTTP 2xx raise `PartialFailureError` (exposing `exc.details`), so failures never pass silently. In bulk operations with `allow_partial_success=True` (the default), Apple returns per-item `success` and `error` entries on each `BulkItemResult`:

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

Automatic retries with exponential backoff and bounded jitter cover rate limiting (`429`) and connection errors across all methods, and server errors (`5xx`) on idempotent requests (`GET`, `PUT`, `DELETE`, and read-only `POST .../query` endpoints). Non-idempotent `POST` writes never retry after `5xx` or read timeouts so entities are not duplicated. Retry behavior is configurable on `AppleAdsClient(..., max_retries=5, retry_initial_delay=5.0, retry_max_delay=120.0, retry_jitter=True)`.

## Reports

v1 reports accept an `AppsReportingRequest` (or `BrandsReportingRequest` on `client.brand_reports`) and support `to_dataframe()` / `to_records()`:

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
            end=date(2026, 8, 7),
            granularity=ReportGranularity.DAILY,
        )
    )
)
df = report.to_dataframe()
```

## CLI

`asa analyze` uses Platform API v1 by default (pass `--api-version v5` only if you specifically need legacy v5 before the sunset):

```bash
asa analyze --period 30d
asa v1-smoke
```

## Migration Crib (v5 → v1)

| v5 | v1 |
|---|---|
| `AppleSearchAdsClient` | `AppleAdsClient` |
| `client.campaigns.list()` | `client.campaigns.query()` / `iter_all()` |
| `Selector().where("status", "==", "ENABLED")` | `Query().where("status", "EQUALS", "ENABLED")` |
| `ACTIVE` keyword status | `ENABLED` |
| `adamId` | `promotedObjectId` + `promotedObjectType` |
| `defaultBidAmount` | `bidStrategy.bid` |
| `limit` / `offset` | `pageSize` / `offset` (+ `fetchTotalCount`) |
| Nested `client.campaigns(id).ad_groups` | Flat `client.ad_groups` + `campaignId` filter |
| Lifetime budget, `cpaCap` | Removed — use `dailyBudget` / `bidStrategy` |
