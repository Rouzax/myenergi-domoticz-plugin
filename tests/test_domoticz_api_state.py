from domoticz_api import apply_updates, device_id, load_state, read_prev_counters, save_state
from persistence import PluginState
from planner import DeviceUpdate


def test_read_prev_counters_parses_energy():
    did = device_id(7)
    update = DeviceUpdate(1, "kWh", {"EnergyMeterMode": "0"}, "S", 0, "250;1234.5000")
    apply_updates(did, [update], {})
    assert read_prev_counters(did, [1, 2]) == {1: 1234.5, 2: 0.0}  # unit 2 missing -> 0.0


def test_state_roundtrip_via_configuration():
    save_state(PluginState(base_wh={"1": 42.0}, last_processed_date="2026-07-01"))
    restored = load_state()
    assert restored.base_wh == {"1": 42.0}
    assert restored.last_processed_date == "2026-07-01"
