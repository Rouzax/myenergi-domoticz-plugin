# Troubleshooting / FAQ

Entries are grouped by what you actually see, not by which module caused it.

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

- Check the log at Basic or Verbose debug level for repeated discovery failures. The plugin
  backs off and retries automatically (starting at 20 seconds, doubling up to 15 minutes) rather
  than hammering myenergi's cloud, so a transient outage can take a few minutes to recover from
  on its own.
- A `401 Unauthorized` during rediscovery means the API key was invalidated (for example, you
  rotated it in the myenergi app). Update the **API Key** field with the current key.

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

Home Consumption is **derived**, not measured directly: generation + grid import − grid export −
EV charging. It is intentionally floored at zero and can genuinely read 0 for a moment,
particularly around export-only periods when the subtraction nets out at or below zero. This is
expected behavior, not a bug. See [How it works](internals.md#live-power) for the exact formula.

## A kWh counter looks wrong after a restart, or after installing the plugin

- Counters do **not** start at zero on install. They seed from whatever the myenergi-reported
  values already show at that point, then build forward from myenergi's own per-minute history.
  See [Accumulate-from-install](internals.md#accumulate-from-install).
- Counters never decrease and never jump by an implausible amount in one refresh (bounded by the
  **Max System Power (kW)** setting). An implausible jump is held back and retried on the next
  refresh rather than applied, so a brief "stuck" value after an unusual event is expected, not a
  bug.
- If Domoticz was offline for a while, the plugin backfills up to **14 days** of missed history
  automatically on the next counter refresh. Gaps beyond 14 days are logged as an error and are
  not recovered automatically.
- If a counter's baseline still looks permanently wrong (for example, after an error about
  backfill being truncated), the only way to force a clean re-seed is to delete the hardware in
  Domoticz and add it again. This clears the plugin's saved state and every counter re-seeds from
  the device's live values on the next poll, the same as a fresh install.

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
