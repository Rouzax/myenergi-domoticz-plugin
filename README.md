# myenergi Monitor for Domoticz

> 📖 **Full documentation, install guide, settings, and FAQ:**
> **[rouzax.github.io/myenergi-domoticz-plugin](https://rouzax.github.io/myenergi-domoticz-plugin/)**

A Domoticz plugin for **myenergi** (zappi + harvi). It polls the myenergi cloud and surfaces
true solar generation, EV charging, derived home consumption, grid import/export, and
per-inverter power as real kWh counters that survive Domoticz restarts, plus **opt-in** charger
control (charge mode, boost, min-green). It is **read-only by default** - control is off unless
you explicitly enable it.

Author: **Rouzax**

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

## License and acknowledgements

MIT licensed (see `LICENSE`). Independent and **not affiliated with myenergi**. Field meanings
were cross-checked against [twonk/MyEnergi-App-Api](https://github.com/twonk/MyEnergi-App-Api)
and [CJNE/pymyenergi](https://github.com/CJNE/pymyenergi) - thanks to their authors.
