import json
from pathlib import Path

from model import jday_date, joules_to_kwh, parse_jday

FIX = Path(__file__).parent / "fixtures" / "jday.json"


def _payload():
    return json.loads(FIX.read_text())


def test_parse_jday_sums_energy_fields_only():
    sums = parse_jday(_payload())
    assert sums["imp"] == 3_600_000
    assert sums["gep"] == 7_200_000
    assert sums["exp"] == 1_800_000
    assert sums["pect1"] == 600_000
    assert "frq" not in sums and "v1" not in sums
    assert joules_to_kwh(sums["gep"]) == 2.0


def test_jday_date():
    assert jday_date(_payload()) == "2026-06-30"


def test_parse_jday_caps_rows():
    rows = [{"yr": 2026, "mon": 6, "dom": 30, "imp": 1000} for _ in range(10)]
    sums = parse_jday({"Ux": rows}, max_rows=3)
    assert sums["imp"] == 3000  # only first 3 rows summed


def test_parse_jday_sums_ev_diverted_and_boosted():
    payload = {
        "Ux": [
            {
                "yr": 2026,
                "mon": 7,
                "dom": 1,
                "h1d": 100,
                "h2d": 100,
                "h3d": 100,
                "h1b": 10,
                "h2b": 10,
                "h3b": 10,
                "imp": 5,
            },
        ]
    }
    sums = parse_jday(payload)
    assert sums["h1d"] == 100 and sums["h3d"] == 100
    assert sums["h1b"] == 10 and sums["h3b"] == 10
    ev_joules = sum(sums[k] for k in ("h1d", "h2d", "h3d", "h1b", "h2b", "h3b"))
    assert ev_joules == 330
