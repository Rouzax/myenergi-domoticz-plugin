# Troubleshooting / FAQ

Entries are grouped by what you actually see happening in Domoticz, not by which part of the
plugin caused it.

## No devices appear at all

1. Check **Setup > Settings** (or the Hardware page, depending on your Domoticz version) and
   make sure **Accept new Hardware Devices** is enabled. Domoticz silently drops new devices from
   a hardware plugin if this is off.
2. Check the Domoticz log for a myenergi discovery error. Set **Debug Level** to Basic or
   Verbose on the hardware settings, save, and watch the log for the next poll.
3. Double-check the **Hub Serial Number** and **API Key**. A `401 Unauthorized` in the log means
   the API key is wrong, was regenerated in the myenergi app without updating Domoticz, or does
   not belong to the hub serial you entered.
4. Confirm the Domoticz host has outbound internet access. The plugin needs to reach
   `director.myenergi.net`; there is no local, network-only fallback.

See also [Installation](install.md) for the full setup sequence.

## Devices stopped updating after working fine

- Check the log at Basic or Verbose debug level for repeated connection failures. The plugin
  waits longer between each retry (starting at 20 seconds and doubling up to a maximum of 15
  minutes) rather than hammering myenergi's cloud with requests, so a short outage can take a few
  minutes to recover from on its own.
- A `401 Unauthorized` error in the log (the API key was rejected) means the key was invalidated,
  for example because you generated a new one in the myenergi app. Update the **API Key** field
  with the current key.

## Control devices (units 12-18) are missing

- **Allow Control** is off. Control devices only exist when this setting is turned on; see
  [Charger control](control.md). With it off, this is expected, not a bug.
- You just turned Allow Control on. Saving hardware settings restarts the plugin, which creates
  the control devices right away, but this still takes a few seconds. If they still aren't there
  after a minute, check the log.
- The plugin has not seen a zappi respond yet. Control devices are created once the plugin has a
  successful status read from your zappi; if the hub or zappi is unreachable, both monitoring and
  control device creation are affected the same way (see "No devices appear at all" above).

## Home Consumption shows 0

Home Consumption is **worked out**, not measured directly: generation + grid import − grid export
− EV charging. It is intentionally never shown below zero, and can genuinely read 0 for a moment,
particularly around export-only periods when the calculation works out at or below zero. This is
expected behaviour, not a bug. See [How it works](internals.md#live-power) for the exact formula.

The myenergi app works out house consumption the same way: from generation and grid flow, minus
what the devices used for charging, rather than measuring it with a separate house meter. Brief 0
readings around export-only moments are expected there too, not just in this plugin.

## A kWh counter looks wrong after a restart, or after installing the plugin

- Counters **do** start low, near zero, on a fresh install, and this is expected, not a bug. The
  plugin has no way to import your myenergi device's full history, and would not want to even if
  it could, since dropping a large historical total into a Domoticz counter in one go would put a
  spike in your charts. Instead, on install the plugin works out a starting point from the
  device's current value (zero on a brand-new device) and today's energy so far, never letting
  that starting point go below zero, then builds forward from myenergi's own minute-by-minute
  history. In practice a fresh install starts near today's accumulated energy and climbs from
  there. This is a one-time thing at install: it is not something that runs every time the
  plugin restarts. See [Starting from zero on a new
  install](internals.md#starting-from-zero-on-a-new-install).
- Counters never count backwards, and are capped by an absolute ceiling (derived from the **Max
  System Power (kW)** setting) that rejects only a genuinely corrupt reading. A legitimate large
  increase, such as a mid-day install or catching up after downtime, is allowed through so the
  counter reaches the correct total. If a reading is rejected the counter keeps its previous value
  and retries on the next refresh; this is rare and is written to the plugin log.
- If Domoticz was offline for a while after already running successfully, the plugin catches up
  automatically on the next counter refresh, backfilling up to **14 days** of missed history.
  This is a catch-up mechanism only, not something that looks back through your myenergi history
  when you first install the plugin; in normal day-to-day running you will not see any backfill
  happen, and that is expected. Gaps beyond 14 days are logged as an error and are not recovered
  automatically.
- If a counter still looks permanently wrong (for example, after an error about backfill being
  cut off), the only way to force a clean restart of the counters is to delete the hardware in
  Domoticz and add it again. This clears the plugin's saved data, and every counter starts fresh
  from the device's live values on the next poll, the same as a new install.

## How do I name a harvi?

Rename the auto-created `Harvi <serial>` device directly in Domoticz, matching it to the right
inverter or circuit by its live watts. The plugin never overwrites a name you set this way. See
[Naming a harvi](devices.md#naming-a-harvi) for the alternative Harvi Names settings, which
survive deleting and recreating the device.

## Can I use this without an internet connection, or with the myenergi local API?

No. myenergi hardware does not expose a documented, supported local API. This plugin talks only
to the myenergi cloud and requires outbound internet access from the Domoticz host.

## Does this plugin work with more than one hub?

Add the hardware once per hub: each hardware instance in Domoticz corresponds to one myenergi
hub serial and its zappi and harvis. Multiple hubs need multiple hardware instances.

## See also

- [Security](security.md) if the concern is about the API key rather than device behavior.
- [Settings](settings.md) for every configurable value mentioned above.
