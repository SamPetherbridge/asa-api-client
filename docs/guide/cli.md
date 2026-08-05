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
