import Domoticz

import plugin


def test_onstart_sets_heartbeat_and_config(monkeypatch):
    """Test that onStart parses config, sets heartbeat, and initializes state."""

    # Fake the client so no network happens.
    class _FakeClient:
        def __init__(self, serial, api_key):
            self.serial = serial

        def discover_from_director(self):
            return "s18.myenergi.net"

    monkeypatch.setattr(plugin, "MyEnergiClient", _FakeClient)
    plugin.Parameters = {
        "Username": "20000002",
        "ApiKey": "k",
        "Language": "English",
        "LivePoll": "20",
        "CounterPoll": "120",
        "MaxSystemKW": "25",
        "DebugLevel": "0",
    }
    plugin.onStart()
    assert Domoticz._heartbeat == 20
    assert plugin._state.config.hub_serial == "20000002"
    assert plugin._state.beat == 0
