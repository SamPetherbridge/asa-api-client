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
    agg_spec: dict[str, str] = dict.fromkeys(label_cols, "first")
    agg_spec |= dict.fromkeys(METRIC_SUMS, "sum")
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
