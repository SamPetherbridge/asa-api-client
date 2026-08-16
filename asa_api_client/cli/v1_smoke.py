"""The ``asa v1-smoke`` command: a read-only live check of the v1 client.

Runs a fixed sequence of read-only calls against the Apple Ads Platform
API v1 and prints one Rich table row per step (status, latency, item
count or error summary). Feature-gated steps (reports, recommendations,
insights, change history) degrade to warnings; the command exits 0 iff
configuration, account discovery, and the campaigns query all succeed.

No write or mutating API call is ever made.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import typer
from rich.console import Console
from rich.table import Table

from asa_api_client.exceptions import AppleSearchAdsError, ConfigurationError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.ad_accounts import UserAcl
from asa_api_client.v1.models.campaigns import Campaign
from asa_api_client.v1.models.insights import (
    SearchTermPopularityGranularity,
    SearchTermPopularityQueryRequest,
    SearchTermPopularityTimeRange,
)
from asa_api_client.v1.models.recommendations import RecommendationQueryRequest
from asa_api_client.v1.models.reports import (
    AppsReportingRequest,
    ReportGranularity,
    ReportTimeRange,
)
from asa_api_client.v1.query import Query

_out = Console()
_err = Console(stderr=True)

_OK = "✅"
_WARN = "⚠️"
_FAIL = "❌"


@dataclass
class _StepRow:
    """One row of the smoke-test summary table.

    Attributes:
        name: The step name (e.g. ``"campaigns"``).
        status: Status marker: ``✅``, ``⚠️``, or ``❌``.
        latency_ms: Wall-clock duration of the step in milliseconds.
        detail: Item count or a one-line error summary.
    """

    name: str
    status: str
    latency_ms: int
    detail: str


def _fail(message: str) -> typer.Exit:
    """Print a clean one-line error and exit 1.

    Args:
        message: The error message to print to stderr.

    Returns:
        The ``typer.Exit`` to raise at the call site.
    """
    _err.print(f"[red]Error:[/red] {message}")
    return typer.Exit(code=1)


def _elapsed_ms(started: float) -> int:
    """Compute milliseconds elapsed since a ``perf_counter()`` mark.

    Args:
        started: The ``time.perf_counter()`` value at step start.

    Returns:
        The elapsed wall-clock time in whole milliseconds.
    """
    return round((time.perf_counter() - started) * 1000)


def _error_summary(exc: AppleSearchAdsError) -> str:
    """Build a one-line error summary for the table's detail column.

    Args:
        exc: The API error raised by the step.

    Returns:
        The exception class name and message on a single line.
    """
    return f"{type(exc).__name__}: {exc}"


def _append_count_row(rows: list[_StepRow], name: str, count: int, started: float) -> None:
    """Append a success row, downgraded to a warning when empty.

    Args:
        rows: The accumulated table rows.
        name: The step name.
        count: The number of items the step returned.
        started: The ``time.perf_counter()`` value at step start.
    """
    status = _OK if count else _WARN
    rows.append(_StepRow(name, status, _elapsed_ms(started), f"{count} items"))


def _run_gated(rows: list[_StepRow], name: str, fetch_count: Callable[[], int]) -> None:
    """Run a feature-gated read-only step; API errors become warnings.

    Args:
        rows: The accumulated table rows.
        name: The step name.
        fetch_count: Callable performing the read and returning the
            item count.
    """
    started = time.perf_counter()
    try:
        count = fetch_count()
    except AppleSearchAdsError as exc:
        rows.append(_StepRow(name, _WARN, _elapsed_ms(started), _error_summary(exc)))
    else:
        _append_count_row(rows, name, count, started)


def _render(rows: list[_StepRow]) -> None:
    """Print the summary table of all executed steps.

    Args:
        rows: The accumulated table rows.
    """
    if not rows:
        return
    table = Table(title="Apple Ads Platform API v1 smoke test")
    table.add_column("Step")
    table.add_column("Status")
    table.add_column("Latency", justify="right")
    table.add_column("Detail")
    for row in rows:
        table.add_row(row.name, row.status, f"{row.latency_ms} ms", row.detail)
    _out.print(table)


def _last_seven_days() -> tuple[date, date]:
    """Compute the last 7 full days, ending yesterday (UTC).

    Returns:
        The inclusive ``(start, end)`` date pair.
    """
    end = datetime.now(tz=UTC).date() - timedelta(days=1)
    return end - timedelta(days=6), end


def _step_me_accounts(client: AppleAdsClient, rows: list[_StepRow]) -> list[UserAcl]:
    """Run the ``me/accounts`` step: caller identity plus ACLs.

    Args:
        client: The v1 API client.
        rows: The accumulated table rows.

    Returns:
        The caller's ACL entries (one per accessible ad account).

    Raises:
        typer.Exit: With code 1 when either call fails.
    """
    started = time.perf_counter()
    try:
        me = client.ad_accounts.me()
        acls = client.acls.list()
    except AppleSearchAdsError as exc:
        rows.append(_StepRow("me/accounts", _FAIL, _elapsed_ms(started), _error_summary(exc)))
        raise typer.Exit(code=1) from exc
    detail = f"org {me.org_id}, {len(acls)} accounts"
    rows.append(_StepRow("me/accounts", _OK, _elapsed_ms(started), detail))
    return acls


def _resolve_account(client: AppleAdsClient, acls: list[UserAcl]) -> None:
    """Ensure the client has an ad account, auto-selecting when unambiguous.

    When ``ASA_AD_ACCOUNT_ID`` is unset and exactly one ad account is
    discoverable from the ACLs, it is selected (and printed). With none
    or several candidates the options are printed and the command exits.

    Args:
        client: The v1 API client.
        acls: The caller's ACL entries.

    Raises:
        typer.Exit: With code 1 when no account can be selected.
    """
    if client.ad_account_id is not None:
        return
    accounts = [
        acl.ad_account
        for acl in acls
        if acl.ad_account is not None and acl.ad_account.id is not None
    ]
    if len(accounts) == 1:
        client.ad_account_id = str(accounts[0].id)
        _out.print(f"Auto-selected ad account {client.ad_account_id} ({accounts[0].name})")
        return
    _err.print("[red]Error:[/red] ASA_AD_ACCOUNT_ID is not set and could not be auto-selected.")
    if accounts:
        _err.print("Accessible ad accounts:")
        for account in accounts:
            _err.print(f"  {account.id}  {account.name}")
    else:
        _err.print("No ad accounts are accessible to this API user.")
    raise typer.Exit(code=1)


def _step_campaigns(client: AppleAdsClient, rows: list[_StepRow]) -> list[Campaign]:
    """Run the ``campaigns`` step: first page of campaigns.

    Args:
        client: The v1 API client.
        rows: The accumulated table rows.

    Returns:
        The campaigns on the first page.

    Raises:
        typer.Exit: With code 1 when the query fails.
    """
    started = time.perf_counter()
    try:
        page = client.campaigns.query(Query().page(size=10, fetch_total_count=True))
    except AppleSearchAdsError as exc:
        rows.append(_StepRow("campaigns", _FAIL, _elapsed_ms(started), _error_summary(exc)))
        raise typer.Exit(code=1) from exc
    total = page.pagination.total_count if page.pagination is not None else None
    detail = f"{len(page)} items" if total is None else f"{len(page)} of {total} items"
    rows.append(_StepRow("campaigns", _OK if len(page) else _WARN, _elapsed_ms(started), detail))
    return page.result


def _report_count(client: AppleAdsClient, start: date, end: date) -> int:
    """Run a daily campaign-level report and count its rows.

    Args:
        client: The v1 API client.
        start: Inclusive report start date.
        end: Inclusive report end date.

    Returns:
        The number of report rows returned.
    """
    request = AppsReportingRequest(
        time_range=ReportTimeRange(start=start, end=end, granularity=ReportGranularity.DAILY)
    )
    response = client.reports.campaigns(request)
    if response.result is None or response.result.rows is None:
        return 0
    return len(response.result.rows)


def _step_recommendations(
    client: AppleAdsClient, campaigns: list[Campaign], rows: list[_StepRow]
) -> None:
    """Run the ``recommendations`` step for the first promoted object.

    The recommendations query API requires ``promotedObjectId`` and
    ``promotedObjectType`` filters, so the step derives them from the
    campaigns page and is skipped (with a warning) when no campaign
    carries a promoted object.

    Args:
        client: The v1 API client.
        campaigns: The campaigns from the previous step.
        rows: The accumulated table rows.
    """
    target = next(
        (c for c in campaigns if c.promoted_object_id and c.promoted_object_type is not None),
        None,
    )
    if target is None or target.promoted_object_id is None or target.promoted_object_type is None:
        rows.append(_StepRow("recommendations", _WARN, 0, "skipped: no promoted object found"))
        return
    query = RecommendationQueryRequest.for_promoted_object(
        target.promoted_object_id, target.promoted_object_type.value
    )
    _run_gated(
        rows,
        "recommendations",
        lambda: len(client.recommendations.query_target_cpas(query)),
    )


def _popularity_count(client: AppleAdsClient, start: date, end: date) -> int:
    """Query search term popularity for a date window and count rows.

    Args:
        client: The v1 API client.
        start: Inclusive window start date.
        end: Inclusive window end date.

    Returns:
        The number of popularity rows returned.
    """
    # Weekly popularity windows must start on a Sunday; align the
    # requested window to the last complete Sun-Sat week before it.
    del start  # the aligned week is derived from the window end alone
    last_saturday = end - timedelta(days=(end.weekday() + 2) % 7 or 7)
    last_sunday = last_saturday - timedelta(days=6)
    request = SearchTermPopularityQueryRequest(
        time_range=SearchTermPopularityTimeRange(
            start=last_sunday,
            end=last_saturday,
            granularity=SearchTermPopularityGranularity.WEEKLY_SUN_SAT,
        )
    )
    return len(client.insights.query_search_term_popularity(request))


def _change_history_count(client: AppleAdsClient, start: date, end: date) -> int:
    """Query the change history audit log for a date window.

    Args:
        client: The v1 API client.
        start: Inclusive window start date.
        end: Inclusive window end date.

    Returns:
        The number of audit summary rows returned.
    """
    # The live API requires an entityType filter on change-history queries.
    query = (
        Query()
        .where("entityType", "IN", ["Campaign"])
        .where("eventTime", "BETWEEN", [f"{start}T00:00:00", f"{end}T23:59:59"])
        .page(size=10)
    )
    return len(client.change_history.query(query))


def _smoke(client: AppleAdsClient, rows: list[_StepRow]) -> None:
    """Run every smoke step in order, appending one row per step.

    Args:
        client: The v1 API client.
        rows: The accumulated table rows.

    Raises:
        typer.Exit: With code 1 when a critical step (identity/ACLs,
            account selection, or campaigns) fails.
    """
    acls = _step_me_accounts(client, rows)
    _resolve_account(client, acls)
    campaigns = _step_campaigns(client, rows)
    start, end = _last_seven_days()
    _run_gated(rows, "campaign report", lambda: _report_count(client, start, end))
    _step_recommendations(client, campaigns, rows)
    _run_gated(rows, "search term popularity", lambda: _popularity_count(client, start, end))
    _run_gated(rows, "change history", lambda: _change_history_count(client, start, end))


def command() -> None:
    """Run a read-only smoke test against the live Apple Ads Platform API v1.

    Builds a client from ``ASA_*`` environment variables, then runs:
    identity/ACL discovery (auto-selecting the ad account when exactly
    one is accessible), a campaigns query, a 7-day daily campaign
    report, a Target CPA recommendations query, a search term
    popularity query, and a change history query. Each step prints a
    table row with status, latency, and item count or error summary.

    Feature-gated steps degrade to ``⚠️`` on API errors; exit code is 0
    iff configuration, account discovery, and campaigns all succeed.

    Raises:
        typer.Exit: With code 1 on configuration or critical failures.
    """
    try:
        client = AppleAdsClient.from_env()
    except ConfigurationError as exc:
        raise _fail(str(exc)) from exc

    rows: list[_StepRow] = []
    try:
        _smoke(client, rows)
    finally:
        _render(rows)
        client.close()


# Module-local app so tests can drive the command in isolation. The real
# CLI registers it with: app.command("v1-smoke")(v1_smoke.command)
app = typer.Typer(add_completion=False)
app.command("v1-smoke")(command)
