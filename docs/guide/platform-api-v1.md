# Platform API v1

Apple launched the **Apple Ads Platform API v1** (`https://api.ads.apple.com/v1`) in Summer 2026, replacing the Campaign Management API v5. **v5 sunsets on January 26, 2027** — after that date, v5 endpoints stop working entirely.

This library ships both clients side by side:

| | v5 (legacy) | v1 (current) |
|---|---|---|
| Client class | `AppleSearchAdsClient` | `AppleAdsClient` |
| Base URL | `api.searchads.apple.com/api/v5` | `api.ads.apple.com/v1` |
| Request scope | `orgId` | `adAccountId` |
| Credentials | ES256 OAuth (shared) | **Same — no changes** |

Always import from the package root — the internal layout may change at the v5 sunset, the root exports will not:

```python
from asa_api_client import AppleAdsClient
```

## Setup

Your existing v5 credentials work unchanged. Add one new variable for the ad account (discoverable, see below):

```bash
ASA_CLIENT_ID=SEARCHADS.xxxxxxxx-...
ASA_TEAM_ID=YOUR_TEAM_ID
ASA_KEY_ID=YOUR_KEY_ID
ASA_PRIVATE_KEY_PATH=/path/to/private-key.pem
ASA_AD_ACCOUNT_ID=123456          # new in v1 (optional at construction)
```

```python
client = AppleAdsClient.from_env()
```

### Discovering your ad account ID

`ad_account_id` may be omitted to bootstrap — account-management endpoints work without it:

```python
client = AppleAdsClient.from_env()

me = client.ad_accounts.me()
for acl in client.acls.list():
    print(acl)

client.ad_account_id = "123456"   # now account-scoped resources work
```

Or run the bundled read-only smoke check, which auto-selects the account when there is exactly one:

```bash
asa v1-smoke
```

## Querying

v1 replaces v5's Selector/`find` with `POST <resource>/query` and a filter grammar. Use the `Query` builder:

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

# Automatic pagination
for campaign in client.campaigns.iter_all():
    print(campaign.name)
```

Filters combine with logical AND. `totalCount` is only returned when you ask for it (`fetch_total_count=True`); `iter_all()` handles this for you.

## Resources

Account-scoped parity resources: `campaigns`, `ad_groups`, `keywords`, `negative_keywords`, `ads`, `creatives`, `assets`, `product_pages`, `budget_orders`, `apps`, `geo`, `reports`.

New in v1:

- **`recommendations`** — target-CPA and daily-budget recommendations with `apply`/`dismiss`
- **`suggestions`** — keyword, phrase, category, and target-CPA suggestions
- **`insights`** — impression share and **search term popularity** reports
- **`change_history`** — the audit trail of account changes
- **`bulk`** — bulk keyword / negative-keyword create and update
- **Apple Maps ads** — `brands`, `locations`, `location_groups`, `business_categories`, `brand_reports`

Every sync method has an `_async` twin, exactly like the v5 client.

## Error handling

v1 responses can carry an `error` block even on HTTP 200 (notably partial failures in bulk operations). The v1 client **always raises** in that case — `PartialFailureError` exposes the per-item `details` list — so a write can never silently half-succeed:

```python
from asa_api_client import PartialFailureError

try:
    client.bulk.create_keywords(items, allow_partial_success=False)
except PartialFailureError as exc:
    for detail in exc.details:
        print(detail["code"], detail["message"])
```

All other exceptions (`AuthenticationError`, `RateLimitError`, ...) behave as in v5, including automatic retry with backoff on 429/5xx — and in v1 the retry also covers `POST .../query` calls, which are idempotent reads.

## Reports

v1 reports use a `timeRange` object and return `rows` with `totalMetrics`/`granularMetrics`:

```python
from asa_api_client.v1.models.reports import AppsReportingRequest, ReportTimeRange

report = client.reports.campaigns(
    AppsReportingRequest(
        time_range=ReportTimeRange(
            start=date(2026, 8, 1),
            end=date(2026, 8, 7),
            granularity="DAILY",
        ),
    )
)
```

Ad-group, keyword, search-term, and ad-level reports follow the same shape (`client.reports.ad_groups(...)` etc.), and Apple Maps ads reporting lives on `client.brand_reports`.

(See the model docstrings for the exact request shapes — they follow the official docs field-for-field.)

## CLI

`asa analyze` and the analysis pipeline accept `--api-version`:

```bash
asa analyze --api-version v1 --period 30d
asa v1-smoke        # read-only live validation of the v1 integration
```

The default remains `v5` until the sunset.

## Migration crib (v5 → v1)

| v5 | v1 |
|---|---|
| `client.campaigns.list()` | `client.campaigns.query()` / `iter_all()` |
| `Selector().where("status", "==", "ENABLED")` | `Query().where("status", "EQUALS", "ENABLED")` |
| `ACTIVE` status | `ENABLED` |
| `adamId` | `promotedObjectId` + `promotedObjectType` |
| `defaultBidAmount` | `bidStrategy.bid` |
| `limit`/`offset` | `pageSize`/`offset` (+ `fetchTotalCount`) |
| Lifetime budget, `cpaCap` | Removed — do not use |
