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
        1,
        0,
        last_row,
        n_cols - 1,
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
            1,
            cpa_idx,
            last_row,
            cpa_idx,
            {
                "type": "formula",
                "criteria": f"=AND(ISNUMBER(${cpa_c}2),${cpa_c}2>{cpa_benchmark * 1.5})",
                "format": amber,
            },
        )
        ws.conditional_format(
            1,
            cpa_idx,
            last_row,
            cpa_idx,
            {
                "type": "formula",
                "criteria": (
                    f"=AND(ISNUMBER(${cpa_c}2),${cpa_c}2<{cpa_benchmark * 0.75},${installs_c}2>=5)"
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
        return "–", "delta_flat"  # noqa: RUF001 - en dash for "no prior data"
    arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "▬")
    improved = (delta < 0) if key in LOWER_IS_BETTER else (delta > 0)
    fmt = "delta_flat" if delta == 0 else ("delta_good" if improved else "delta_bad")
    return f"{arrow} {abs(delta):.1%} vs prior", fmt


def _write_summary(book: Any, summary: SummaryData, fmts: dict[str, Format]) -> None:
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
    kpi_deltas = _deltas(summary.kpis, summary.prior_kpis) if summary.prior_kpis else {}
    for idx, (label, key, kind) in enumerate(KPI_SPEC):
        ws.write_string(3, idx, label, fmts["kpi_label"])
        _write_value(ws, 4, idx, summary.kpis.get(key), fmts[kpi_fmt[kind]], fmts["dash"])
        text, fmt_key = _delta_cell(key, kpi_deltas.get(key))
        ws.write_string(5, idx, text, fmts[fmt_key])

    chart_ws = book.add_worksheet("Chart Data")
    chart_ws.write_row(0, 0, ["date", "spend", "installs"])
    for r, (_, daily_row) in enumerate(summary.daily.iterrows(), start=1):
        chart_ws.write_string(r, 0, str(daily_row["date"]))
        chart_ws.write_number(r, 1, float(daily_row["spend"]))
        chart_ws.write_number(r, 2, float(daily_row["installs"]))
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

    row = 25  # clear of the chart, which spans roughly rows 8-24
    ws.write_string(row, 0, "Top 5 keywords by installs", fmts["callout_header"])
    top_last = _write_table(
        ws,
        summary.top_keywords,
        _CALLOUT_SPEC,
        fmts,
        start_row=row + 1,
        autofilter=False,
        freeze=False,
    )
    ws.write_string(row, 5, "Wasted spend", fmts["callout_header"])
    wasted_spec = [(c, h, k) for c, h, k in _CALLOUT_SPEC if c != "cpa"]
    for col_idx, (_, header, _kind) in enumerate(wasted_spec):
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
            ws,
            summary.per_app,
            _PER_APP_SPEC,
            fmts,
            start_row=app_row + 1,
            autofilter=False,
            freeze=False,
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
                book,
                label,
                analysis.get(key, pd.DataFrame()),
                ANALYSIS_COLUMNS[key],
                fmts,
                cpa_benchmark,
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
