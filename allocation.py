"""Stable Unit-block allocation within the Domoticz 1..255 ceiling."""

BLOCK_SIZE = 25
MAX_UNIT = 255


class UnitExhaustionError(Exception):
    pass


def allocate_blocks(serials, existing):
    result = dict(existing)
    used = set(existing.values())
    for serial in sorted(s for s in serials if s not in result):
        base = 1
        while base in used:
            base += BLOCK_SIZE
        if base + BLOCK_SIZE - 1 > MAX_UNIT:
            raise UnitExhaustionError(
                f"no free Unit block for serial {serial}; 1..{MAX_UNIT} exhausted"
            )
        result[serial] = base
        used.add(base)
    return result
