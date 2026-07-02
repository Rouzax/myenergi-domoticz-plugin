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
        <param field="LivePoll" type="number" label="Live Poll Interval (s)" min="15" max="300" default="20" width="100px">
            <description>How often to poll live power and status, in seconds (15 to 300). myenergi data updates about once per second, so 15 to 30s is plenty and gentle on their cloud.</description>
        </param>
        <param field="CounterPoll" type="number" label="Counter Refresh (s)" min="30" max="900" default="120" width="100px">
            <description>How often to refresh the cumulative kWh counters from myenergi's energy history, in seconds (30 to 900). Rounded to a whole multiple of the live poll interval.</description>
        </param>
        <param field="MaxSystemKW" type="number" label="Max System Power (kW)" min="1" max="100" default="25" width="100px">
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
    </params>
</plugin>
"""

from dataclasses import dataclass, field, replace

import DomoticzEx as Domoticz

import domoticz_api
from config import parse_config
from energy import missing_dates
from model import parse_jday, parse_jstatus
from myenergi_client import MyEnergiClient
from persistence import PluginState
from planner import AGG_UNITS, advance_baselines, plan

_MAX_BACKFILL_DAYS = 14


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


_state = _PluginState()


def onStart():
    global _state
    _state = _PluginState()
    cfg = parse_config(Parameters)  # noqa: F821 - Parameters injected by Domoticz
    _state.config = cfg
    _state.counter_every = max(1, round(cfg.counter_interval / cfg.live_interval))
    Domoticz.Heartbeat(cfg.live_interval)
    # Restore name-ownership from persisted state (survives settings-edit restarts).
    # Guarded: corrupt persisted JSON must never block the plugin from starting.
    try:
        _state.auto_names = domoticz_api.load_state().auto_names
    except Exception:  # noqa: BLE001
        _state.auto_names = {}
    try:
        _state.client = MyEnergiClient(cfg.hub_serial, cfg.api_key)
        _state.client.discover_from_director()
    except Exception as exc:  # noqa: BLE001 - never let onStart crash the framework
        domoticz_api.log_redacted(Domoticz.Error, f"myenergi discovery failed: {exc}", cfg.api_key)


def onStop():
    _state.client = None


def onHeartbeat():
    st = _state
    if st.client is None or st.config is None:
        return
    try:
        st.beat += 1
        did = domoticz_api.device_id(_hardware_id())
        status = parse_jstatus(st.client.fetch_status())
        if not status.zappi:
            return
        prev = domoticz_api.read_prev_counters(did, list(AGG_UNITS.values()))
        max_step = st.config.max_system_kw * 1000.0 * (st.config.counter_interval / 3600.0) * 4.0
        serial = st.config.hub_serial

        is_refresh = (st.beat % st.counter_every) == 0
        hub_date = _hub_date(status.zappi) if is_refresh else None

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
            backfill = [parse_jday(st.client.fetch_jday("Z", serial, d)) for d in missing]
            today_raw = parse_jday(st.client.fetch_jday("Z", serial, hub_date))
            state = advance_baselines(
                state, backfill, today_raw, prev, AGG_UNITS, st.config.max_system_kw, hub_date
            )
            updates, state = plan(status, today_raw, state, prev, st.config, max_step)
            st.auto_names = domoticz_api.apply_updates(did, updates, st.auto_names)
            state = replace(state, auto_names=st.auto_names)  # persist name-ownership
            domoticz_api.save_state(state)
        else:
            # Live beat (or refresh with no hub date): update power/status only.
            # No load_state (base_wh is unused when today_sums is None).
            before_names = st.auto_names
            updates, _ = plan(status, None, PluginState(), prev, st.config, max_step)
            st.auto_names = domoticz_api.apply_updates(did, updates, st.auto_names)
            if st.auto_names != before_names:
                # Devices were just created on this live beat; persist ownership now
                # so a crash before the first refresh beat cannot lose it.
                saved = domoticz_api.load_state()
                domoticz_api.save_state(replace(saved, auto_names=st.auto_names))
    except Exception as exc:  # noqa: BLE001 - heartbeat must never raise into the framework
        domoticz_api.log_redacted(
            Domoticz.Error, f"myenergi heartbeat error: {exc}", st.config.api_key
        )
