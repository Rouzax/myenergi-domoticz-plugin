from energy import clamp_counter, lifetime_ceiling_wh, seed_base_wh

CEILING = lifetime_ceiling_wh(25.0)  # ~2.19e9 Wh


def test_clamp_accepts_normal_increase():
    counter, warn = clamp_counter(prev_wh=1000.0, candidate_wh=1050.0, ceiling_wh=CEILING)
    assert counter == 1050.0 and warn is None


def test_clamp_holds_on_decrease():
    counter, warn = clamp_counter(prev_wh=1000.0, candidate_wh=990.0, ceiling_wh=CEILING)
    assert counter == 1000.0 and "decrease" in warn


def test_clamp_holds_over_absolute_ceiling():
    counter, warn = clamp_counter(prev_wh=1000.0, candidate_wh=1e12, ceiling_wh=CEILING)
    assert counter == 1000.0 and "ceiling" in warn


def test_clamp_allows_large_catchup_under_ceiling():
    # A counter far below the authoritative base+today (stuck at 0 after a mid-day
    # install, or lagging after an offline backfill) must catch up in one step, not
    # stay held below the truth. This is the empty-kWh regression.
    counter, warn = clamp_counter(prev_wh=0.0, candidate_wh=37_915.0, ceiling_wh=CEILING)
    assert counter == 37_915.0 and warn is None


def test_seed_normal_and_implausible():
    assert seed_base_wh(svalue_wh=5000.0, today_sum_wh=200.0, max_plausible_wh=1e9) == 4800.0
    assert seed_base_wh(svalue_wh=1e12, today_sum_wh=200.0, max_plausible_wh=1e9) is None


def test_seed_mid_day_install_never_negative():
    # Fresh device created mid-day: svalue=0 but today already > 0. Base must not go negative.
    assert seed_base_wh(svalue_wh=0.0, today_sum_wh=1000.0, max_plausible_wh=1e9) == 0.0
