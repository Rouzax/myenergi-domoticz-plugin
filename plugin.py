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
        <group label="Control (opt-in)">
            <param field="AllowControl" label="Allow Control" width="150px">
                <description>Enable charger control (mode changes, boost, min-green). Off by default: the plugin stays strictly read-only until this is turned on.</description>
                <options>
                    <option label="No" value="false" default="true"/>
                    <option label="Yes" value="true"/>
                </options>
            </param>
            <param field="AllowLock" label="Allow Lock" width="150px">
                <description>Enable charger lock/unlock control. Off by default; independent of Allow Control.</description>
                <options>
                    <option label="No" value="false" default="true"/>
                    <option label="Yes" value="true"/>
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
from dataclasses import dataclass, field, replace

import DomoticzEx as Domoticz

import domoticz_api
from config import parse_config
from energy import missing_dates
from model import parse_jday, parse_jstatus
from myenergi_client import MyEnergiClient
from persistence import PluginState
from planner import AGG_UNITS, advance_baselines, assign_harvi_units, plan, plan_harvi_updates

_MAX_BACKFILL_DAYS = 14

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
            lock_enabled=cfg.allow_lock,
        )
        _state.client.discover_from_director()
        Domoticz.Debug(f"discovery ok: base={_state.client.base_url}")
    except Exception as exc:  # noqa: BLE001 - never let onStart crash the framework
        domoticz_api.log_redacted(Domoticz.Error, f"myenergi discovery failed: {exc}", cfg.api_key)


def onStop():
    _state.client = None


def onHeartbeat():
    st = _state
    if st.client is None or st.config is None:
        return
    devices = globals().get("Devices")
    if devices is None:
        return
    try:
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
        harvis = [d for d in status.devices if d.kind == "harvi"]
        Domoticz.Debug(
            f"status zappi={status.zappi.get('sno')} gen={status.zappi.get('gen')} "
            f"grd={status.zappi.get('grd')} div={status.zappi.get('div')} "
            f"sta={status.zappi.get('sta')} pst={status.zappi.get('pst')} "
            f"vol={status.zappi.get('vol')} frq={status.zappi.get('frq')} harvis={len(harvis)}"
        )
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
            Domoticz.Debug(f"apply units={len(updates)}")
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
            Domoticz.Debug(f"apply units={len(updates)}")
            if st.auto_names != before_names or alloc_changed:
                saved = domoticz_api.load_state()
                domoticz_api.save_state(
                    replace(saved, auto_names=st.auto_names, unit_alloc=st.unit_alloc)
                )
    except Exception as exc:  # noqa: BLE001 - heartbeat must never raise into the framework
        domoticz_api.log_redacted(
            Domoticz.Error, f"myenergi heartbeat error: {exc}", st.config.api_key
        )
