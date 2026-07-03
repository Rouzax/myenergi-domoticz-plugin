# How it works

This page explains where the numbers on each device come from. You do not need to read it to
use the plugin, but it is useful if a value looks surprising.

## Live power

On every poll (the **Live Poll Interval** setting), the plugin fetches the zappi's current
status from the myenergi cloud and derives the power split shown on the [monitoring
devices](devices.md):

- **Solar Total** power = the generation reading from your inverters, never shown below zero.
- **EV Charging** power = the charging (diversion) reading reported by the zappi.
- **Grid Import** power = the grid reading when it is positive, meaning you are drawing from the
  grid, never shown below zero.
- **Grid Export** power = the grid reading when it is negative, meaning you are feeding power
  back to the grid, never shown below zero.
- **Home Consumption** power = generation + grid reading − EV charging power, never shown below
  zero. In plain terms: what was generated, plus what was drawn from the grid (or minus what was
  sent to the grid), minus what went to the car, is what the rest of the house used.

Because Home Consumption is worked out by combining several live readings, it can briefly show 0
even when you would expect a small positive number, if the underlying readings do not line up
exactly at that instant. The device never shows a negative value.

## Cumulative kWh counters

Solar Total, Home Consumption, EV Charging, Grid Import, and Grid Export also carry a running
kWh counter, refreshed on the schedule set by **Counter Refresh (every N live polls)**.

The counters are **not** a running total the plugin keeps by adding up its own live power
readings as it goes. Instead, on every counter refresh, the plugin fetches the whole day's
minute-by-minute energy history straight from myenergi and recalculates each counter as:

```
counter = starting point for the day + today's energy so far (from myenergi's own history)
```

This keeps the counters matching what the myenergi app shows, and immune to gaps: if Domoticz
was offline, restarted, or missed some polls, the next refresh still produces the correct total
for the day.

### Starting from zero on a new install

The plugin does not import your myenergi device's lifetime energy history. myenergi's cloud
service does not offer a way to fetch that history, and even if it did, dropping a large
historical total into a Domoticz counter in one go would put a spike in your charts. Instead,
counters start near zero on a fresh install and build up from there as real energy is measured.

On the very first run, the plugin works out a starting point for each counter from the device's
current value (zero on a brand-new device) and how much energy myenergi has already recorded for
today, never letting that starting point go below zero. On a brand-new device this comes out at
zero, so the counter begins at roughly today's energy so far and grows with every later refresh.
It is completely normal for a freshly installed counter to read low, or even zero, to begin with.
If you restart the plugin on an install that has already been running for a while (not a fresh
device), the same calculation lets the counter carry on smoothly from where it left off, instead
of jumping or resetting.

### Counters only ever go up, within reason

Every time a counter is about to be updated, the plugin checks two things:

- the new value is never lower than before (a counter should never count backwards), and
- the jump since the last update is never bigger than what your system could plausibly produce,
  based on the **Max System Power (kW)** setting.

If an update fails either check, the plugin skips it for that cycle and simply tries again on the
next refresh, rather than writing a bad number and putting a spike in your chart.

### Catching up after downtime (backfill)

This only matters if Domoticz, or the plugin, has been offline for one or more whole days after
already running successfully, for example because the host was switched off over a long weekend.
It is a catch-up mechanism only, not something that looks back through your myenergi history when
you first install the plugin: a fresh install always follows the "starting from zero" behaviour
above. In normal day-to-day running you will not see any backfill happen, and that is expected.

If a counter refresh finds that one or more full days were missed, the plugin fetches each
missing day's full-day total from myenergi and adds it to the counter's running total, up to
**14 days** of catch-up. Older gaps beyond 14 days are logged as an error and are permanently
skipped for that counter; recovering them means clearing the plugin's saved data, for example by
deleting the hardware in Domoticz and adding it again.

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
- [Settings](settings.md) for the poll and counter-refresh intervals, and the system power limit
  used to catch unrealistic counter jumps.
