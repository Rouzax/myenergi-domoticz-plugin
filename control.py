"""Pure control plane for the zappi: validators, command decision, reconciliation.

No Domoticz or HTTP imports. Every value that reaches a myenergi write URL is
validated and int-coerced here first; the client interpolates only validated ints.
"""

import math
from dataclasses import dataclass

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


@dataclass
class WriteIntent:
    kind: str
    mode: "int | None" = None
    kwh: "int | None" = None
    hhmm: "str | None" = None
    pct: "int | None" = None
    locked: "bool | None" = None


def _sibling_float(siblings, unit):
    try:
        return float(str(siblings.get(unit, "")).strip())
    except (TypeError, ValueError):
        return None


def decide_write(unit, command, level, siblings) -> "WriteIntent | None":
    if unit == UNIT_MODE:
        zmo = MODE_LEVELS.get(int(level)) if command == "Set Level" else None
        return WriteIntent("mode", mode=zmo) if zmo is not None else None
    if unit == UNIT_BOOST:
        if command != "Set Level":
            return None
        lvl = int(level)
        if lvl == 0:
            return WriteIntent("boost_cancel")
        kwh = validate_kwh(_sibling_float(siblings, UNIT_BOOST_KWH))
        if kwh is None:
            return None
        if lvl == 10:
            return WriteIntent("boost_manual", kwh=kwh)
        if lvl == 20:
            hhmm = validate_hhmm(_sibling_float(siblings, UNIT_BOOST_TIME))
            return WriteIntent("boost_smart", kwh=kwh, hhmm=hhmm) if hhmm else None
        return None
    if unit == UNIT_MIN_GREEN:
        pct = clamp_min_green(level) if command == "Set Level" else None
        return WriteIntent("min_green", pct=pct) if pct is not None else None
    if unit == UNIT_LOCK:
        if command == "On":
            return WriteIntent("lock", locked=True)
        if command == "Off":
            return WriteIntent("lock", locked=False)
        return None
    return None
