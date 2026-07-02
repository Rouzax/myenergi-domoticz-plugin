"""Pure control plane for the zappi: validators, command decision, reconciliation.

No Domoticz or HTTP imports. Every value that reaches a myenergi write URL is
validated and int-coerced here first; the client interpolates only validated ints.
"""

import math

UNIT_MODE = 12
UNIT_BOOST = 13
UNIT_BOOST_KWH = 14
UNIT_BOOST_TIME = 15
UNIT_MIN_GREEN = 16
UNIT_LOCK = 17
UNIT_LOCK_STATE = 18

MODE_LEVELS = {0: 1, 10: 2, 20: 3, 30: 4}
ZMO_TO_LEVEL = {1: 0, 2: 10, 3: 20, 4: 30}

MAX_KWH = 100
MAX_GREEN = 100

LCK_BITS = (
    (0, "Locked Now"),
    (1, "Lock when plugged in"),
    (2, "Lock when unplugged"),
    (3, "Charge when locked"),
    (4, "Charge session allowed"),
)


def _finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def validate_kwh(level) -> "int | None":
    if not _finite(level):
        return None
    kwh = int(round(float(level)))
    if kwh <= 0:
        return None
    return min(kwh, MAX_KWH)


def validate_hhmm(level) -> "str | None":
    if not _finite(level):
        return None
    hhmm = int(round(float(level)))
    if hhmm < 0:
        return None
    hh, mm = divmod(hhmm, 100)
    if hh >= 24 or mm >= 60:
        return None
    return f"{hhmm:04d}"


def clamp_min_green(level) -> "int | None":
    if not _finite(level):
        return None
    pct = int(round(float(level)))
    return max(0, min(pct, MAX_GREEN))


def decode_lck(lck: int) -> str:
    flags = [name for bit, name in LCK_BITS if lck & (1 << bit)]
    return f"{lck} ({', '.join(flags) if flags else 'none'})"
