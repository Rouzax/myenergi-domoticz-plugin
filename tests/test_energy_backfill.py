from energy import fold_days, missing_dates


def test_missing_dates_half_open_single_day():
    # normal midnight rollover: last=yesterday, today=today -> no full days between
    assert missing_dates("2026-06-30", "2026-07-01") == []


def test_missing_dates_multi_day_excludes_endpoints():
    assert missing_dates("2026-06-28", "2026-07-01") == ["2026-06-29", "2026-06-30"]


def test_missing_dates_same_day():
    assert missing_dates("2026-07-01", "2026-07-01") == []


def test_fold_days_adds_once():
    assert fold_days(1000.0, [500.0, 250.0]) == 1750.0
