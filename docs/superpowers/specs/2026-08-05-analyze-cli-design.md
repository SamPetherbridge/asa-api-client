# `asa analyze` CLI — Performance Analysis Workbook

**Date:** 2026-08-05
**Status:** Approved

## Purpose

Add a proper console command to `asa-api-client` that generates a fully formatted
Excel workbook reviewing Apple Search Ads performance for an app (or the whole
org) at every reporting level: campaign → ad group → keyword → search term → ad.
The document is an opinionated analysis — headline KPIs, prior-period deltas,
highlighting of over/under-performers — backed by raw daily data sheets for
pivoting.

## Command surface

Console script `asa` (Typer app), installed via `[project.scripts]`, with one
subcommand:

```
asa analyze [OPTIONS]

  --app, -a INTEGER       Adam ID to scope to one app; repeatable (-a 123 -a 456).
                          Omit for all apps in the org.
  --period, -p [30d|90d|365d]
                          Preset range of full days ending yesterday. Default: 30d.
  --from DATE / --to DATE Explicit range; overrides --period.
  --output, -o PATH       Output file. Default: asa-analysis-<app|org>-<YYYY-MM-DD>.xlsx
  --timezone TEXT         Reporting timezone. Default: UTC.
  --currency-format TEXT  Currency display format. Default inferred from org.
```

- Credentials come from the existing `AppleSearchAdsClient.from_env()` path
  (env vars / `.env`); no auth flags.
- Rich progress display while fetching: one line per level, ticking per
  completed request/chunk.
- On success: print output path plus a one-line headline
  (e.g. `$4,231 spend · 312 installs · $13.56 CPA over 30 days`).
- If the `cli` extra's dependencies are missing, `asa` exits with:
  `Install the CLI extra: pip install "asa-api-client[cli]"` — never a traceback.

## Data pipeline

1. **Scope resolution.** `client.campaigns.list()` once → map
   `campaignId → (adamId, app name)` → filter to `--app` IDs if given.
2. **Fetch five levels** — campaigns, ad groups, keywords, search terms, ads —
   using the existing `reports.*_async()` methods with bounded concurrency
   (semaphore, ~5 in flight). Keyword/search-term reports are per-campaign
   requests, so large accounts × long ranges mean many calls.
3. **Granularity & chunking.** All data fetched at DAILY granularity. The API
   caps DAILY requests at 90 days per request, so longer ranges are split into
   ≤90-day windows and rows stitched. Search terms are only served for the
   trailing 90 days: on longer runs the search-term sheets cover the most
   recent 90 days and carry a visible note; the run does not fail.
4. **Prior-period comparison.** One extra campaign-level fetch for the
   preceding window of equal length. Campaign level only — it feeds the
   summary KPIs.
5. **Shaping.** Each response → `to_dataframe()`; chunks concatenated;
   campaign/ad-group/app names joined on; derived metrics computed in pandas:
   TTR (taps/impressions), CVR (installs/taps), avg CPT (spend/taps),
   CPA (spend/installs). Zero denominators render as "—".

## Workbook structure

Sheet order: `Summary` → `Campaigns` → `Ad Groups` → `Keywords` →
`Search Terms` → `Ads` → grey-tabbed `Daily · <Level>` sheets at the back.

### Summary sheet

- Title block: app/org name, period, generated timestamp, timezone.
- KPI band: Spend, Impressions, Taps, Installs, TTR, CVR, avg CPT, CPA — each
  with prior-period delta beneath (green/red arrows, direction-aware: falling
  CPA is green).
- Embedded line chart: daily spend vs installs across the period.
- Per-app breakdown table when the run covers multiple apps.
- Callout tables: *Top 5 keywords by installs* and *Wasted spend* (keywords
  with spend > 0 and installs = 0, sorted by spend desc).

### Analysis sheets (one per level)

One row per entity, aggregated over the period.

- Columns: names/IDs, status, then metrics incl. derived metrics.
- Formatting: bold header on dark fill, freeze panes, autofilter, set column
  widths, currency/percent/integer number formats defined once and reused.
- Conditional formatting:
  - Data bars on Spend.
  - Red row-tint: spend > 0 and installs = 0.
  - Amber CPA cell: CPA > 1.5× account average.
  - Green CPA cell: CPA < 0.75× account average with ≥ 5 installs.

### Daily sheets

Raw daily rows per level, number-formatted, autofilter, no highlighting —
pivot-table fuel. Search-term daily sheet notes the 90-day lookback on longer
runs.

## Architecture

```
asa_api_client/cli/
    __init__.py    # main() entry point: lazy-import guard → typer app
    analyze.py     # the analyze command: options, date resolution, orchestration
    fetch.py       # async fetching: chunk windows, semaphore, prior period
    metrics.py     # pure pandas: aggregation + derived metrics
    workbook.py    # xlsxwriter rendering: formats, sheets, chart, conditionals
```

- `pyproject.toml`: add `[project.scripts] asa = "asa_api_client.cli:main"` and
  optional extra `cli = ["typer", "rich", "pandas", "xlsxwriter"]`.
- `metrics.py` and `fetch.py` contain no Excel/terminal concerns; `workbook.py`
  takes DataFrames in and writes a file, knowing nothing about the API.

## Error handling

- Missing credentials → existing settings validation error, presented as a
  clean one-liner.
- Transient API failures retry, respecting the client's rate-limit handling.
- A whole level failing to fetch aborts the run with context.
- Individual per-campaign chunks failing after retries: warn on stderr, note on
  the affected sheet, continue — a 95%-complete review beats a dead run.
- `--from`/`--to` validated (order, not future, within API lookback) before any
  network call.

## Testing

- Existing `pytest-httpx` mock pattern.
- Unit tests: chunk-window math, metric derivation (pure functions).
- CLI wiring: `typer.testing.CliRunner` with mocked transport.
- Workbook: write to temp file, read back with `openpyxl` (added to dev deps);
  assert sheet names, header cells, KPI values, number formats.
- Strict mypy + ruff, as everywhere else in the repo.

## Documentation

- New `docs/guide/cli.md` page documenting installation of the extra and the
  `analyze` command.

## Out of scope

- Additional subcommands (`asa export`, etc.) — the subcommand structure
  leaves room, nothing else ships now.
- Non-Excel output formats (CSV, Google Sheets).
- Scheduling/automation of report generation.
