"""Pure energy accumulation: clamps, seeding, rollover/backfill, home derivation."""

from datetime import date, timedelta


def lifetime_ceiling_wh(max_system_kw: float) -> float:
    """Absolute plausibility ceiling for a cumulative counter: ~10 years at full
    system power, in Wh. Used to reject only genuinely corrupt values, not to cap
    the per-refresh step."""
    return max_system_kw * 1000.0 * 24.0 * 3650.0


# myenergi re-reports a completed minute a few hundred J lower on a later fetch, so
# the re-summed whole-day total dips a fraction of a Wh below the banked counter. Hold
# such a dip (the counter is monotonic) but do not warn on it: below this threshold it
# is cloud re-aggregation noise, not a data fault. A real backslide clears the band.
COUNTER_DEADBAND_WH = 1.0


def clamp_counter(prev_wh, candidate_wh, ceiling_wh):
    # The refresh candidate is base + myenergi's authoritative whole-day sum, so it is
    # trusted: guard only against going backwards (monotonic) and against an absurd
    # absolute value (corrupt fetch). A large legitimate jump - a lagging counter
    # catching up after a mid-day install or an offline backfill - must be allowed,
    # otherwise the counter sticks below the truth forever.
    if candidate_wh < prev_wh:
        if prev_wh - candidate_wh < COUNTER_DEADBAND_WH:
            return prev_wh, None
        return prev_wh, f"decrease held: {candidate_wh:.4f} < {prev_wh:.4f}"
    if candidate_wh > ceiling_wh:
        return prev_wh, f"over ceiling held: {candidate_wh:.4f} > {ceiling_wh:.4f}"
    return candidate_wh, None


def seed_base_wh(svalue_wh, today_sum_wh, max_plausible_wh):
    if svalue_wh > max_plausible_wh:
        return None
    return max(0.0, svalue_wh - today_sum_wh)


def _parse(d: str) -> date:
    y, m, day = (int(p) for p in d.split("-"))
    return date(y, m, day)


def missing_dates(last_processed: str, today: str) -> "list[str]":
    start = _parse(last_processed)
    end = _parse(today)
    out = []
    cur = start + timedelta(days=1)
    while cur < end:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def fold_days(base_wh: float, day_sums_wh: "list[float]") -> float:
    return base_wh + sum(day_sums_wh)


def home_energy_wh(gep_wh, imp_wh, exp_wh, car_ev_wh) -> float:
    return max(0.0, gep_wh + imp_wh - exp_wh - car_ev_wh)
