from planner import aggregate_today_wh


def test_aggregate_today_wh():
    day = {
        "gep": 3_600_000,
        "imp": 1_800_000,
        "exp": 900_000,
        "h1d": 300_000,
        "h2d": 300_000,
        "h3d": 300_000,  # 900k J diverted
        "h1b": 0,
        "h2b": 0,
        "h3b": 0,
    }
    agg = aggregate_today_wh(day)
    assert agg["solar"] == 1000.0  # 3.6e6 J -> 1000 Wh
    assert agg["ev"] == 250.0  # 900k J -> 250 Wh
    # home = gep + imp - exp - ev = 3.6e6 + 1.8e6 - 0.9e6 - 0.9e6 = 3.6e6 J -> 1000 Wh
    assert agg["home"] == 1000.0


def test_aggregate_home_never_negative_and_missing_fields():
    agg = aggregate_today_wh({"exp": 3_600_000})  # only export, no gen/imp
    assert agg["solar"] == 0.0 and agg["ev"] == 0.0
    assert agg["home"] == 0.0  # clamped >= 0
