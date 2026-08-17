"""The ``asa analyze`` command: options, orchestration, presentation."""

import asyncio
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskID, TextColumn
from xlsxwriter.exceptions import XlsxWriterException

from asa_api_client.cli import dates, fetch, metrics, popularity, v1_smoke
from asa_api_client.cli.v1_adapter import V1FetchAdapter
from asa_api_client.cli.workbook import SummaryData, write_workbook
from asa_api_client.client import AppleSearchAdsClient
from asa_api_client.exceptions import AppleSearchAdsError, ConfigurationError
from asa_api_client.v1.client import AppleAdsClient

app = typer.Typer(no_args_is_help=True, add_completion=False)
app.command("v1-smoke")(v1_smoke.command)
_err = Console(stderr=True)


@app.callback()
def _root() -> None:
    """Apple Search Ads analysis toolkit."""


class Period(StrEnum):
    """Preset reporting periods."""

    D30 = "30d"
    D90 = "90d"
    D365 = "365d"


class ApiVersion(StrEnum):
    """Selectable Apple Ads API backends."""

    V5 = "v5"
    V1 = "v1"


_CURRENCY_FORMATS = {
    "USD": "$#,##0.00",
    "AUD": "$#,##0.00",
    "CAD": "$#,##0.00",
    "NZD": "$#,##0.00",
    "EUR": "€#,##0.00",
    "GBP": "£#,##0.00",
    "JPY": "¥#,##0",
}


def _currency_format(code: str | None) -> str:
    """Map an ISO currency code to an Excel number format."""
    if code is None:
        return "$#,##0.00"
    return _CURRENCY_FORMATS.get(code, f'"{code} "#,##0.00')


def _currency_symbol(currency_format: str) -> str:
    """First non-format character of the currency format, for the headline."""
    head = currency_format[0]
    return head if head not in '#0["' else "$"


def _fail(message: str) -> "typer.Exit":
    """Print a clean one-line error and exit 1."""
    _err.print(f"[red]Error:[/red] {message}")
    return typer.Exit(code=1)


async def _fetch(
    client: fetch.FetchClient,
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
            client,
            meta,
            start,
            end,
            timezone=timezone,
            today=datetime.now(tz=UTC).date(),
            on_progress=on_progress,
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
    timezone: Annotated[str, typer.Option("--timezone", help="Reporting timezone.")] = "UTC",
    currency_format: Annotated[
        str | None,
        typer.Option("--currency-format", help="Excel number format for money."),
    ] = None,
    api_version: Annotated[
        ApiVersion,
        typer.Option("--api-version", help="Apple Ads API version to fetch with."),
    ] = ApiVersion.V5,
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

    client: AppleSearchAdsClient | V1FetchAdapter
    try:
        if api_version is ApiVersion.V1:
            client = V1FetchAdapter(AppleAdsClient.from_env())
        else:
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
        key: metrics.aggregate(daily_frames[key], metrics.LEVEL_KEYS[key]) for key in daily_frames
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
        period_label=f"{start} – {end} ({day_count} days)",  # noqa: RUF001
        timezone=timezone,
        generated_at=datetime.now(tz=UTC),
        kpis=current_kpis,
        prior_kpis=prior_kpis,
        daily=metrics.daily_series(campaign_daily),
        per_app=metrics.per_app(campaign_daily) if len(apps_in_scope) > 1 else None,
        top_keywords=metrics.top_keywords(analysis["keywords"]),
        wasted=metrics.wasted_spend(analysis["keywords"]),
    )

    # The popularity sheet is enrichment via the v1 insights API; it
    # must never break (or fail) an otherwise successful analyze run.
    try:
        popularity_frame, popularity_notes = popularity.build_popularity(result)
    except Exception as exc:  # nothing from this sheet may abort the workbook
        popularity_frame, popularity_notes = pd.DataFrame(), []
        _err.print(f"[yellow]Warning:[/yellow] Search Popularity sheet skipped: {exc}")

    out_path = output or Path(f"asa-analysis-{file_scope}-{today:%Y-%m-%d}.xlsx")
    notes = {key: lv.notes for key, lv in result.levels.items()}
    try:
        write_workbook(
            out_path,
            summary=summary,
            analysis=analysis,
            daily=daily_frames,
            notes=notes,
            currency_format=fmt,
            popularity=popularity_frame,
            popularity_notes=popularity_notes,
        )
    except (OSError, XlsxWriterException) as exc:
        raise _fail(f"Could not write {out_path}: {exc}") from exc

    symbol = _currency_symbol(fmt)
    spend = current_kpis["spend"]
    installs = int(current_kpis["installs"])
    cpa = current_kpis["cpa"]
    cpa_text = f"{symbol}{cpa:,.2f} CPA" if cpa == cpa else "— CPA"
    typer.echo(str(out_path))
    typer.echo(
        f"{symbol}{spend:,.0f} spend · {installs} installs · {cpa_text} over {day_count} days"
    )
