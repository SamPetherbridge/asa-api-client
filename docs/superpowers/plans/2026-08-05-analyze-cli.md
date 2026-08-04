# `asa analyze` CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `asa analyze` console command that fetches Apple Search Ads performance at five reporting levels and renders an opinionated, fully formatted Excel analysis workbook.

**Architecture:** A new `asa_api_client/cli/` package with four modules: `__init__.py` (lazy-import guarded entry point), `analyze.py` (Typer command + orchestration), `fetch.py` (all network: scope resolution, chunked async fetching with a semaphore, prior period), `metrics.py` (pure pandas aggregation/derived metrics), `workbook.py` (pure xlsxwriter rendering — DataFrames in, file out). Data flows `fetch → metrics → workbook`, coordinated by `analyze.py`.

**Tech Stack:** Python 3.13, Typer, Rich, pandas, xlsxwriter (write), openpyxl (test readback), pytest + pytest-httpx, strict mypy, ruff.

**Spec:** `docs/superpowers/specs/2026-08-05-analyze-cli-design.md`

## Global Constraints

- `requires-python = ">=3.13"`; strict mypy (`[tool.mypy] strict = true`) and ruff (line-length 100, pydocstyle `google` convention — **every public module/class/function needs a docstring**; only D100/D104 are ignored).
- Run everything through uv: `uv sync --all-extras` once, then `uv run pytest`, `uv run mypy asa_api_client`, `uv run ruff check asa_api_client tests`.
- Commit style (from CLAUDE.md): Gitmoji prefix, imperative mood, subject ≤ 50 chars, **no** Claude attribution / Co-Authored-By lines.
- Missing CLI deps message, verbatim: `Install the CLI extra: pip install "asa-api-client[cli]"` — never a traceback.
- All report fetching at DAILY granularity; ≤ 90 days per request window; search terms limited to trailing 90 days (note, don't fail).
- Concurrency: `asyncio.Semaphore(5)`.
- Sheet order: `Summary`, `Campaigns`, `Ad Groups`, `Keywords`, `Search Terms`, `Ads`, then grey-tabbed `Daily · <Level>` sheets.
- Zero denominators for derived metrics render as `—` in the workbook (NaN in DataFrames).
- Existing client APIs used (do not modify them):
  - `AppleSearchAdsClient.from_env()` — raises `asa_api_client.exceptions.ConfigurationError` on missing/invalid settings.
  - `client.campaigns.list()` → `PaginatedResponse[Campaign]` with `.data: list[Campaign]`; `Campaign` has `id`, `name`, `adam_id`, `status`, `daily_budget_amount`/`budget_amount` (`Money | None`, `Money` has `.currency`).
  - `client.apps.search(query=..., return_own_apps=...)` → `list[AppInfo]` (`AppInfo` has `app_name`, `adam_id`).
  - `client.reports.campaigns_async(start_date, end_date, *, campaign_ids=None, granularity, timezone)`;
    `client.reports.ad_groups_async(campaign_id, start_date, end_date, *, granularity, timezone)`;
    `client.reports.keywords_async(campaign_id, start_date, end_date, *, granularity, timezone)`;
    `client.reports.search_terms_async(campaign_id, start_date, end_date, *, granularity, timezone)`;
    `client.reports.ads_async(campaign_id, start_date, end_date, *, granularity, timezone)` — all return `ReportingResponse`.
  - `ReportingResponse.row: list[ReportRow]`; `ReportRow.metadata: ReportMetadata`, `.total: MetricData | None`, `.granularity: list[MetricData] | None` (per-day breakdown, each entry has `.date`). **`to_dataframe()` drops the `granularity` breakdown**, so daily flattening is implemented in `fetch.py` (Task 4).
  - Retries/rate-limit handling live in `BaseResource._request_async`; API errors surface as subclasses of `asa_api_client.exceptions.AppleSearchAdsError`.
- Report API JSON shape for test mocks: `{"data": {"reportingDataResponse": {"row": [...], "grandTotals": {...}}}}`; campaign list: `{"data": [...], "pagination": {"totalResults": N, "startIndex": 0, "itemsPerPage": N}}`; OAuth token endpoint `https://appleid.apple.com/auth/oauth2/token` returns `{"access_token": "tok", "token_type": "Bearer", "expires_in": 3600}`. API base URL: `https://api.searchads.apple.com/api/v5`.

---

### Task 1: Packaging + guarded CLI entry point

**Files:**
- Modify: `pyproject.toml`
- Create: `asa_api_client/cli/__init__.py`
- Create: `asa_api_client/cli/analyze.py` (skeleton only — just the Typer app; the real command body lands in Task 6)
- Create: `tests/unit/cli/__init__.py`
- Test: `tests/unit/cli/test_entry.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `asa_api_client.cli.main() -> None` (console entry point); `asa_api_client.cli.analyze.app: typer.Typer` with an `analyze` command (placeholder body). Later tasks replace the body of `analyze.py` but keep `app` and the command name.

- [ ] **Step 1: Update `pyproject.toml`**

Add after `[project.optional-dependencies]`'s `docs` list, a `cli` extra; extend `dev`; add scripts section:

```toml
cli = [
    "typer>=0.15.0",
    "rich>=13.0.0",
    "pandas>=2.2.0",
    "xlsxwriter>=3.2.0",
]
```

In the `dev` list, append:

```toml
    "typer>=0.15.0",
    "rich>=13.0.0",
    "xlsxwriter>=3.2.0",
    "openpyxl>=3.1.0",
    "types-openpyxl>=3.1.0",
```

Add a new table (place it after `[project.urls]`):

```toml
[project.scripts]
asa = "asa_api_client.cli:main"
```

Run: `uv sync --all-extras` — must succeed.

- [ ] **Step 2: Write the failing tests**

`tests/unit/cli/__init__.py` — empty file.

`tests/unit/cli/test_entry.py`:

```python
"""Tests for the ``asa`` console entry point."""

import pytest


def test_main_importable() -> None:
    """The entry point referenced by [project.scripts] must exist."""
    from asa_api_client.cli import main

    assert callable(main)


def test_missing_cli_extra_message(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Missing optional deps produce the install hint, not a traceback."""
    import builtins

    from asa_api_client import cli

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("typer") or name == "asa_api_client.cli.analyze":
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    assert excinfo.value.code == 1
    assert 'Install the CLI extra: pip install "asa-api-client[cli]"' in capsys.readouterr().err


def test_help_runs() -> None:
    """`asa --help` exits 0 and mentions the analyze subcommand."""
    from typer.testing import CliRunner

    from asa_api_client.cli.analyze import app

    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "analyze" in result.output
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/cli/test_entry.py -v`
Expected: FAIL / ERROR with `ModuleNotFoundError: No module named 'asa_api_client.cli'`.

- [ ] **Step 4: Implement**

`asa_api_client/cli/__init__.py`:

```python
"""Console entry point for the ``asa`` CLI.

The CLI's dependencies (typer, rich, pandas, xlsxwriter) are an optional
extra.  ``main`` guards the import so a bare install gets a clean install
hint instead of a traceback.
"""

import sys

_INSTALL_HINT = 'Install the CLI extra: pip install "asa-api-client[cli]"'


def main() -> None:
    """Run the ``asa`` command-line interface."""
    try:
        from asa_api_client.cli.analyze import app
    except ImportError:
        sys.stderr.write(_INSTALL_HINT + "\n")
        raise SystemExit(1) from None
    app()
```

`asa_api_client/cli/analyze.py` (skeleton — Task 6 fills in the real implementation):

```python
"""The ``asa analyze`` command."""

import typer

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def _root() -> None:
    """Apple Search Ads analysis toolkit."""


@app.command()
def analyze() -> None:
    """Generate an Excel performance analysis workbook."""
    raise typer.Exit(code=0)
```

The `@app.callback()` is load-bearing: a Typer app with exactly one command and no callback collapses that command into the root (so the binary would be `asa` with no `analyze` subcommand). The callback keeps `asa analyze` as a real subcommand, which the spec requires and `test_help_runs` asserts.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/cli/test_entry.py -v`
Expected: 3 passed.

- [ ] **Step 6: Lint & type-check**

Run: `uv run ruff check asa_api_client tests && uv run mypy asa_api_client`
Expected: clean. Fix anything reported before committing.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock asa_api_client/cli tests/unit/cli
git commit -m "✨ Add asa console script with cli extra"
```

---

### Task 2: Date-range resolution and window chunking

**Files:**
- Create: `asa_api_client/cli/dates.py`
- Test: `tests/unit/cli/test_dates.py`

**Interfaces:**
- Consumes: nothing (stdlib only — importable without the `cli` extra).
- Produces:
  - `PERIODS: dict[str, int]` — `{"30d": 30, "90d": 90, "365d": 365}`
  - `MAX_LOOKBACK_DAYS: int = 730`, `MAX_DAILY_WINDOW: int = 90`, `SEARCH_TERM_LOOKBACK: int = 90`
  - `resolve_range(period: str, from_date: date | None, to_date: date | None, *, today: date) -> tuple[date, date]` — raises `ValueError` with a human-readable message on invalid input.
  - `chunk_windows(start: date, end: date, max_days: int = MAX_DAILY_WINDOW) -> list[tuple[date, date]]`
  - `prior_window(start: date, end: date) -> tuple[date, date]`

- [ ] **Step 1: Write the failing tests**

`tests/unit/cli/test_dates.py`:

```python
"""Tests for date-range resolution and window chunking."""

from datetime import date

import pytest

from asa_api_client.cli.dates import chunk_windows, prior_window, resolve_range

TODAY = date(2026, 8, 5)


class TestResolveRange:
    """resolve_range: presets, explicit ranges, validation."""

    def test_default_30d_ends_yesterday(self) -> None:
        """30d preset covers 30 full days ending yesterday."""
        start, end = resolve_range("30d", None, None, today=TODAY)
        assert end == date(2026, 8, 4)
        assert (end - start).days + 1 == 30

    def test_365d(self) -> None:
        """365d preset covers 365 full days."""
        start, end = resolve_range("365d", None, None, today=TODAY)
        assert (end - start).days + 1 == 365

    def test_explicit_overrides_period(self) -> None:
        """--from/--to win over --period."""
        start, end = resolve_range(
            "30d", date(2026, 1, 1), date(2026, 3, 31), today=TODAY
        )
        assert (start, end) == (date(2026, 1, 1), date(2026, 3, 31))

    def test_from_without_to_defaults_to_yesterday(self) -> None:
        """--from alone runs through yesterday."""
        start, end = resolve_range("30d", date(2026, 7, 1), None, today=TODAY)
        assert (start, end) == (date(2026, 7, 1), date(2026, 8, 4))

    def test_unknown_period_rejected(self) -> None:
        """Bad preset raises ValueError."""
        with pytest.raises(ValueError, match="period"):
            resolve_range("7d", None, None, today=TODAY)

    def test_from_after_to_rejected(self) -> None:
        """Reversed range raises ValueError."""
        with pytest.raises(ValueError, match="before"):
            resolve_range("30d", date(2026, 5, 2), date(2026, 5, 1), today=TODAY)

    def test_future_to_rejected(self) -> None:
        """--to today or later raises ValueError."""
        with pytest.raises(ValueError, match="future|yesterday"):
            resolve_range("30d", date(2026, 8, 1), date(2026, 8, 5), today=TODAY)

    def test_lookback_limit(self) -> None:
        """Ranges older than the API lookback raise ValueError."""
        with pytest.raises(ValueError, match="lookback"):
            resolve_range("30d", date(2020, 1, 1), date(2020, 2, 1), today=TODAY)


class TestChunkWindows:
    """chunk_windows: ≤90-day inclusive windows that tile the range."""

    def test_short_range_single_window(self) -> None:
        """A 30-day range is one window."""
        assert chunk_windows(date(2026, 7, 6), date(2026, 8, 4)) == [
            (date(2026, 7, 6), date(2026, 8, 4))
        ]

    def test_exact_90_days_single_window(self) -> None:
        """Exactly 90 days stays one window."""
        windows = chunk_windows(date(2026, 1, 1), date(2026, 3, 31))
        assert windows == [(date(2026, 1, 1), date(2026, 3, 31))]

    def test_long_range_tiles_without_gaps(self) -> None:
        """365 days splits into contiguous ≤90-day windows."""
        start, end = date(2025, 8, 5), date(2026, 8, 4)
        windows = chunk_windows(start, end)
        assert windows[0][0] == start
        assert windows[-1][1] == end
        assert all((w_end - w_start).days + 1 <= 90 for w_start, w_end in windows)
        for (_, prev_end), (next_start, _) in zip(windows, windows[1:], strict=False):
            assert (next_start - prev_end).days == 1


class TestPriorWindow:
    """prior_window: equal-length window immediately before the range."""

    def test_adjacent_equal_length(self) -> None:
        """Prior window ends the day before start and has equal length."""
        p_start, p_end = prior_window(date(2026, 7, 6), date(2026, 8, 4))
        assert p_end == date(2026, 7, 5)
        assert (p_end - p_start).days == (date(2026, 8, 4) - date(2026, 7, 6)).days
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/cli/test_dates.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'asa_api_client.cli.dates'`.

- [ ] **Step 3: Implement**

`asa_api_client/cli/dates.py`:

```python
"""Pure date arithmetic for the analyze command.

Stdlib-only so it can be imported and unit-tested without the ``cli``
extra installed.
"""

from datetime import date, timedelta

PERIODS: dict[str, int] = {"30d": 30, "90d": 90, "365d": 365}
MAX_LOOKBACK_DAYS = 730
MAX_DAILY_WINDOW = 90
SEARCH_TERM_LOOKBACK = 90


def resolve_range(
    period: str,
    from_date: date | None,
    to_date: date | None,
    *,
    today: date,
) -> tuple[date, date]:
    """Resolve CLI options into an inclusive (start, end) date range.

    Args:
        period: Preset key from :data:`PERIODS` (used when no explicit dates).
        from_date: Explicit start date; overrides the preset.
        to_date: Explicit end date; defaults to yesterday when only
            ``from_date`` is given.
        today: The current date (injected for testability).

    Returns:
        Inclusive ``(start, end)`` dates.

    Raises:
        ValueError: If the preset is unknown, the range is reversed, ends
            in the future, or starts beyond the API lookback.
    """
    yesterday = today - timedelta(days=1)

    if from_date is None and to_date is None:
        if period not in PERIODS:
            raise ValueError(f"Unknown period {period!r}; choose one of {sorted(PERIODS)}")
        end = yesterday
        start = end - timedelta(days=PERIODS[period] - 1)
    else:
        if from_date is None:
            raise ValueError("--to requires --from")
        start = from_date
        end = to_date if to_date is not None else yesterday

    if start > end:
        raise ValueError(f"--from ({start}) must be before --to ({end})")
    if end > yesterday:
        raise ValueError(f"--to ({end}) must not be in the future; latest full day is {yesterday}")
    if start < today - timedelta(days=MAX_LOOKBACK_DAYS):
        raise ValueError(
            f"--from ({start}) is beyond the API lookback of {MAX_LOOKBACK_DAYS} days"
        )

    return start, end


def chunk_windows(
    start: date, end: date, max_days: int = MAX_DAILY_WINDOW
) -> list[tuple[date, date]]:
    """Split an inclusive date range into contiguous windows of at most ``max_days``.

    Args:
        start: Range start (inclusive).
        end: Range end (inclusive).
        max_days: Maximum days per window (the API caps DAILY reports at 90).

    Returns:
        Ordered list of inclusive ``(start, end)`` windows tiling the range.
    """
    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=max_days - 1), end)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


def prior_window(start: date, end: date) -> tuple[date, date]:
    """Return the equal-length window immediately preceding ``start``–``end``.

    Args:
        start: Current range start (inclusive).
        end: Current range end (inclusive).

    Returns:
        Inclusive ``(start, end)`` of the preceding window.
    """
    length = (end - start).days
    prior_end = start - timedelta(days=1)
    return prior_end - timedelta(days=length), prior_end
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/cli/test_dates.py -v`
Expected: all pass.

- [ ] **Step 5: Lint & type-check, then commit**

Run: `uv run ruff check asa_api_client tests && uv run mypy asa_api_client`

```bash
git add asa_api_client/cli/dates.py tests/unit/cli/test_dates.py
git commit -m "✨ Add date resolution and window chunking"
```

---

### Task 3: metrics.py — aggregation and derived metrics

**Files:**
- Create: `asa_api_client/cli/metrics.py`
- Test: `tests/unit/cli/test_metrics.py`

**Interfaces:**
- Consumes: nothing from other tasks (pure pandas; no API or Excel imports).
- Produces (all take/return `pd.DataFrame` unless noted):
  - `LEVEL_KEYS: dict[str, list[str]]` — group-by keys per level key (`campaigns`, `ad_groups`, `keywords`, `search_terms`, `ads`).
  - `normalize(df: pd.DataFrame) -> pd.DataFrame` — renames `total_installs → installs`, `local_spend → spend`, coerces numerics, guarantees the metric columns exist.
  - `add_derived(df: pd.DataFrame) -> pd.DataFrame` — adds `ttr`, `cvr`, `cpt`, `cpa` (float, NaN on zero denominator).
  - `aggregate(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame` — one row per entity, metric sums + derived metrics, label columns carried via `first`, sorted by `spend` descending.
  - `kpis(df: pd.DataFrame) -> dict[str, float]` — keys `spend, impressions, taps, installs, ttr, cvr, cpt, cpa` (NaN for zero denominators).
  - `deltas(current: dict[str, float], prior: dict[str, float]) -> dict[str, float | None]` — fractional change per KPI key; `None` when prior is 0/NaN.
  - `daily_series(df: pd.DataFrame) -> pd.DataFrame` — columns `date, spend, installs`, one row per day, sorted.
  - `per_app(df: pd.DataFrame) -> pd.DataFrame` — per-`app_name` aggregate with derived metrics.
  - `top_keywords(df: pd.DataFrame, n: int = 5) -> pd.DataFrame` — top n by installs (spend as tiebreak).
  - `wasted_spend(df: pd.DataFrame) -> pd.DataFrame` — rows with `spend > 0` and `installs == 0`, sorted by spend desc.
- Input contract (produced by Task 4's `flatten_daily` + `normalize`): daily rows with `date` (str `YYYY-MM-DD`), metric columns, and level-dependent id/label columns (`campaign_id`, `campaign_name`, `app_name`, `ad_group_id`, `ad_group_name`, `keyword_id`, `keyword`, `match_type`, `search_term_text`, `ad_id`, `ad_name`, statuses).

- [ ] **Step 1: Write the failing tests**

`tests/unit/cli/test_metrics.py`:

```python
"""Tests for pure pandas metric aggregation."""

import math

import pandas as pd

from asa_api_client.cli.metrics import (
    LEVEL_KEYS,
    add_derived,
    aggregate,
    daily_series,
    deltas,
    kpis,
    normalize,
    per_app,
    top_keywords,
    wasted_spend,
)


def _daily() -> pd.DataFrame:
    """Two campaigns over two days; campaign 2 spends with no installs."""
    return normalize(
        pd.DataFrame(
            [
                {"date": "2026-07-01", "campaign_id": 1, "campaign_name": "One",
                 "app_name": "App A", "impressions": 1000, "taps": 100,
                 "total_installs": 10, "local_spend": "50.0"},
                {"date": "2026-07-02", "campaign_id": 1, "campaign_name": "One",
                 "app_name": "App A", "impressions": 1000, "taps": 100,
                 "total_installs": 10, "local_spend": "50.0"},
                {"date": "2026-07-01", "campaign_id": 2, "campaign_name": "Two",
                 "app_name": "App B", "impressions": 500, "taps": 0,
                 "total_installs": 0, "local_spend": "25.0"},
            ]
        )
    )


class TestNormalize:
    """normalize: renames, coercion, missing columns."""

    def test_renames_and_coerces(self) -> None:
        """String spend becomes float; totals become installs."""
        df = _daily()
        assert df["spend"].tolist() == [50.0, 50.0, 25.0]
        assert df["installs"].tolist() == [10, 10, 0]

    def test_missing_metric_columns_added_as_zero(self) -> None:
        """Absent metric columns appear as zeros."""
        df = normalize(pd.DataFrame([{"campaign_id": 1, "date": "2026-07-01"}]))
        assert df["spend"].tolist() == [0.0]
        assert df["impressions"].tolist() == [0]

    def test_empty_frame(self) -> None:
        """A fully empty frame still gains the metric columns."""
        df = normalize(pd.DataFrame())
        assert {"impressions", "taps", "installs", "spend"} <= set(df.columns)


class TestDerived:
    """add_derived: ratios with NaN on zero denominators."""

    def test_ratios(self) -> None:
        """TTR, CVR, CPT, CPA computed from sums."""
        df = add_derived(
            pd.DataFrame([{"impressions": 1000, "taps": 100, "installs": 10, "spend": 50.0}])
        )
        row = df.iloc[0]
        assert row["ttr"] == 0.1
        assert row["cvr"] == 0.1
        assert row["cpt"] == 0.5
        assert row["cpa"] == 5.0

    def test_zero_denominators_are_nan(self) -> None:
        """No impressions/taps/installs → NaN, not inf or ZeroDivisionError."""
        df = add_derived(
            pd.DataFrame([{"impressions": 0, "taps": 0, "installs": 0, "spend": 25.0}])
        )
        row = df.iloc[0]
        assert math.isnan(row["ttr"]) and math.isnan(row["cvr"])
        assert math.isnan(row["cpt"]) and math.isnan(row["cpa"])


class TestAggregate:
    """aggregate: one row per entity with sums, labels, and sorting."""

    def test_campaign_rollup(self) -> None:
        """Daily rows collapse to one row per campaign, spend-desc."""
        agg = aggregate(_daily(), LEVEL_KEYS["campaigns"])
        assert len(agg) == 2
        assert agg.iloc[0]["campaign_id"] == 1  # 100 spend > 25 spend
        assert agg.iloc[0]["spend"] == 100.0
        assert agg.iloc[0]["installs"] == 20
        assert agg.iloc[0]["campaign_name"] == "One"
        assert agg.iloc[0]["cpa"] == 5.0

    def test_empty_input(self) -> None:
        """Empty daily data aggregates to an empty frame without error."""
        agg = aggregate(normalize(pd.DataFrame()), LEVEL_KEYS["campaigns"])
        assert agg.empty


class TestKpisAndDeltas:
    """kpis/deltas: headline numbers and prior-period comparison."""

    def test_kpis(self) -> None:
        """KPIs sum the whole frame then derive ratios."""
        k = kpis(_daily())
        assert k["spend"] == 125.0
        assert k["installs"] == 20
        assert k["cpa"] == 6.25

    def test_deltas(self) -> None:
        """Fractional change; None when prior is zero."""
        d = deltas({"spend": 110.0, "installs": 0.0}, {"spend": 100.0, "installs": 0.0})
        assert d["spend"] is not None and abs(d["spend"] - 0.1) < 1e-9
        assert d["installs"] is None


class TestSummaryTables:
    """daily_series / per_app / top_keywords / wasted_spend."""

    def test_daily_series(self) -> None:
        """Per-day totals across all campaigns."""
        ds = daily_series(_daily())
        assert ds["date"].tolist() == ["2026-07-01", "2026-07-02"]
        assert ds["spend"].tolist() == [75.0, 50.0]
        assert ds["installs"].tolist() == [10, 10]

    def test_per_app(self) -> None:
        """One row per app."""
        pa = per_app(_daily())
        assert set(pa["app_name"]) == {"App A", "App B"}

    def test_top_and_wasted_keywords(self) -> None:
        """Top-5 by installs; wasted = spend>0, installs==0."""
        kw = aggregate(
            normalize(
                pd.DataFrame(
                    [
                        {"campaign_id": 1, "ad_group_id": 1, "keyword_id": 11,
                         "keyword": "good", "impressions": 100, "taps": 10,
                         "total_installs": 5, "local_spend": "10"},
                        {"campaign_id": 1, "ad_group_id": 1, "keyword_id": 12,
                         "keyword": "bad", "impressions": 100, "taps": 10,
                         "total_installs": 0, "local_spend": "30"},
                    ]
                )
            ),
            LEVEL_KEYS["keywords"],
        )
        assert top_keywords(kw).iloc[0]["keyword"] == "good"
        wasted = wasted_spend(kw)
        assert wasted["keyword"].tolist() == ["bad"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/cli/test_metrics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'asa_api_client.cli.metrics'`.

- [ ] **Step 3: Implement**

`asa_api_client/cli/metrics.py`:

```python
"""Pure pandas shaping for the analyze command.

No API, terminal, or Excel concerns here — DataFrames in, DataFrames out.
"""

import pandas as pd

METRIC_SUMS = ["impressions", "taps", "installs", "spend"]
INT_METRICS = ["impressions", "taps", "installs"]
KPI_KEYS = ["spend", "impressions", "taps", "installs", "ttr", "cvr", "cpt", "cpa"]

LEVEL_KEYS: dict[str, list[str]] = {
    "campaigns": ["campaign_id"],
    "ad_groups": ["campaign_id", "ad_group_id"],
    "keywords": ["campaign_id", "ad_group_id", "keyword_id"],
    "search_terms": ["campaign_id", "ad_group_id", "search_term_text"],
    "ads": ["campaign_id", "ad_group_id", "ad_id"],
}

_LABEL_COLUMNS = [
    "app_name",
    "adam_id",
    "campaign_name",
    "campaign_status",
    "ad_group_name",
    "ad_group_status",
    "keyword",
    "keyword_status",
    "match_type",
    "search_term_source",
    "ad_name",
    "ad_display_status",
]


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Rename raw report columns and coerce metric columns to numbers.

    Args:
        df: Raw daily frame from ``fetch.flatten_daily`` (may be empty).

    Returns:
        A copy with ``installs``/``spend`` named columns, numeric metric
        dtypes, and all of :data:`METRIC_SUMS` guaranteed present.
    """
    df = df.rename(columns={"total_installs": "installs", "local_spend": "spend"}).copy()
    for col in INT_METRICS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "spend" not in df.columns:
        df["spend"] = 0.0
    df["spend"] = pd.to_numeric(df["spend"], errors="coerce").fillna(0.0).astype(float)
    return df


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Add TTR, CVR, CPT and CPA columns; zero denominators become NaN.

    Args:
        df: Frame containing :data:`METRIC_SUMS` columns.

    Returns:
        The same frame (copied) with four derived float columns.
    """
    df = df.copy()
    df["ttr"] = (df["taps"] / df["impressions"]).where(df["impressions"] > 0)
    df["cvr"] = (df["installs"] / df["taps"]).where(df["taps"] > 0)
    df["cpt"] = (df["spend"] / df["taps"]).where(df["taps"] > 0)
    df["cpa"] = (df["spend"] / df["installs"]).where(df["installs"] > 0)
    return df


def aggregate(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Aggregate daily rows to one row per entity.

    Args:
        df: Normalized daily frame.
        keys: Group-by key columns (one of :data:`LEVEL_KEYS` values).

    Returns:
        Per-entity frame with metric sums, carried label columns, derived
        metrics, sorted by spend descending. Empty in → empty out.
    """
    if df.empty or any(k not in df.columns for k in keys):
        return pd.DataFrame(columns=[*keys, *_LABEL_COLUMNS, *METRIC_SUMS])
    label_cols = [c for c in _LABEL_COLUMNS if c in df.columns]
    agg_spec: dict[str, str] = {c: "first" for c in label_cols}
    agg_spec |= {c: "sum" for c in METRIC_SUMS}
    out = df.groupby(keys, dropna=False).agg(agg_spec).reset_index()
    out = add_derived(out)
    return out.sort_values("spend", ascending=False, ignore_index=True)


def kpis(df: pd.DataFrame) -> dict[str, float]:
    """Compute headline KPIs from a normalized daily frame.

    Args:
        df: Normalized daily campaign frame.

    Returns:
        Mapping of :data:`KPI_KEYS` to values (NaN where undefined).
    """
    totals = {c: float(df[c].sum()) if c in df.columns else 0.0 for c in METRIC_SUMS}
    derived = add_derived(pd.DataFrame([totals])).iloc[0]
    return {k: float(derived[k]) for k in KPI_KEYS}


def deltas(current: dict[str, float], prior: dict[str, float]) -> dict[str, float | None]:
    """Fractional change of each KPI versus the prior period.

    Args:
        current: Current-period KPIs.
        prior: Prior-period KPIs.

    Returns:
        Per-key fractional change, or ``None`` where the prior value is
        zero or NaN.
    """
    out: dict[str, float | None] = {}
    for key, value in current.items():
        base = prior.get(key)
        if base is None or base != base or base == 0 or value != value:
            out[key] = None
        else:
            out[key] = (value - base) / base
    return out


def daily_series(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a normalized daily frame to per-day spend and installs.

    Args:
        df: Normalized daily campaign frame with a ``date`` column.

    Returns:
        Frame with ``date``, ``spend``, ``installs`` sorted by date.
    """
    if df.empty or "date" not in df.columns:
        return pd.DataFrame(columns=["date", "spend", "installs"])
    out = df.groupby("date", as_index=False)[["spend", "installs"]].sum()
    return out.sort_values("date", ignore_index=True)


def per_app(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a normalized daily frame per app.

    Args:
        df: Normalized daily campaign frame with an ``app_name`` column.

    Returns:
        Per-app frame with metric sums and derived metrics, spend-desc.
    """
    if df.empty or "app_name" not in df.columns:
        return pd.DataFrame(columns=["app_name", *METRIC_SUMS])
    out = df.groupby("app_name", as_index=False)[METRIC_SUMS].sum()
    out = add_derived(out)
    return out.sort_values("spend", ascending=False, ignore_index=True)


def top_keywords(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Top keywords by installs (spend as tiebreak).

    Args:
        df: Aggregated keyword frame.
        n: Number of rows to keep.

    Returns:
        The top ``n`` keyword rows.
    """
    if df.empty:
        return df
    return df.sort_values(["installs", "spend"], ascending=False, ignore_index=True).head(n)


def wasted_spend(df: pd.DataFrame) -> pd.DataFrame:
    """Keywords that spent money without a single install.

    Args:
        df: Aggregated keyword frame.

    Returns:
        Rows with spend > 0 and installs == 0, sorted by spend descending.
    """
    if df.empty:
        return df
    mask = (df["spend"] > 0) & (df["installs"] == 0)
    return df[mask].sort_values("spend", ascending=False, ignore_index=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/cli/test_metrics.py -v`
Expected: all pass.

- [ ] **Step 5: Lint & type-check, then commit**

Run: `uv run ruff check asa_api_client tests && uv run mypy asa_api_client`

```bash
git add asa_api_client/cli/metrics.py tests/unit/cli/test_metrics.py
git commit -m "✨ Add pandas metric aggregation for analyze"
```

---

### Task 4: fetch.py — scope resolution and chunked async fetching

**Files:**
- Create: `asa_api_client/cli/fetch.py`
- Create: `tests/unit/cli/conftest.py`
- Test: `tests/unit/cli/test_fetch.py`

**Interfaces:**
- Consumes: `chunk_windows`, `prior_window`, `SEARCH_TERM_LOOKBACK` from `asa_api_client.cli.dates` (Task 2).
- Produces:
  - `LEVELS: list[tuple[str, str]]` — ordered `(key, label)` pairs: `[("campaigns", "Campaigns"), ("ad_groups", "Ad Groups"), ("keywords", "Keywords"), ("search_terms", "Search Terms"), ("ads", "Ads")]`.
  - `CONCURRENCY: int = 5`
  - `class ScopeError(Exception)` — no campaigns matched the requested apps.
  - `class LevelFetchError(Exception)` — an entire level failed to fetch.
  - `@dataclass LevelData: label: str; daily: pd.DataFrame; notes: list[str]`
  - `@dataclass FetchResult: levels: dict[str, LevelData]; prior_campaigns: pd.DataFrame; warnings: list[str]`
  - `flatten_daily(resp: ReportingResponse) -> pd.DataFrame` — one row per (entity, day) using `row.granularity` (falls back to `row.total`), spend fields flattened to their string amounts.
  - `resolve_scope(client: AppleSearchAdsClient, app_ids: list[int] | None) -> tuple[pd.DataFrame, str | None]` — sync; returns (meta frame with columns `campaign_id, campaign_name, adam_id, app_name`, org currency code or None). Raises `ScopeError` when nothing matches.
  - `async fetch_all(client: AppleSearchAdsClient, meta: pd.DataFrame, start: date, end: date, *, timezone: str = "UTC", today: date, on_progress: Callable[[str, int, int], None] | None = None) -> FetchResult` — daily granularity, ≤90-day chunks, semaphore(5), prior-period campaign fetch, search terms clipped to trailing 90 days with a note, per-chunk failures collected as warnings + sheet notes, whole-level failure raises `LevelFetchError`. `on_progress(level_key, completed, total)` fires as chunks finish. Every level's `daily` frame has `campaign_name`/`app_name`/`adam_id` merged on from `meta`.

- [ ] **Step 1: Write the shared conftest**

`tests/unit/cli/conftest.py`:

```python
"""Shared fixtures for CLI tests: env credentials and report JSON builders."""

from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"
API = "https://api.searchads.apple.com/api/v5"


@pytest.fixture
def asa_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the client at fake credentials with a real EC P-256 key."""
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    monkeypatch.setenv("ASA_CLIENT_ID", "SEARCHADS.test")
    monkeypatch.setenv("ASA_TEAM_ID", "TEAM123")
    monkeypatch.setenv("ASA_KEY_ID", "KEY123")
    monkeypatch.setenv("ASA_ORG_ID", "999")
    monkeypatch.setenv("ASA_PRIVATE_KEY", pem)
    monkeypatch.delenv("ASA_PRIVATE_KEY_PATH", raising=False)


def token_json() -> dict[str, Any]:
    """OAuth token response body."""
    return {"access_token": "tok", "token_type": "Bearer", "expires_in": 3600}


def campaigns_json() -> dict[str, Any]:
    """Two campaigns for two apps."""
    def campaign(cid: int, name: str, adam: int) -> dict[str, Any]:
        return {
            "id": cid,
            "orgId": 999,
            "name": name,
            "adamId": adam,
            "countriesOrRegions": ["US"],
            "status": "ENABLED",
            "servingStatus": "RUNNING",
            "modificationTime": "2026-08-01T00:00:00.000",
            "displayStatus": "RUNNING",
            "supplySources": ["APPSTORE_SEARCH_RESULTS"],
            "dailyBudgetAmount": {"amount": "100", "currency": "USD"},
        }

    data = [campaign(1, "Campaign One", 111), campaign(2, "Campaign Two", 222)]
    return {
        "data": data,
        "pagination": {"totalResults": 2, "startIndex": 0, "itemsPerPage": 2},
    }


def report_json(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap rows in the reporting response envelope."""
    return {"data": {"reportingDataResponse": {"row": rows, "grandTotals": {}}}}


def report_row(
    metadata: dict[str, Any], days: list[tuple[str, int, int, int, str]]
) -> dict[str, Any]:
    """Build a report row with a DAILY granularity breakdown.

    Args:
        metadata: The row metadata (campaignId etc.).
        days: Tuples of (date, impressions, taps, installs, spend).
    """
    granularity = [
        {
            "date": d,
            "impressions": imp,
            "taps": taps,
            "totalInstalls": installs,
            "localSpend": {"amount": spend, "currency": "USD"},
        }
        for d, imp, taps, installs, spend in days
    ]
    total = {
        "impressions": sum(g["impressions"] for g in granularity),
        "taps": sum(g["taps"] for g in granularity),
        "totalInstalls": sum(g["totalInstalls"] for g in granularity),
        "localSpend": {
            "amount": str(sum(float(g["localSpend"]["amount"]) for g in granularity)),
            "currency": "USD",
        },
    }
    return {"metadata": metadata, "total": total, "granularity": granularity}
```

- [ ] **Step 2: Write the failing tests**

`tests/unit/cli/test_fetch.py`:

```python
"""Tests for scope resolution and chunked async report fetching."""

import re
from datetime import date

import pandas as pd
import pytest
from pytest_httpx import HTTPXMock

from asa_api_client import AppleSearchAdsClient
from asa_api_client.cli.fetch import (
    LevelFetchError,
    ScopeError,
    fetch_all,
    flatten_daily,
    resolve_scope,
)
from asa_api_client.models.reports import ReportingResponse
from tests.unit.cli.conftest import (
    API,
    TOKEN_URL,
    campaigns_json,
    report_json,
    report_row,
    token_json,
)

START, END = date(2026, 7, 1), date(2026, 7, 2)
TODAY = date(2026, 8, 5)


def _client() -> AppleSearchAdsClient:
    return AppleSearchAdsClient.from_env(env_file=None)


def _mock_common(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=TOKEN_URL, json=token_json(), is_reusable=True)
    httpx_mock.add_response(
        url=f"{API}/campaigns?limit=1000&offset=0", json=campaigns_json(), is_reusable=True
    )
    httpx_mock.add_response(
        url=re.compile(rf"{API}/search/apps\?.*"), json={"data": []}, is_reusable=True
    )


class TestFlattenDaily:
    """flatten_daily: one row per entity-day from the granularity array."""

    def test_explodes_granularity(self) -> None:
        """Two days become two rows carrying metadata and date."""
        resp = ReportingResponse.model_validate(
            report_json(
                [
                    report_row(
                        {"campaignId": 1, "campaignName": "One"},
                        [("2026-07-01", 100, 10, 1, "5.0"), ("2026-07-02", 200, 20, 2, "10.0")],
                    )
                ]
            )["data"]["reportingDataResponse"]
        )
        df = flatten_daily(resp)
        assert len(df) == 2
        assert df["date"].tolist() == ["2026-07-01", "2026-07-02"]
        assert df["local_spend"].tolist() == ["5.0", "10.0"]
        assert df["campaign_id"].tolist() == [1, 1]

    def test_empty_response(self) -> None:
        """No rows → empty frame."""
        resp = ReportingResponse.model_validate({"row": []})
        assert flatten_daily(resp).empty


class TestResolveScope:
    """resolve_scope: campaign metadata map + currency."""

    def test_all_apps(self, asa_env: None, httpx_mock: HTTPXMock) -> None:
        """Without --app, every campaign is in scope; currency inferred."""
        _mock_common(httpx_mock)
        client = _client()
        try:
            meta, currency = resolve_scope(client, None)
        finally:
            client.close()
        assert sorted(meta["campaign_id"]) == [1, 2]
        assert currency == "USD"
        assert meta.loc[meta["adam_id"] == 111, "app_name"].iloc[0] == "App 111"

    def test_app_filter(self, asa_env: None, httpx_mock: HTTPXMock) -> None:
        """--app filters campaigns by adam_id."""
        _mock_common(httpx_mock)
        client = _client()
        try:
            meta, _ = resolve_scope(client, [111])
        finally:
            client.close()
        assert meta["campaign_id"].tolist() == [1]

    def test_no_match_raises(self, asa_env: None, httpx_mock: HTTPXMock) -> None:
        """An adam_id with no campaigns raises ScopeError."""
        _mock_common(httpx_mock)
        client = _client()
        try:
            with pytest.raises(ScopeError):
                resolve_scope(client, [999])
        finally:
            client.close()


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
class TestFetchAll:
    """fetch_all: five levels + prior period, failure tolerance."""

    def _mock_reports(self, httpx_mock: HTTPXMock) -> None:
        rows = [
            report_row(
                {"campaignId": 1, "campaignName": "One"},
                [("2026-07-01", 100, 10, 1, "5.0"), ("2026-07-02", 100, 10, 1, "5.0")],
            )
        ]
        httpx_mock.add_response(
            url=f"{API}/reports/campaigns", json=report_json(rows), is_reusable=True
        )
        for cid in (1, 2):
            for tail in ("adgroups", "keywords", "searchterms", "ads"):
                httpx_mock.add_response(
                    url=f"{API}/reports/campaigns/{cid}/{tail}",
                    json=report_json(rows),
                    is_reusable=True,
                )

    async def test_happy_path(self, asa_env: None, httpx_mock: HTTPXMock) -> None:
        """All five levels populated; prior campaigns fetched; names merged."""
        _mock_common(httpx_mock)
        self._mock_reports(httpx_mock)
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            result = await fetch_all(client, meta, START, END, today=TODAY)
        assert set(result.levels) == {"campaigns", "ad_groups", "keywords", "search_terms", "ads"}
        camp = result.levels["campaigns"].daily
        assert "app_name" in camp.columns
        assert not result.prior_campaigns.empty
        assert result.warnings == []

    async def test_progress_callback(self, asa_env: None, httpx_mock: HTTPXMock) -> None:
        """on_progress fires with (key, done, total) and reaches total."""
        _mock_common(httpx_mock)
        self._mock_reports(httpx_mock)
        seen: dict[str, tuple[int, int]] = {}
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            await fetch_all(
                client, meta, START, END, today=TODAY,
                on_progress=lambda key, done, total: seen.__setitem__(key, (done, total)),
            )
        assert seen["campaigns"] == (2, 2)  # current + prior window
        assert seen["keywords"] == (2, 2)  # one window x two campaigns

    async def test_chunk_failure_warns_and_continues(
        self, asa_env: None, httpx_mock: HTTPXMock
    ) -> None:
        """A failing per-campaign chunk becomes a warning + note, not a crash.

        The failure response is registered BEFORE the reusable success
        mocks: pytest-httpx matches responses in registration order, so a
        reusable success registered first would shadow the failure forever.
        """
        _mock_common(httpx_mock)
        httpx_mock.add_response(
            url=f"{API}/reports/campaigns/2/keywords", status_code=400,
            json={"error": {"errors": [{"message": "boom"}]}}, is_reusable=True,
        )
        self._mock_reports(httpx_mock)
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            result = await fetch_all(client, meta, START, END, today=TODAY)
        assert any("Keywords" in w for w in result.warnings)
        assert result.levels["keywords"].notes
        assert not result.levels["keywords"].daily.empty  # campaign 1 still there

    async def test_whole_level_failure_raises(
        self, asa_env: None, httpx_mock: HTTPXMock
    ) -> None:
        """Every chunk of a level failing aborts the run with context.

        Failure mocks registered first — see the note on the previous test.
        """
        _mock_common(httpx_mock)
        for cid in (1, 2):
            httpx_mock.add_response(
                url=f"{API}/reports/campaigns/{cid}/ads", status_code=400,
                json={"error": {"errors": [{"message": "no ads"}]}}, is_reusable=True,
            )
        self._mock_reports(httpx_mock)
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            with pytest.raises(LevelFetchError, match="Ads"):
                await fetch_all(client, meta, START, END, today=TODAY)

    async def test_search_terms_clipped_to_90_days(
        self, asa_env: None, httpx_mock: HTTPXMock
    ) -> None:
        """Long ranges clip search terms to trailing 90 days with a note."""
        _mock_common(httpx_mock)
        self._mock_reports(httpx_mock)
        async with _client() as client:
            meta, _ = resolve_scope(client, None)
            result = await fetch_all(
                client, meta, date(2025, 8, 6), date(2026, 8, 4), today=TODAY
            )
        assert any("90" in n for n in result.levels["search_terms"].notes)
```

Note on `pytest-httpx` behavior: a `400` response makes the client raise `ValidationError` (a subclass of `AppleSearchAdsError`) without retrying — `_request_async` retries only 429/5xx. That keeps the failure tests fast. If the retry behavior differs when you run it, check `asa_api_client/resources/base.py` `_request_async` and pick a non-retried status code accordingly.

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/cli/test_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'asa_api_client.cli.fetch'`.

- [ ] **Step 4: Implement**

`asa_api_client/cli/fetch.py`:

```python
"""Async data fetching for the analyze command.

Owns everything network-shaped: scope resolution, chunked report
fetching with bounded concurrency, the prior-period comparison fetch,
and flattening API responses into daily DataFrames.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from asa_api_client.cli.dates import SEARCH_TERM_LOOKBACK, chunk_windows, prior_window
from asa_api_client.exceptions import AppleSearchAdsError
from asa_api_client.models.reports import ReportingResponse

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient

LEVELS: list[tuple[str, str]] = [
    ("campaigns", "Campaigns"),
    ("ad_groups", "Ad Groups"),
    ("keywords", "Keywords"),
    ("search_terms", "Search Terms"),
    ("ads", "Ads"),
]
LEVEL_LABELS = dict(LEVELS)
CONCURRENCY = 5

_SPEND_FIELDS = ("tap_install_cpi", "total_avg_cpi", "avg_cpt", "avg_cpm", "local_spend")
_META_SPEND_FIELDS = ("bid_amount", "suggested_bid_amount")


class ScopeError(Exception):
    """No campaigns matched the requested scope."""


class LevelFetchError(Exception):
    """An entire reporting level failed to fetch."""


@dataclass
class LevelData:
    """Fetched daily data for one reporting level."""

    label: str
    daily: pd.DataFrame
    notes: list[str] = field(default_factory=list)


@dataclass
class FetchResult:
    """Everything fetched for one analyze run."""

    levels: dict[str, LevelData]
    prior_campaigns: pd.DataFrame
    warnings: list[str] = field(default_factory=list)


def flatten_daily(resp: ReportingResponse) -> pd.DataFrame:
    """Flatten a reporting response into one row per entity per day.

    Uses each row's ``granularity`` breakdown (falling back to ``total``
    when absent) so DAILY reports keep their per-day resolution —
    ``ReportingResponse.to_dataframe`` drops it.

    Args:
        resp: A parsed reporting response.

    Returns:
        A DataFrame with snake_case metadata columns plus per-day metric
        columns; spend fields flattened to their string amounts.
    """
    records: list[dict[str, object]] = []
    for row in resp.row:
        meta = row.metadata.model_dump(by_alias=False, exclude_none=True)
        for spend_field in _META_SPEND_FIELDS:
            value = meta.get(spend_field)
            if isinstance(value, dict):
                meta[spend_field] = value.get("amount")
        entries = row.granularity or ([row.total] if row.total is not None else [])
        for entry in entries:
            metric = entry.model_dump(by_alias=False, exclude_none=True)
            for spend_field in _SPEND_FIELDS:
                value = metric.get(spend_field)
                if isinstance(value, dict):
                    metric[spend_field] = value.get("amount")
            records.append({**meta, **metric})
    return pd.DataFrame(records)


def _app_names(client: "AppleSearchAdsClient", adam_ids: list[int]) -> dict[int, str]:
    """Best-effort lookup of app names for the org's adam IDs.

    Falls back to ``App <adam_id>`` labels when the search endpoint
    yields nothing (it requires a query and may not match).

    Args:
        client: The API client.
        adam_ids: Adam IDs present in the campaign scope.

    Returns:
        Mapping of adam ID to display name.
    """
    names: dict[int, str] = {}
    try:
        for info in client.apps.search(query="", return_own_apps=True):
            if info.adam_id is not None and info.app_name:
                names[int(info.adam_id)] = info.app_name
    except Exception:  # noqa: BLE001 - purely cosmetic lookup, never fatal
        names = {}
    return {adam: names.get(adam, f"App {adam}") for adam in adam_ids}


def resolve_scope(
    client: "AppleSearchAdsClient", app_ids: list[int] | None
) -> tuple[pd.DataFrame, str | None]:
    """List campaigns once and build the campaign → app scope map.

    Args:
        client: The API client.
        app_ids: Adam IDs to scope to, or None for the whole org.

    Returns:
        Tuple of (meta frame with ``campaign_id``, ``campaign_name``,
        ``adam_id``, ``app_name`` columns; org currency code or None).

    Raises:
        ScopeError: If no campaigns match the requested apps.
    """
    campaigns = list(client.campaigns.list())
    if app_ids:
        campaigns = [c for c in campaigns if c.adam_id in set(app_ids)]
    if not campaigns:
        detail = f" for app(s) {sorted(set(app_ids))}" if app_ids else ""
        raise ScopeError(f"No campaigns found{detail}")

    currency: str | None = None
    for campaign in campaigns:
        money = campaign.daily_budget_amount or campaign.budget_amount
        if money is not None:
            currency = money.currency
            break

    adam_ids = sorted({c.adam_id for c in campaigns})
    names = _app_names(client, adam_ids)
    meta = pd.DataFrame(
        [
            {
                "campaign_id": c.id,
                "campaign_name": c.name,
                "adam_id": c.adam_id,
                "app_name": names[c.adam_id],
            }
            for c in campaigns
        ]
    )
    return meta, currency


def _merge_names(df: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """Join campaign/app names onto a level frame by campaign_id."""
    if df.empty or "campaign_id" not in df.columns:
        return df
    df = df.drop(columns=[c for c in ("campaign_name", "app_name", "adam_id") if c in df.columns])
    return df.merge(meta, on="campaign_id", how="left")


async def fetch_all(
    client: "AppleSearchAdsClient",
    meta: pd.DataFrame,
    start: date,
    end: date,
    *,
    timezone: str = "UTC",
    today: date,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> FetchResult:
    """Fetch all five reporting levels plus the prior campaign period.

    Args:
        client: The API client.
        meta: Scope frame from :func:`resolve_scope`.
        start: Range start (inclusive).
        end: Range end (inclusive).
        timezone: Reporting timezone passed to the API.
        today: Current date (drives the search-term lookback clip).
        on_progress: Optional callback ``(level_key, completed, total)``.

    Returns:
        A :class:`FetchResult` with per-level daily frames (names merged
        on), the prior-period campaign frame, and accumulated warnings.

    Raises:
        LevelFetchError: If the campaign level fails, or every chunk of
            any other level fails.
    """
    windows = chunk_windows(start, end)
    p_start, p_end = prior_window(start, end)
    prior_windows = chunk_windows(p_start, p_end)
    campaign_ids = [int(c) for c in meta["campaign_id"].tolist()]

    st_start = max(start, today - timedelta(days=SEARCH_TERM_LOOKBACK))
    st_windows = chunk_windows(st_start, end) if st_start <= end else []
    st_clipped = st_start > start

    reports = client.reports
    per_campaign: dict[str, Callable[[int, date, date], Awaitable[ReportingResponse]]] = {
        "ad_groups": lambda cid, s, e: reports.ad_groups_async(cid, s, e, timezone=timezone),
        "keywords": lambda cid, s, e: reports.keywords_async(cid, s, e, timezone=timezone),
        "search_terms": lambda cid, s, e: reports.search_terms_async(
            cid, s, e, timezone=timezone
        ),
        "ads": lambda cid, s, e: reports.ads_async(cid, s, e, timezone=timezone),
    }
    level_windows = {key: st_windows if key == "search_terms" else windows for key in per_campaign}

    totals: dict[str, int] = {"campaigns": len(windows) + len(prior_windows)}
    totals |= {key: len(level_windows[key]) * len(campaign_ids) for key in per_campaign}
    done = dict.fromkeys(totals, 0)

    semaphore = asyncio.Semaphore(CONCURRENCY)
    warnings: list[str] = []
    frames: dict[str, list[pd.DataFrame]] = {key: [] for key, _ in LEVELS}
    prior_frames: list[pd.DataFrame] = []
    notes: dict[str, list[str]] = {key: [] for key, _ in LEVELS}
    failures: dict[str, int] = dict.fromkeys(totals, 0)

    def _tick(level: str) -> None:
        done[level] += 1
        if on_progress is not None:
            on_progress(level, done[level], totals[level])

    async def _campaign_window(win: tuple[date, date], *, prior: bool) -> None:
        async with semaphore:
            try:
                resp = await reports.campaigns_async(
                    win[0], win[1], campaign_ids=campaign_ids, timezone=timezone
                )
            except AppleSearchAdsError as exc:
                raise LevelFetchError(
                    f"Campaigns report failed for {win[0]}–{win[1]}: {exc}"
                ) from exc
            finally:
                _tick("campaigns")
            (prior_frames if prior else frames["campaigns"]).append(flatten_daily(resp))

    async def _chunk(level: str, cid: int, win: tuple[date, date]) -> None:
        label = LEVEL_LABELS[level]
        async with semaphore:
            try:
                resp = await per_campaign[level](cid, win[0], win[1])
            except AppleSearchAdsError as exc:
                failures[level] += 1
                message = f"{label}: campaign {cid} window {win[0]}–{win[1]} failed: {exc}"
                warnings.append(message)
                notes[level].append(message)
                return
            finally:
                _tick(level)
            frames[level].append(flatten_daily(resp))

    tasks: list[Awaitable[None]] = []
    tasks += [_campaign_window(win, prior=False) for win in windows]
    tasks += [_campaign_window(win, prior=True) for win in prior_windows]
    for level in per_campaign:
        tasks += [
            _chunk(level, cid, win) for cid in campaign_ids for win in level_windows[level]
        ]
    # return_exceptions=True lets every in-flight request finish before we
    # re-raise, so an aborting run doesn't leave tasks using a closing client.
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for outcome in results:
        if isinstance(outcome, BaseException):
            raise outcome

    if st_clipped:
        notes["search_terms"].insert(
            0,
            "Search terms are only available for the trailing 90 days; "
            f"this sheet covers {st_start}–{end}.",
        )

    levels: dict[str, LevelData] = {}
    for key, label in LEVELS:
        if key != "campaigns" and failures[key] and not frames[key]:
            raise LevelFetchError(
                f"{label}: every request failed; first error: {notes[key][0]}"
            )
        daily = pd.concat(frames[key], ignore_index=True) if frames[key] else pd.DataFrame()
        levels[key] = LevelData(label=label, daily=_merge_names(daily, meta), notes=notes[key])

    prior = pd.concat(prior_frames, ignore_index=True) if prior_frames else pd.DataFrame()
    return FetchResult(levels=levels, prior_campaigns=prior, warnings=warnings)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/cli/test_fetch.py -v`
Expected: all pass. If the empty-`query` app search hits a validation error in the mocked transport, that's fine — `_app_names` swallows it and falls back to `App <adam_id>` labels (which is what `test_all_apps` asserts).

- [ ] **Step 6: Lint & type-check, then commit**

Run: `uv run ruff check asa_api_client tests && uv run mypy asa_api_client`

```bash
git add asa_api_client/cli/fetch.py tests/unit/cli/conftest.py tests/unit/cli/test_fetch.py
git commit -m "✨ Add chunked async report fetching"
```

---

### Task 5: workbook.py — Excel rendering

**Files:**
- Create: `asa_api_client/cli/workbook.py`
- Test: `tests/unit/cli/test_workbook.py`

**Interfaces:**
- Consumes: DataFrames shaped by Task 3 (`aggregate` output with derived metric columns; `daily_series`/`per_app`/`top_keywords`/`wasted_spend` outputs; normalized daily frames). Does **not** import `fetch.py` or anything API-shaped.
- Produces:
  - `LEVELS: list[tuple[str, str]]` — same pairs as `fetch.LEVELS` (deliberately duplicated to keep workbook free of API imports).
  - `@dataclass SummaryData: title: str; period_label: str; timezone: str; generated_at: datetime; kpis: dict[str, float]; prior_kpis: dict[str, float] | None; daily: pd.DataFrame; per_app: pd.DataFrame | None; top_keywords: pd.DataFrame; wasted: pd.DataFrame`
  - `write_workbook(path: Path, *, summary: SummaryData, analysis: dict[str, pd.DataFrame], daily: dict[str, pd.DataFrame], notes: dict[str, list[str]], currency_format: str = "$#,##0.00") -> None` — `analysis`/`daily`/`notes` keyed by level key (`campaigns`…`ads`).
- Layout contract (tests depend on these exact positions):
  - Summary: `A1` title, `A2` = `"{period_label} · {timezone} · generated {generated_at:%Y-%m-%d %H:%M}"`; KPI labels on row 4 (cells `A4:H4`), values row 5, deltas row 6; chart inserted at `A8`; callout tables start at row 24 (0-indexed 23): `Top 5 keywords by installs` block in columns A–D, `Wasted spend` block in columns F–I, per-app table (if any) below at 4 rows past the longer callout.
  - Analysis sheets: header in row 1, data from row 2, autofilter, freeze at `A2`.
  - Daily sheets: named `Daily · <Label>`, grey tab `#9CA3AF`; if the level has notes, each note occupies one row starting at `A1` and the table starts beneath them, otherwise the table starts at row 1.
  - Hidden sheet `Chart Data` with `date/spend/installs` columns feeding the chart.

- [ ] **Step 1: Write the failing tests**

`tests/unit/cli/test_workbook.py`:

```python
"""Tests for xlsxwriter workbook rendering (read back with openpyxl)."""

from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from asa_api_client.cli.metrics import LEVEL_KEYS, aggregate, normalize
from asa_api_client.cli.workbook import SummaryData, write_workbook


def _campaign_daily() -> pd.DataFrame:
    return normalize(
        pd.DataFrame(
            [
                {"date": "2026-07-01", "campaign_id": 1, "campaign_name": "One",
                 "campaign_status": "ENABLED", "app_name": "App A",
                 "impressions": 1000, "taps": 100, "total_installs": 10,
                 "local_spend": "50.0"},
                {"date": "2026-07-02", "campaign_id": 2, "campaign_name": "Two",
                 "campaign_status": "ENABLED", "app_name": "App B",
                 "impressions": 500, "taps": 5, "total_installs": 0,
                 "local_spend": "25.0"},
            ]
        )
    )


def _keyword_agg() -> pd.DataFrame:
    return aggregate(
        normalize(
            pd.DataFrame(
                [
                    {"campaign_id": 1, "ad_group_id": 1, "keyword_id": 11,
                     "keyword": "good", "campaign_name": "One", "ad_group_name": "AG",
                     "impressions": 100, "taps": 10, "total_installs": 5,
                     "local_spend": "10"},
                    {"campaign_id": 1, "ad_group_id": 1, "keyword_id": 12,
                     "keyword": "bad", "campaign_name": "One", "ad_group_name": "AG",
                     "impressions": 100, "taps": 10, "total_installs": 0,
                     "local_spend": "30"},
                ]
            )
        ),
        LEVEL_KEYS["keywords"],
    )


def _write(tmp_path: Path) -> Path:
    daily = _campaign_daily()
    kw = _keyword_agg()
    camp_agg = aggregate(daily, LEVEL_KEYS["campaigns"])
    empty = pd.DataFrame()
    summary = SummaryData(
        title="App A · Performance analysis",
        period_label="2026-07-01 – 2026-07-02 (2 days)",
        timezone="UTC",
        generated_at=datetime(2026, 8, 5, 9, 30),
        kpis={"spend": 75.0, "impressions": 1500.0, "taps": 105.0, "installs": 10.0,
              "ttr": 0.07, "cvr": 0.095, "cpt": 0.714, "cpa": 7.5},
        prior_kpis={"spend": 50.0, "impressions": 1000.0, "taps": 100.0, "installs": 20.0,
                    "ttr": 0.1, "cvr": 0.2, "cpt": 0.5, "cpa": 2.5},
        daily=pd.DataFrame(
            {"date": ["2026-07-01", "2026-07-02"], "spend": [50.0, 25.0], "installs": [10, 0]}
        ),
        per_app=pd.DataFrame(
            {"app_name": ["App A", "App B"], "spend": [50.0, 25.0],
             "impressions": [1000, 500], "taps": [100, 5], "installs": [10, 0]}
        ),
        top_keywords=kw.head(5),
        wasted=kw[(kw["spend"] > 0) & (kw["installs"] == 0)],
    )
    path = tmp_path / "out.xlsx"
    write_workbook(
        path,
        summary=summary,
        analysis={"campaigns": camp_agg, "ad_groups": empty, "keywords": kw,
                  "search_terms": empty, "ads": empty},
        daily={"campaigns": daily, "ad_groups": empty, "keywords": empty,
               "search_terms": empty, "ads": empty},
        notes={"campaigns": [], "ad_groups": [], "keywords": [],
               "search_terms": ["Search terms limited to trailing 90 days."], "ads": []},
    )
    return path


class TestWorkbook:
    """End-to-end workbook structure assertions."""

    def test_sheet_order(self, tmp_path: Path) -> None:
        """Summary, five analysis sheets, then grey daily sheets."""
        wb = load_workbook(_write(tmp_path))
        expected = ["Summary", "Campaigns", "Ad Groups", "Keywords", "Search Terms",
                    "Ads", "Daily · Campaigns", "Daily · Ad Groups", "Daily · Keywords",
                    "Daily · Search Terms", "Daily · Ads"]
        visible = [n for n in wb.sheetnames if n != "Chart Data"]
        assert visible == expected

    def test_summary_content(self, tmp_path: Path) -> None:
        """Title, KPI band with deltas, callout headers."""
        ws = load_workbook(_write(tmp_path))["Summary"]
        assert ws["A1"].value == "App A · Performance analysis"
        assert ws["A4"].value == "Spend"
        assert ws["A5"].value == 75.0
        assert "▲" in ws["A6"].value  # spend up
        assert "▲" in ws["H6"].value and "CPA" == ws["H4"].value  # CPA up = bad arrow up
        texts = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)]
        assert "Top 5 keywords by installs" in texts
        assert "Wasted spend" in texts

    def test_currency_and_percent_formats(self, tmp_path: Path) -> None:
        """Spend uses the currency format; TTR uses a percent format."""
        ws = load_workbook(_write(tmp_path))["Summary"]
        assert "$" in ws["A5"].number_format
        assert "%" in ws["E5"].number_format

    def test_analysis_sheet(self, tmp_path: Path) -> None:
        """Campaigns sheet has headers, data, freeze panes and autofilter."""
        ws = load_workbook(_write(tmp_path))["Campaigns"]
        headers = [c.value for c in ws[1]]
        assert "Campaign" in headers and "Spend" in headers and "CPA" in headers
        assert ws.freeze_panes == "A2"
        assert ws.auto_filter.ref is not None
        spend_col = headers.index("Spend") + 1
        assert "$" in ws.cell(row=2, column=spend_col).number_format

    def test_dash_for_nan_cpa(self, tmp_path: Path) -> None:
        """Campaign 2 (0 installs) renders CPA as an em dash."""
        ws = load_workbook(_write(tmp_path))["Campaigns"]
        headers = [c.value for c in ws[1]]
        cpa_col = headers.index("CPA") + 1
        values = {ws.cell(row=r, column=cpa_col).value for r in (2, 3)}
        assert "—" in values

    def test_daily_sheet_tab_color_and_note(self, tmp_path: Path) -> None:
        """Daily tabs are grey; search-term note appears above the table."""
        wb = load_workbook(_write(tmp_path))
        daily = wb["Daily · Campaigns"]
        assert daily.sheet_properties.tabColor is not None
        st = wb["Daily · Search Terms"]
        assert st["A1"].value == "Search terms limited to trailing 90 days."

    def test_chart_data_hidden(self, tmp_path: Path) -> None:
        """Chart Data sheet exists, is hidden, and holds the series."""
        wb = load_workbook(_write(tmp_path))
        cd = wb["Chart Data"]
        assert cd.sheet_state == "hidden"
        assert cd["A1"].value == "date" and cd["B1"].value == "spend"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/cli/test_workbook.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'asa_api_client.cli.workbook'`.

- [ ] **Step 3: Implement**

`asa_api_client/cli/workbook.py`:

```python
"""xlsxwriter rendering for the analyze command.

Takes shaped DataFrames and writes the workbook.  Knows nothing about
the API or the terminal.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import xlsxwriter
from xlsxwriter.format import Format
from xlsxwriter.worksheet import Worksheet

from asa_api_client.cli.metrics import deltas as _deltas

LEVELS: list[tuple[str, str]] = [
    ("campaigns", "Campaigns"),
    ("ad_groups", "Ad Groups"),
    ("keywords", "Keywords"),
    ("search_terms", "Search Terms"),
    ("ads", "Ads"),
]

KPI_SPEC: list[tuple[str, str, str]] = [
    ("Spend", "spend", "currency"),
    ("Impressions", "impressions", "int"),
    ("Taps", "taps", "int"),
    ("Installs", "installs", "int"),
    ("TTR", "ttr", "percent"),
    ("CVR", "cvr", "percent"),
    ("Avg CPT", "cpt", "currency"),
    ("CPA", "cpa", "currency"),
]
LOWER_IS_BETTER = {"cpt", "cpa"}

_METRIC_BLOCK: list[tuple[str, str, str]] = [
    ("impressions", "Impressions", "int"),
    ("taps", "Taps", "int"),
    ("installs", "Installs", "int"),
    ("spend", "Spend", "currency"),
    ("ttr", "TTR", "percent"),
    ("cvr", "CVR", "percent"),
    ("cpt", "Avg CPT", "currency"),
    ("cpa", "CPA", "currency"),
]

ANALYSIS_COLUMNS: dict[str, list[tuple[str, str, str]]] = {
    "campaigns": [
        ("app_name", "App", "text"),
        ("campaign_id", "Campaign ID", "id"),
        ("campaign_name", "Campaign", "text"),
        ("campaign_status", "Status", "text"),
        *_METRIC_BLOCK,
    ],
    "ad_groups": [
        ("app_name", "App", "text"),
        ("campaign_name", "Campaign", "text"),
        ("ad_group_id", "Ad Group ID", "id"),
        ("ad_group_name", "Ad Group", "text"),
        ("ad_group_status", "Status", "text"),
        *_METRIC_BLOCK,
    ],
    "keywords": [
        ("campaign_name", "Campaign", "text"),
        ("ad_group_name", "Ad Group", "text"),
        ("keyword_id", "Keyword ID", "id"),
        ("keyword", "Keyword", "text"),
        ("match_type", "Match Type", "text"),
        ("keyword_status", "Status", "text"),
        *_METRIC_BLOCK,
    ],
    "search_terms": [
        ("campaign_name", "Campaign", "text"),
        ("ad_group_name", "Ad Group", "text"),
        ("search_term_text", "Search Term", "text"),
        ("search_term_source", "Source", "text"),
        ("keyword", "Matched Keyword", "text"),
        *_METRIC_BLOCK,
    ],
    "ads": [
        ("campaign_name", "Campaign", "text"),
        ("ad_group_name", "Ad Group", "text"),
        ("ad_id", "Ad ID", "id"),
        ("ad_name", "Ad", "text"),
        ("ad_display_status", "Status", "text"),
        *_METRIC_BLOCK,
    ],
}

_COLUMN_WIDTHS = {"text": 28, "id": 12, "int": 12, "currency": 12, "percent": 9}
_TAB_GREY = "#9CA3AF"


@dataclass
class SummaryData:
    """Everything the Summary sheet needs."""

    title: str
    period_label: str
    timezone: str
    generated_at: datetime
    kpis: dict[str, float]
    prior_kpis: dict[str, float] | None
    daily: pd.DataFrame
    per_app: pd.DataFrame | None
    top_keywords: pd.DataFrame
    wasted: pd.DataFrame


def _is_nan(value: object) -> bool:
    """True for None or float NaN."""
    return value is None or (isinstance(value, float) and value != value)


def _formats(book: Any, currency_format: str) -> dict[str, Format]:
    """Create every cell format once."""
    return {
        "title": book.add_format({"bold": True, "font_size": 16}),
        "subtitle": book.add_format({"font_color": "#666666"}),
        "header": book.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F2937", "border": 1}
        ),
        "text": book.add_format({}),
        "id": book.add_format({"num_format": "0"}),
        "int": book.add_format({"num_format": "#,##0"}),
        "currency": book.add_format({"num_format": currency_format}),
        "percent": book.add_format({"num_format": "0.00%"}),
        "kpi_label": book.add_format(
            {"bold": True, "font_color": "#666666", "font_size": 10, "bottom": 1}
        ),
        "kpi_currency": book.add_format({"num_format": currency_format, "font_size": 13}),
        "kpi_int": book.add_format({"num_format": "#,##0", "font_size": 13}),
        "kpi_percent": book.add_format({"num_format": "0.00%", "font_size": 13}),
        "delta_good": book.add_format({"font_color": "#15803D", "font_size": 10}),
        "delta_bad": book.add_format({"font_color": "#B91C1C", "font_size": 10}),
        "delta_flat": book.add_format({"font_color": "#666666", "font_size": 10}),
        "note": book.add_format({"italic": True, "font_color": "#92400E"}),
        "dash": book.add_format({"align": "center", "font_color": "#999999"}),
        "callout_header": book.add_format({"bold": True, "font_size": 12}),
    }


def _write_value(
    ws: Worksheet, row: int, col: int, value: object, fmt: Format, dash: Format
) -> None:
    """Write a cell, rendering NaN/None as an em dash."""
    if _is_nan(value):
        ws.write_string(row, col, "—", dash)
    elif isinstance(value, int | float):
        ws.write_number(row, col, float(value), fmt)
    else:
        ws.write(row, col, value, fmt)


def _write_table(
    ws: Worksheet,
    df: pd.DataFrame,
    spec: list[tuple[str, str, str]],
    fmts: dict[str, Format],
    *,
    start_row: int = 0,
    autofilter: bool = True,
    freeze: bool = True,
) -> int:
    """Write a header + rows table; returns the last written row index."""
    for col_idx, (_, header, kind) in enumerate(spec):
        ws.write_string(start_row, col_idx, header, fmts["header"])
        ws.set_column(col_idx, col_idx, _COLUMN_WIDTHS.get(kind, 12))
    body = df.reindex(columns=[c for c, _, _ in spec])
    for r, (_, row) in enumerate(body.iterrows(), start=start_row + 1):
        for col_idx, (col, _, kind) in enumerate(spec):
            fmt = fmts[kind] if kind in fmts else fmts["text"]
            value = row[col]
            if kind == "text" and _is_nan(value):
                ws.write_string(r, col_idx, "", fmts["text"])
            else:
                _write_value(ws, r, col_idx, value, fmt, fmts["dash"])
    last_row = start_row + len(body)
    if autofilter and len(spec) > 1:
        ws.autofilter(start_row, 0, max(last_row, start_row + 1), len(spec) - 1)
    if freeze:
        ws.freeze_panes(start_row + 1, 0)
    return last_row


def _col_letter(idx: int) -> str:
    """0-based column index to Excel letters."""
    letters = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _write_analysis_sheet(
    book: Any,
    label: str,
    df: pd.DataFrame,
    spec: list[tuple[str, str, str]],
    fmts: dict[str, Format],
    cpa_benchmark: float | None,
) -> None:
    """Write one analysis sheet with conditional formatting."""
    ws = book.add_worksheet(label)
    last_row = _write_table(ws, df, spec, fmts)
    if last_row == 0:
        return
    cols = [c for c, _, _ in spec]
    spend_c = _col_letter(cols.index("spend"))
    installs_c = _col_letter(cols.index("installs"))
    cpa_idx = cols.index("cpa")
    cpa_c = _col_letter(cpa_idx)
    n_cols = len(spec)

    ws.conditional_format(
        f"{spend_c}2:{spend_c}{last_row + 1}", {"type": "data_bar", "bar_color": "#93C5FD"}
    )
    red_fill = book.add_format({"bg_color": "#FEE2E2"})
    ws.conditional_format(
        1, 0, last_row, n_cols - 1,
        {
            "type": "formula",
            "criteria": f"=AND(${spend_c}2>0,${installs_c}2=0)",
            "format": red_fill,
        },
    )
    if cpa_benchmark is not None and cpa_benchmark == cpa_benchmark and cpa_benchmark > 0:
        amber = book.add_format({"bg_color": "#FEF3C7"})
        green = book.add_format({"bg_color": "#DCFCE7"})
        ws.conditional_format(
            1, cpa_idx, last_row, cpa_idx,
            {
                "type": "formula",
                "criteria": f"=AND(ISNUMBER(${cpa_c}2),${cpa_c}2>{cpa_benchmark * 1.5})",
                "format": amber,
            },
        )
        ws.conditional_format(
            1, cpa_idx, last_row, cpa_idx,
            {
                "type": "formula",
                "criteria": (
                    f"=AND(ISNUMBER(${cpa_c}2),${cpa_c}2<{cpa_benchmark * 0.75},"
                    f"${installs_c}2>=5)"
                ),
                "format": green,
            },
        )


_CALLOUT_SPEC: list[tuple[str, str, str]] = [
    ("keyword", "Keyword", "text"),
    ("installs", "Installs", "int"),
    ("spend", "Spend", "currency"),
    ("cpa", "CPA", "currency"),
]
_PER_APP_SPEC: list[tuple[str, str, str]] = [
    ("app_name", "App", "text"),
    ("spend", "Spend", "currency"),
    ("impressions", "Impressions", "int"),
    ("taps", "Taps", "int"),
    ("installs", "Installs", "int"),
]


def _delta_cell(key: str, delta: float | None) -> tuple[str, str]:
    """Return (text, format key) for a KPI delta cell."""
    if delta is None:
        return "–", "delta_flat"
    arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "▬")
    improved = (delta < 0) if key in LOWER_IS_BETTER else (delta > 0)
    fmt = "delta_flat" if delta == 0 else ("delta_good" if improved else "delta_bad")
    return f"{arrow} {abs(delta):.1%} vs prior", fmt


def _write_summary(
    book: Any, summary: SummaryData, fmts: dict[str, Format]
) -> None:
    """Write the Summary sheet: title, KPI band, chart, callouts."""
    ws = book.add_worksheet("Summary")
    ws.set_column(0, 8, 16)
    ws.write_string(0, 0, summary.title, fmts["title"])
    ws.write_string(
        1,
        0,
        f"{summary.period_label} · {summary.timezone} · "
        f"generated {summary.generated_at:%Y-%m-%d %H:%M}",
        fmts["subtitle"],
    )

    kpi_fmt = {"currency": "kpi_currency", "int": "kpi_int", "percent": "kpi_percent"}
    kpi_deltas = (
        _deltas(summary.kpis, summary.prior_kpis) if summary.prior_kpis else {}
    )
    for idx, (label, key, kind) in enumerate(KPI_SPEC):
        ws.write_string(3, idx, label, fmts["kpi_label"])
        _write_value(ws, 4, idx, summary.kpis.get(key), fmts[kpi_fmt[kind]], fmts["dash"])
        text, fmt_key = _delta_cell(key, kpi_deltas.get(key))
        ws.write_string(5, idx, text, fmts[fmt_key])

    chart_ws = book.add_worksheet("Chart Data")
    chart_ws.write_row(0, 0, ["date", "spend", "installs"])
    for r, (_, row) in enumerate(summary.daily.iterrows(), start=1):
        chart_ws.write_string(r, 0, str(row["date"]))
        chart_ws.write_number(r, 1, float(row["spend"]))
        chart_ws.write_number(r, 2, float(row["installs"]))
    chart_ws.hide()

    n = len(summary.daily)
    if n:
        chart = book.add_chart({"type": "line"})
        chart.add_series(
            {
                "name": "Spend",
                "categories": ["Chart Data", 1, 0, n, 0],
                "values": ["Chart Data", 1, 1, n, 1],
            }
        )
        chart.add_series(
            {
                "name": "Installs",
                "categories": ["Chart Data", 1, 0, n, 0],
                "values": ["Chart Data", 1, 2, n, 2],
                "y2_axis": True,
            }
        )
        chart.set_title({"name": "Daily spend vs installs"})
        chart.set_legend({"position": "bottom"})
        ws.insert_chart(7, 0, chart, {"x_scale": 1.8, "y_scale": 1.1})

    row = 23
    ws.write_string(row, 0, "Top 5 keywords by installs", fmts["callout_header"])
    top_last = _write_table(
        ws, summary.top_keywords, _CALLOUT_SPEC, fmts,
        start_row=row + 1, autofilter=False, freeze=False,
    )
    ws.write_string(row, 5, "Wasted spend", fmts["callout_header"])
    wasted_spec = [(c, h, k) for c, h, k in _CALLOUT_SPEC if c != "cpa"]
    for col_idx, (_, header, kind) in enumerate(wasted_spec):
        ws.write_string(row + 1, 5 + col_idx, header, fmts["header"])
    body = summary.wasted.reindex(columns=[c for c, _, _ in wasted_spec])
    for r, (_, wrow) in enumerate(body.iterrows(), start=row + 2):
        for col_idx, (col, _, kind) in enumerate(wasted_spec):
            _write_value(ws, r, 5 + col_idx, wrow[col], fmts[kind], fmts["dash"])
    wasted_last = row + 1 + len(body)

    if summary.per_app is not None and len(summary.per_app) > 1:
        app_row = max(top_last, wasted_last) + 4
        ws.write_string(app_row, 0, "Per-app breakdown", fmts["callout_header"])
        _write_table(
            ws, summary.per_app, _PER_APP_SPEC, fmts,
            start_row=app_row + 1, autofilter=False, freeze=False,
        )


_DAILY_BASE: list[tuple[str, str, str]] = [
    ("date", "Date", "text"),
    ("app_name", "App", "text"),
    ("campaign_name", "Campaign", "text"),
]
_DAILY_EXTRAS: dict[str, list[tuple[str, str, str]]] = {
    "campaigns": [],
    "ad_groups": [("ad_group_name", "Ad Group", "text")],
    "keywords": [
        ("ad_group_name", "Ad Group", "text"),
        ("keyword", "Keyword", "text"),
        ("match_type", "Match Type", "text"),
    ],
    "search_terms": [
        ("ad_group_name", "Ad Group", "text"),
        ("search_term_text", "Search Term", "text"),
    ],
    "ads": [("ad_group_name", "Ad Group", "text"), ("ad_name", "Ad", "text")],
}
_DAILY_METRICS: list[tuple[str, str, str]] = [
    ("impressions", "Impressions", "int"),
    ("taps", "Taps", "int"),
    ("installs", "Installs", "int"),
    ("spend", "Spend", "currency"),
]


def write_workbook(
    path: Path,
    *,
    summary: SummaryData,
    analysis: dict[str, pd.DataFrame],
    daily: dict[str, pd.DataFrame],
    notes: dict[str, list[str]],
    currency_format: str = "$#,##0.00",
) -> None:
    """Write the full analysis workbook to ``path``.

    Args:
        path: Output ``.xlsx`` path.
        summary: Summary-sheet content.
        analysis: Aggregated per-entity frames keyed by level key.
        daily: Normalized daily frames keyed by level key.
        notes: Per-level notes rendered above the daily tables.
        currency_format: Excel number format for money cells.
    """
    book = xlsxwriter.Workbook(str(path), {"nan_inf_to_errors": True})
    try:
        fmts = _formats(book, currency_format)
        _write_summary(book, summary, fmts)
        cpa_benchmark = summary.kpis.get("cpa")
        for key, label in LEVELS:
            _write_analysis_sheet(
                book, label, analysis.get(key, pd.DataFrame()),
                ANALYSIS_COLUMNS[key], fmts, cpa_benchmark,
            )
        for key, label in LEVELS:
            ws = book.add_worksheet(f"Daily · {label}")
            ws.set_tab_color(_TAB_GREY)
            start = 0
            for note in notes.get(key, []):
                ws.write_string(start, 0, note, fmts["note"])
                start += 1
            spec = _DAILY_BASE + _DAILY_EXTRAS[key] + _DAILY_METRICS
            _write_table(ws, daily.get(key, pd.DataFrame()), spec, fmts, start_row=start)
    finally:
        book.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/cli/test_workbook.py -v`
Expected: all pass. If `xlsxwriter` chart/format API kwargs disagree with the installed version, fix the call — do not weaken the tests.

- [ ] **Step 5: Lint & type-check, then commit**

Run: `uv run ruff check asa_api_client tests && uv run mypy asa_api_client`
(If mypy lacks stubs for `xlsxwriter`, add `xlsxwriter.*` to a `[[tool.mypy.overrides]]` with `ignore_missing_imports = true` in `pyproject.toml` rather than sprinkling `# type: ignore`.)

```bash
git add asa_api_client/cli/workbook.py tests/unit/cli/test_workbook.py pyproject.toml
git commit -m "✨ Add xlsxwriter workbook rendering"
```

---

### Task 6: analyze.py — the real command

**Files:**
- Modify: `asa_api_client/cli/analyze.py` (replace the Task 1 placeholder body; keep `app` and the command name)
- Test: `tests/unit/cli/test_cli.py`

**Interfaces:**
- Consumes:
  - `dates.resolve_range`, `dates.PERIODS`
  - `fetch.resolve_scope`, `fetch.fetch_all`, `fetch.LEVELS`, `fetch.ScopeError`, `fetch.LevelFetchError`, `fetch.FetchResult`
  - `metrics.normalize`, `metrics.aggregate`, `metrics.LEVEL_KEYS`, `metrics.kpis`, `metrics.daily_series`, `metrics.per_app`, `metrics.top_keywords`, `metrics.wasted_spend`
  - `workbook.SummaryData`, `workbook.write_workbook`
  - `AppleSearchAdsClient.from_env`, `asa_api_client.exceptions.ConfigurationError`, `AppleSearchAdsError`
- Produces: the finished `asa analyze` command. Exit code 0 on success (prints output path + headline), 1 on any handled error (clean one-line message on stderr, never a traceback), 2 on option-validation errors (Typer's default).

- [ ] **Step 1: Write the failing tests**

`tests/unit/cli/test_cli.py`:

```python
"""End-to-end CLI tests with a mocked transport."""

import re
from pathlib import Path

import pytest
from openpyxl import load_workbook
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from asa_api_client.cli.analyze import app
from tests.unit.cli.conftest import (
    API,
    TOKEN_URL,
    campaigns_json,
    report_json,
    report_row,
    token_json,
)

runner = CliRunner()


def _mock_api(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=TOKEN_URL, json=token_json(), is_reusable=True)
    httpx_mock.add_response(
        url=f"{API}/campaigns?limit=1000&offset=0", json=campaigns_json(), is_reusable=True
    )
    httpx_mock.add_response(
        url=re.compile(rf"{API}/search/apps\?.*"), json={"data": []}, is_reusable=True
    )
    rows = [
        report_row(
            {"campaignId": 1, "campaignName": "Campaign One"},
            [("2026-07-01", 1000, 100, 10, "50.0")],
        )
    ]
    httpx_mock.add_response(
        url=f"{API}/reports/campaigns", json=report_json(rows), is_reusable=True
    )
    for cid in (1, 2):
        for tail in ("adgroups", "keywords", "searchterms", "ads"):
            httpx_mock.add_response(
                url=f"{API}/reports/campaigns/{cid}/{tail}",
                json=report_json(rows),
                is_reusable=True,
            )


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
class TestAnalyzeCommand:
    """asa analyze end to end."""

    def test_happy_path(
        self, asa_env: None, httpx_mock: HTTPXMock, tmp_path: Path
    ) -> None:
        """Writes the workbook, prints its path and a headline."""
        _mock_api(httpx_mock)
        out = tmp_path / "report.xlsx"
        result = runner.invoke(app, ["analyze", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        assert str(out) in result.output
        assert "spend" in result.output and "installs" in result.output
        wb = load_workbook(out)
        assert wb.sheetnames[0] == "Summary"

    def test_app_filter_and_default_name(
        self, asa_env: None, httpx_mock: HTTPXMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--app scopes; default filename includes the adam id."""
        _mock_api(httpx_mock)
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["analyze", "--app", "111"])
        assert result.exit_code == 0, result.output
        produced = list(tmp_path.glob("asa-analysis-111-*.xlsx"))
        assert len(produced) == 1

    def test_invalid_range_fails_before_network(
        self, asa_env: None, httpx_mock: HTTPXMock
    ) -> None:
        """--from after --to exits non-zero with a clean message and no requests."""
        result = runner.invoke(app, ["analyze", "--from", "2026-05-02", "--to", "2026-05-01"])
        assert result.exit_code != 0
        assert "before" in (result.output + str(result.exception or ""))
        assert not httpx_mock.get_requests()

    def test_missing_credentials_clean_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """No env vars → one-line configuration error, no traceback."""
        monkeypatch.chdir(tmp_path)  # hermetic: don't pick up a stray repo .env
        for var in ("ASA_CLIENT_ID", "ASA_TEAM_ID", "ASA_KEY_ID", "ASA_ORG_ID",
                    "ASA_PRIVATE_KEY", "ASA_PRIVATE_KEY_PATH"):
            monkeypatch.delenv(var, raising=False)
        result = runner.invoke(app, ["analyze"])
        assert result.exit_code == 1
        assert result.exception is None or isinstance(result.exception, SystemExit)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/cli/test_cli.py -v`
Expected: FAIL (placeholder command takes no options → usage errors / missing output).

- [ ] **Step 3: Implement**

Replace `asa_api_client/cli/analyze.py` with:

```python
"""The ``asa analyze`` command: options, orchestration, presentation."""

import asyncio
import sys
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskID, TextColumn

from asa_api_client.cli import dates, fetch, metrics
from asa_api_client.cli.workbook import SummaryData, write_workbook
from asa_api_client.client import AppleSearchAdsClient
from asa_api_client.exceptions import AppleSearchAdsError, ConfigurationError

app = typer.Typer(no_args_is_help=True, add_completion=False)
_err = Console(stderr=True)


@app.callback()
def _root() -> None:
    """Apple Search Ads analysis toolkit."""


class Period(StrEnum):
    """Preset reporting periods."""

    D30 = "30d"
    D90 = "90d"
    D365 = "365d"


_CURRENCY_FORMATS = {
    "USD": "$#,##0.00", "AUD": "$#,##0.00", "CAD": "$#,##0.00", "NZD": "$#,##0.00",
    "EUR": "€#,##0.00", "GBP": "£#,##0.00", "JPY": "¥#,##0",
}


def _currency_format(code: str | None) -> str:
    """Map an ISO currency code to an Excel number format."""
    if code is None:
        return "$#,##0.00"
    return _CURRENCY_FORMATS.get(code, f'"{code} "#,##0.00')


def _currency_symbol(currency_format: str) -> str:
    """First non-format character of the currency format, for the headline."""
    head = currency_format[0]
    return head if head not in "#0[\"" else "$"


def _fail(message: str) -> "typer.Exit":
    """Print a clean one-line error and exit 1."""
    _err.print(f"[red]Error:[/red] {message}")
    return typer.Exit(code=1)


async def _fetch(
    client: AppleSearchAdsClient,
    meta: pd.DataFrame,
    start: date,
    end: date,
    timezone: str,
    progress: Progress,
) -> fetch.FetchResult:
    """Run fetch_all wired to the rich progress display."""
    tasks: dict[str, TaskID] = {
        key: progress.add_task(label, total=None) for key, label in fetch.LEVELS
    }

    def on_progress(key: str, done: int, total: int) -> None:
        progress.update(tasks[key], completed=done, total=total)

    try:
        return await fetch.fetch_all(
            client, meta, start, end, timezone=timezone,
            today=datetime.now(tz=UTC).date(), on_progress=on_progress,
        )
    finally:
        await client.aclose()


@app.command()
def analyze(
    app_ids: Annotated[
        list[int] | None,
        typer.Option("--app", "-a", help="Adam ID to scope to; repeatable."),
    ] = None,
    period: Annotated[
        Period, typer.Option("--period", "-p", help="Preset range ending yesterday.")
    ] = Period.D30,
    from_date: Annotated[
        datetime | None,
        typer.Option("--from", formats=["%Y-%m-%d"], help="Explicit start date."),
    ] = None,
    to_date: Annotated[
        datetime | None,
        typer.Option("--to", formats=["%Y-%m-%d"], help="Explicit end date."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output .xlsx path.")
    ] = None,
    timezone: Annotated[
        str, typer.Option("--timezone", help="Reporting timezone.")
    ] = "UTC",
    currency_format: Annotated[
        str | None,
        typer.Option("--currency-format", help="Excel number format for money."),
    ] = None,
) -> None:
    """Generate an Excel performance analysis workbook."""
    today = datetime.now(tz=UTC).date()
    try:
        start, end = dates.resolve_range(
            period.value,
            from_date.date() if from_date else None,
            to_date.date() if to_date else None,
            today=today,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    try:
        client = AppleSearchAdsClient.from_env()
    except ConfigurationError as exc:
        raise _fail(str(exc)) from exc

    try:
        meta, currency = fetch.resolve_scope(client, app_ids)
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
        ) as progress:
            result = asyncio.run(_fetch(client, meta, start, end, timezone, progress))
    except fetch.ScopeError as exc:
        raise _fail(str(exc)) from exc
    except fetch.LevelFetchError as exc:
        raise _fail(str(exc)) from exc
    except AppleSearchAdsError as exc:
        raise _fail(str(exc)) from exc
    finally:
        client.close()

    for warning in result.warnings:
        _err.print(f"[yellow]Warning:[/yellow] {warning}")

    daily_frames = {key: metrics.normalize(lv.daily) for key, lv in result.levels.items()}
    analysis = {
        key: metrics.aggregate(daily_frames[key], metrics.LEVEL_KEYS[key])
        for key in daily_frames
    }
    campaign_daily = daily_frames["campaigns"]
    current_kpis = metrics.kpis(campaign_daily)
    prior_kpis = (
        metrics.kpis(metrics.normalize(result.prior_campaigns))
        if not result.prior_campaigns.empty
        else None
    )

    apps_in_scope = sorted(meta["adam_id"].unique().tolist())
    if app_ids and len(apps_in_scope) == 1:
        scope_label = meta["app_name"].iloc[0]
        file_scope = str(apps_in_scope[0])
    else:
        scope_label = "All apps"
        file_scope = "org"
    day_count = (end - start).days + 1
    fmt = currency_format or _currency_format(currency)

    summary = SummaryData(
        title=f"{scope_label} · Apple Search Ads performance",
        period_label=f"{start} – {end} ({day_count} days)",
        timezone=timezone,
        generated_at=datetime.now(tz=UTC),
        kpis=current_kpis,
        prior_kpis=prior_kpis,
        daily=metrics.daily_series(campaign_daily),
        per_app=metrics.per_app(campaign_daily) if len(apps_in_scope) > 1 else None,
        top_keywords=metrics.top_keywords(analysis["keywords"]),
        wasted=metrics.wasted_spend(analysis["keywords"]),
    )

    out_path = output or Path(f"asa-analysis-{file_scope}-{today:%Y-%m-%d}.xlsx")
    notes = {key: lv.notes for key, lv in result.levels.items()}
    write_workbook(
        out_path, summary=summary, analysis=analysis, daily=daily_frames,
        notes=notes, currency_format=fmt,
    )

    symbol = _currency_symbol(fmt)
    spend = current_kpis["spend"]
    installs = int(current_kpis["installs"])
    cpa = current_kpis["cpa"]
    cpa_text = f"{symbol}{cpa:,.2f} CPA" if cpa == cpa else "— CPA"
    typer.echo(str(out_path))
    typer.echo(
        f"{symbol}{spend:,.0f} spend · {installs} installs · {cpa_text} "
        f"over {day_count} days"
    )
```

- [ ] **Step 4: Run the new tests, then the whole suite**

Run: `uv run pytest tests/unit/cli/test_cli.py -v` → all pass.
Run: `uv run pytest` → everything passes (Task 1's `test_help_runs` still green).

- [ ] **Step 5: Lint & type-check, then commit**

Run: `uv run ruff check asa_api_client tests && uv run mypy asa_api_client`

```bash
git add asa_api_client/cli/analyze.py tests/unit/cli/test_cli.py
git commit -m "✨ Wire up asa analyze command"
```

---

### Task 7: Documentation

**Files:**
- Create: `docs/guide/cli.md`
- Modify: `mkdocs.yml` (nav: add `CLI: guide/cli.md` after `Async Usage: guide/async.md`)
- Modify: `README.md` (add a short "CLI" section after the existing usage/features content)

**Interfaces:**
- Consumes: the shipped command surface from Task 6.
- Produces: user-facing docs; no code.

- [ ] **Step 1: Write `docs/guide/cli.md`**

```markdown
# CLI

`asa-api-client` ships an optional command-line interface for generating
a formatted Excel performance analysis workbook.

## Installation

```bash
pip install "asa-api-client[cli]"
```

## Credentials

The CLI uses the same environment-based configuration as
[`AppleSearchAdsClient.from_env`](../getting-started/authentication.md):
`ASA_CLIENT_ID`, `ASA_TEAM_ID`, `ASA_KEY_ID`, `ASA_ORG_ID`, and
`ASA_PRIVATE_KEY` or `ASA_PRIVATE_KEY_PATH` (a `.env` file works too).

## `asa analyze`

```bash
# Whole org, last 30 full days
asa analyze

# One app, last 90 days, custom output path
asa analyze --app 123456789 --period 90d --output my-report.xlsx

# Explicit range
asa analyze --from 2026-01-01 --to 2026-03-31
```

| Option | Description |
| ------ | ----------- |
| `--app, -a` | Adam ID to scope to one app; repeatable. Omit for all apps in the org. |
| `--period, -p` | Preset range of full days ending yesterday: `30d` (default), `90d`, or `365d`. |
| `--from` / `--to` | Explicit date range (`YYYY-MM-DD`); overrides `--period`. |
| `--output, -o` | Output file. Defaults to `asa-analysis-<app|org>-<YYYY-MM-DD>.xlsx`. |
| `--timezone` | Reporting timezone. Default `UTC`. |
| `--currency-format` | Excel number format for money cells. Default inferred from the org's currency. |

The workbook contains a `Summary` sheet (headline KPIs with
prior-period deltas, a daily spend/installs chart, top keywords, and
wasted-spend callouts), one formatted analysis sheet per reporting
level (campaigns, ad groups, keywords, search terms, ads), and raw
daily data sheets at the back for pivoting.

Search term reports are only served by Apple for the trailing 90 days;
longer runs still succeed and the search-term sheets carry a note.
```

- [ ] **Step 2: Update `mkdocs.yml` nav**

In the `User Guide` section, after `- Async Usage: guide/async.md`, add:

```yaml
    - CLI: guide/cli.md
```

- [ ] **Step 3: Update `README.md`**

Add a `## CLI` section (near the other usage sections) with the install
command, one `asa analyze` example, and a one-line description of the
workbook — condensed from the guide page above.

- [ ] **Step 4: Verify docs build**

Run: `uv run mkdocs build --strict`
Expected: build succeeds with no nav warnings. (If `--strict` flags pre-existing unrelated warnings, note them and build without `--strict`.)

- [ ] **Step 5: Commit**

```bash
git add docs/guide/cli.md mkdocs.yml README.md
git commit -m "📝 Document the asa analyze CLI"
```

---

## Final verification (after all tasks)

- `uv run pytest` — full suite green.
- `uv run mypy asa_api_client` — clean.
- `uv run ruff check asa_api_client tests` — clean.
- `uv run asa analyze --help` — renders option help without credentials.
