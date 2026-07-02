"""Pure planning: aggregate energy, advance baselines, and build device updates."""

from dataclasses import replace
from datetime import date, timedelta

from energy import seed_base_wh
from model import joules_to_wh
from persistence import PluginState

_EV_FIELDS = ("h1d", "h2d", "h3d", "h1b", "h2b", "h3b")


def aggregate_today_wh(day_sums: dict) -> dict:
    def j(field):
        return float(day_sums.get(field, 0) or 0)

    gep, imp, exp = j("gep"), j("imp"), j("exp")
    ev_j = sum(j(f) for f in _EV_FIELDS)
    home_j = max(0.0, gep + imp - exp - ev_j)
    return {
        "solar": joules_to_wh(gep),
        "ev": joules_to_wh(ev_j),
        "home": joules_to_wh(home_j),
    }


def _prev_date(iso: str) -> str:
    y, m, d = (int(p) for p in iso.split("-"))
    return (date(y, m, d) - timedelta(days=1)).isoformat()


def advance_baselines(
    state, backfill_day_sums, today_sums, prev_counters, agg_units, max_system_kw, hub_date
) -> PluginState:
    base = dict(state.base_wh)
    ceiling = max_system_kw * 1000.0 * 24.0 * 3650.0  # ~10y lifetime ceiling in Wh

    # Fold each fully-completed missing day once into the baseline.
    for day in backfill_day_sums:
        agg = aggregate_today_wh(day)
        for name, unit in agg_units.items():
            base[str(unit)] = base.get(str(unit), 0.0) + agg[name]

    # Seed any missing baseline from the device's current cumulative counter.
    today = aggregate_today_wh(today_sums)
    for name, unit in agg_units.items():
        key = str(unit)
        if key not in base:
            seeded = seed_base_wh(prev_counters.get(unit, 0.0), today[name], ceiling)
            base[key] = 0.0 if seeded is None else seeded

    # last_processed_date = the last COMPLETED day (the day BEFORE today). Today is
    # never folded here; it is added live in plan(). Using hub_date would drop today
    # from base at the next midnight and freeze the monotonic counter.
    return replace(state, base_wh=base, last_processed_date=_prev_date(hub_date))
