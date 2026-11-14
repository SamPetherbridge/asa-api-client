# Reports

Platform API v1 reporting covers all five App Store levels on `client.reports` (`campaigns`, `ad_groups`, `ads`, `keywords`, `search_terms`) and all five Apple Maps levels on `client.brand_reports`.

## Campaign Report

```python
from datetime import date

from asa_api_client.v1.models.reports import (
    AppsReportingRequest,
    ReportGranularity,
    ReportTimeRange,
    ReportTimeZone,
)

report = client.reports.campaigns(
    AppsReportingRequest(
        time_range=ReportTimeRange(
            start=date(2026, 8, 1),
            end=date(2026, 8, 31),
            time_zone=ReportTimeZone.UTC,
            granularity=ReportGranularity.DAILY,
        )
    )
)

if report.result and report.result.rows:
    for row in report.result.rows:
        if row.metadata and row.total_metrics:
            print(f"{row.metadata.name}: {row.total_metrics.impressions}")
```

## Entity-Level Reports

Filter by campaign, ad group, or storefront using `ReportFilter`:

```python
from asa_api_client.v1.models.reports import (
    AppsGroupBy,
    ReportFilter,
    ReportFilterOperator,
)

request = AppsReportingRequest(
    filters=[
        ReportFilter(
            field="campaignId",
            operator=ReportFilterOperator.IN,
            value=[str(campaign_id)],
        )
    ],
    group_by=[AppsGroupBy.COUNTRY_OR_REGION],
    time_range=ReportTimeRange(
        start=date(2026, 8, 1),
        end=date(2026, 8, 31),
    ),
)

ad_group_report = client.reports.ad_groups(request)
keyword_report = client.reports.keywords(request)
search_term_report = client.reports.search_terms(request)
ad_report = client.reports.ads(request)
```

## Granularities

- `HOURLY` — Hourly breakdown (supported on campaign, ad group, and keyword reports)
- `DAILY` — Daily breakdown
- `WEEKLY` — Weekly breakdown
- `MONTHLY` — Monthly breakdown

## DataFrame & Dictionary Export

Every report response provides `to_records()` (no extra dependencies) and `to_dataframe()` (requires `pip install "asa-api-client[pandas]"`). When `granular_metrics` are present, one row is emitted per granular period; otherwise `total_metrics` are used, and `Money` wrappers are unwrapped cleanly:

```python
df = report.to_dataframe()
print(df.head())
```
