# Apple Ads Platform API v1 Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a complete, self-contained Apple Ads Platform API v1 client (`AppleAdsClient`) to `asa_api_client` alongside the untouched v5 client, covering parity resources plus all v1-only features, with mocked unit tests, a CLI `--api-version` flag, and a read-only live smoke command.

**Architecture:** New `asa_api_client/v1/` subpackage (client, query builder, transport base, per-resource modules, self-contained models) importing only `Authenticator`, `exceptions`, and `logging` from the existing package. v5 files are modified only for root exports and the CLI flag. Resource groups are independent modules implemented in parallel; a final integration task wires client properties and exports.

**Tech Stack:** Python 3.12+, httpx, Pydantic v2, Typer/Rich (CLI), pytest + pytest-httpx + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-08-16-apple-ads-platform-api-v1-design.md`

## Global Constraints

- v1 base URL: `https://api.ads.apple.com/v1` (no trailing slash stored).
- Context header: `X-AP-Context: adAccountId={ad_account_id}`.
- Auth: reuse `asa_api_client.auth.Authenticator` unchanged.
- Response envelope: `{result, pagination, error}`; **any `error` block raises, even on HTTP 2xx**.
- Pagination: `offset` / `pageSize` / `totalCount`.
- `v1/` may import from the existing package ONLY `auth`, `exceptions`, `logging`. `v1/models/` imports nothing from v5 `models/`.
- Nothing under `asa_api_client/` outside `v1/` may import from `v1/` except `__init__.py` (root exports) and `cli/` (flag wiring).
- Model conventions (mirror v5): Pydantic v2, `StrEnum`, `ConfigDict(populate_by_name=True, extra="ignore")`, camelCase field aliases, `Money.amount` is `str`.
- Public import surface is the package root: `from asa_api_client import AppleAdsClient`.
- Every code file passes `uv run ruff check`, `uv run ruff format --check`, `uv run mypy asa_api_client`.
- Commits: Gitmoji style, imperative, ≤50-char subject, no AI attribution lines.
- Docs source of truth: Apple docs JSON (Task 0 procedure). The preview PDF is background only.

---

## Phase R: Research (swarm, no repo writes)

### Task 0: Distill Apple docs into per-group notes

**Files:**
- Create (scratchpad, NOT repo): `<scratchpad>/v1-docs/<group>.md` for each group listed below.

**Procedure (per group):** Apple's docs are served as JSON. For a docs page slug `X`, fetch `https://developer.apple.com/tutorials/data/documentation/apple-ads-platform-api/X.json`. Start from the section index slugs below, follow `topicSections[].identifiers` (slug = last path segment) to endpoint and data-object pages, and for each endpoint record: HTTP method + path, request body schema (field names, types, required/optional), response schema, and enums with all values. For each data object record: every field, alias, type, enum values.

Groups and their index slugs:

| Group | Index slugs |
|---|---|
| ad_accounts | `access-overview`, `org-me`, `ad-account-endpoints`, `account-management-data-objects`, `account-management-data-types` |
| campaigns | `campaigns-endpoints`, `campaigns-data-objects`, `campaign-data-types` |
| ad_groups | `adgroups-endpoints`, `adgroups-data-objects`, `adgroups-data-types` |
| keywords | `keywords-and-negative-keywords`, `keywords-endpoints`, `negative-keywords-endpoints`, `keywords-data-objects`, `negative-keywords-objects`, `keywords-shared-data-types` |
| ads | `ads-endpoints`, `ads-data-objects`, `ads-data-types` |
| creatives_assets | `creatives-endpoints`, `creatives-data-objects`, `creative-data-types`, `assets-endpoints`, `assets-data-objects`, `assets-data-types` |
| product_pages | `product-pages-endpoints`, `product-pages-data-objects` |
| budget_orders | `budget-orders-endpoints`, `budget-orders-data-objects`, `budget-orders-data-types` |
| apps | `search-apps-endpoints`, `search-apps-data-objects`, `app-eligibility-endpoints`, `app-eligibility-data-objects` |
| geo | `geo-targeting-endpoints`, `geo-targeting-data-objects`, `geo-targeting-data-types` |
| brands | `brands-endpoints`, `location-groups-overview`, `locations-overview`, `brands-data-objects`, `brands-data-types` |
| reports | `reports`, `apps-reports-endpoints`, `brands-reports-endpoints`, `apps-reports-objects`, `brands-reports-objects`, `reports-shared-objects` |
| insights | `insights-endpoints`, `insights-data-objects` |
| recommendations | `recommendations-endpoints`, `recommendations-data-objects`, `recommendations-query-filter-objects` |
| suggestions | `suggestions-endpoints`, `suggestions-data-objects` |
| change_history | `change-history-endpoints`, `change-history-response-objects`, `change-history-query-objects`, `change-history-enumerations` |
| bulk | `bulk-operations-endpoints`, `bulk-data-objects` |
| core (query/envelope) | `calling-apple-ads-platform-api`, `rate-limits` |

**Note format:** markdown; one `## Endpoint` block per endpoint with method/path/request/response; one `## Object` block per data object with a field table. Include verbatim enum value lists. Flag anything surprising (payload wrappers, non-standard envelopes, endpoints that don't take the account header).

- [ ] Step 1: Fan out one research agent per group; each writes its notes file.
- [ ] Step 2: Verify every group file exists and contains at least one `## Endpoint`.

---

## Phase C: Core infrastructure (sequential — everything depends on it)

### Task 1: `PartialFailureError` exception

**Files:**
- Modify: `asa_api_client/exceptions.py` (append after existing classes)
- Test: `tests/unit/v1/test_exceptions.py` (new; create `tests/unit/v1/__init__.py`)

**Interfaces:**
- Produces: `PartialFailureError(AppleSearchAdsError)` with `details: list[dict[str, Any]]` attribute; constructor `PartialFailureError(message, *, status_code=None, response_body=None, details=None)`.

- [ ] Step 1: Write failing test:

```python
"""Tests for v1-specific exceptions."""

from asa_api_client.exceptions import AppleSearchAdsError, PartialFailureError


def test_partial_failure_error_carries_details() -> None:
    details = [{"code": "NOT_SAME_CURRENCY_AS_ORG_CURRENCY", "message": "bad", "info": {}}]
    err = PartialFailureError("partial failure", status_code=200, details=details)
    assert isinstance(err, AppleSearchAdsError)
    assert err.details == details
    assert err.status_code == 200


def test_partial_failure_error_defaults_empty_details() -> None:
    err = PartialFailureError("partial failure")
    assert err.details == []
```

- [ ] Step 2: Run `uv run pytest tests/unit/v1/test_exceptions.py -v` — expect FAIL (ImportError).
- [ ] Step 3: Implement in `exceptions.py`, matching the file's existing docstring style:

```python
class PartialFailureError(AppleSearchAdsError):
    """Raised when the API reports errors inside a successful HTTP response.

    The Apple Ads Platform API v1 can return HTTP 2xx with an ``error``
    block describing per-item failures (e.g. in bulk operations). This
    exception surfaces those instead of silently reporting success.

    Attributes:
        details: The ``error.details`` list from the response.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, response_body=response_body)
        self.details = details or []
```

(Check `AppleSearchAdsError.__init__` signature first and match it exactly; adjust `super().__init__` if its kwargs differ.)

- [ ] Step 4: Run the test — expect PASS.
- [ ] Step 5: Commit: `✨ Add PartialFailureError for v1 partial failures`

### Task 2: v1 model base (`v1/models/base.py`)

**Files:**
- Create: `asa_api_client/v1/__init__.py` (empty for now), `asa_api_client/v1/models/__init__.py` (empty for now), `asa_api_client/v1/models/base.py`
- Test: `tests/unit/v1/test_models_base.py`

**Interfaces:**
- Produces:
  - `Money(BaseModel)`: `amount: str`, `currency: str`, classmethod `usd(amount) -> Self`, classmethod `of(amount, currency) -> Self`.
  - `V1Pagination(BaseModel)`: `offset: int`, `page_size: int` (alias `pageSize`), `total_count: int` (alias `totalCount`).
  - `V1Page(BaseModel, Generic[T])`: `result: list[T]`, `pagination: V1Pagination | None`; `__iter__`, `__len__`, `__getitem__`; property `has_more: bool` (True iff pagination present and `offset + len(result) < total_count`).
  - `ErrorDetail(BaseModel)`: `code: str | None`, `message: str | None`, `info: dict[str, Any] | None`.
  - `V1Error(BaseModel)`: `code: str | None`, `message: str | None`, `details: list[ErrorDetail] | None`.
  - `V1Model(BaseModel)`: shared base with `model_config = ConfigDict(populate_by_name=True, extra="ignore")` — ALL v1 models inherit from this.

- [ ] Step 1: Write failing tests covering: `Money.usd(9.99)` → `amount="9.99", currency="USD"`; `V1Pagination` parses `{"offset": 0, "pageSize": 10, "totalCount": 12}` via aliases; `V1Page[Money]` parses a result list and `has_more` is False when `offset+len == totalCount` and True when smaller; `V1Error` parses the spec's error example.
- [ ] Step 2: Run — expect FAIL.
- [ ] Step 3: Implement (module docstring + Google-style docstrings, mirroring `asa_api_client/models/base.py` tone).
- [ ] Step 4: Run — expect PASS.
- [ ] Step 5: Commit: `✨ Add v1 model base: envelope, pagination, Money`

### Task 3: Query builder (`v1/query.py`)

**Files:**
- Create: `asa_api_client/v1/query.py`
- Test: `tests/unit/v1/test_query.py`

**Interfaces:**
- Produces:
  - `FilterOperator(StrEnum)` — values exactly per `core` docs notes (at minimum `EQUALS`, `IN`; take the full list from Task 0's core notes).
  - `SortDirection(StrEnum)`: `ASC`, `DESC`.
  - `Query(BaseModel)` with fluent, chainable methods (each returns `self`):
    - `where(field: str, operator: FilterOperator | str, value: Any) -> Self` — appends `{"field": field, "operator": str(operator), "value": value}`.
    - `order_by(field: str, direction: SortDirection | str = "ASC") -> Self`.
    - `page(*, size: int | None = None, offset: int | None = None) -> Self`.
    - `to_payload() -> dict[str, Any]` — `{"filters": [...], "sorting": [...], "pagination": {"pageSize": ..., "offset": ...}}`, omitting empty/None sections entirely.

- [ ] Step 1: Failing tests: empty `Query().to_payload() == {}`; chained where/order_by/page produces the exact dict from the spec's `POST /v1/keywords/query` example plus sorting/pagination; string operators accepted; invalid operator string raises `ValueError`.
- [ ] Step 2: Run — FAIL. Step 3: Implement. Step 4: Run — PASS.
- [ ] Step 5: Commit: `✨ Add v1 Query builder (filters/sorting/pagination)`

### Task 4: v1 transport + mixins (`v1/resources/base.py`)

**Files:**
- Create: `asa_api_client/v1/resources/__init__.py` (empty), `asa_api_client/v1/resources/base.py`
- Test: `tests/unit/v1/test_resource_base.py`

**Interfaces:**
- Consumes: `V1Page`, `V1Pagination`, `V1Error` (Task 2); `Query` (Task 3); `PartialFailureError` (Task 1); `AppleAdsClient` protocol attributes (Task 5): `_base_url`, `ad_account_id`, `_authenticator`, `_get_http_client()`, `_get_async_http_client()`.
- Produces (all later resource tasks build on exactly these):

```python
T = TypeVar("T", bound=BaseModel)
CreateT = TypeVar("CreateT", bound=BaseModel)
UpdateT = TypeVar("UpdateT", bound=BaseModel)

class V1Resource(Generic[T, CreateT, UpdateT]):
    base_path: str = ""                     # e.g. "campaigns"
    model_class: type[T]
    payload_wrapper: str | None = None      # e.g. "campaign" → create/update body {"campaign": {...}}
    requires_account_context: bool = True   # False for me/ad-accounts endpoints

    def __init__(self, client: "AppleAdsClient") -> None
    def _build_url(self, path: str = "") -> str
    def _get_headers(self) -> dict[str, str]            # raises ConfigurationError if account context required but ad_account_id unset
    async def _get_headers_async(self) -> dict[str, str]
    def _request(self, method, path="", *, json=None, params=None, max_retries=5) -> dict[str, Any]
    async def _request_async(...) -> dict[str, Any]     # same contract
    def _parse_item(self, data: dict[str, Any]) -> T    # reads data["result"]
    def _parse_page(self, data: dict[str, Any]) -> V1Page[T]
    def _wrap(self, body: dict[str, Any]) -> dict[str, Any]  # applies payload_wrapper

class GettableMixin:   get(resource_id) / get_async
class QueryableMixin:  query(query: Query | None = None) -> V1Page[T] / query_async
                       iter_all(query: Query | None = None, *, page_size: int = 500) -> Iterator[T] / iter_all_async
class CreatableMixin:  create(data: CreateT) -> T / create_async
class UpdatableMixin:  update(resource_id, data: UpdateT) -> T / update_async
class DeletableMixin:  delete(resource_id) -> None / delete_async
```

**Behavioral requirements (each gets a test):**
1. Headers: `Authorization` from `Authenticator.get_access_token(...).authorization_header`, `X-AP-Context: adAccountId={id}`, `Content-Type: application/json`. `ConfigurationError` when `requires_account_context` and `client.ad_account_id is None`.
2. Envelope: any response JSON containing a non-null `error` raises — on 2xx raise `PartialFailureError` with `error.message` and `details`; on ≥400 map exactly like v5 `_handle_error` (401 invalidates token → `AuthenticationError`; 403 `AuthorizationError`; 404 `NotFoundError`; 400/422 `ValidationError` with field errors built from `error.details[].info`/`code`; 429 `RateLimitError` with `Retry-After`; ≥500 `ServerError`). Copy the v5 retry loop structure (`RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}`, exponential backoff constants, `Retry-After` respect, stderr notice, `ASA_DEBUG` request echo with the v1 base URL stripped).
3. `query()` POSTs to `{base_path}/query` with `query.to_payload()` (empty dict when `query is None`); it is retried like GETs (it goes through `_request`, which retries on status regardless of method).
4. `iter_all()` repeatedly calls `query()` advancing `offset` by page size until `offset + len(result) >= total_count`; when the server returns no pagination object, a single page ends iteration.
5. `create`/`update` serialize with `data.model_dump(by_alias=True, exclude_none=True, mode="json")`, wrapped by `_wrap`.
6. 204 → `{}`.

- [ ] Step 1: Write failing tests using `pytest-httpx` (`httpx_mock` fixture) and a `DummyModel(V1Model)`; construct a minimal fake client object (`types.SimpleNamespace` is fine) providing `_base_url`, `ad_account_id`, `_authenticator` (stub returning a token with `authorization_header="Bearer test"` and a no-op `invalidate_token()`), `_get_http_client()` returning `httpx.Client()`. Cover all six behavioral requirements sync; cover envelope + query async.
- [ ] Step 2: Run — FAIL. Step 3: Implement. Step 4: Run — PASS (`uv run pytest tests/unit/v1/test_resource_base.py -v`).
- [ ] Step 5: Commit: `✨ Add v1 transport base and resource mixins`

### Task 5: `AppleAdsClient` (`v1/client.py`) + root export

**Files:**
- Create: `asa_api_client/v1/client.py`
- Modify: `asa_api_client/__init__.py` (add `AppleAdsClient` to imports and `__all__`), `asa_api_client/v1/__init__.py` (export `AppleAdsClient`, `Query`)
- Test: `tests/unit/v1/test_client.py`

**Interfaces:**
- Consumes: `Authenticator` (existing), resources arrive in Phase F — client ships now WITHOUT resource properties (they're wired in Task 23).
- Produces:

```python
DEFAULT_V1_BASE_URL = "https://api.ads.apple.com/v1"

class AppleAdsClient:
    def __init__(self, *, client_id, team_id, key_id, ad_account_id: str | int | None = None,
                 private_key=None, private_key_path=None,
                 base_url=DEFAULT_V1_BASE_URL, timeout=30.0) -> None
    ad_account_id: str | None          # normalized to str; settable attribute
    @classmethod
    def from_env(cls, *, env_file=".env", base_url=DEFAULT_V1_BASE_URL, timeout=30.0) -> Self
        # reads ASA_AD_ACCOUNT_ID via os.environ / dotenv in addition to Authenticator.from_env()
    _get_http_client() / _get_async_http_client()   # lazy, same as v5
    close() / aclose() / context managers / __repr__
```

- [ ] Step 1: Failing tests: constructor stores normalized `ad_account_id` ("123" from 123, None stays None); `base_url` trailing slash stripped; `from_env` picks up `ASA_AD_ACCOUNT_ID` (use `monkeypatch.setenv` for all `ASA_*` vars with a valid test EC private key — copy the key fixture approach from existing tests if present, else generate with `cryptography` in a fixture); `from asa_api_client import AppleAdsClient` works; context manager closes.
- [ ] Step 2: Run — FAIL. Step 3: Implement (model the file on v5 `client.py`, including docstrings; no resource properties yet). Step 4: Run — PASS, plus `uv run pytest` (full suite) to prove v5 untouched.
- [ ] Step 5: Commit: `✨ Add AppleAdsClient for Platform API v1`

---

## Phase F: Resource groups (swarm — parallel, disjoint files)

Seventeen groups, one task each. **Every group task follows the canonical procedure below** (shown fully worked for campaigns in Task 6). Group tasks touch ONLY their own three files — never `client.py`, never `__init__.py` files. Tests construct resources directly: `CampaignResource(client)`.

**Canonical per-group procedure:**
1. Read your group's docs notes file from Task 0 (`<scratchpad>/v1-docs/<group>.md`) and the spec.
2. Write `asa_api_client/v1/models/<group>.py`: a `V1Model` subclass per data object, enums as `StrEnum` with the exact documented values, camelCase aliases, `Money` from `models/base.py` for monetary fields, separate `<X>Create`/`<X>Update` models when the API distinguishes writable fields.
3. Write `asa_api_client/v1/resources/<group>.py`: one class per API resource, inheriting `V1Resource[...]` + exactly the mixins the endpoints support; set `base_path`, `model_class`, `payload_wrapper` (only if the docs show a wrapped body), `requires_account_context`. Add explicit methods for endpoints that don't fit the mixins (custom actions, report runs), each with sync + `_async` variants using `_request`/`_request_async` and `_parse_item`/`_parse_page`.
4. Write `tests/unit/v1/test_<group>.py` (pytest-httpx): for each endpoint — correct method+URL, request body serialization (aliases, wrapper), response parsing into models, and one enum round-trip. TDD: write tests first, watch them fail, implement, watch them pass.
5. Run `uv run pytest tests/unit/v1/test_<group>.py -v` then `uv run ruff check asa_api_client/v1 tests/unit/v1 && uv run ruff format asa_api_client/v1/models/<group>.py asa_api_client/v1/resources/<group>.py tests/unit/v1/test_<group>.py && uv run mypy asa_api_client/v1`.
6. Commit: `✨ Add v1 <group> resource and models`.
7. Report back: class names defined, client property name(s) wanted, endpoints implemented, anything in the docs that contradicted this plan.

### Task 6: campaigns (canonical worked example)

**Files:**
- Create: `asa_api_client/v1/models/campaigns.py`, `asa_api_client/v1/resources/campaigns.py`
- Test: `tests/unit/v1/test_campaigns.py`

**Interfaces:**
- Consumes: Task 2 base models, Task 3 `Query`, Task 4 `V1Resource` + mixins.
- Produces: `CampaignResource` (client property `campaigns`); models `Campaign`, `CampaignCreate`, `CampaignUpdate`, plus enums/objects per docs (`PromotedObject`, `BidStrategy`, status/serving enums, etc.).

- [ ] Step 1: From `v1-docs/campaigns.md`, write failing tests. Shape (adapt names/paths to the docs — the docs win):

```python
def test_get_campaign(httpx_mock, v1_client):
    httpx_mock.add_response(
        url="https://api.ads.apple.com/v1/campaigns/542370549",
        json={"result": {"id": 542370549, "name": "Test", "status": "ENABLED"}},
    )
    campaign = CampaignResource(v1_client).get(542370549)
    assert campaign.id == 542370549
    assert campaign.status is CampaignStatus.ENABLED


def test_query_campaigns_serializes_filters(httpx_mock, v1_client):
    httpx_mock.add_response(
        url="https://api.ads.apple.com/v1/campaigns/query",
        json={"result": [{"id": 1, "name": "A"}],
              "pagination": {"offset": 0, "pageSize": 10, "totalCount": 1}},
    )
    page = CampaignResource(v1_client).query(
        Query().where("status", "EQUALS", "ENABLED").page(size=10)
    )
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body == {"filters": [{"field": "status", "operator": "EQUALS", "value": "ENABLED"}],
                    "pagination": {"pageSize": 10, "offset": 0}}
    assert len(page) == 1 and not page.has_more
```

plus create (asserting the exact POST body incl. wrapper if documented, `promotedObjectId`/`promotedObjectType`, `bidStrategy`), update, delete, and a 200-with-error-block test asserting `PartialFailureError`. Shared fixture `v1_client` lives in `tests/unit/v1/conftest.py` (create it in this task): a real `AppleAdsClient` with dummy creds (test EC key), `ad_account_id="12345"`.

- [ ] Step 2: Run — FAIL. Step 3: Implement models + resource per docs. Step 4: Run — PASS + lint/type gates.
- [ ] Step 5: Commit: `✨ Add v1 campaigns resource and models`

### Tasks 7–22: remaining groups (canonical procedure each)

| Task | Group | Resource classes (expected; docs may adjust) | Client property |
|---|---|---|---|
| 7 | ad_accounts | `AdAccountResource` (incl. `me()` on client or resource per docs; `requires_account_context=False`) | `ad_accounts` |
| 8 | ad_groups | `AdGroupResource` | `ad_groups` |
| 9 | keywords | `KeywordResource`, `NegativeKeywordResource` | `keywords`, `negative_keywords` |
| 10 | ads | `AdResource` | `ads` |
| 11 | creatives_assets | `CreativeResource`, `AssetResource` | `creatives`, `assets` |
| 12 | product_pages | `ProductPageResource` | `product_pages` |
| 13 | budget_orders | `BudgetOrderResource` | `budget_orders` |
| 14 | apps | `AppResource` (search + eligibility) | `apps` |
| 15 | geo | `GeoResource` | `geo` |
| 16 | brands | `BrandResource`, `LocationResource`, `LocationGroupResource` | `brands`, `locations`, `location_groups` |
| 17 | reports | `ReportResource` (app-store levels + impression share), `BrandReportResource` | `reports`, `brand_reports` |
| 18 | insights | `InsightResource` (search term popularity) | `insights` |
| 19 | recommendations | `RecommendationResource` | `recommendations` |
| 20 | suggestions | `SuggestionResource` (incl. target-CPA suggested bid) | `suggestions` |
| 21 | change_history | `ChangeHistoryResource` (query-only) | `change_history` |
| 22 | bulk | `BulkOperationResource` | `bulk` |

Notes:
- Reports (17): request models must express `timeRange`, granularity, and grouping per docs; response parsing must expose `rows`, `totalMetrics`, `granularMetrics` as typed models. Partial-error handling matters most here and in bulk (22) — both must include a 200-with-error-block test.
- Change history (21): read-only; `GettableMixin` only if docs show a get-by-id.
- Bulk (22): methods per documented operation; each returns typed per-item results; per-item failures inside 2xx raise `PartialFailureError` (this is the issue-#30 class).

---

## Phase I: Integration, CLI, smoke, docs (sequential)

### Task 23: Wire client properties and exports

**Files:**
- Modify: `asa_api_client/v1/client.py` (import + instantiate every resource in `__init__`, add a documented `@property` per the table above, add `me()` if Task 7 put it on the client), `asa_api_client/v1/__init__.py`, `asa_api_client/v1/models/__init__.py` (re-export all public models), `asa_api_client/v1/resources/__init__.py`
- Test: extend `tests/unit/v1/test_client.py`

- [ ] Step 1: Failing test: every property in the table returns the right resource class; `client.campaigns` is cached (same object twice).
- [ ] Step 2: Wire everything; docstring examples on key properties (campaigns, reports, recommendations).
- [ ] Step 3: `uv run pytest` (FULL suite) + ruff + mypy — all green.
- [ ] Step 4: Commit: `✨ Wire v1 resources into AppleAdsClient`

### Task 24: CLI `--api-version` flag + fetch adapter

**Files:**
- Create: `asa_api_client/cli/v1_adapter.py`
- Modify: `asa_api_client/cli/analyze.py` (add `--api-version` Typer option, default `"v5"`, choices v5/v1; branch client construction), `asa_api_client/cli/fetch.py` (accept a client-or-adapter that satisfies the narrow interface it already uses)
- Test: `tests/unit/cli/test_v1_adapter.py`

**Interfaces:**
- Produces: `V1FetchAdapter(client: AppleAdsClient)` exposing exactly the methods/attributes `cli/fetch.py` calls on `AppleSearchAdsClient` (enumerate them by reading `fetch.py` first; implement each by calling v1 resources and mapping rows into the same shapes `fetch.py` returns today — campaign/ad-group/keyword/search-term/ad report rows and entity lookups).

- [ ] Step 1: Read `cli/fetch.py` and `cli/analyze.py`; list every client touchpoint in the test file as comments. Write failing tests: adapter maps a mocked v1 campaign report response into the exact row dict/model shape the v5 path produces (fixture-compare), and `asa analyze --api-version v1` constructs `AppleAdsClient.from_env` (monkeypatched) without error.
- [ ] Step 2: Run — FAIL. Step 3: Implement adapter + flag. Step 4: Full suite + gates PASS.
- [ ] Step 5: Commit: `✨ Add --api-version flag with v1 fetch adapter`

### Task 25: `asa v1-smoke` command

**Files:**
- Create: `asa_api_client/cli/v1_smoke.py`
- Modify: `asa_api_client/cli/__init__.py` (register command)
- Test: `tests/unit/cli/test_v1_smoke.py`

Behavior: read-only sequence — `me`/ad-accounts list (auto-selecting the account when `ASA_AD_ACCOUNT_ID` unset and exactly one account exists), campaigns query (first page), one campaign-level report for the last 7 days, recommendations query, search term popularity query, change history query. Each step prints a Rich table row: step, status (✅/⚠️ for empty/❌ with error), latency, item count. Steps that 4xx because a feature isn't enabled for the account print ⚠️ and continue; the command exits 0 if auth + campaigns succeed, 1 otherwise. **No write calls anywhere.**

- [ ] Step 1: Failing tests with pytest-httpx: full happy path (all endpoints mocked) exits 0 and prints all steps; campaigns failing exits 1; a 403 on recommendations still exits 0 with ⚠️.
- [ ] Step 2: Run — FAIL. Step 3: Implement. Step 4: Full suite + gates PASS.
- [ ] Step 5: Commit: `✨ Add asa v1-smoke read-only live check`

### Task 26: Documentation

**Files:**
- Modify: `README.md` (v1 section: quickstart, root-import rule, sunset note), `docs/` (add `docs/getting-started/platform-api-v1.md` mirroring existing docs style; link from nav if mkdocs config exists — check `mkdocs.yml`)

- [ ] Step 1: Write docs: install/auth unchanged, `AppleAdsClient` quickstart (list campaigns, run a report, fetch recommendations), `Query` examples, `--api-version` flag, `asa v1-smoke`, v5 sunset 2027-01-26 + migration crib table from the spec.
- [ ] Step 2: `uv run mkdocs build --strict` if mkdocs is configured; otherwise proofread.
- [ ] Step 3: Commit: `📝 Document Apple Ads Platform API v1 client`

### Task 27: Independent review + live smoke

- [ ] Step 1: Dispatch an independent reviewer agent with SHIP/HOLD authority (per user's global verification practices): it must re-run the full suite itself, grep call sites of everything Task 24 re-pointed in `cli/fetch.py`/`analyze.py`, verify v5 behavior is untouched (`git diff main -- asa_api_client/client.py asa_api_client/resources asa_api_client/models` must be empty), and spot-check three resource modules against the Apple docs JSON.
- [ ] Step 2: Feed findings back to implementers (fix round); re-run suite.
- [ ] Step 3: Run `uv run asa v1-smoke` against the live API with the user's real `.env` (read-only). Record output; any live-contract mismatch (envelope/field surprises) becomes a fix + regression test.
- [ ] Step 4: Final full suite + ruff + mypy. Commit any fixes: `🐛 Fix v1 issues found in review/live smoke`

## Execution notes (swarm)

- Task 0 runs as a Workflow research fan-out (17 agents, read-only, writes to scratchpad).
- Tasks 1–5 run sequentially in the main session (each depends on the previous).
- Tasks 6–22 fan out via Workflow in waves (disjoint files; no shared-file edits; guideline ~8 agents per wave). Each agent receives: this plan (their task + canonical procedure + Global Constraints), the spec path, their docs notes file, and the Task 4/5 interface block verbatim.
- Tasks 23–27 run sequentially in the main session.
- Any agent that finds the docs contradicting this plan STOPS on that point and reports the discrepancy instead of improvising silently.
