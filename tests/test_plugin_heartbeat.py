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
                        "frq": 5000,
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
    plugin._state.config = Config("20000002", "k", "English", 20, 120, 25.0, 0)
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


def test_live_beat_updates_power_keeps_energy():
    _setup(counter_every=2, last_date="2026-07-01")
    plugin.onHeartbeat()  # beat 1 -> live (1 % 2 != 0)
    did = device_id(0)
    solar = Domoticz.Devices[did].Units[1]
    assert solar.sValue.startswith("1000;")  # power set; energy from prev (0)
