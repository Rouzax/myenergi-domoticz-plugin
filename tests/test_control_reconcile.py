from config import Config
from control import UNIT_LOCK_STATE, UNIT_MODE, plan_control_updates
from model import SystemStatus


def _cfg(allow_control=False, allow_lock=False):
    return Config(
        "10000001",
        "k",
        "English",
        20,
        6,
        25.0,
        0,
        allow_control=allow_control,
        allow_lock=allow_lock,
    )


def _status(zappi=None, lck=None):
    return SystemStatus(devices=[], zappi=zappi or {}, zappi_lck=lck)


def test_no_updates_when_gates_off():
    status = _status(zappi={"zmo": 1}, lck=16)
    assert plan_control_updates(status, _cfg()) == []


def test_mode_reconciled_when_control_on():
    status = _status(zappi={"zmo": 3})  # Eco+
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert updates[UNIT_MODE].nvalue == 20  # ZMO_TO_LEVEL[3]


def test_mode_absent_field_not_reconciled():
    status = _status(zappi={})  # no zmo
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert UNIT_MODE not in updates


def test_lock_state_emitted_when_lock_on():
    status = _status(zappi={"zmo": 1}, lck=1)
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_lock=True))}
    assert UNIT_LOCK_STATE in updates
    assert "Locked Now" in updates[UNIT_LOCK_STATE].svalue
