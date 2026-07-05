import json
import time
import urllib.error

import Domoticz

import control
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
            },
            {
                "harvi": [
                    {
                        "sno": 19000001,
                        "ectt1": "Generation",
                        "ectp1": 100,
                        "ectt2": "Generation",
                        "ectp2": 100,
                        "ectt3": "Generation",
                        "ectp3": 50,
                    }
                ]
            },
        ]

    def fetch_jday(self, letter, serial, iso_date):
        return {"U": [{"yr": 2026, "mon": 7, "dom": 1, "gep": 3_600_000}]}


def _setup(counter_every=1, last_date="2026-07-01", allow_control=False):
    plugin._state = plugin._PluginState()
    plugin._state.config = Config(
        "20000002",
        "k",
        "English",
        20,
        6,
        25.0,
        0,
        allow_control=allow_control,
    )
    plugin._state.client = _FakeClient()
    plugin._state.counter_every = counter_every
    import domoticz_api
    from persistence import PluginState

    domoticz_api.save_state(
        PluginState(base_wh={"1": 0.0, "4": 0.0, "5": 0.0}, last_processed_date=last_date)
    )
    return plugin._state


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
    # A live beat that creates all 11 devices must persist auto_names ownership
    # immediately so a crash cannot lose it before the next refresh writes state.
    _setup(counter_every=2, last_date="2026-07-01")
    plugin._state.beat = 2  # next beat = 3 -> live beat (not first, 3 % 2 != 0)
    plugin.onHeartbeat()

    state_json = Domoticz.Configuration().get("state", "")
    assert state_json, "state must be written after device creation"
    auto_names = json.loads(state_json).get("auto_names", {})
    assert set(auto_names.keys()) == {
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "20",
    }
    assert auto_names["1"] == "Solar Total"
    assert auto_names["7"] == "Zappi Mode"
    # The harvi's serial -> Unit allocation is persisted so it survives restarts.
    unit_alloc = json.loads(state_json).get("unit_alloc", {})
    assert unit_alloc == {"19000001": 20}


def test_heartbeat_creates_grid_and_harvi_devices():
    _setup(counter_every=1)
    plugin.onHeartbeat()  # beat 1 -> refresh
    did = device_id(0)
    units = Domoticz.Devices[did].Units
    assert "2" in [str(k) for k in units] or 2 in units  # Grid Import
    assert 3 in units  # Grid Export
    assert 20 in units  # first harvi power device
    assert units[20].sValue == "250"  # 100+100+50


def test_verbose_logging_emits_status_and_timing():
    _setup(counter_every=1)
    plugin.onHeartbeat()
    log = Domoticz._log
    assert any(line.startswith("status beat=") and "harvis=" in line for line in log)
    assert any(
        line.startswith("fetch_status beat=")
        and "duration_ms=" in line
        and "outcome=success" in line
        and "devices=" in line
        for line in log
    )
    assert any(line.startswith("apply units=") for line in log)
    # FB14: per-harvi summed watts logged at Debug, keyed by serial.
    assert any(line == "harvi power harvi_19000001=250" for line in log)


def test_heartbeat_caches_validated_serial_and_hides_mode_text_once():
    st = _setup(counter_every=1, allow_control=True)
    plugin.onHeartbeat()
    assert st.zappi_serial == "20000002"
    did = device_id(0)
    # Mode Text (unit 7) is hidden once Charge Mode (unit 12) takes over.
    assert Domoticz.Devices[did].Units[7].Used == 0
    assert st.mode_text_hidden is True


def test_heartbeat_no_control_updates_when_gate_off():
    _setup(counter_every=1, allow_control=False)
    plugin.onHeartbeat()
    did = device_id(0)
    assert 12 not in Domoticz.Devices[did].Units  # no Charge Mode device created
    assert Domoticz.Devices[did].Units[7].Used == 1  # Mode Text stays visible
    assert plugin._state.mode_text_hidden is False


def test_heartbeat_hides_control_devices_when_control_disabled():
    st = _setup(counter_every=1, allow_control=True)
    plugin.onHeartbeat()  # beat 1: creates the control devices, all visible
    did = device_id(0)
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].Used == 1
    assert Domoticz.Devices[did].Units[control.UNIT_BOOST].Used == 1

    assert Domoticz.Devices[did].Units[7].Used == 0  # Mode Text hidden while control on

    st.config.allow_control = False
    plugin.onHeartbeat()
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].Used == 0
    assert Domoticz.Devices[did].Units[control.UNIT_BOOST].Used == 0
    # Zappi Mode text (unit 7) is re-shown when control is disabled (symmetric).
    assert Domoticz.Devices[did].Units[7].Used == 1
    assert st.mode_text_hidden is False


def test_heartbeat_respects_manual_hide_while_control_stays_on():
    # A control unit is shown once when control is enabled, then never re-forced
    # Used=1. If the user hides one (e.g. Charger Lock State), it must stay hidden
    # across later heartbeats while control remains on. UNIT_MODE stands in for any
    # CONTROL_UNITS member since they are shown/hidden together.
    _setup(counter_every=1, allow_control=True)
    plugin.onHeartbeat()  # beat 1: creates the control devices, all visible
    did = device_id(0)
    Domoticz.Devices[did].Units[control.UNIT_MODE].Used = 0  # user hides it

    plugin.onHeartbeat()  # still allow_control=True
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].Used == 0


def test_heartbeat_reshows_control_devices_on_off_then_on_toggle():
    st = _setup(counter_every=1, allow_control=True)
    plugin.onHeartbeat()  # beat 1: creates the control devices
    did = device_id(0)

    st.config.allow_control = False
    plugin.onHeartbeat()  # off transition -> hidden once
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].Used == 0

    st.config.allow_control = True
    plugin.onHeartbeat()  # on transition -> re-shown once
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].Used == 1


def test_devices_created_in_ascending_unit_order():
    # Domoticz shows devices in creation order, so a fresh install must create them
    # in ascending unit order: monitoring (1-11), control (12-18), then harvi (20+).
    _setup(counter_every=1, allow_control=True)
    plugin.onHeartbeat()  # first beat on a fresh install creates every device
    did = device_id(0)
    created = list(Domoticz.Devices[did].Units.keys())
    assert created == sorted(created), f"units created out of order: {created}"


def test_control_device_name_translates_on_language_switch():
    # A language switch must re-translate a control device name even when its value
    # is unchanged: the no-op filter drops value-unchanged updates, but an owned
    # rename must still go through.
    st = _setup(counter_every=1, allow_control=True)  # English
    plugin.onHeartbeat()  # creates control devices with English names
    did = device_id(0)
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].Name == "Charge Mode"

    assert Domoticz.Devices[did].Units[control.UNIT_BOOST_KWH].Name == "Boost - Add kWh"

    st.config.language = "Nederlands"
    plugin.onHeartbeat()  # zmo unchanged -> only the name should change
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].Name == "Laadmodus"
    # Input-only unit (never re-emitted after creation) must still re-translate.
    assert Domoticz.Devices[did].Units[control.UNIT_BOOST_KWH].Name == "Boost - kWh toevoegen"


def test_reconcile_suppression_skips_units_with_future_deadline():
    class _ModeClient(_FakeClient):
        def __init__(self):
            super().__init__()
            self.zmo = 1

        def fetch_status(self):
            payload = super().fetch_status()
            payload[0]["zappi"][0]["zmo"] = self.zmo
            return payload

    _setup(counter_every=1, allow_control=True)
    client = _ModeClient()
    plugin._state.client = client
    plugin.onHeartbeat()  # beat 1: creates unit 12, zmo=1 -> level 10
    did = device_id(0)
    assert Domoticz.Devices[did].Units[12].nValue == 10

    client.zmo = 2  # hub reports Eco (level 20) while we suppress reconcile
    plugin._state.reconcile_suppress[control.UNIT_MODE] = time.monotonic() + 1000
    plugin.onHeartbeat()
    assert Domoticz.Devices[did].Units[12].nValue == 10  # suppressed -> unchanged

    plugin._state.reconcile_suppress[control.UNIT_MODE] = time.monotonic() - 1
    plugin.onHeartbeat()
    assert Domoticz.Devices[did].Units[12].nValue == 20  # deadline passed -> reconciled


class _ModeClient(_FakeClient):
    def __init__(self):
        super().__init__()
        self.zmo = 1

    def fetch_status(self):
        payload = super().fetch_status()
        payload[0]["zappi"][0]["zmo"] = self.zmo
        return payload


def test_control_unchanged_value_not_reapplied_on_live_beat(monkeypatch):
    # FB9: control reconcile now runs every heartbeat, but a no-op (unchanged)
    # control value must not be re-applied on a live beat.
    _setup(counter_every=2, allow_control=True)
    client = _ModeClient()
    plugin._state.client = client
    calls = []
    orig_apply = plugin.domoticz_api.apply_updates

    def _spy(devices, dev_id, updates, auto_names, allow_create=True):
        calls.append(list(updates))
        return orig_apply(devices, dev_id, updates, auto_names, allow_create=allow_create)

    monkeypatch.setattr(plugin.domoticz_api, "apply_updates", _spy)

    plugin.onHeartbeat()  # beat 1 (refresh): creates unit 12, zmo=1 -> level 10
    did = device_id(0)
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].nValue == 10

    plugin._state.beat = 2  # next beat -> 3, live (not first, 3 % 2 != 0)
    calls.clear()
    plugin.onHeartbeat()  # zmo unchanged -> no-op, dropped before apply_updates
    assert not any(u.unit == control.UNIT_MODE for c in calls for u in c)
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].nValue == 10


def test_control_changed_value_updates_on_live_beat():
    # FB9: an external/app change (here zmo) must reflect on the very next live
    # beat, not wait for the ~120s counter refresh.
    _setup(counter_every=2, allow_control=True)
    client = _ModeClient()
    plugin._state.client = client

    plugin.onHeartbeat()  # beat 1 (refresh): zmo=1 -> level 10
    did = device_id(0)
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].nValue == 10

    client.zmo = 3  # Eco+ -> level 30
    plugin._state.beat = 2  # next beat -> 3, live
    plugin.onHeartbeat()
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].nValue == 30


def test_control_suppressed_unit_skipped_on_live_beat():
    # FB9: reconcile-suppression (set right after a command) must still be
    # honored on the live cadence, not just on a refresh beat.
    _setup(counter_every=2, allow_control=True)
    client = _ModeClient()
    plugin._state.client = client

    plugin.onHeartbeat()  # beat 1 (refresh): zmo=1 -> level 10
    did = device_id(0)
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].nValue == 10

    client.zmo = 2  # Eco -> level 20, would otherwise reconcile
    plugin._state.reconcile_suppress[control.UNIT_MODE] = time.monotonic() + 1000
    plugin._state.beat = 2  # next beat -> 3, live
    plugin.onHeartbeat()
    assert Domoticz.Devices[did].Units[control.UNIT_MODE].nValue == 10  # suppressed


class _DiscoveryClient(_FakeClient):
    def __init__(self, outcomes):
        super().__init__()
        self.base_url = None
        self._outcomes = list(outcomes)
        self.discover_calls = 0

    def discover_from_director(self):
        self.discover_calls += 1
        outcome = self._outcomes.pop(0)
        if outcome is not None:
            raise outcome
        self.base_url = "https://s18.myenergi.net"


def test_discovery_transient_failure_backs_off_and_does_not_retry_every_beat():
    _setup(counter_every=1)
    client = _DiscoveryClient([OSError("dns failure"), OSError("dns failure")])
    plugin._state.client = client

    plugin.onHeartbeat()
    assert client.discover_calls == 1
    assert plugin._state.discovery_failing is True
    assert plugin._state.discovery_backoff_ts > time.monotonic()
    log_len = len(Domoticz._log)

    plugin.onHeartbeat()  # still within the backoff window -> no retry, no duplicate log
    assert client.discover_calls == 1
    assert len(Domoticz._log) == log_len


def test_discovery_backoff_grows_on_repeated_transient_failures():
    _setup(counter_every=1)
    client = _DiscoveryClient([OSError("dns failure"), OSError("dns failure")])
    plugin._state.client = client

    plugin.onHeartbeat()
    first_backoff = plugin._state.discovery_backoff_seconds
    plugin._state.discovery_backoff_ts = 0.0  # force the next beat to retry immediately
    plugin.onHeartbeat()
    assert client.discover_calls == 2
    assert plugin._state.discovery_backoff_seconds > first_backoff


def test_discovery_401_is_permanent_and_logs_once():
    _setup(counter_every=1)
    err = urllib.error.HTTPError("https://director.myenergi.net", 401, "unauthorized", None, None)
    client = _DiscoveryClient([err, err, err])
    plugin._state.client = client

    plugin.onHeartbeat()
    plugin.onHeartbeat()
    plugin.onHeartbeat()

    assert client.discover_calls == 1  # long backoff blocks retries for the rest of the test
    assert plugin._state.discovery_backoff_seconds == 900.0
    # log_redacted replaces every occurrence of the (single-char, "k") test secret, so
    # match on a fragment that survives redaction rather than the literal wording.
    assert sum("401" in line and "Unauthorized" in line for line in Domoticz._log) == 1


def test_discovery_recovers_and_clears_backoff():
    _setup(counter_every=1)
    client = _DiscoveryClient([OSError("dns failure"), None])
    plugin._state.client = client

    plugin.onHeartbeat()  # fails, backoff scheduled
    assert plugin._state.discovery_failing is True
    plugin._state.discovery_backoff_ts = 0.0  # force the retry now instead of waiting

    plugin.onHeartbeat()  # succeeds
    assert plugin._state.discovery_failing is False
    assert plugin._state.discovery_backoff_ts == 0.0
    assert any("recovered" in line for line in Domoticz._log)


def test_heartbeat_reconciles_control_when_enabled():
    _setup(counter_every=1, allow_control=True)
    plugin.onHeartbeat()  # beat 1 (refresh): creates energy + control devices
    did = device_id(0)
    units = Domoticz.Devices[did].Units
    # control devices created and shown
    assert control.UNIT_MODE in units and units[control.UNIT_MODE].Used == 1
    assert control.UNIT_BOOST in units
    # one-time Zappi Mode text (unit 7) hidden, flag set
    assert units[7].Used == 0
    assert plugin._state.mode_text_hidden is True


def test_heartbeat_hides_control_when_disabled():
    _setup(counter_every=1, allow_control=False)
    plugin.onHeartbeat()
    did = device_id(0)
    units = Domoticz.Devices[did].Units
    for u in plugin.CONTROL_UNITS:
        if u in units:
            assert units[u].Used == 0
    # Zappi Mode text stays visible when control is off
    assert units[7].Used == 1
