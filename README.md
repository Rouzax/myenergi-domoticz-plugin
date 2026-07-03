# myenergi Monitor for Domoticz

Real solar, EV, home, grid, and per-inverter energy from your myenergi system - plus opt-in charger control - in Domoticz.

[![Docs](https://img.shields.io/badge/docs-online-2e7d32?style=for-the-badge&logo=materialformkdocs&logoColor=white)](https://rouzax.github.io/myenergi-domoticz-plugin/)
[![Release](https://img.shields.io/github/v/release/Rouzax/myenergi-domoticz-plugin?style=for-the-badge&color=orange)](https://github.com/Rouzax/myenergi-domoticz-plugin/releases)
[![Domoticz](https://img.shields.io/badge/Domoticz-plugin-1a6fc9?style=for-the-badge)](https://www.domoticz.com/)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-4caf50?style=for-the-badge)](LICENSE)

> **Full documentation, install guide, settings, and FAQ:**
> **[rouzax.github.io/myenergi-domoticz-plugin](https://rouzax.github.io/myenergi-domoticz-plugin/)**

A Domoticz plugin for **myenergi** (zappi + harvi). It polls the myenergi cloud and surfaces true
solar generation, EV charging, derived home consumption, grid import/export, and per-inverter
power as real kWh counters that survive Domoticz restarts, plus **opt-in** charger control. It is
**read-only by default** - control is off unless you explicitly enable it.

_Screenshot of the Domoticz devices goes here._

## Features

| Feature | What you get |
|---------|--------------|
| **True solar generation** | Whole-system generation (all inverters) with a real cumulative kWh counter. |
| **EV charging** | Live charge power plus session and cumulative energy added. |
| **Derived home consumption** | What the rest of the house used, computed from generation, grid, and EV flow. |
| **Grid import / export** | Instantaneous power and cumulative kWh in both directions. |
| **Per-inverter (harvi) power** | One live-power device per harvi, auto-styled for generation vs battery/load. |
| **Persistent counters** | Rebuilt from myenergi's per-minute history; monotonic and restart-proof. |
| **Opt-in charger control** | Charge mode, boost (kWh + ready-by), and Eco+ min-green - off by default. |
| **English + Nederlands** | Device names and status text in either language. |

## Requirements

- A myenergi hub with at least one zappi, its hub serial, and an API key (myenergi app ->
  Account -> Advanced -> API key).
- Internet access from the Domoticz host (the myenergi local API is not supported).

## Install (short)

Clone the lean **`dist`** branch into your Domoticz plugins directory, then restart Domoticz and
add the hardware:

```bash
cd /opt/domoticz/plugins            # adjust to your install path
git clone -b dist https://github.com/Rouzax/myenergi-domoticz-plugin myenergi
```

Then: **Setup -> Hardware -> Add -> myenergi Monitor**, fill in the settings, and enable
**Accept new Hardware Devices**. Full steps, every setting, the device list, and the opt-in
control surface are in the **[documentation](https://rouzax.github.io/myenergi-domoticz-plugin/)**.

## Security

Your API key grants **full charger control** and is stored in the Domoticz database in cleartext.
Control writes are gated behind an **Allow Control** setting that is **off by default**. Treat the
key (and any DB backup) as a secret, and rotate it in the myenergi app if it is ever exposed. See
the [Security page](https://rouzax.github.io/myenergi-domoticz-plugin/security/).

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the dev setup
(tests, linting, type checks).

## License and acknowledgements

MIT licensed (see [`LICENSE`](LICENSE)). Independent and **not affiliated with myenergi**. Field
meanings were cross-checked against [twonk/MyEnergi-App-Api](https://github.com/twonk/MyEnergi-App-Api)
and [CJNE/pymyenergi](https://github.com/CJNE/pymyenergi) - thanks to their authors.
