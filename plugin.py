# pyright: reportMissingImports=false, reportUndefinedVariable=false, reportAttributeAccessIssue=false
"""\
<plugin key="myenergi" name="myenergi Monitor" author="Rouzax" version="1.0.0" externallink="https://github.com/Rouzax">
    <description>
        <h2>myenergi cloud monitor (read-only)</h2>
        <p>Reads your myenergi system (zappi, harvi) via the cloud API and creates Solar Total, Home Consumption, EV Charging (real kWh counters), plus mode/status/voltage/frequency devices.</p>
        <p><b>Your API key grants charger control and is stored in cleartext in the Domoticz database. Treat DB backups as secrets and rotate the key if exposed.</b></p>
    </description>
    <params>
        <param field="Username" label="Hub Serial Number" width="150px" required="true">
            <description>The serial number of your myenergi hub (shown in the myenergi app and on the hub label). Used as the API username.</description>
        </param>
        <param field="ApiKey" label="API Key" width="200px" required="true" password="true">
            <description>API key generated in the myenergi app (Account, Advanced, API Key). Grants full control of your charger and is stored in cleartext in the Domoticz database, so treat DB backups as secrets and rotate the key if it is ever exposed.</description>
        </param>
        <param field="AllowControl" label="Allow Control" width="150px">
            <description>Enable charger control (mode changes, boost, min-green). Off by default: the plugin stays strictly read-only until this is turned on. Once enabled, any Domoticz user, scene, timer, or API client with access to this hardware can command the charger.</description>
            <options>
                <option label="No" value="false" default="true"/>
                <option label="Yes" value="true"/>
            </options>
        </param>
        <param field="Language" label="Language" width="150px">
            <description>Language for device names and status text (English or Nederlands). The settings page itself is always English.</description>
            <options>
                <option label="English" value="English" default="true"/>
                <option label="Nederlands" value="Nederlands"/>
            </options>
        </param>
        <group label="Polling">
            <param field="LivePoll" type="number" label="Live Poll Interval (s)" min="15" max="300" step="5" default="20" width="100px">
                <description>How often to poll live power and status, in seconds (15 to 300). myenergi data updates about once per second, so 15 to 30s is plenty and gentle on their cloud.</description>
            </param>
            <param field="CounterEvery" type="number" label="Counter Refresh (every N live polls)" min="1" max="60" step="1" default="6" width="100px">
                <description>How often to refresh the cumulative kWh counters from myenergi's energy history, expressed as a multiple of the live poll interval (1 to 60). At the default 20s live poll, 6 refreshes the counters every 120s. 1 = refresh on every live poll (heaviest on myenergi's cloud).</description>
            </param>
        </group>
        <group label="Advanced">
            <param field="MaxSystemKW" type="number" label="Max System Power (kW)" min="1" max="100" step="1" default="25" width="100px">
                <description>Total system power ceiling in kW, used as a sanity clamp on counter jumps. Set it roughly to your combined solar plus grid plus charger capacity.</description>
            </param>
            <param field="DebugLevel" label="Debug Level" width="150px">
                <description>Logging verbosity. None for normal use; Basic or Verbose for troubleshooting. The API key is never written to the log at any level.</description>
                <options>
                    <option label="None" value="0" default="true"/>
                    <option label="Basic" value="1"/>
                    <option label="Verbose" value="2"/>
                </options>
            </param>
        </group>
        <group label="Harvi Names (optional)">
            <param field="Harvi1Serial" label="Harvi 1 serial" width="120px">
                <description>Optional. To give a harvi a friendly name, copy its serial from the auto-created 'Harvi &lt;serial&gt;' device (match it by its live watts) and enter it here. Easiest alternative: just rename the device in Domoticz - the plugin never overwrites your rename.</description>
            </param>
            <param field="Harvi1Name" label="Harvi 1 name" width="150px"/>
            <param field="Harvi2Serial" label="Harvi 2 serial" width="120px"/>
            <param field="Harvi2Name" label="Harvi 2 name" width="150px"/>
            <param field="Harvi3Serial" label="Harvi 3 serial" width="120px"/>
            <param field="Harvi3Name" label="Harvi 3 name" width="150px"/>
            <param field="Harvi4Serial" label="Harvi 4 serial" width="120px"/>
            <param field="Harvi4Name" label="Harvi 4 name" width="150px"/>
        </group>
    </params>
</plugin>
"""

import time
import urllib.error
from dataclasses import dataclass, field, replace

import DomoticzEx as Domoticz

import control
import domoticz_api
from config import parse_config
from energy import missing_dates
from model import parse_jday, parse_jstatus
from myenergi_client import MyEnergiClient
from persistence import PluginState
from planner import AGG_UNITS, advance_baselines, assign_harvi_units, plan, plan_harvi_updates

_MAX_BACKFILL_DAYS = 14
_DISCOVERY_BACKOFF_INITIAL = 20.0
_DISCOVERY_BACKOFF_CAP = 900.0

# Units plan_control_updates can emit; hidden (Used=0) when control is disabled,
# re-shown (Used=1) when it is re-enabled. Unit 17 was removed and is not a member.
CONTROL_UNITS = (
    control.UNIT_MODE,
    control.UNIT_BOOST,
    control.UNIT_BOOST_KWH,
    control.UNIT_BOOST_TIME,
    control.UNIT_MIN_GREEN,
    control.UNIT_LOCK_STATE,
)

UNIT_MODE_TEXT = 7  # Zappi Mode read-only text; hidden once while control is enabled.

# Debug Level -> Domoticz.Debugging() bitmask. 2 = Python-only (this plugin's own
# Domoticz.Debug lines); 1 = All (adds framework internals). 0 = off.
_DEBUG_MASK = {0: 0, 1: 2, 2: 1}


def _apply_debug_level(level):
    Domoticz.Debugging(_DEBUG_MASK.get(level, 0))


def _hardware_id():
    # Parameters is injected by the framework at runtime; may be absent in tests.
    params = globals().get("Parameters") or {}
    try:
        return int(params.get("HardwareID", 0))
    except (ValueError, TypeError):
        return 0


def _hub_date(zappi):
    dat = str(zappi.get("dat", ""))
    parts = dat.split("-")
    if len(parts) == 3:
        try:
            d, m, y = parts
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        except (ValueError, TypeError):
            return None  # malformed cloud date -> fall through to the live path
    return None


@dataclass
class _PluginState:
    config: object = None
    client: object = None
    beat: int = 0
    counter_every: int = 6
    auto_names: dict = field(default_factory=dict)
    unit_alloc: dict = field(default_factory=dict)
    zappi_serial: "str | None" = None
    last_write: dict = field(default_factory=dict)
    last_any_write_ts: float = 0.0
    discovery_backoff_ts: float = 0.0
    discovery_backoff_seconds: float = 0.0
    discovery_failing: bool = False
    mode_text_hidden: bool = False
    reconcile_suppress: dict = field(default_factory=dict)


_state = _PluginState()


def onStart():
    global _state
    _state = _PluginState()
    cfg = parse_config(Parameters)  # noqa: F821 - Parameters injected by Domoticz
    _state.config = cfg
    _apply_debug_level(cfg.debug_level)
    _state.counter_every = cfg.counter_multiple
    Domoticz.Heartbeat(cfg.live_interval)
    Domoticz.Debug(
        f"onStart: hub={cfg.hub_serial} live={cfg.live_interval}s "
        f"counter_every={_state.counter_every} lang={cfg.language}"
    )
    # Restore name-ownership from persisted state (survives settings-edit restarts).
    # Guarded: corrupt persisted JSON must never block the plugin from starting.
    try:
        _restored = domoticz_api.load_state()
        _state.auto_names = _restored.auto_names
        _state.unit_alloc = _restored.unit_alloc
        _state.mode_text_hidden = _restored.mode_text_hidden
    except Exception:  # noqa: BLE001
        _state.auto_names = {}
        _state.unit_alloc = {}
    try:
        _state.client = MyEnergiClient(
            cfg.hub_serial,
            cfg.api_key,
            writes_enabled=cfg.allow_control,
        )
        _state.client.discover_from_director()
        Domoticz.Debug(f"discovery ok: base={_state.client.base_url}")
    except Exception as exc:  # noqa: BLE001 - never let onStart crash the framework
        domoticz_api.log_redacted(Domoticz.Error, f"myenergi discovery failed: {exc}", cfg.api_key)
        _state.discovery_failing = True
    _initial_control_reconcile(_state)


def onStop():
    _state.client = None


def _note_transient_discovery_failure(st, now, exc) -> None:
    if not st.discovery_failing:
        domoticz_api.log_redacted(
            Domoticz.Error, f"myenergi discovery failed: {exc}", st.config.api_key
        )
    st.discovery_failing = True
    prev = st.discovery_backoff_seconds
    next_backoff = (
        _DISCOVERY_BACKOFF_INITIAL if prev <= 0 else min(prev * 2, _DISCOVERY_BACKOFF_CAP)
    )
    st.discovery_backoff_seconds = next_backoff
    st.discovery_backoff_ts = now + next_backoff


def _maybe_rediscover(st) -> None:
    now = time.monotonic()
    if now < st.discovery_backoff_ts:
        return
    try:
        st.client.discover_from_director()
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            if not st.discovery_failing:
                domoticz_api.log_redacted(
                    Domoticz.Error,
                    f"myenergi discovery failed (401 Unauthorized, check API key): {exc}",
                    st.config.api_key,
                )
            st.discovery_failing = True
            st.discovery_backoff_seconds = _DISCOVERY_BACKOFF_CAP
            st.discovery_backoff_ts = now + _DISCOVERY_BACKOFF_CAP
            return
        _note_transient_discovery_failure(st, now, exc)
    except Exception as exc:  # noqa: BLE001 - discovery must never crash the heartbeat
        _note_transient_discovery_failure(st, now, exc)
    else:
        if st.discovery_failing:
            Domoticz.Log(f"myenergi discovery recovered: base={st.client.base_url}")
        st.discovery_failing = False
        st.discovery_backoff_seconds = 0.0
        st.discovery_backoff_ts = 0.0


def _persist_state(st):
    saved = domoticz_api.load_state()
    return replace(
        saved,
        auto_names=st.auto_names,
        unit_alloc=st.unit_alloc,
        mode_text_hidden=st.mode_text_hidden,
    )


def onHeartbeat():
    st = _state
    if st.client is None or st.config is None:
        return
    devices = globals().get("Devices")
    if devices is None:
        return
    try:
        if st.client.base_url is None:
            _maybe_rediscover(st)
            if st.client.base_url is None:
                return
        st.beat += 1
        did = domoticz_api.device_id(_hardware_id())
        t0 = time.monotonic()
        status = parse_jstatus(st.client.fetch_status())
        Domoticz.Debug(
            f"fetch_status duration_ms={(time.monotonic() - t0) * 1000:.0f} outcome=success"
        )
        if not status.zappi:
            Domoticz.Debug("skip reason=no_zappi")
            return
        zappi_dev = next((d for d in status.devices if d.kind == "zappi"), None)
        if zappi_dev is not None:
            st.zappi_serial = zappi_dev.serial
        harvis = [d for d in status.devices if d.kind == "harvi"]
        Domoticz.Debug(
            f"status zappi={status.zappi.get('sno')} gen={status.zappi.get('gen')} "
            f"grd={status.zappi.get('grd')} div={status.zappi.get('div')} "
            f"sta={status.zappi.get('sta')} pst={status.zappi.get('pst')} "
            f"vol={status.zappi.get('vol')} frq={status.zappi.get('frq')} harvis={len(harvis)}"
        )
        if harvis:
            harvi_values = " ".join(
                f"harvi_{h.serial}={sum(ct.power_w for ct in h.cts)}" for h in harvis
            )
            Domoticz.Debug(f"harvi power {harvi_values}")
        new_alloc = assign_harvi_units(st.unit_alloc, [h.serial for h in harvis])
        alloc_changed = new_alloc != st.unit_alloc
        st.unit_alloc = new_alloc
        prev = domoticz_api.read_prev_counters(devices, did, list(AGG_UNITS.values()))
        refresh_seconds = st.config.live_interval * st.config.counter_multiple
        max_step = st.config.max_system_kw * 1000.0 * (refresh_seconds / 3600.0) * 4.0
        serial = st.config.hub_serial

        is_refresh = st.beat == 1 or (st.beat % st.counter_every) == 0
        hub_date = _hub_date(status.zappi) if is_refresh else None
        Domoticz.Debug(f"heartbeat beat={st.beat} refresh={is_refresh} hub_date={hub_date}")

        now = time.monotonic()

        if is_refresh and hub_date:
            state = domoticz_api.load_state()
            missing = missing_dates(state.last_processed_date or hub_date, hub_date)
            if len(missing) > _MAX_BACKFILL_DAYS:
                domoticz_api.log_redacted(
                    Domoticz.Error,
                    f"myenergi backfill truncated: {len(missing)} missing days; folding "
                    f"{missing[0]}..{missing[_MAX_BACKFILL_DAYS - 1]}; "
                    f"{missing[_MAX_BACKFILL_DAYS]}..{missing[-1]} permanently skipped (reset plugin state to recover)",
                    st.config.api_key,
                )
                missing = missing[:_MAX_BACKFILL_DAYS]
            Domoticz.Debug(f"counter refresh hub_date={hub_date} backfill_days={len(missing)}")
            backfill = [parse_jday(st.client.fetch_jday("Z", serial, d)) for d in missing]
            today_raw = parse_jday(st.client.fetch_jday("Z", serial, hub_date))
            state = advance_baselines(
                state, backfill, today_raw, prev, AGG_UNITS, st.config.max_system_kw, hub_date
            )
            updates, state = plan(status, today_raw, state, prev, st.config, max_step)
            updates = updates + plan_harvi_updates(
                harvis, st.unit_alloc, st.config.harvi_names, st.config.language
            )
            st.auto_names = domoticz_api.apply_updates(devices, did, updates, st.auto_names)
            state = replace(state, auto_names=st.auto_names, unit_alloc=st.unit_alloc)
            domoticz_api.save_state(state)
        else:
            # Live beat (or refresh with no hub date): update power/status only.
            # No load_state (base_wh is unused when today_sums is None).
            before_names = st.auto_names
            updates, _ = plan(status, None, PluginState(), prev, st.config, max_step)
            updates = updates + plan_harvi_updates(
                harvis, st.unit_alloc, st.config.harvi_names, st.config.language
            )
            st.auto_names = domoticz_api.apply_updates(devices, did, updates, st.auto_names)
            if st.auto_names != before_names or alloc_changed:
                domoticz_api.save_state(_persist_state(st))

        _reconcile_control(st, devices, did, status, now)
    except Exception as exc:  # noqa: BLE001 - heartbeat must never raise into the framework
        domoticz_api.log_redacted(
            Domoticz.Error, f"myenergi heartbeat error: {exc}", st.config.api_key
        )


def _read_siblings(devices, did, units):
    siblings = {}
    dev = devices.get(did) if devices else None
    if dev is not None:
        for unit in units:
            u = dev.Units.get(unit)
            if u is not None:
                siblings[unit] = u.sValue
    return siblings


def _dispatch_write(client, serial, intent):
    if intent.kind == "mode":
        return client.set_zappi_mode(serial, intent.mode)
    if intent.kind == "boost_manual":
        return client.set_boost_manual(serial, intent.kwh)
    if intent.kind == "boost_smart":
        return client.set_boost_smart(serial, intent.kwh, intent.hhmm)
    if intent.kind == "boost_cancel":
        return client.cancel_boost(serial)
    if intent.kind == "min_green":
        return client.set_min_green(serial, intent.pct)
    return None


def _existing_units(devices, did):
    dev = devices.get(did) if devices else None
    return frozenset(dev.Units.keys()) if dev is not None else frozenset()


def _current_unit_values(devices, did, units):
    dev = devices.get(did) if devices else None
    values = {}
    if dev is not None:
        for unit in units:
            u = dev.Units.get(unit)
            if u is not None:
                values[unit] = (u.nValue, u.sValue)
    return values


def _filter_control_updates(devices, did, updates, reconcile_suppress, now):
    current = _current_unit_values(devices, did, [u.unit for u in updates])
    kept = []
    for u in updates:
        if reconcile_suppress.get(u.unit, 0) > now:
            continue
        cur = current.get(u.unit)
        if cur is not None and control.is_noop_update(cur[0], cur[1], u):
            continue
        kept.append(u)
    return kept


def _reconcile_control(st, devices, did, status, now):
    before_names = st.auto_names
    before_hidden = st.mode_text_hidden
    control_updates = control.plan_control_updates(status, st.config, _existing_units(devices, did))
    control_updates = _filter_control_updates(
        devices, did, control_updates, st.reconcile_suppress, now
    )
    st.auto_names = domoticz_api.apply_updates(devices, did, control_updates, st.auto_names)

    dev = devices.get(did)
    mode_text_exists = dev is not None and UNIT_MODE_TEXT in dev.Units

    if st.config.allow_control:
        # Defer the one-time hide until unit 4 exists (energy path creates it on the
        # first heartbeat); setting the flag before it exists would suppress it forever.
        if not st.mode_text_hidden and mode_text_exists:
            domoticz_api.deactivate_units(devices, did, [UNIT_MODE_TEXT])
            st.mode_text_hidden = True
        domoticz_api.activate_units(devices, did, CONTROL_UNITS)
    else:
        domoticz_api.deactivate_units(devices, did, CONTROL_UNITS)
        if st.mode_text_hidden:
            domoticz_api.activate_units(devices, did, [UNIT_MODE_TEXT])
            st.mode_text_hidden = False

    if st.auto_names != before_names or st.mode_text_hidden != before_hidden:
        domoticz_api.save_state(_persist_state(st))


def _initial_control_reconcile(st):
    try:
        if st.client is None or st.client.base_url is None:
            return
        devices = globals().get("Devices")
        if devices is None:
            return
        status = parse_jstatus(st.client.fetch_status())
        if not status.zappi:
            return
        did = domoticz_api.device_id(_hardware_id())
        _reconcile_control(st, devices, did, status, time.monotonic())
        Domoticz.Debug("onStart control reconcile applied")
    except Exception as exc:  # noqa: BLE001 - onStart must never crash the framework
        domoticz_api.log_redacted(
            Domoticz.Error,
            f"myenergi onStart control reconcile failed: {exc}",
            st.config.api_key,
        )


def onCommand(DeviceID, Unit, Command, Level, Color):  # noqa: N803
    st = _state
    devices = globals().get("Devices")
    if st.client is None or st.config is None or devices is None:
        return
    try:
        Domoticz.Debug(f"onCommand unit={Unit} command={Command} level={Level}")
        if not st.config.allow_control:
            Domoticz.Debug("onCommand blocked: control disabled")
            return
        did = domoticz_api.device_id(_hardware_id())
        if Unit in (control.UNIT_BOOST_KWH, control.UNIT_BOOST_TIME) and Command == "Set Level":
            upd = control.persist_input_setpoint(Unit, Level, st.config.language)
            if upd is not None:
                st.auto_names = domoticz_api.apply_updates(devices, did, [upd], st.auto_names)
                Domoticz.Debug(f"onCommand persisted setpoint unit={Unit} value={upd.svalue}")
            return
        siblings = _read_siblings(devices, did, [control.UNIT_BOOST_KWH, control.UNIT_BOOST_TIME])
        intent = control.decide_write(Unit, Command, Level, siblings)
        if intent is None:
            return
        if st.zappi_serial is None:
            Domoticz.Debug("onCommand skipped: charger not seen yet")
            return
        now = time.monotonic()
        if control.should_debounce(Unit, now, st.last_write, 3.0) or not control.allow_write_now(
            now, st.last_any_write_ts, 1.0
        ):
            Domoticz.Debug(f"onCommand debounced unit={Unit}")
            return
        st.last_write[Unit] = now
        st.last_any_write_ts = now
        Domoticz.Debug(f"onCommand write attempt kind={intent.kind}")
        resp = _dispatch_write(st.client, st.zappi_serial, intent)
        if not control.write_succeeded(intent.kind, resp):
            domoticz_api.log_redacted(
                Domoticz.Error, f"myenergi write rejected: {resp}", st.config.api_key
            )
            return
        Domoticz.Debug(f"control write ok kind={intent.kind}")
        opt = control.optimistic_update(Unit, Command, Level, st.config.language)
        if opt is not None:
            st.auto_names = domoticz_api.apply_updates(devices, did, [opt], st.auto_names)
        st.reconcile_suppress[Unit] = now + 2 * st.config.live_interval
    except Exception as exc:  # noqa: BLE001 - onCommand must never raise into the framework
        domoticz_api.log_redacted(
            Domoticz.Error, f"myenergi onCommand error: {exc}", st.config.api_key
        )
