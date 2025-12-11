# Reports

Generate performance reports for campaigns, ad groups, and keywords.

## Campaign Report

```python
from datetime import date

report = client.reports.campaigns(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
)

for row in report.rows:
    print(f"{row.metadata.campaign_name}: {row.total.impressions} impressions")
```

## Ad Group Report

```python
report = client.reports.ad_groups(
    campaign_id,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
)
```

## Keyword Report

```python
report = client.reports.keywords(
    campaign_id,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
)
```

## Granularity

Reports support different time granularities:

```python
from asa_api_client.models import ReportGranularity

# Daily breakdown
report = client.reports.campaigns(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
    granularity=ReportGranularity.DAILY,
)
```

Options:

- `HOURLY` - Hourly breakdown
- `DAILY` - Daily breakdown
- `WEEKLY` - Weekly breakdown
- `MONTHLY` - Monthly breakdown

## DataFrame Export

With pandas installed, export to DataFrame:

```python
report = client.reports.campaigns(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
)

df = report.to_dataframe()
print(df.head())
```

## Available Metrics

Reports include:

- `impressions` - Number of ad impressions
- `taps` - Number of taps (clicks)
- `installs` - Number of app installs
- `new_downloads` - New users
- `redownloads` - Returning users
- `spend` - Amount spent
- `avg_cpa` - Average cost per acquisition
- `avg_cpt` - Average cost per tap
- `conversion_rate` - Install rate
