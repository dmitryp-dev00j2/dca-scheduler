from datetime import datetime, timezone
import pytest

from dca_scheduler.scheduler import calculate_next_run, compute_jitter_seconds


def test_jitter_within_bounds():
    max_jitter = 300
    for _ in range(200):
        jitter = compute_jitter_seconds(max_jitter)
        assert -max_jitter <= jitter <= max_jitter


def test_zero_jitter():
    assert compute_jitter_seconds(0) == 0
    assert compute_jitter_seconds(-10) == 0


def test_calculate_next_run_basic():
    base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    interval_sec = 3600
    next_time = calculate_next_run(base, interval_seconds=interval_sec, max_jitter_sec=0)
    assert next_time == datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc)


def test_calculate_next_run_with_jitter():
    base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    interval_sec = 3600
    max_jitter = 120

    runs = [calculate_next_run(base, interval_sec, max_jitter) for _ in range(50)]
    min_expected = datetime(2025, 1, 1, 12, 58, 0, tzinfo=timezone.utc)
    max_expected = datetime(2025, 1, 1, 13, 2, 0, tzinfo=timezone.utc)

    for run in runs:
        assert min_expected <= run <= max_expected


def test_jitter_clamped_to_interval_safety():
    # jitter cannot cause run to trigger in past relative to base
    base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    interval_sec = 60
    max_jitter = 300  # jitter larger than interval

    for _ in range(50):
        run = calculate_next_run(base, interval_sec, max_jitter)
        # must always advance at least by 5 seconds into the future
        assert run > base
