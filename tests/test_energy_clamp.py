from energy import clamp_counter, lifetime_ceiling_wh, seed_base_wh

CEILING = lifetime_ceiling_wh(25.0)  # ~2.19e9 Wh


def test_clamp_accepts_normal_increase():
    counter, warn = clamp_counter(prev_wh=1000.0, candidate_wh=1050.0, ceiling_wh=CEILING)
    assert counter == 1050.0 and warn is None


def test_clamp_holds_on_decrease():
    counter, warn = clamp_counter(prev_wh=1000.0, candidate_wh=990.0, ceiling_wh=CEILING)
    assert counter == 1000.0
    assert warn is not None and "decrease" in warn


def test_clamp_holds_subwh_jitter_silently():
    # myenergi re-reports a completed minute a few hundred J lower, so the re-summed
    # day total dips a fraction of a Wh below the banked counter. Hold it (never go
    # backwards) but do NOT warn: it is cloud re-aggregation noise, not a data fault.
    counter, warn = clamp_counter(prev_wh=45071.44, candidate_wh=45071.38, ceiling_wh=CEILING)
    assert counter == 45071.44 and warn is None


def test_clamp_warns_on_decrease_at_or_above_deadband():
    # A drop of a full Wh or more is a real anomaly worth a line; the message carries
    # enough precision to be legible (not "X < X" after rounding).
    counter, warn = clamp_counter(prev_wh=1000.0, candidate_wh=998.5, ceiling_wh=CEILING)
    assert counter == 1000.0
    assert warn is not None and "998.5000" in warn and "1000.0000" in warn


def test_clamp_holds_over_absolute_ceiling():
    counter, warn = clamp_counter(prev_wh=1000.0, candidate_wh=1e12, ceiling_wh=CEILING)
    assert counter == 1000.0
    assert warn is not None and "ceiling" in warn


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
