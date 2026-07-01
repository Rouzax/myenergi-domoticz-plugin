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
