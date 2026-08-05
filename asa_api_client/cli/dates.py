"""Pure date arithmetic for the analyze command.

Stdlib-only so it can be imported and unit-tested without the ``cli``
extra installed.
"""

from datetime import date, timedelta

PERIODS: dict[str, int] = {"30d": 30, "90d": 90, "365d": 365}
MAX_LOOKBACK_DAYS = 730
MAX_DAILY_WINDOW = 90
SEARCH_TERM_LOOKBACK = 90


def resolve_range(
    period: str,
    from_date: date | None,
    to_date: date | None,
    *,
    today: date,
) -> tuple[date, date]:
    """Resolve CLI options into an inclusive (start, end) date range.

    Args:
        period: Preset key from :data:`PERIODS` (used when no explicit dates).
        from_date: Explicit start date; overrides the preset.
        to_date: Explicit end date; defaults to yesterday when only
            ``from_date`` is given.
        today: The current date (injected for testability).

    Returns:
        Inclusive ``(start, end)`` dates.

    Raises:
        ValueError: If the preset is unknown, the range is reversed, ends
            in the future, or starts beyond the API lookback.
    """
    yesterday = today - timedelta(days=1)

    if from_date is None and to_date is None:
        if period not in PERIODS:
            raise ValueError(f"Unknown period {period!r}; choose one of {sorted(PERIODS)}")
        end = yesterday
        start = end - timedelta(days=PERIODS[period] - 1)
    else:
        if from_date is None:
            raise ValueError("--to requires --from")
        start = from_date
        end = to_date if to_date is not None else yesterday

    if start > end:
        raise ValueError(f"--from ({start}) must be before --to ({end})")
    if end > yesterday:
        raise ValueError(f"--to ({end}) must not be in the future; latest full day is {yesterday}")
    if start < today - timedelta(days=MAX_LOOKBACK_DAYS):
        raise ValueError(f"--from ({start}) is beyond the API lookback of {MAX_LOOKBACK_DAYS} days")

    return start, end


def chunk_windows(
    start: date, end: date, max_days: int = MAX_DAILY_WINDOW
) -> list[tuple[date, date]]:
    """Split an inclusive date range into contiguous windows of at most ``max_days``.

    Args:
        start: Range start (inclusive).
        end: Range end (inclusive).
        max_days: Maximum days per window (the API caps DAILY reports at 90).

    Returns:
        Ordered list of inclusive ``(start, end)`` windows tiling the range.
    """
    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=max_days - 1), end)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


def prior_window(start: date, end: date) -> tuple[date, date]:
    """Return the equal-length window immediately preceding ``start``-``end``.

    Args:
        start: Current range start (inclusive).
        end: Current range end (inclusive).

    Returns:
        Inclusive ``(start, end)`` of the preceding window.
    """
    length = (end - start).days
    prior_end = start - timedelta(days=1)
    return prior_end - timedelta(days=length), prior_end
