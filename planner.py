"""Pure planning: aggregate energy, advance baselines, and build device updates."""

from model import joules_to_wh

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
