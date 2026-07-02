# myenergi Monitor for Domoticz

A read-only Domoticz plugin that polls the myenergi cloud API and surfaces solar generation,
EV charging, and derived home consumption as real kWh counters that match the myenergi app.
It covers the whole system (zappi + harvi) and exposes data that a utility meter alone cannot
see: instantaneous power split between solar, EV, and home, plus cumulative daily energy totals
that survive Domoticz restarts.

Author: **Rouzax**

---

## What it does

Each poll cycle retrieves live status and per-minute energy history from the myenergi cloud.
Eleven fixed devices appear in Domoticz, plus one extra device per harvi:

| Unit | Device name | Type | Notes |
|------|-------------|------|-------|
| 1 | Solar Total | kWh | Total solar generation (all inverters) + cumulative counter; created as Domoticz "Return" type |
| 2 | Home Consumption | kWh | Derived: generation + grid import - grid export - EV charge |
| 3 | EV Charging | kWh | Power delivered to the vehicle + cumulative counter |
| 4 | Zappi Mode | Text | Current operating mode (e.g. Fast, Eco, Eco+, Stop) |
| 5 | Charge Status | Text | Current charge state |
| 6 | Plug Status | Text | Current plug/connection state |
| 7 | Charge Added | Custom (kWh) | Energy added in the current charging session |
| 8 | Supply Voltage | Voltage (V) | Grid voltage |
| 9 | Supply Frequency | Custom (Hz) | Grid frequency |
| 10 | Grid Import | kWh | Power drawn from the grid + cumulative counter |
| 11 | Grid Export | kWh | Power fed back to the grid + cumulative counter; created as Domoticz "Return" type |
| 20+ | one per harvi | Usage (W) or Custom (W) | Live power measured by each harvi (see below) |

The five kWh devices (Solar Total, Home Consumption, EV Charging, Grid Import, Grid Export)
carry both an instantaneous power reading and a real cumulative counter. The counter is built
from myenergi's per-minute energy history and persists across Domoticz restarts.

### Harvi devices (per inverter / circuit)

Each harvi becomes its own live-power device. A harvi whose CTs measure generation (solar) is a
Usage (W) device with a sun icon; a harvi clamped to anything else (a load, a battery) is a
signed Custom (W) sensor so a battery's charge/discharge (+/-) renders correctly. Harvis carry
no cumulative energy: the myenergi API exposes only their instantaneous power, so these devices
are watts-only. Each is named `Harvi <serial>` by default.

**Naming a harvi.** The easiest way is to just rename the `Harvi <serial>` device in Domoticz
(match it to the right inverter by its live watts); the plugin never overwrites your rename. If
you prefer names that survive deleting and recreating the device, use the optional "Harvi Names"
slots in the hardware settings: copy the serial from the device name into a `Harvi N serial`
field and type the friendly name in `Harvi N name` (up to four). A harvi with no matching slot
keeps its default name.

**Note on inverter totals:** the per-inverter (harvi) power devices and Solar Total are
independent readings from myenergi. Each harvi reports wirelessly to the hub on its own cadence,
so at any given instant the individual inverter figures may not add up exactly to Solar Total.
This is normal timing behavior, not a plugin error; over time the cumulative counters converge.

---

## Prerequisites

- A myenergi hub with at least one zappi.
- Your hub serial number (visible in the myenergi app under Account > myenergi devices).
- A myenergi API key (generated in the myenergi app under Account > Advanced > API key).
- Internet access from the Domoticz host; the myenergi local API is not supported.
- Domoticz 2026.x or later (extended plugin settings support) is recommended.

---

## Install

1. Copy or clone the plugin folder into your Domoticz plugins directory so that `plugin.py`
   lives at `.../domoticz/plugins/myenergi/plugin.py`.

   ```
   cd /opt/domoticz/plugins          # adjust to your install path
   git clone <repo-url> myenergi
   ```

2. Restart Domoticz.

3. Go to **Setup -> Hardware -> Add**, choose **myenergi Monitor**, fill in
   the settings (see below), and click **Add**.

4. On first run the plugin creates all 9 devices. For them to appear in the Devices list,
   **Accept new Hardware Devices** must be enabled: **Settings -> Hardware -> (tick) Accept
   new Hardware Devices**.

---

## Settings

| Setting | Range / options | Default | What it does |
|---------|----------------|---------|--------------|
| Hub Serial Number | text, required | | The serial number printed on the hub, used as the API username. |
| API Key | text, required, masked | | The API key from the myenergi app. Grants full charger control; see Security below. |
| Language | English, Nederlands | English | Language used for device names and status text. |
| Live Poll Interval (s) | 15-300 | 20 | How often (in seconds) to fetch live power and status from the cloud. |
| Counter Refresh (s) | 30-900 | 120 | How often (in seconds) to fetch per-minute energy history and update the kWh counters. |
| Max System Power (kW) | 1-100 | 25 | The rated output of your solar installation. Used as a sanity ceiling on counter increments. |
| Debug Level | None, Basic, Verbose | None | Logging verbosity written to the Domoticz log. |

---

## Notes

- **Cloud only.** myenergi hardware does not expose a documented local API. All data is
  fetched from `director.myenergi.net`.
- **Rate limiting.** myenergi has no published rate limit, but the default poll intervals
  (20s live, 120s counter) are chosen to keep requests gentle. The minimum live poll is
  capped at 15 seconds.
- **Counter continuity.** The cumulative kWh counters are rebuilt from myenergi's per-minute
  history on each counter refresh and survive Domoticz restarts without manual reset.
- **Home Consumption is derived.** It equals: solar generation + grid import - grid export
  - EV charge. It reflects what the rest of the house consumed and can be zero if the
  calculation yields a negative result (e.g. during export-only moments).
- **Backfill.** On startup the plugin can back-fill up to 14 days of missed history into
  the counters.

---

## Marking Solar Total as production

The plugin automatically sets the **Solar Total** device to Domoticz's **Return** type when
created. This changes the device's icon to a solar panel and its Type label to Return in the
Utility list.

Note: Domoticz's Energy Dashboard (Setup -> Settings -> Energy Dashboard tab, or the Energy
Dashboard nav item) splits generation and usage only from an officially recognized P1 Smart
Meter. The **Solar Total** Return type is cosmetic:
it affects the device icon and label, but not the dashboard energy accounting. If you remove
**Solar Total** and let the plugin recreate it, the Return type is set automatically again.

---

## Security

**Your API key grants full charger control** (it can start, stop, and change the charge
mode on your zappi). The Domoticz database stores it in cleartext.

- Treat any Domoticz database backup as a secret.
- Never paste your API key into a chat, screenshot, or log.
- If the key is ever exposed, generate a new one immediately in the myenergi app
  (Account -> Advanced -> API key) and update the hardware settings in Domoticz.

This plugin implements no write or control commands. It is strictly read-only: it fetches
data and updates Domoticz devices; it never sends a command back to the charger.

---

## Acknowledgements

The myenergi cloud API is unofficial and undocumented. The field meanings used here (status
codes, plug states, energy fields) were cross-checked against two community projects:

- [twonk/MyEnergi-App-Api](https://github.com/twonk/MyEnergi-App-Api) - a reverse-engineered
  reference for the myenergi app API.
- [CJNE/pymyenergi](https://github.com/CJNE/pymyenergi) - an async Python library for myenergi
  devices.

Thanks to their authors and contributors. This plugin is independent and not affiliated with
myenergi or either project.
