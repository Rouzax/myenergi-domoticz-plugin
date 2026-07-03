"""Pure energy accumulation: clamps, seeding, rollover/backfill, home derivation."""

from datetime import date, timedelta


def clamp_counter(prev_wh, candidate_wh, max_step_wh):
    if candidate_wh < prev_wh:
        return prev_wh, f"counter decrease held: {candidate_wh:.1f} < {prev_wh:.1f}"
    if candidate_wh > prev_wh + max_step_wh:
        return prev_wh, f"implausible counter step held: +{candidate_wh - prev_wh:.1f} Wh"
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
