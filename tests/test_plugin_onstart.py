import Domoticz

import control
import plugin
from domoticz_api import device_id


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
        "CounterEvery": "6",
        "MaxSystemKW": "25",
        "DebugLevel": "0",
    }
    plugin.onStart()
    assert Domoticz._heartbeat == 20
    assert plugin._state.config.hub_serial == "20000002"
    assert plugin._state.counter_every == 6
    assert plugin._state.beat == 0
    assert Domoticz._debugging == 0  # DebugLevel None -> Debugging off


def test_onstart_verbose_enables_debugging(monkeypatch):
    """DebugLevel Verbose (2) turns on Domoticz.Debugging(1) = all."""

    class _FakeClient:
        def __init__(self, serial, api_key):
            self.base_url = "https://s18.myenergi.net"

        def discover_from_director(self):
            return "s18.myenergi.net"

    monkeypatch.setattr(plugin, "MyEnergiClient", _FakeClient)
    plugin.Parameters = {
        "Username": "20000002",
        "ApiKey": "k",
        "Language": "English",
        "LivePoll": "20",
        "CounterEvery": "6",
        "MaxSystemKW": "25",
        "DebugLevel": "2",
    }
    plugin.onStart()
    assert Domoticz._debugging == 1


def test_onstart_passes_gates_to_client(monkeypatch):
    """AllowControl flows into the client's write gate."""
    captured = {}

    class _FakeClient:
        def __init__(self, serial, api_key, writes_enabled=False, **kw):
            captured["writes"] = writes_enabled

        def discover_from_director(self):
            return "s18.myenergi.net"

        @property
        def base_url(self):
            return "https://s18.myenergi.net"

    monkeypatch.setattr(plugin, "MyEnergiClient", _FakeClient)
    plugin.Parameters = {
        "Username": "10000001",
        "ApiKey": "k",
        "AllowControl": "true",
    }
    plugin.onStart()
    assert captured["writes"] is True


def test_onstart_discovery_failure_sets_discovery_failing(monkeypatch):
    """A discovery failure during onStart must mark discovery_failing so a later
    heartbeat self-heal logs the matching 'recovered' transition."""

    class _FailingClient:
        def __init__(self, serial, api_key, **kw):
            pass

        def discover_from_director(self):
            raise ConnectionError("network unreachable")

    monkeypatch.setattr(plugin, "MyEnergiClient", _FailingClient)
    plugin.Parameters = {
        "Username": "20000002",
        "ApiKey": "k",
    }
    plugin.onStart()
    assert plugin._state.discovery_failing is True


class _ReconcileClient:
    def __init__(self, serial, api_key, writes_enabled=False, **kw):
        self.base_url = "https://s18.myenergi.net"

    def discover_from_director(self):
        return "s18.myenergi.net"

    def fetch_status(self):
        return [
            {
                "zappi": [
                    {
                        "sno": 20000002,
                        "zmo": 1,
                        "mgl": 50,
                        "lck": 16,
                        "gen": 0,
                        "grd": 0,
                        "div": 0,
                        "pst": "A",
                        "sta": 1,
                    }
                ]
            }
        ]


def _params(allow):
    return {"Username": "20000002", "ApiKey": "k", "AllowControl": allow}


def test_onstart_creates_control_devices_when_enabled(monkeypatch):
    monkeypatch.setattr(plugin, "MyEnergiClient", _ReconcileClient)
    plugin.Parameters = _params("true")
    plugin.onStart()
    units = Domoticz.Devices[device_id(0)].Units
    assert control.UNIT_MODE in units and units[control.UNIT_MODE].Used == 1
    assert control.UNIT_BOOST in units and control.UNIT_MIN_GREEN in units
    # unit 7 (energy Zappi Mode text) is not created on onStart, so the hide defers
    assert plugin._state.mode_text_hidden is False


def test_onstart_hides_mode_text_when_unit7_present(monkeypatch):
    monkeypatch.setattr(plugin, "MyEnergiClient", _ReconcileClient)
    plugin.Parameters = _params("true")
    # Simulate a restart where the energy Zappi Mode text device already exists and is
    # visible. Unit(...).Create() auto-creates the device in the stub.
    did = device_id(0)
    Domoticz.Unit(Name="Zappi Mode", DeviceID=did, Unit=7, TypeName="Text", Used=1).Create()
    plugin.onStart()
    assert Domoticz.Devices[did].Units[7].Used == 0
    assert plugin._state.mode_text_hidden is True


def test_onstart_hides_control_when_disabled(monkeypatch):
    monkeypatch.setattr(plugin, "MyEnergiClient", _ReconcileClient)
    plugin.Parameters = _params("false")
    # Model a restart where control was ON in the prior run: the control devices
    # exist and are visible, and control_shown was persisted True. plan_control_updates
    # emits nothing while disabled, so onStart must hide them once on the disable
    # transition (control_shown True -> deactivate -> False).
    import domoticz_api
    from persistence import PluginState

    did = device_id(0)
    for u in plugin.CONTROL_UNITS:
        Domoticz.Unit(Name="x", DeviceID=did, Unit=u, TypeName="Selector Switch", Used=1).Create()
    domoticz_api.save_state(PluginState(control_shown=True))
    plugin.onStart()
    units = Domoticz.Devices[did].Units
    for u in plugin.CONTROL_UNITS:
        assert units[u].Used == 0


def test_onstart_fetch_status_failure_does_not_raise(monkeypatch):
    class _BadFetch(_ReconcileClient):
        def fetch_status(self):
            raise ConnectionError("boom")

    monkeypatch.setattr(plugin, "MyEnergiClient", _BadFetch)
    plugin.Parameters = _params("true")
    plugin.onStart()  # must not raise
    assert any("onStart control reconcile failed" in m for m in Domoticz._log)
