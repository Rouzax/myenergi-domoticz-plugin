"""Pure parsing, discovery, and conversion for myenergi cloud data."""

_JOULES_PER_WH = 3600.0
_JOULES_PER_KWH = 3_600_000.0


def joules_to_wh(j: float) -> float:
    return j / _JOULES_PER_WH


def joules_to_kwh(j: float) -> float:
    return j / _JOULES_PER_KWH


def deci_volts_to_v(v: int) -> float:
    return round(v / 10.0, 1)


def centi_hz_to_hz(f: int) -> float:
    return round(f / 100.0, 2)
