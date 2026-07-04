# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Create devices in ascending unit order on a fresh install, so the logical layout (monitoring
  1-11, control 12-18, harvi 20+) also matches Domoticz's creation-ordered device list. Previously
  control was created on start (before the monitoring devices existed) and monitoring/harvi were
  emitted out of unit order, so devices did not sit next to each other. Existing installs are
  unaffected (devices are only created once).

## [1.0.2] - 2026-07-03

### Fixed

- Respect a manual hide of a control device. The control units (Charge Mode, Boost, Boost kWh,
  Boost Ready-By, Min Green, Charger Lock State) are now shown or hidden only once on the
  Allow Control on/off transition, instead of being re-forced visible on every heartbeat, so
  unchecking "Used" on a control device (for example Charger Lock State) now sticks.
- Re-translate control device names on a language switch. Control names (including the input-only
  Boost kWh and Boost Ready-By, which are not re-emitted after creation) now follow the Language
  setting, matching the monitoring devices. User-renamed control devices are still left untouched.

## [1.0.1] - 2026-07-03

### Fixed

- Point the plugin manifest `externallink` at the repository instead of the author profile, so the
  Domoticz plugin managers can match an install to its registry entry.

## [1.0.0] - 2026-07-03

Initial public release.

### Added

- **Monitoring devices** (read-only): Solar Total, Home Consumption, EV Charging, Zappi Mode,
  Charge Status, Plug Status, Charge Added, Grid Voltage, Grid Frequency, Grid Import, Grid Export.
- **Real cumulative kWh counters** rebuilt from myenergi's per-minute history: monotonic,
  accumulate-from-install, restart-proof, with up to 14 days of backfill.
- **Per-inverter (harvi) power** devices, one per harvi, auto-styled for generation (sun icon) vs
  battery/load (signed), with optional friendly-name slots.
- **Opt-in charger control** (`Allow Control`, off by default): Charge Mode and Boost selectors,
  Boost kWh + Ready-By and Eco+ Min Green as dropdown menus, and a read-only Charger Lock State.
  The control surface is created and reconciled immediately on plugin start.
- **English and Nederlands** device names and status text.
- **Verbose device-lifecycle logging** (create / rename / show / hide) at the Verbose debug level.
- Documentation site (MkDocs Material, WCAG 2.1 AA) and a lean `dist` install branch.

### Security

- Charger control is off by default; the plugin is read-only until `Allow Control` is enabled.
- The API key is redacted from logs and never written to device fields.
