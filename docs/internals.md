# How it works

This page explains where the numbers on each device come from. You do not need to read it to
use the plugin, but it is useful if a value looks surprising.

## Live power

On every poll (the **Live Poll Interval** setting), the plugin fetches the zappi's current
status from the myenergi cloud and derives the power split shown on the [monitoring
devices](devices.md):

- **Solar Total** power = generation reading, floored at zero.
- **EV Charging** power = the diversion (charging) reading reported by the zappi.
- **Grid Import** power = the grid reading when it is positive (drawing from the grid), floored
  at zero.
- **Grid Export** power = the grid reading when it is negative (feeding back to the grid),
  floored at zero.
- **Home Consumption** power = generation + grid reading − EV charging power, floored at zero.
  In plain terms: what was generated, plus what was drawn from (or minus what was sent to) the
  grid, minus what went to the car, is what the rest of the house used.

Because it is a subtraction of several live readings, Home Consumption can be zero for a moment
even when it "should" be small but positive, if the underlying readings do not line up exactly
at that instant. The device never shows a negative value.

## Cumulative kWh counters

Solar Total, Home Consumption, EV Charging, Grid Import, and Grid Export also carry a cumulative
energy counter, refreshed on the schedule set by **Counter Refresh (every N live polls)**.

The counters are **not** a running total the plugin keeps by adding up its own live power
samples. Instead, on every counter refresh, the plugin fetches the day's full per-minute energy
history straight from myenergi and recalculates each counter as:

```
counter = base + today's accumulated energy (from myenergi's own history)
```

This keeps the counters matching what the myenergi app shows, and immune to gaps: if Domoticz
was offline, restarted, or missed some polls, the next refresh still produces the correct total
for the day.

### Accumulate-from-install

The plugin does not import a myenergi device's lifetime energy total. There is no way to fetch
one from the API, and even if there were, dropping a large lifetime figure into a Domoticz
counter in one step would spike the charts. Instead, counters start low, at or near zero, on a
fresh install and build forward from there.

On first run, the plugin seeds each counter's internal baseline as
`max(0, current Domoticz device value − today's energy so far)`. On a brand-new device the
current value is zero, so the baseline clamps to zero and the counter starts at roughly today's
accumulated energy, then grows on each subsequent refresh. It is normal for a freshly installed
counter to read low, or even zero, at first. On a restart of an existing install (not a fresh
device), the same formula lets the counter continue smoothly from where it already was instead of
jumping or resetting.

### Monotonic and clamped

Every counter update is clamped so it can:

- never decrease, and
- never jump by an implausible amount in one refresh, based on the **Max System Power (kW)**
  setting.

An update that fails either check is discarded for that cycle and retried on the next refresh,
rather than corrupting the counter or spiking a chart.

### Backfill on gaps

If a counter refresh finds that one or more full days were missed (for example, Domoticz was
down over a weekend), the plugin fetches each missing day's full-day total from myenergi and
folds it into the counter's baseline, up to **14 days** of backfill. Older gaps beyond 14 days
are logged as an error and permanently skipped for that counter; recovering them requires
resetting the plugin's saved state.

## The "Return" device type

**Solar Total** and **Grid Export** are created with Domoticz's **Return** meter type. This is
purely cosmetic: it changes the device's icon and its Type label in the Utility device list. It
does **not** feed Domoticz's Energy Dashboard, which only performs generation/usage splitting for
an officially recognized P1 smart meter. If you delete either device, the plugin recreates it
with the Return type set automatically on the next poll.

## Per-harvi power versus Solar Total

Each harvi reports to the hub wirelessly on its own schedule, independently of the zappi's own
generation reading that feeds Solar Total. At any single instant, the sum of the per-harvi power
devices may therefore not exactly equal Solar Total. This is expected timing behavior between
independent samples, not a plugin error, and it evens out over time.

## See also

- [Monitoring devices](devices.md) for what each device shows.
- [Settings](settings.md) for the poll and counter-refresh intervals, and the system power
  ceiling used for clamping.
