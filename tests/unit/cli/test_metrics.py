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
