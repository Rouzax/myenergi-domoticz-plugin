"""Pure energy accumulation: clamps, seeding, rollover/backfill, home derivation."""


def clamp_counter(prev_wh, candidate_wh, max_step_wh):
    if candidate_wh < prev_wh:
        return prev_wh, f"counter decrease held: {candidate_wh:.1f} < {prev_wh:.1f}"
    if candidate_wh > prev_wh + max_step_wh:
        return prev_wh, f"implausible counter step held: +{candidate_wh - prev_wh:.1f} Wh"
    return candidate_wh, None


def seed_base_wh(svalue_wh, today_sum_wh, max_plausible_wh):
    if svalue_wh > max_plausible_wh:
        return None
    return svalue_wh - today_sum_wh
