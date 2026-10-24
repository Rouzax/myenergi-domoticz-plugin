# Settings

These are the fields on the **Setup > Hardware** page when you add or edit the myenergi Monitor
hardware. The settings page itself is always in English, regardless of the **Language** setting
below.

## Connection

| Setting | Type | Default | What it does |
|---|---|---|---|
| Hub Serial Number | text, required | | The serial number of your myenergi hub, shown in the myenergi app and printed on the hub. Used as the API username. |
| API Key | text, required, masked | | The API key generated in the myenergi app (**Account > Advanced > API key**). Grants full control of your charger and is stored as plain, readable text in the Domoticz database. See [Security](security.md). |

## Charger control

| Setting | Options | Default | What it does |
|---|---|---|---|
| Allow Control | No / Yes | **No** | Turns on the charger control devices (charge mode, boost, min-green). Off by default: the plugin stays read-only until you turn this on. Once enabled, the control devices become writable in Domoticz; use Domoticz's own per-user device permissions to control which Domoticz users can operate them. See [Charger control](control.md). |

## Language

| Setting | Options | Default | What it does |
|---|---|---|---|
| Language | English / Nederlands | English | Language used for device names and status text (for example "Fast/Eco/Eco+/Stop" versus "Snel/Eco/Eco+/Stop"). Does not affect the settings page itself. |

## Polling

| Setting | Range | Default | What it does |
|---|---|---|---|
| Live Poll Interval (s) | 15-300, step 5 | 20 | How often, in seconds, the plugin fetches live power and status from the myenergi cloud. myenergi data updates roughly once a second, so 15-30s is plenty and keeps requests gentle on their cloud. |
| Counter Refresh (every N live polls) | 1-60, step 1 | 6 | How often the plugin refreshes the cumulative kWh counters from myenergi's per-minute energy history, expressed as a multiple of the live poll interval. At the default 20s live poll and a value of 6, counters refresh every 120s. A value of 1 refreshes counters on every live poll, which is the heaviest setting on myenergi's cloud. |

## Advanced

| Setting | Range / options | Default | What it does |
|---|---|---|---|
| Max System Power (kW) | 1-100, step 1 | 25 | A safety limit for the energy counters, roughly your combined solar, grid, and charger capacity in kW. The plugin uses it as an absolute ceiling to reject a genuinely corrupt counter reading; it does not cap normal catch-up or the live power readings themselves. |
| Debug Level | None / Basic / Verbose | None | Logging verbosity written to the Domoticz log. Use Basic or Verbose only while troubleshooting; the API key is never written to the log at any level. |
| Update check | Automatic / Stable releases only / Including betas / Off | Automatic | Whether the plugin tells you about a newer version. See [Update check](#update-check) below. |

## Update check

Once a day the plugin asks GitHub whether a newer release of the plugin exists. The first check
runs about five minutes after the plugin starts. When it finds one, it announces it **once**:

- a line in the Domoticz log, for example
  `myenergi Monitor 1.2.0 is available (running 1.1.0): https://github.com/Rouzax/myenergi-domoticz-plugin/releases/tag/v1.2.0`, and
- one notification, "myenergi Monitor plugin 1.2.0 is available", sent through every
  notification system enabled in Domoticz (**Setup > Settings > Notifications**: email,
  Pushover, Telegram, browser notifications and so on). The text follows the **Language**
  setting.

The same version is never announced again, also not after a restart; the next newer version is.
The plugin never updates itself: the notification links to the release page, which says what
changed and how to update.

| Option | What it reports |
|---|---|
| Automatic | Stable releases while you run a stable version, betas too while you run a beta. Right for almost everyone. |
| Stable releases only | Only stable releases, even while you run a beta. |
| Including betas | Stable releases and betas. |
| Off | Nothing: the plugin makes no connection to GitHub at all. |

Notifications need Domoticz 2026.1 or newer; older versions only get the log line. A check that
fails (for example, no internet) is retried a day later and only shows up at Debug Level Basic or
Verbose. What the check sends is described under [Security](security.md#what-the-plugin-connects-to).

## Harvi Names (optional)

Four optional serial/name slots let you give a harvi a friendly, restart-proof name instead of
its default `Harvi <serial>`. All eight fields are optional and blank by default.

| Setting | Type | What it does |
|---|---|---|
| Harvi 1 serial | text, optional | Serial number of a harvi, copied from its auto-created device name. |
| Harvi 1 name | text, optional | Friendly name to use for that harvi instead of `Harvi <serial>`. |
| Harvi 2 serial / name | text, optional | Same, for a second harvi. |
| Harvi 3 serial / name | text, optional | Same, for a third harvi. |
| Harvi 4 serial / name | text, optional | Same, for a fourth harvi. |

!!! tip "You usually don't need these"
    The simplest way to name a harvi is to rename the auto-created `Harvi <serial>` device
    directly in Domoticz; the plugin never overwrites a name you've set. Use the Harvi Names
    slots instead only if you want the name to survive deleting and recreating the device. See
    [Monitoring devices](devices.md#per-harvi-devices-unit-20-and-up) for details.

!!! note "Settings changes restart the plugin"
    Saving hardware settings restarts the plugin's connection to Domoticz. As part of that
    restart, it checks the current Allow Control setting and shows or hides the charger control
    devices to match. Expect a short gap in polling right after you save.
