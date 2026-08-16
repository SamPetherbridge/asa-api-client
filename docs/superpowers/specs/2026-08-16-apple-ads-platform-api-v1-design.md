# Apple Ads Platform API v1 Client — Design

**Date:** 2026-08-16
**Status:** Approved
**Scope:** Add a complete Apple Ads Platform API v1 client to `asa_api_client` alongside the existing v5 client, including all v1-only features, without modifying v5 behavior.

## Context

Apple launched the **Apple Ads Platform API v1** (`https://api.ads.apple.com/v1/`), replacing the Campaign Management API v5, which sunsets on **2027-01-26**. Verified live 2026-08-16: `api.ads.apple.com` resolves and answers 401 without credentials.

Key contract changes (from the July 2026 preview release notes and live docs):

| Area | v5 | v1 |
|------|----|----|
| Base URL | `api.searchads.apple.com/api/v5/` | `api.ads.apple.com/v1/` |
| Auth (OAuth) | `appleid.apple.com` ES256 client credentials | **Unchanged** |
| Context header | `X-AP-Context: orgId={orgId}` | `X-AP-Context: adAccountId={adAccountId}` |
| Response envelope | `{data, pagination, error}` | `{result, pagination, error}` |
| Endpoint shape | Nested paths (`/campaigns/{id}/adgroups/...`) | Flat top-level resources + `POST /{resource}/query` |
| Query grammar | `conditions` / `orderBy` / `ASCENDING` | `filters` / `sorting` / `ASC`, operators like `EQUALS` |
| Pagination | `limit`/`offset`, has-more inference | `pageSize`/`offset`/`totalCount` |
| Status enum | `ACTIVE` | `ENABLED` |
| Campaign app ref | `adamId` | `promotedObjectId` + `promotedObjectType` |
| Bid | `defaultBidAmount` | `bidStrategy.bid` |
| Reports | Flat request fields | `timeRange` object; `rows`/`totalMetrics`/`granularMetrics` |
| Errors | `error.errors[]` | `error: {code, message, details[{code, message, info}]}` — may appear with HTTP 200 |

Deprecated in v1: Lifetime Budget; ad group `cpaCap` (present at launch, do not use).

New in v1 (all in scope): account management (ad accounts, `me`), bulk operations, recommendations, suggestions (incl. target-CPA suggested bid), search term popularity report (Insights), change history, Apple Maps ads (brands, locations, location groups), creatives and assets, expanded impression share reports.

## Decisions (locked with user)

1. **Feature scope:** everything — parity with the current v5 client plus all v1-only features above.
2. **API shape:** separate `AppleAdsClient` class in a **self-contained `asa_api_client/v1/` subpackage**. v5 code untouched except root exports.
3. **Testing:** mocked unit tests (pytest-httpx) + a read-only live smoke CLI command.
4. **CLI:** `--api-version v5|v1` on `asa fetch` / `asa analyze` (default `v5`).

## Architecture

### Package layout

```
asa_api_client/
  __init__.py           # + export AppleAdsClient (root is the ONLY public import surface)
  v1/
    __init__.py
    client.py           # AppleAdsClient
    query.py            # Query builder → {filters, sorting, pagination}
    resources/
      base.py           # v1 transport: envelope, retries, CRUD/query/bulk mixins
      ad_accounts.py    # ad accounts + me
      campaigns.py
      ad_groups.py
      keywords.py       # keywords + negative keywords
      ads.py
      creatives.py      # creatives + assets
      product_pages.py
      budget_orders.py
      apps.py           # search apps + eligibility
      geo.py            # geo targeting
      brands.py         # Apple Maps ads: brands, locations, location groups
      reports.py        # app-store + brands reports, impression share
      insights.py       # search term popularity
      recommendations.py
      suggestions.py
      change_history.py
      bulk.py           # bulk operations
    models/
      base.py           # V1Response envelope, V1Pagination, Money, shared enums
      <one module per resource group, mirroring resources/>
```

**Isolation rule:** `v1/` imports from the existing package only `auth.Authenticator`, `exceptions`, and `logging`. `v1/models/` is fully self-contained (own `Money`, own enums) — no imports from v5 `models/`. Nothing in v5 imports from `v1/`.

**Public import rule:** users import `AppleAdsClient` (and v1 models via `asa_api_client.v1.models` documented namespace) — README shows root imports only, so internal layout can change at the v5 sunset without breaking users.

### Client

```python
AppleAdsClient(
    *, client_id, team_id, key_id,
    ad_account_id: str | None = None,
    private_key / private_key_path,
    base_url="https://api.ads.apple.com/v1",
    timeout=30.0,
)
```

- Reuses `Authenticator` unchanged (Apple: "No changes" to auth).
- `from_env()` reads existing `ASA_*` vars plus `ASA_AD_ACCOUNT_ID` (optional).
- `ad_account_id` optional at construction for bootstrap: `client.me()` and `client.ad_accounts.*` work without it; account-scoped resources raise `ConfigurationError` at request time if unset. `ad_account_id` is a settable attribute.
- Sync + `_async` method pairs, `close()`/`aclose()`, context managers — same ergonomics as v5.

### Transport (`v1/resources/base.py`)

- Parses the `{result, pagination, error}` envelope.
- **Any `error` block raises**, regardless of HTTP status. HTTP 2xx with `error.details[]` raises `PartialFailureError` (new, in `exceptions.py`) carrying structured details — this closes the v5 issue #30 class of silent partial failures by design.
- HTTP-status error mapping mirrors v5 (401→`AuthenticationError` + token invalidation, 403, 404, 400/422→`ValidationError` with field errors from `details[]`, 429→`RateLimitError`, 5xx→`ServerError`).
- Retry: exponential backoff with `Retry-After` support, statuses {429, 500, 502, 503, 504}; **`POST …/query` is retryable** (idempotent read).
- Pagination: `iter_all()` walks `offset` until `offset + pageSize ≥ totalCount` — no has-more guessing.
- `ASA_DEBUG` request logging, matching v5.

### Query builder (`v1/query.py`)

```python
Query().where("adGroupId", "EQUALS", 123)
       .order_by("name", "ASC")
       .page(size=100, offset=0)
```

Serializes to `{"filters": [...], "sorting": [...], "pagination": {...}}`. Operator and direction enums per docs. `where()` accepts multiple calls (AND semantics, per API).

### Resources

Each resource file declares path, model, and mixes in what it supports (`Gettable`, `Queryable`, `Creatable`, `Updatable`, `Deletable`, `BulkOps`). Exact endpoint paths, request/response schemas, and enums are taken from Apple's docs JSON (`developer.apple.com/tutorials/data/documentation/apple-ads-platform-api/…`) at implementation time — the docs are the source of truth, not the preview PDF.

Coverage:

- **Parity:** ad accounts/me, campaigns, ad groups, keywords, negative keywords, ads, product pages, budget orders, app search/eligibility, geo targeting, reports (campaign/ad-group/keyword/search-term/ad levels; impression share) with `timeRange` + `rows`/`totalMetrics`/`granularMetrics` parsing.
- **New:** recommendations, suggestions (target-CPA suggested bid), search term popularity (Insights), change history, bulk operations, Apple Maps ads (brands endpoints, locations, location groups, brands reports), creatives + assets.

### Models

Pydantic v2, camelCase aliases, same conventions as v5 models. Self-contained: own `Money`, own status enums (`ENABLED`/`PAUSED`/…), `promotedObjectId`/`promotedObjectType`, `bidStrategy`. Unknown fields tolerated (`model_config` extra="allow" where v5 does the same).

### CLI

- `--api-version v5|v1` (default `v5`) on `asa fetch` and `asa analyze`. A thin fetch adapter maps v1 report rows into the row shapes the metrics/workbook pipeline already consumes; the analyze pipeline itself does not change.
- New `asa v1-smoke`: read-only live validation — `me` → ad accounts → campaigns list → one campaign report → recommendations → search term popularity → change history. Rich table output. **No write calls.**

### Testing

- pytest-httpx unit tests per resource: envelope parsing, query serialization, pagination iteration (`iter_all` against `totalCount`), retry on 429 incl. `Retry-After`, HTTP error mapping, and the **200-with-error-block → raises** case.
- Async variants covered for the base transport at minimum.
- Live validation is manual via `asa v1-smoke`.

### v5 sunset path (for later, recorded here)

1. Now: v1 ships alongside v5 (minor release).
2. Near sunset: v5 client constructor emits `DeprecationWarning` (minor release).
3. At/after 2027-01-26: delete v5 `client.py`, `resources/`, `models/`; remove root exports; optionally flatten `v1/` (major release). Nothing in `v1/` will require surgery.

## Out of scope

- Migrating the analyze pipeline's internals to v1-native shapes (adapter only).
- v5 deprecation warnings (step 2 above is future work).
- Write-path live tests (smoke is read-only).
- Fixing v5 issue #30 in the v5 code (tracked separately).
