"""Tests for date-range resolution and window chunking."""

from datetime import date
from itertools import pairwise

import pytest

from asa_api_client.cli.dates import chunk_windows, prior_window, resolve_range

TODAY = date(2026, 8, 5)


class TestResolveRange:
    """resolve_range: presets, explicit ranges, validation."""

    def test_default_30d_ends_yesterday(self) -> None:
        """30d preset covers 30 full days ending yesterday."""
        start, end = resolve_range("30d", None, None, today=TODAY)
        assert end == date(2026, 8, 4)
        assert (end - start).days + 1 == 30

    def test_365d(self) -> None:
        """365d preset covers 365 full days."""
        start, end = resolve_range("365d", None, None, today=TODAY)
        assert (end - start).days + 1 == 365

    def test_explicit_overrides_period(self) -> None:
        """--from/--to win over --period."""
        start, end = resolve_range(
            "30d", date(2026, 1, 1), date(2026, 3, 31), today=TODAY
        )
        assert (start, end) == (date(2026, 1, 1), date(2026, 3, 31))

    def test_from_without_to_defaults_to_yesterday(self) -> None:
        """--from alone runs through yesterday."""
        start, end = resolve_range("30d", date(2026, 7, 1), None, today=TODAY)
        assert (start, end) == (date(2026, 7, 1), date(2026, 8, 4))

    def test_unknown_period_rejected(self) -> None:
        """Bad preset raises ValueError."""
        with pytest.raises(ValueError, match="period"):
            resolve_range("7d", None, None, today=TODAY)

    def test_from_after_to_rejected(self) -> None:
        """Reversed range raises ValueError."""
        with pytest.raises(ValueError, match="before"):
            resolve_range("30d", date(2026, 5, 2), date(2026, 5, 1), today=TODAY)

    def test_future_to_rejected(self) -> None:
        """--to today or later raises ValueError."""
        with pytest.raises(ValueError, match=r"future|yesterday"):
            resolve_range("30d", date(2026, 8, 1), date(2026, 8, 5), today=TODAY)

    def test_lookback_limit(self) -> None:
        """Ranges older than the API lookback raise ValueError."""
        with pytest.raises(ValueError, match="lookback"):
            resolve_range("30d", date(2020, 1, 1), date(2020, 2, 1), today=TODAY)


class TestChunkWindows:
    """chunk_windows: ≤90-day inclusive windows that tile the range."""

    def test_short_range_single_window(self) -> None:
        """A 30-day range is one window."""
        assert chunk_windows(date(2026, 7, 6), date(2026, 8, 4)) == [
            (date(2026, 7, 6), date(2026, 8, 4))
        ]

    def test_exact_90_days_single_window(self) -> None:
        """Exactly 90 days stays one window."""
        windows = chunk_windows(date(2026, 1, 1), date(2026, 3, 31))
        assert windows == [(date(2026, 1, 1), date(2026, 3, 31))]

    def test_long_range_tiles_without_gaps(self) -> None:
        """365 days splits into contiguous ≤90-day windows."""
        start, end = date(2025, 8, 5), date(2026, 8, 4)
        windows = chunk_windows(start, end)
        assert windows[0][0] == start
        assert windows[-1][1] == end
        assert all((w_end - w_start).days + 1 <= 90 for w_start, w_end in windows)
        for (_, prev_end), (next_start, _) in pairwise(windows):
            assert (next_start - prev_end).days == 1


class TestPriorWindow:
    """prior_window: equal-length window immediately before the range."""

    def test_adjacent_equal_length(self) -> None:
        """Prior window ends the day before start and has equal length."""
        p_start, p_end = prior_window(date(2026, 7, 6), date(2026, 8, 4))
        assert p_end == date(2026, 7, 5)
        assert (p_end - p_start).days == (date(2026, 8, 4) - date(2026, 7, 6)).days
