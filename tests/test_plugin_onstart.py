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
