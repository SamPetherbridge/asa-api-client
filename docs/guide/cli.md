# CLI

`asa-api-client` ships an optional command-line toolkit for generating multi-sheet Excel performance and search-popularity workbooks and validating Platform API v1 credentials.

## Installation

```bash
pip install "asa-api-client[cli]"
```

## Credentials

The CLI reads the same environment variables (or `.env` file) as [`AppleAdsClient.from_env`](../getting-started/authentication.md):

- `ASA_CLIENT_ID`
- `ASA_TEAM_ID`
- `ASA_KEY_ID`
- `ASA_PRIVATE_KEY` or `ASA_PRIVATE_KEY_PATH`
- `ASA_AD_ACCOUNT_ID` (optional when a single ad account is accessible or when `ASA_ORG_ID` matches one of your `/v1/acls` accounts)

## `asa analyze`

```bash
# Whole account, last 30 full days (uses Platform API v1 by default)
asa analyze

# Scope to one app, last 90 days, custom output path
asa analyze --app 123456789 --period 90d --output my-report.xlsx

# Explicit date range
asa analyze --from 2026-08-01 --to 2026-08-31
```

| Option | Description |
| ------ | ----------- |
| `--app, -a` | Adam ID to scope to one app; repeatable. Omit for all apps in the account. |
| `--period, -p` | Preset range of full days ending yesterday: `30d` (default), `90d`, or `365d`. |
| `--from` / `--to` | Explicit date range (`YYYY-MM-DD`); overrides `--period`. |
| `--output, -o` | Output file. Defaults to `asa-analysis-<app|org>-<YYYY-MM-DD>.xlsx`. |
| `--timezone` | Reporting timezone (`UTC` or `ORTZ`). Default `UTC`. |
| `--currency-format` | Excel number format for money cells. Default inferred from the account currency. |
| `--api-version` | Apple Ads API backend: `v1` (default) or `v5` (legacy, sunset 2027-01-26). |

The generated workbook includes:

- **`Summary`** — Headline KPIs with prior-period deltas, daily spend/installs chart, top keywords, and wasted-spend callouts
- **Analysis tabs** — Formatted tables per reporting level (campaigns, ad groups, keywords, search terms, ads)
- **`Search Popularity`** — Latest storefront search-popularity scores (`1–100` and `1–5`) for your active keywords and search terms via the v1 Insights API
- **Raw daily tabs** — Normalized daily data sheets at the back for custom pivoting

Search term reports are served by Apple for the trailing 90 days; longer runs still succeed and annotate the search-term sheets.

## `asa v1-smoke`

Run a read-only smoke test against the live Platform API v1 to verify OAuth credentials, discover accessible ad accounts, and exercise core read/report endpoints:

```bash
asa v1-smoke
```
