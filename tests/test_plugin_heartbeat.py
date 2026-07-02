import json

import Domoticz

import plugin
from config import Config
from domoticz_api import device_id


class _FakeClient:
    def __init__(self):
        self.base_url = "https://s18.myenergi.net"

    def fetch_status(self):
        return [
            {
                "zappi": [
                    {
                        "sno": 20000002,
                        "dat": "01-07-2026",
                        "gen": 1000,
                        "grd": 0,
                        "div": 0,
                        "che": 0.0,
                        "vol": 2300,
                        "frq": 49.98,
                        "zmo": 1,
                        "sta": 1,
                        "pst": "A",
                    }
                ]
            }
        ]

    def fetch_jday(self, letter, serial, iso_date):
        return {"U": [{"yr": 2026, "mon": 7, "dom": 1, "gep": 3_600_000}]}


def _setup(counter_every=1, last_date="2026-07-01"):
    plugin._state = plugin._PluginState()
    plugin._state.config = Config("20000002", "k", "English", 20, 6, 25.0, 0)
    plugin._state.client = _FakeClient()
    plugin._state.counter_every = counter_every
    import domoticz_api
    from persistence import PluginState

    domoticz_api.save_state(
        PluginState(base_wh={"1": 0.0, "2": 0.0, "3": 0.0}, last_processed_date=last_date)
    )


def test_refresh_beat_creates_devices_and_counter():
    _setup(counter_every=1)
    plugin.onHeartbeat()
    did = device_id(0)  # HardwareID defaults to 0 in the stub context
    solar = Domoticz.Devices[did].Units[1]
    # power 1000 W, energy = base 0 + today 1000 Wh
    assert solar.sValue == "1000;1000.0000"


def test_first_beat_is_always_a_refresh():
    # Item 3: beat 1 refreshes counters even when counter_every is large, so the
    # kWh devices carry a real total from the first heartbeat instead of 0.
    _setup(counter_every=99)
    plugin.onHeartbeat()  # beat 1
    did = device_id(0)
    solar = Domoticz.Devices[did].Units[1]
    assert solar.sValue == "1000;1000.0000"  # base 0 + today 1000 Wh (refresh path)


def test_live_beat_updates_power_keeps_energy():
    _setup(counter_every=2, last_date="2026-07-01")
    plugin._state.beat = 2  # next beat = 3 -> live (not first, 3 % 2 != 0)
    plugin.onHeartbeat()
    did = device_id(0)
    solar = Domoticz.Devices[did].Units[1]
    assert solar.sValue.startswith("1000;")  # power set; energy from prev (0)


def test_backfill_truncation_logs_and_caps_days():
    # last_date 29 days before hub date triggers the >14-day truncation path.
    # Hub date from _FakeClient is 01-07-2026 -> 2026-07-01.
    # missing_dates("2026-06-01", "2026-07-01") = 29 days -> truncated to 14.
    class _CountingClient(_FakeClient):
        def __init__(self):
            super().__init__()
            self.jday_call_count = 0

        def fetch_jday(self, letter, serial, iso_date):
            self.jday_call_count += 1
            return {"U": [{"yr": 2026, "mon": 6, "dom": 1, "gep": 0}]}

    _setup(counter_every=1, last_date="2026-06-01")
    counting = _CountingClient()
    plugin._state.client = counting

    plugin.onHeartbeat()

    assert any("truncated" in msg for msg in Domoticz._log)
    # 14 truncated backfill days + 1 today fetch
    assert counting.jday_call_count == 15


def test_live_beat_persists_auto_names_on_device_creation():
    # A live beat that creates all 9 devices must persist auto_names ownership
    # immediately so a crash cannot lose it before the next refresh writes state.
    _setup(counter_every=2, last_date="2026-07-01")
    plugin._state.beat = 2  # next beat = 3 -> live beat (not first, 3 % 2 != 0)
    plugin.onHeartbeat()

    state_json = Domoticz.Configuration().get("state", "")
    assert state_json, "state must be written after device creation"
    auto_names = json.loads(state_json).get("auto_names", {})
    assert set(auto_names.keys()) == {"1", "2", "3", "4", "5", "6", "7", "8", "9"}
    assert auto_names["1"] == "Solar Total"
    assert auto_names["4"] == "Zappi Mode"
