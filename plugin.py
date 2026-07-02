"""\
<plugin key="myenergi" name="myenergi (zappi/harvi) Monitor" author="Rouzax" version="1.0.0" externallink="https://github.com/Rouzax">
    <description>
        <h2>myenergi cloud monitor (read-only)</h2>
        <p>Reads your myenergi system via the cloud API and creates Solar Total, Home Consumption, EV Charging (real kWh counters), plus mode/status/voltage/frequency devices.</p>
        <p><b>Your API key grants charger control and is stored in cleartext in the Domoticz database. Treat DB backups as secrets and rotate the key if exposed.</b></p>
    </description>
    <params>
        <param field="Username" label="Hub Serial Number" width="150px" required="true"/>
        <param field="ApiKey" label="API Key" width="200px" required="true" password="true"/>
        <param field="Language" label="Language" width="150px">
            <options>
                <option label="English" value="English" default="true"/>
                <option label="Nederlands" value="Nederlands"/>
            </options>
        </param>
        <param field="LivePoll" type="number" label="Live Poll Interval (s)" min="15" max="300" default="20" width="100px"/>
        <param field="CounterPoll" type="number" label="Counter Refresh (s)" min="30" max="900" default="120" width="100px"/>
        <param field="MaxSystemKW" type="number" label="Max System Power (kW)" min="1" max="100" default="25" width="100px"/>
        <param field="DebugLevel" label="Debug Level" width="150px">
            <options>
                <option label="None" value="0" default="true"/>
                <option label="Basic" value="1"/>
                <option label="Verbose" value="2"/>
            </options>
        </param>
    </params>
</plugin>
"""

from dataclasses import dataclass, field

import Domoticz

import domoticz_api
from config import parse_config
from myenergi_client import MyEnergiClient


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
    pass
